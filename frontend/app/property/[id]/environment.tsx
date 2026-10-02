import { useQuery } from "@tanstack/react-query";
import { Image } from "expo-image";
import { useLocalSearchParams, useRouter } from "expo-router";
import { ArrowsClockwiseIcon, CaretDownIcon, CaretUpIcon, InfoIcon, LinkIcon, MapPinIcon, ScalesIcon, SparkleIcon, WarningIcon } from "phosphor-react-native";
import { useState } from "react";
import { ActivityIndicator, Linking, Pressable, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { EnvAnalysis, EnvItem, EnvironmentResult, api, formatK, formatPct } from "@/src/api";
import { PrimaryButton } from "@/src/components/PrimaryButton";
import { ScreenHeader } from "@/src/components/ScreenHeader";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

const SOURCE_SHORT: Record<string, string> = { bdtopo: "IGN BD TOPO", osm: "OpenStreetMap", cadastre: "Cadastre", gpu: "GPU", georisques: "Géorisques", clc: "CLC 2018", alti: "RGE ALTI", ban: "BAN" };
const LEVEL: Record<string, string> = { none: "nul", low: "faible", medium: "moyen", high: "fort", info: "recensé" };

const fmtDist = (m: number) => (m >= 1000 ? `${(m / 1000).toFixed(1).replace(".", ",")} km` : `${m} m`);

export default function EnvironmentScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const [refreshing, setRefreshing] = useState(false);
  const [open, setOpen] = useState<Record<string, boolean>>({ resume: true });

  const q = useQuery({ queryKey: ["environment", id], queryFn: () => api.environment(id!), enabled: !!id, staleTime: 5 * 60_000, retry: 1 });
  const toggle = (k: string) => setOpen((o) => ({ ...o, [k]: !o[k] }));
  const refresh = async () => {
    setRefreshing(true);
    try {
      const fresh = await api.environment(id!, true);
      q.refetch();
      void fresh;
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <View style={styles.screen} testID="environment-screen">
      <ScreenHeader title="Environnement du bien" subtitle="Données publiques · distances mesurées · IA pour la synthèse" onBack={() => router.back()} />
      <ScrollView contentContainerStyle={[styles.content, { paddingBottom: insets.bottom + spacing.xl }]}>
        {q.isLoading || refreshing ? (
          <View style={styles.loading} testID="environment-loading">
            <ActivityIndicator color={colors.brandPrimary} />
            <Text style={styles.loadingTitle}>Analyse en cours (environ 30 secondes)</Text>
            <Text style={styles.hint}>Géocodage BAN · parcelle (Cadastre) · bâtiments, routes, eau, végétation (IGN BD TOPO) · altimétrie · occupation du sol · urbanisme (GPU) · risques (Géorisques) · services (OpenStreetMap) · rédaction du rapport</Text>
            <View style={styles.skelMap} />
            {[0, 1, 2].map((i) => <View key={i} style={styles.skelCard} />)}
          </View>
        ) : q.isError || !q.data ? (
          <View style={styles.card} testID="environment-error">
            <WarningIcon size={20} color={colors.error} weight="fill" />
            <Text style={styles.p}>{(q.error as Error)?.message ?? "Analyse indisponible"}</Text>
            <PrimaryButton title="Réessayer" variant="secondary" onPress={() => q.refetch()} testID="environment-retry" />
          </View>
        ) : (
          <Body data={q.data} open={open} toggle={toggle} onRefresh={refresh} onEstimation={() => router.push(`/property/${id}`)} />
        )}
      </ScrollView>
    </View>
  );
}

function Body({ data, open, toggle, onRefresh, onEstimation }: { data: EnvironmentResult; open: Record<string, boolean>; toggle: (k: string) => void; onRefresh: () => void; onEstimation: () => void }) {
  const styles = useStyles();
  const { colors } = useTheme();
  const a = data.analysis;
  const r = data.report;
  const sections = r?.sections ?? null;
  const order = r?.order ?? [];
  const envPct = data.estimation_adjustments.reduce((s, x) => s + x.pct, 0);
  const unbuilt = a.nearby_parcels.filter((p) => !p.built);

  const facts: Record<string, React.ReactNode> = {
    immediat: <Facts items={[`${a.density.within_50m} bâtiment(s) dans un rayon de 50 m, le plus proche à ${a.density.nearest_m ?? "—"} m`, ...a.neighbours.slice(0, 4).map((n) => `Bâtiment ${n.usage?.toLowerCase() ?? n.nature?.toLowerCase() ?? ""} à ${n.distance_m} m${n.etages ? ` · ${n.etages} niveau(x)` : ""}${n.hauteur_m ? ` · ${n.hauteur_m} m` : ""}`), ...a.roads.filter((x) => x.distance_m <= 50).slice(0, 3).map((x) => `${x.name || x.nature} (${x.importance_label}) à ${x.distance_m} m`)]} source="IGN BD TOPO · calculé" />,
    voisinage: <Facts items={[`Densité bâtie ${a.density.built_ratio_pct} % dans 250 m (${a.density.buildings} bâtiments)`, ...a.rings.slice(1, 2).map((rg) => `${rg.label} : ${rg.services} service(s), ${rg.transport} arrêt(s), ${rg.green} espace(s) vert(s), ${rg.industrial} activité(s)/parking(s)`)]} source="calculé à partir de BD TOPO / OSM" />,
    nature: <List items={[...a.green_spaces.slice(0, 6), ...a.water.slice(0, 4)]} />,
    mobilite: <List items={[...a.roads.slice(0, 6), ...a.railways.slice(0, 2), ...a.transport.slice(0, 5)]} />,
    services: <List items={a.services.slice(0, 14)} />,
    nuisances: <List items={a.nuisances.slice(0, 10)} />,
    terrain: <Facts items={[a.terrain.altitude_m != null ? `Altitude ${a.terrain.altitude_m} m` : "Altitude non disponible", a.terrain.slope_pct != null ? `Pente ${String(a.terrain.slope_pct).replace(".", ",")} % · ${a.terrain.aspect}` : "Pente non disponible", a.terrain.landcover ? `Occupation du sol : ${a.terrain.landcover.label} (${a.terrain.landcover.precision})` : "Occupation du sol non disponible", a.terrain.nearest_water_m != null ? `Eau la plus proche à ${fmtDist(a.terrain.nearest_water_m)}` : "Aucun cours d'eau dans 1 km", a.terrain.nearest_forest_m != null ? `Bois/forêt le plus proche à ${fmtDist(a.terrain.nearest_forest_m)}` : "Aucun boisement dans 1 km", a.terrain.vegetation_ratio_250m_pct != null ? `Végétation : ${a.terrain.vegetation_ratio_250m_pct} % de la surface dans 250 m` : ""]} source="IGN RGE ALTI · CLC · BD TOPO · calculé" />,
    risques: a.risks ? <Facts items={[...a.risks.at_address.map((x) => `À l'adresse : ${x.label} — ${LEVEL[x.level] ?? x.level}${x.detail ? ` (${x.detail})` : ""}`), a.risks.at_address.length === 0 ? "Aucun risque recensé à l'adresse même" : "", ...a.risks.commune_only.slice(0, 6).map((x) => `Échelle communale : ${x.label}`), a.risks.argile ? `Argiles : ${a.risks.argile.label}` : "", a.risks.radon ? `Radon : ${a.risks.radon.label}` : "", a.risks.catnat?.count ? `${a.risks.catnat.count} arrêté(s) de catastrophe naturelle sur la commune` : ""]} source="Géorisques (officiel)" url={a.risks.source_url} /> : <Facts items={["Géorisques n'a pas pu être consulté : information indisponible."]} source="indisponible" />,
    urbanisme: a.urbanism ? <Facts items={[...a.urbanism.zones.map((z) => `Zone ${z.libelle ?? "?"}${z.typezone ? ` (type ${z.typezone})` : ""}${z.libelong ? ` — ${z.libelong}` : ""}${z.reglement ? ` · règlement : ${z.reglement}` : ""}`), ...a.urbanism.servitudes.slice(0, 5).map((s) => `Servitude : ${s.libelle}`), ...a.urbanism.prescriptions.slice(0, 5).map((s) => `Prescription : ${s.libelle}`), ...a.urbanism.infos.slice(0, 4).map((s) => `Information : ${s.libelle}`), a.urbanism.notice]} source="Géoportail de l'Urbanisme (officiel)" url={a.urbanism.documents[0]?.url} /> : <Facts items={["Le Géoportail de l'Urbanisme n'a pas répondu : zonage indisponible."]} source="indisponible" />,
    evolution: <Facts items={unbuilt.length ? unbuilt.slice(0, 6).map((p) => `Parcelle ${p.section} ${p.numero} non bâtie · ${p.surface_m2} m² · à ${p.distance_m} m${p.adjacent ? " · mitoyenne" : ""}`) : ["Aucune parcelle non bâtie identifiée dans l'emprise analysée (≈120 m)."]} source="Cadastre × BD TOPO · calculé" />,
  };

  return (
    <>
      <View style={styles.mapWrap} testID="environment-map">
        <Image source={{ uri: api.environmentMapUrl(a.coordinates.lon, a.coordinates.lat) }} style={styles.map} contentFit="cover" transition={300} />
        <View style={styles.pin}><MapPinIcon size={30} color={colors.error} weight="fill" /></View>
        <Text style={styles.mapCredit}>Orthophoto & parcellaire © IGN — {a.parcel ? `parcelle ${a.parcel.section} ${a.parcel.numero}${a.parcel.contenance_m2 ? ` · ${a.parcel.contenance_m2} m²` : ""}` : "parcelle non identifiée"}</Text>
      </View>
      <Text style={styles.addr} testID="environment-address">{a.address.label ?? a.address.input ?? `Point ${a.coordinates.lat.toFixed(5)}, ${a.coordinates.lon.toFixed(5)}`}</Text>

      {/* Impact estimation */}
      <View style={styles.impact} testID="environment-impact">
        <View style={styles.rowHead}>
          <ScalesIcon size={20} color={colors.brandPrimary} weight="duotone" />
          <Text style={styles.h3}>Impact sur l’estimation</Text>
          <Text style={[styles.impactPct, { color: envPct < 0 ? colors.error : envPct > 0 ? colors.success : colors.muted }]} testID="environment-impact-pct">{data.estimation_adjustments.length ? formatPct(envPct, 1) : "0 %"}</Text>
        </View>
        {data.estimation_adjustments.length ? data.estimation_adjustments.map((x) => (
          <View key={x.key} style={styles.lineRow}>
            <Text style={styles.lineLabel}>{x.label}</Text>
            <Text style={[styles.lineValue, { color: x.amount < 0 ? colors.error : colors.success }]}>{formatPct(x.pct, 1)} ({x.amount > 0 ? "+" : "−"}{formatK(Math.abs(x.amount))})</Text>
          </View>
        )) : <Text style={styles.hint}>Aucun facteur de micro-localisation mesuré ne justifie d’ajustement.</Text>}
        <Text style={styles.hint}>Ajustements indicatifs fondés uniquement sur des distances mesurées (bornés à −6 % / +4 %) ; les ventes comparables reflètent déjà le niveau de prix du quartier. Ils sont intégrés à la valeur affichée sur la fiche du bien.</Text>
        <PrimaryButton title="Voir l’estimation mise à jour" variant="secondary" onPress={onEstimation} testID="environment-see-estimation" />
      </View>

      {r?.error ? (
        <View style={styles.warn}><WarningIcon size={18} color={colors.warning} weight="fill" /><Text style={styles.warnText}>{r.error} Les données mesurées ci-dessous restent disponibles.</Text></View>
      ) : null}

      {/* Sections */}
      {(order.length ? order : Object.keys(facts)).map((k) => {
        const text = sections?.[k];
        const title = r?.titles?.[k] ?? k;
        const isOpen = !!open[k];
        return (
          <View key={k} style={styles.card} testID={`env-section-${k}`}>
            <Pressable accessibilityRole="button" onPress={() => toggle(k)} style={styles.rowHead} testID={`env-toggle-${k}`}>
              <Text style={[styles.h3, { flex: 1 }]}>{title}</Text>
              {isOpen ? <CaretUpIcon size={16} color={colors.muted} /> : <CaretDownIcon size={16} color={colors.muted} />}
            </Pressable>
            {isOpen ? (
              <>
                {Array.isArray(text) ? (
                  <View style={{ gap: 6 }}>{text.map((t, i) => <Text key={i} style={styles.p}>• {t}</Text>)}</View>
                ) : text ? (
                  <View style={styles.ai}>
                    <View style={styles.aiHead}><SparkleIcon size={14} color={colors.brandPrimary} weight="fill" /><Text style={styles.aiLabel}>Synthèse IA (interprétation des données ci-dessous)</Text></View>
                    <Text style={styles.p}>{text}</Text>
                  </View>
                ) : null}
                {facts[k]}
              </>
            ) : null}
          </View>
        );
      })}

      {/* Fiabilité */}
      <View style={styles.card} testID="environment-reliability">
        <View style={styles.rowHead}><InfoIcon size={18} color={colors.muted} /><Text style={styles.h3}>Comment lire ce rapport</Text></View>
        <Text style={styles.p}><Text style={styles.bold}>Donnée officielle</Text> : issue d’une source publique (BAN, IGN, Cadastre, GPU, Géorisques). <Text style={styles.bold}>Donnée calculée</Text> : distance à vol d’oiseau, densité, pente, calculées par l’application. <Text style={styles.bold}>Synthèse IA</Text> : interprétation, jamais une mesure. <Text style={styles.bold}>Indisponible</Text> : la source n’a pas répondu ou ne couvre pas ce point.</Text>
        {a.limits.map((l, i) => <Text key={i} style={styles.hint}>• {l}</Text>)}
        {a.unavailable.length ? <Text style={[styles.hint, { color: colors.warning }]}>Sources indisponibles lors de cette analyse : {a.unavailable.join(", ")}.</Text> : null}
        {r?.disclaimer ? <Text style={styles.hint}>{r.disclaimer}</Text> : null}
      </View>

      {/* Sources */}
      <View style={styles.card} testID="environment-sources">
        <Text style={styles.h3}>Sources consultées</Text>
        {dedupeSources(a).map((s) => (
          <Pressable key={s.id} accessibilityRole="link" onPress={() => Linking.openURL(s.doc_url)} style={styles.srcRow}>
            <LinkIcon size={14} color={colors.brandPrimary} />
            <View style={{ flex: 1 }}>
              <Text style={styles.srcName}>{s.name}</Text>
              <Text style={styles.hint}>{s.kind === "official" ? "Source officielle" : "Données ouvertes"} · {s.licence} · consultée le {new Date(s.fetched_at).toLocaleDateString("fr-FR")}{s.status !== "ok" ? ` · ${s.status === "partial" ? "réponse partielle" : "indisponible"}` : ""}</Text>
            </View>
          </Pressable>
        ))}
        <Text style={styles.hint}>Analyse générée le {new Date(a.generated_at).toLocaleString("fr-FR")}{data.cached ? " (mise en cache 30 jours)" : ""}.</Text>
        <Pressable accessibilityRole="button" onPress={onRefresh} style={styles.refreshRow} testID="environment-refresh">
          <ArrowsClockwiseIcon size={16} color={colors.brandPrimary} />
          <Text style={styles.link}>Relancer l’analyse avec des données fraîches</Text>
        </Pressable>
      </View>
    </>
  );
}

function dedupeSources(a: EnvAnalysis) {
  const seen = new Map<string, EnvAnalysis["sources"][number]>();
  for (const s of a.sources) {
    const prev = seen.get(s.id);
    if (!prev || (prev.status === "ok" && s.status !== "ok")) seen.set(s.id, s);
  }
  return [...seen.values()];
}

function Facts({ items, source, url }: { items: string[]; source: string; url?: string | null }) {
  const styles = useStyles();
  const list = items.filter(Boolean);
  return (
    <View style={styles.facts}>
      {list.map((t, i) => <Text key={i} style={styles.fact}>• {t}</Text>)}
      <Pressable disabled={!url} onPress={() => url && Linking.openURL(url)}><Text style={styles.factSrc}>Source : {source}{url ? " ↗" : ""}</Text></Pressable>
    </View>
  );
}

function List({ items }: { items: EnvItem[] }) {
  const styles = useStyles();
  if (!items.length) return <Text style={styles.hint}>Aucun élément de ce type dans les rayons analysés (sources consultées).</Text>;
  return (
    <View style={styles.facts}>
      {items.map((it, i) => (
        <View key={i} style={styles.itemRow}>
          <Text style={styles.fact} numberOfLines={2}>
            {it.label ?? it.name ?? it.nature ?? it.type ?? "Élément"}
            {it.importance_label ? ` · ${it.importance_label}` : it.type && it.name ? ` · ${it.type.replace(/^[a-z_]+=/, "")}` : ""}
            {it.direction && it.direction !== "sur place" ? ` · ${it.direction}` : ""}
          </Text>
          <View style={styles.distWrap}>
            <Text style={styles.dist}>{fmtDist(it.distance_m)}</Text>
            <Text style={styles.srcTag}>{SOURCE_SHORT[it.source] ?? it.source}</Text>
          </View>
        </View>
      ))}
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  screen: { flex: 1, backgroundColor: colors.surface },
  content: { padding: spacing.lg, gap: spacing.lg },
  loading: { gap: spacing.md, alignItems: "stretch" },
  loadingTitle: { fontFamily: fonts.semibold, fontSize: 15, color: colors.onSurface, textAlign: "center" },
  skelMap: { height: 200, borderRadius: radius.lg, backgroundColor: colors.skeleton },
  skelCard: { height: 96, borderRadius: radius.lg, backgroundColor: colors.skeleton },
  mapWrap: { borderRadius: radius.lg, overflow: "hidden", backgroundColor: colors.skeleton },
  map: { width: "100%", aspectRatio: 1.6 },
  pin: { position: "absolute", left: "50%", top: "50%", marginLeft: -15, marginTop: -30 },
  mapCredit: { fontFamily: fonts.regular, fontSize: 11, color: colors.onSurfaceTertiary, padding: spacing.sm, backgroundColor: colors.surfaceSecondary },
  addr: { fontFamily: fonts.semibold, fontSize: 15, color: colors.onSurface },
  impact: { backgroundColor: colors.brandTertiary, borderRadius: radius.lg, padding: spacing.lg, gap: spacing.sm },
  impactPct: { fontFamily: fonts.bold, fontSize: 20, fontVariant: ["tabular-nums"] },
  card: { backgroundColor: colors.surfaceSecondary, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, padding: spacing.lg, gap: spacing.md },
  rowHead: { flexDirection: "row", alignItems: "center", gap: spacing.sm, minHeight: 32 },
  h3: { fontFamily: fonts.semibold, fontSize: 16, color: colors.onSurfaceSecondary, flexShrink: 1 },
  p: { fontFamily: fonts.regular, fontSize: 14, lineHeight: 21, color: colors.onSurfaceTertiary },
  bold: { fontFamily: fonts.semibold, color: colors.onSurfaceSecondary },
  hint: { fontFamily: fonts.regular, fontSize: 12, lineHeight: 17, color: colors.muted },
  link: { fontFamily: fonts.medium, fontSize: 14, color: colors.brandPrimary },
  ai: { backgroundColor: colors.surface, borderRadius: radius.md, padding: spacing.md, gap: 6, borderLeftWidth: 3, borderLeftColor: colors.brandPrimary },
  aiHead: { flexDirection: "row", alignItems: "center", gap: 6 },
  aiLabel: { fontFamily: fonts.medium, fontSize: 11, color: colors.brandPrimary, textTransform: "uppercase", letterSpacing: 0.5 },
  facts: { gap: 6 },
  fact: { flex: 1, fontFamily: fonts.regular, fontSize: 13, lineHeight: 19, color: colors.onSurfaceSecondary },
  factSrc: { fontFamily: fonts.medium, fontSize: 11, color: colors.muted, marginTop: 2 },
  itemRow: { flexDirection: "row", alignItems: "center", gap: spacing.md, paddingVertical: 2 },
  distWrap: { alignItems: "flex-end" },
  dist: { fontFamily: fonts.semibold, fontSize: 13, color: colors.onSurfaceSecondary, fontVariant: ["tabular-nums"] },
  srcTag: { fontFamily: fonts.regular, fontSize: 10, color: colors.muted },
  lineRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: spacing.md },
  lineLabel: { flex: 1, fontFamily: fonts.regular, fontSize: 13, color: colors.onBrandTertiary },
  lineValue: { fontFamily: fonts.semibold, fontSize: 13, fontVariant: ["tabular-nums"] },
  warn: { flexDirection: "row", gap: spacing.md, alignItems: "center", backgroundColor: colors.warningSoft, borderRadius: radius.md, padding: spacing.lg },
  warnText: { flex: 1, fontFamily: fonts.medium, fontSize: 13, lineHeight: 19, color: colors.warning },
  srcRow: { flexDirection: "row", alignItems: "flex-start", gap: spacing.sm, minHeight: 40 },
  srcName: { fontFamily: fonts.medium, fontSize: 13, color: colors.onSurfaceSecondary },
  refreshRow: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: spacing.sm, minHeight: 44 },
}));
