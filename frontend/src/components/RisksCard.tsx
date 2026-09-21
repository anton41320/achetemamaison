import { useQuery } from "@tanstack/react-query";
import { ArrowSquareOutIcon, ShieldWarningIcon } from "phosphor-react-native";
import { useState } from "react";
import { ActivityIndicator, Linking, Pressable, Text, View } from "react-native";

import { RiskLevel, api } from "@/src/api";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

interface Props {
  propertyId: string;
}

const LEVEL_LABEL: Record<RiskLevel, string> = { none: "Non concerné", low: "Faible", medium: "Moyen", high: "Fort", info: "Commune" };

const EXPLAIN: Record<string, string> = {
  argile: "Sols argileux : risque de fissures par sécheresse. Une étude géotechnique peut être demandée à la vente.",
  radon: "Gaz naturel radioactif issu du sol : à mesurer si le potentiel est significatif, aération conseillée.",
  inondation: "Zone concernée par un plan de prévention ou des crues passées.",
  nappe: "Remontée de nappe : possibles infiltrations en sous-sol lors d’épisodes pluvieux.",
  seisme: "Zonage sismique réglementaire de la commune.",
  mouvement_terrain: "Glissements, effondrements ou cavités recensés sur la commune.",
  icpe: "Sites industriels soumis à autorisation ou déclaration à proximité.",
  pollution_sols: "Anciens sites industriels ou sols pollués référencés à proximité.",
  canalisations: "Canalisations de gaz, hydrocarbures ou produits chimiques à proximité.",
  feu_foret: "Commune exposée au risque de feu de forêt.",
};

