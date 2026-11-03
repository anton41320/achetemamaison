import { useQuery } from "@tanstack/react-query";
import { Image } from "expo-image";
import { Link } from "expo-router";
import { CaretRightIcon, MagnifyingGlassIcon } from "phosphor-react-native";
import { useMemo, useState } from "react";
import { ActivityIndicator, Pressable, Text, TextInput, View } from "react-native";

import { PublicCommune, PublicDept, PublicPriceStat, api, formatEuro, formatInt } from "@/src/api";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";
import { FreeEstimate } from "@/src/web/FreeEstimate";
import { PublicPage } from "@/src/web/PublicPage";
import { useBreakpoint } from "@/src/web/useBreakpoint";

const MAP_IMG = require("../../assets/web/map-data.jpg");
const norm = (v: string) => v.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

const pm2 = (s: PublicPriceStat | null | undefined) => (s ? `${formatInt(s.median_pm2)} €/m²` : "—");

function Stat({ label, stat, testID }: { label: string; stat: PublicPriceStat | null | undefined; testID?: string }) {
  const styles = useStyles();
  return (
    <View style={styles.stat} testID={testID}>
      <Text style={styles.statLabel}>{label}</Text>
      <Text style={styles.statValue}>{pm2(stat)}</Text>
      {stat ? <Text style={styles.statSub}>Prix médian {formatEuro(stat.median_price)} · {stat.median_surface} m² · {formatInt(stat.count)} ventes</Text> : <Text style={styles.statSub}>Pas assez de ventes</Text>}
    </View>
  );
}

function Loading() {
  const { colors } = useTheme();
  return <ActivityIndicator color={colors.brandPrimary} style={{ marginVertical: spacing.xl }} />;
}

/** Tableau responsive : lignes cliquables, barres de prix proportionnelles, filtre par nom. */
function PriceTable<T extends { key: string; href: string; name: string; sub?: string; maison: PublicPriceStat | null; appartement: PublicPriceStat | null; count: number }>({ rows, testID, searchable }: { rows: T[]; testID: string; searchable?: boolean }) {
  const styles = useStyles();
  const { colors } = useTheme();
  const { isTablet } = useBreakpoint();
  const [q, setQ] = useState("");
  const filtered = useMemo(() => (q.trim() ? rows.filter((r) => norm(`${r.name} ${r.sub ?? ""}`).includes(norm(q.trim()))) : rows), [rows, q]);
  const max = useMemo(() => Math.max(1, ...rows.map((r) => Math.max(r.maison?.median_pm2 ?? 0, r.appartement?.median_pm2 ?? 0))), [rows]);
  const bar = (stat: PublicPriceStat | null, color: string) => (
    <View style={styles.barWrap}>
      <View style={styles.barTrack}><View style={[styles.barFill, { width: `${stat ? Math.max(4, Math.round((stat.median_pm2 / max) * 100)) : 0}%`, backgroundColor: color }]} /></View>
      <Text style={styles.num}>{pm2(stat)}</Text>
    </View>
  );
  return (
    <View style={{ gap: spacing.sm }}>
      {searchable ? (
        <View style={styles.search}>
          <MagnifyingGlassIcon size={18} color={colors.muted} />
          <TextInput value={q} onChangeText={setQ} placeholder="Rechercher un département, une commune ou un code postal…" placeholderTextColor={colors.muted}
            style={styles.searchInput} autoCorrect={false} testID={`${testID}-search`} />
          {q ? <Pressable onPress={() => setQ("")} hitSlop={8} accessibilityLabel="Effacer"><Text style={styles.clear}>Effacer</Text></Pressable> : null}
        </View>
      ) : null}
      <View style={styles.table} testID={testID}>
        <View style={[styles.tr, styles.th]}>
          <Text style={[styles.td, styles.tdName, styles.thText]}>Commune / département</Text>
          <Text style={[styles.td, styles.thText, styles.thRight]}>Maison €/m²</Text>
          <Text style={[styles.td, styles.thText, styles.thRight]}>Appartement €/m²</Text>
          {isTablet ? <Text style={[styles.tdSmall, styles.thText, styles.thRight]}>Ventes</Text> : null}
          <View style={styles.tdChevron} />
        </View>
        {filtered.length === 0 ? <Text style={styles.empty}>Aucun résultat pour « {q} ».</Text> : null}
        {filtered.map((r, i) => (
          <View key={r.key} style={i % 2 === 1 ? styles.trAlt : undefined}>
            <Link href={r.href as any} asChild>
              <Pressable accessibilityRole="link" style={styles.tr} testID={`price-row-${r.key}`}>
                <View style={[styles.td, styles.tdName]}>
                  <Text style={styles.name}>{r.name}</Text>
                  {r.sub ? <Text style={styles.sub}>{r.sub}</Text> : null}
                </View>
                <View style={styles.td}>{bar(r.maison, colors.brandPrimary)}</View>
                <View style={styles.td}>{bar(r.appartement, colors.brandSecondary)}</View>
                {isTablet ? <Text style={[styles.tdSmall, styles.num, styles.sub]}>{formatInt(r.count)}</Text> : null}
                <View style={styles.tdChevron}><CaretRightIcon size={16} color={colors.muted} /></View>
              </Pressable>
            </Link>
          </View>
        ))}
      </View>
      <View style={styles.legendRow}>
        <View style={[styles.legendDot, { backgroundColor: colors.brandPrimary }]} /><Text style={styles.sub}>Maisons</Text>
        <View style={[styles.legendDot, { backgroundColor: colors.brandSecondary, marginLeft: spacing.md }]} /><Text style={styles.sub}>Appartements</Text>
        <Text style={[styles.sub, { marginLeft: "auto" }]}>Barres proportionnelles au prix médian le plus élevé du tableau</Text>
      </View>
    </View>
  );
}

export function DeptsPage() {
  const styles = useStyles();
  const { isDesktop } = useBreakpoint();
  const q = useQuery({ queryKey: ["public-depts"], queryFn: api.publicDepts, staleTime: 3600_000 });
  const rows = (q.data?.departements ?? []).map((d: PublicDept) => ({ key: d.code, href: `/prix-immobilier/${d.code}`, name: `${d.name} (${d.code})`, maison: d.maison, appartement: d.appartement, count: d.count }));
  return (
    <PublicPage title="Prix immobilier par département et par commune (ventes réelles DVF)" description="Prix médian au m² des maisons et appartements dans chaque département et commune de France, calculé sur les ventes réelles des 3 dernières années (DVF)." path="/prix-immobilier" testID="prices-depts">
      <View style={[styles.hero, isDesktop && { flexDirection: "row", alignItems: "center" }]}>
        <View style={[{ gap: spacing.md }, isDesktop && { flex: 1 }]}>
          <Text style={styles.kicker}>OBSERVATOIRE DES PRIX · DONNÉES PUBLIQUES DVF</Text>
          <Text style={styles.h1} accessibilityRole="header">Prix immobilier en France : €/m² par département et par commune</Text>
          <Text style={styles.intro}>Médianes calculées sur les ventes réelles enregistrées par les notaires et publiées par l’État (DVF){q.data ? `, millésimes ${q.data.years[0]}–${q.data.years[1]}` : ""} — pas sur les prix affichés dans les annonces. Cliquez sur un département pour voir chaque commune.</Text>
          {q.data ? (
            <View style={styles.kpis}>
              <View style={styles.kpi}><Text style={styles.kpiValue}>{formatInt(rows.length)}</Text><Text style={styles.kpiLabel}>départements</Text></View>
              <View style={styles.kpi}><Text style={styles.kpiValue}>{formatInt(rows.reduce((n, r) => n + r.count, 0))}</Text><Text style={styles.kpiLabel}>ventes analysées</Text></View>
              <View style={styles.kpi}><Text style={styles.kpiValue}>{q.data.years[0]}–{q.data.years[1]}</Text><Text style={styles.kpiLabel}>millésimes</Text></View>
            </View>
          ) : null}
        </View>
        <Image source={MAP_IMG} style={[styles.heroImage, isDesktop && { flex: 0.9 }]} contentFit="cover" accessibilityLabel="Carte des ventes réelles autour d’une adresse" />
      </View>
      {q.isLoading ? <Loading /> : <PriceTable rows={rows} testID="depts-table" searchable />}
      <FreeEstimate />
    </PublicPage>
  );
}