/** « Risques & environnement » — données publiques Géorisques, gratuites pour tous. */
export function RisksCard({ propertyId }: Props) {
  const styles = useStyles();
  const { colors } = useTheme();
  const [showAll, setShowAll] = useState(false);
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ["risks", propertyId], queryFn: () => api.risks(propertyId), staleTime: 60 * 60 * 1000 });

  const tone = (level: RiskLevel) =>
    level === "high" ? { fg: colors.error, bg: colors.errorSoft } : level === "medium" ? { fg: colors.warning, bg: colors.warningSoft }
      : level === "low" ? { fg: colors.success, bg: colors.successSoft } : { fg: colors.onBrandTertiary, bg: colors.brandTertiary };

  const present = (data?.items ?? []).filter((it) => it.present);
  const order: Record<RiskLevel, number> = { high: 0, medium: 1, low: 2, info: 3, none: 4 };
  const sorted = [...present].sort((a, b) => order[a.level] - order[b.level]);
  const visible = showAll ? sorted : sorted.slice(0, 4);
  const worst = sorted[0]?.level ?? "none";

  return (
    <View style={styles.card} testID="risks-card">
      <View style={styles.header}>
        <ShieldWarningIcon size={20} color={colors.brandPrimary} weight="duotone" />
        <Text style={styles.h3}>Risques & environnement</Text>
        <Text style={styles.source}>Géorisques</Text>
      </View>
      {isLoading ? (
        <ActivityIndicator color={colors.brandPrimary} />
      ) : isError || !data ? (
        <Pressable onPress={() => refetch()} testID="risks-retry">
          <Text style={styles.detail}>Données Géorisques indisponibles pour le moment · appuyer pour réessayer</Text>
        </Pressable>
      ) : (
        <>
          <Text style={styles.p} testID="risks-summary">
            {present.length === 0
              ? "Aucun risque recensé à cette adresse."
              : `${present.filter((i) => i.scope === "adresse").length} risque(s) identifié(s) à l’adresse, ${present.filter((i) => i.scope === "commune").length} recensé(s) sur la commune.`}
            {worst === "high" ? " Un point mérite votre attention." : ""}
          </Text>

          <View style={styles.grid}>
            <View style={[styles.kpi, { backgroundColor: tone(data.argile.level).bg }]} testID="risks-argile">
              <Text style={[styles.kpiValue, { color: tone(data.argile.level).fg }]}>{data.argile.label}</Text>
              <Text style={styles.kpiLabel}>Argiles (retrait-gonflement)</Text>
            </View>
            <View style={[styles.kpi, { backgroundColor: tone(data.radon.level).bg }]} testID="risks-radon">
              <Text style={[styles.kpiValue, { color: tone(data.radon.level).fg }]}>{data.radon.label}</Text>
              <Text style={styles.kpiLabel}>Radon</Text>
            </View>
            <View style={styles.kpi} testID="risks-catnat">
              <Text style={styles.kpiValue}>{data.catnat.count}</Text>
              <Text style={styles.kpiLabel}>Arrêtés CatNat (commune)</Text>
            </View>
            <View style={styles.kpi} testID="risks-icpe">
              <Text style={styles.kpiValue}>{data.icpe.count}</Text>
              <Text style={styles.kpiLabel}>Sites industriels à {data.icpe.radius_m / 1000} km</Text>
            </View>
          </View>

          {visible.map((it) => (
            <View key={it.key} style={styles.row} testID={`risk-${it.key}`}>
              <View style={[styles.pill, { backgroundColor: tone(it.level).bg }]}>
                <Text style={[styles.pillText, { color: tone(it.level).fg }]}>{it.detail ?? LEVEL_LABEL[it.level]}</Text>
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.rowLabel}>{it.label}</Text>
                <Text style={styles.detail}>{EXPLAIN[it.key] ?? (it.scope === "commune" ? "Recensé à l’échelle de la commune." : it.status_address ?? "")}</Text>
              </View>
            </View>
          ))}
          {sorted.length > 4 ? (
            <Pressable onPress={() => setShowAll((v) => !v)} testID="risks-toggle" accessibilityRole="button" style={styles.moreBtn}>
              <Text style={styles.more}>{showAll ? "Réduire" : `Voir les ${sorted.length - 4} autres risques`}</Text>
            </Pressable>
          ) : null}

          {data.catnat.last.length > 0 ? (
            <Text style={styles.detail}>
              Derniers arrêtés : {data.catnat.last.slice(0, 3).map((e) => `${e.type} (${e.start?.slice(-4)})`).join(" · ")}
            </Text>
          ) : null}
          {data.dossier_flags.geotechnique_required ? (
            <Text style={styles.flag} testID="risks-flag-geotech">Étude géotechnique ajoutée aux pièces requises du dossier de vente.</Text>
          ) : null}
          <Pressable onPress={() => Linking.openURL(data.source_url)} testID="risks-source" accessibilityRole="link" style={styles.linkRow}>
            <ArrowSquareOutIcon size={14} color={colors.brandPrimary} />
            <Text style={styles.link}>Rapport complet sur georisques.gouv.fr</Text>
          </Pressable>
          <Text style={styles.detail}>Information publique indicative, consultée le {new Date(data.fetched_at).toLocaleDateString("fr-FR")}. L’état des risques (ERP) réglementaire reste à établir pour la vente.</Text>
        </>
      )}
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  card: { backgroundColor: colors.surfaceSecondary, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, padding: spacing.lg, gap: spacing.md },
  header: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  h3: { flex: 1, fontFamily: fonts.semibold, fontSize: 17, color: colors.onSurfaceSecondary },
  source: { fontFamily: fonts.semibold, fontSize: 11, color: colors.onBrandTertiary, backgroundColor: colors.brandTertiary, paddingHorizontal: spacing.sm, height: 22, lineHeight: 22, borderRadius: radius.pill },
  p: { fontFamily: fonts.regular, fontSize: 14, lineHeight: 20, color: colors.onSurfaceTertiary },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  kpi: { flexBasis: "47%", flexGrow: 1, backgroundColor: colors.surface, borderRadius: radius.md, padding: spacing.md, gap: 2 },
  kpiValue: { fontFamily: fonts.bold, fontSize: 15, color: colors.onSurface },
  kpiLabel: { fontFamily: fonts.regular, fontSize: 12, color: colors.muted },
  row: { flexDirection: "row", gap: spacing.md, alignItems: "flex-start", borderTopWidth: 1, borderTopColor: colors.divider, paddingTop: spacing.sm },
  pill: { minWidth: 72, paddingHorizontal: spacing.sm, height: 24, borderRadius: radius.pill, justifyContent: "center", alignItems: "center" },
  pillText: { fontFamily: fonts.semibold, fontSize: 11 },
  rowLabel: { fontFamily: fonts.semibold, fontSize: 14, color: colors.onSurfaceSecondary },
  detail: { fontFamily: fonts.regular, fontSize: 12, lineHeight: 17, color: colors.muted },
  moreBtn: { minHeight: 44, justifyContent: "center" },
  more: { fontFamily: fonts.semibold, fontSize: 13, color: colors.brandPrimary },
  flag: { fontFamily: fonts.medium, fontSize: 12, lineHeight: 17, color: colors.warning },
  linkRow: { flexDirection: "row", alignItems: "center", gap: 6, minHeight: 32 },
  link: { fontFamily: fonts.semibold, fontSize: 13, color: colors.brandPrimary },
}));