export function DeptPage({ dept }: { dept: string }) {
  const styles = useStyles();
  const q = useQuery({ queryKey: ["public-dept", dept], queryFn: () => api.publicDept(dept), staleTime: 3600_000, enabled: !!dept });
  const d = q.data;
  const rows = (d?.communes ?? []).map((c: PublicCommune) => ({ key: c.insee, href: `/prix-immobilier/${dept}/${c.insee}-${c.slug}`, name: c.name, sub: `${c.code_postal}${c.population ? ` · ${formatInt(c.population)} hab.` : ""}`, maison: c.maison, appartement: c.appartement, count: c.count }));
  const name = d?.name ?? "";
  return (
    <PublicPage title={d ? `Prix immobilier ${name} (${dept}) : prix au m² par commune` : "Prix immobilier par commune"} description={d ? `Prix médian au m² des maisons et appartements dans le ${name} et dans chacune de ses communes, d'après les ventes réelles DVF.` : "Prix médian au m² par commune, d'après les ventes réelles DVF."} path={d ? `/prix-immobilier/${dept}` : "/prix-immobilier"} testID="prices-dept">
      <Link href="/prix-immobilier" asChild><Pressable accessibilityRole="link"><Text style={styles.crumb}>← Tous les départements</Text></Pressable></Link>
      <Text style={styles.h1} accessibilityRole="header">Prix immobilier {d ? `${name} (${dept})` : ""}</Text>
      {q.isLoading ? <Loading /> : d ? (
        <>
          <View style={styles.stats}>
            <Stat label="Maisons" stat={d.maison} testID="dept-stat-maison" />
            <Stat label="Appartements" stat={d.appartement} testID="dept-stat-appartement" />
          </View>
          <Text style={styles.intro}>Prix au m² par commune ({d.communes.length} communes avec des ventes, millésimes {d.years[0]}–{d.years[1]}), classées par nombre de ventes.</Text>
          <PriceTable rows={rows} testID="communes-table" searchable />
        </>
      ) : <Text style={styles.intro}>Département introuvable.</Text>}
      <FreeEstimate />
    </PublicPage>
  );
}

export function CommunePage({ dept, insee }: { dept: string; insee: string }) {
  const styles = useStyles();
  const { isTablet } = useBreakpoint();
  const q = useQuery({ queryKey: ["public-commune", dept, insee], queryFn: () => api.publicCommune(dept, insee), staleTime: 3600_000, enabled: !!dept && !!insee });
  const c = q.data;
  const title = c ? `Prix immobilier ${c.name} (${c.code_postal}) : prix au m² maison et appartement` : "Prix immobilier";
  const diff = (a: PublicPriceStat | null, b: PublicPriceStat | null) => (a && b ? Math.round(((a.median_pm2 - b.median_pm2) / b.median_pm2) * 100) : null);
  const dm = c ? diff(c.maison, c.dept_maison) : null;
  const jsonLd = c ? { "@context": "https://schema.org", "@type": "Dataset", name: title, description: `Prix médian au m² à ${c.name} d'après les ventes réelles DVF ${c.years[0]}–${c.years[1]}.`, license: "https://www.etalab.gouv.fr/licence-ouverte-open-licence" } : undefined;
  return (
    <PublicPage title={title} description={c ? `À ${c.name} (${c.dept_name}), le prix médian est de ${pm2(c.maison)} pour une maison et ${pm2(c.appartement)} pour un appartement (ventes réelles ${c.years[0]}–${c.years[1]}). Estimez votre bien gratuitement.` : "Prix au m² par commune"} path={`/prix-immobilier/${dept}/${insee}${c ? `-${c.slug}` : ""}`} jsonLd={jsonLd} testID="prices-commune">
      <Link href={`/prix-immobilier/${dept}` as any} asChild><Pressable accessibilityRole="link"><Text style={styles.crumb}>← {c?.dept_name ?? "Département"} ({dept})</Text></Pressable></Link>
      {q.isLoading ? <Loading /> : !c ? <Text style={styles.intro}>Commune introuvable ou sans vente enregistrée.</Text> : (
        <>
          <Text style={styles.h1} accessibilityRole="header">Prix immobilier à {c.name} ({c.code_postal})</Text>
          <Text style={styles.intro}>
            {c.population ? `${formatInt(c.population)} habitants · ` : ""}{formatInt(c.count)} ventes enregistrées sur {c.years[0]}–{c.years[1]}.
            {dm !== null ? ` Les maisons s’y vendent ${Math.abs(dm)} % ${dm >= 0 ? "au-dessus" : "en dessous"} de la médiane du ${c.dept_name} (${pm2(c.dept_maison)}).` : ""}
          </Text>
          <View style={styles.stats}>
            <Stat label="Maisons" stat={c.maison} testID="commune-stat-maison" />
            <Stat label="Appartements" stat={c.appartement} testID="commune-stat-appartement" />
          </View>
          {c.trend.length ? (
            <View style={styles.section}>
              <Text style={styles.h2} accessibilityRole="header">Évolution du prix au m²</Text>
              <View style={styles.table}>
                {c.trend.map((t) => (
                  <View key={`${t.type}-${t.year}`} style={styles.tr}>
                    <Text style={[styles.td, styles.tdName, styles.name]}>{t.year} · {t.type === "maison" ? "Maison" : "Appartement"}</Text>
                    <Text style={[styles.td, styles.num]}>{formatInt(t.median_pm2)} €/m²</Text>
                    <Text style={[styles.td, styles.num, styles.sub]}>{t.count} ventes</Text>
                  </View>
                ))}
              </View>
            </View>
          ) : null}
          <View style={styles.section}>
            <Text style={styles.h2} accessibilityRole="header">Dernières ventes enregistrées</Text>
            <View style={styles.table} testID="recent-sales">
              {c.recent_sales.map((s, i) => (
                <View key={i} style={styles.tr}>
                  <Text style={[styles.td, styles.tdName, styles.name]}>{s.date} · {s.type === "maison" ? "Maison" : "Appartement"} {s.surface} m²{s.rooms ? ` · ${s.rooms} p.` : ""}{isTablet && s.land_surface ? ` · terrain ${formatInt(s.land_surface)} m²` : ""}</Text>
                  <Text style={[styles.td, styles.num]}>{formatEuro(s.price)}</Text>
                  <Text style={[styles.td, styles.num, styles.sub]}>{formatInt(s.price_m2)} €/m²</Text>
                </View>
              ))}
            </View>
            <Text style={styles.sub}>Source : DVF (Etalab, licence ouverte). Les prix incluent le terrain pour les maisons.</Text>
          </View>
          <FreeEstimate />
          {c.neighbours.length ? (
            <View style={styles.section}>
              <Text style={styles.h2} accessibilityRole="header">Communes voisines dans le {c.dept_name}</Text>
              <PriceTable rows={c.neighbours.map((n) => ({ key: n.insee, href: `/prix-immobilier/${dept}/${n.insee}-${n.slug}`, name: n.name, sub: n.code_postal, maison: n.maison, appartement: n.appartement, count: n.count }))} testID="neighbours-table" />
            </View>
          ) : null}
        </>
      )}
    </PublicPage>
  );
}

const useStyles = makeStyles((colors) => ({
  h1: { fontFamily: fonts.extrabold, fontSize: 30, lineHeight: 38, color: colors.onSurface },
  kicker: { fontFamily: fonts.bold, fontSize: 12, letterSpacing: 1, color: colors.brandPrimary },
  hero: { gap: spacing.xl },
  heroImage: { width: "100%", aspectRatio: 1.4, borderRadius: radius.lg, backgroundColor: colors.surfaceSecondary },
  kpis: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  kpi: { flex: 1, minWidth: 140, backgroundColor: colors.surfaceSecondary, borderWidth: 1, borderColor: colors.border, borderRadius: radius.md, padding: spacing.md, gap: 2 },
  kpiValue: { fontFamily: fonts.extrabold, fontSize: 22, color: colors.brandPrimary },
  kpiLabel: { fontFamily: fonts.medium, fontSize: 12, color: colors.muted },
  search: { flexDirection: "row", alignItems: "center", gap: spacing.sm, backgroundColor: colors.surfaceSecondary, borderWidth: 1, borderColor: colors.border, borderRadius: radius.pill, paddingHorizontal: spacing.md, minHeight: 48 },
  searchInput: { flex: 1, fontFamily: fonts.regular, fontSize: 15, color: colors.onSurface, minHeight: 44 },
  clear: { fontFamily: fonts.semibold, fontSize: 13, color: colors.brandPrimary },
  empty: { fontFamily: fonts.medium, fontSize: 14, color: colors.muted, padding: spacing.lg, textAlign: "center" },
  barWrap: { gap: 4, alignItems: "flex-end" },
  barTrack: { width: "100%", height: 6, borderRadius: 3, backgroundColor: colors.border, overflow: "hidden" },
  barFill: { height: "100%", borderRadius: 3 },
  tdSmall: { width: 72, paddingVertical: spacing.sm },
  tdChevron: { width: 24, alignItems: "flex-end" },
  thRight: { textAlign: "right" },
  trAlt: { backgroundColor: colors.surfaceSecondary },
  legendRow: { flexDirection: "row", alignItems: "center", gap: 6, flexWrap: "wrap" },
  legendDot: { width: 10, height: 10, borderRadius: 5 },
  h2: { fontFamily: fonts.bold, fontSize: 21, lineHeight: 28, color: colors.onSurface },
  intro: { fontFamily: fonts.regular, fontSize: 16, lineHeight: 25, color: colors.onSurfaceTertiary },
  crumb: { fontFamily: fonts.semibold, fontSize: 14, color: colors.brandPrimary, minHeight: 36, lineHeight: 36 },
  section: { gap: spacing.sm },
  stats: { flexDirection: "row", flexWrap: "wrap", gap: spacing.md },
  stat: { flex: 1, minWidth: 240, backgroundColor: colors.brandTertiary, borderRadius: radius.lg, padding: spacing.lg, gap: 4 },
  statLabel: { fontFamily: fonts.semibold, fontSize: 12, letterSpacing: 1, textTransform: "uppercase", color: colors.onBrandTertiary },
  statValue: { fontFamily: fonts.bold, fontSize: 30, color: colors.onBrandTertiary },
  statSub: { fontFamily: fonts.regular, fontSize: 13, color: colors.onBrandTertiary },
  table: { borderWidth: 1, borderColor: colors.border, borderRadius: radius.lg, overflow: "hidden" },
  tr: { flexDirection: "row", alignItems: "center", gap: spacing.md, minHeight: 56, paddingHorizontal: spacing.md, borderBottomWidth: 1, borderBottomColor: colors.border },
  th: { backgroundColor: colors.surfaceSecondary, minHeight: 44 },
  thText: { fontFamily: fonts.semibold, fontSize: 12, textTransform: "uppercase", letterSpacing: 0.5, color: colors.muted },
  td: { flex: 1, paddingVertical: spacing.sm },
  tdName: { flex: 2 },
  name: { fontFamily: fonts.semibold, fontSize: 15, color: colors.onSurface },
  sub: { fontFamily: fonts.regular, fontSize: 12, color: colors.muted },
  num: { fontFamily: fonts.semibold, fontSize: 15, color: colors.onSurfaceSecondary, textAlign: "right" },
}));
