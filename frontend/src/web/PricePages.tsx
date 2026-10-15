import { useQuery } from "@tanstack/react-query";
import { Link } from "expo-router";
import { ActivityIndicator, Pressable, Text, View } from "react-native";

import { PublicCommune, PublicDept, PublicPriceStat, api, formatEuro, formatInt } from "@/src/api";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";
import { FreeEstimate } from "@/src/web/FreeEstimate";
import { PublicPage } from "@/src/web/PublicPage";
import { useBreakpoint } from "@/src/web/useBreakpoint";

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

/** Tableau responsive : lignes cliquables, colonnes « €/m² maison / appartement / ventes ». */
function PriceTable<T extends { key: string; href: string; name: string; sub?: string; maison: PublicPriceStat | null; appartement: PublicPriceStat | null; count: number }>({ rows, testID }: { rows: T[]; testID: string }) {
  const styles = useStyles();
  const { isTablet } = useBreakpoint();
  return (
    <View style={styles.table} testID={testID}>
      <View style={[styles.tr, styles.th]}>
        <Text style={[styles.td, styles.tdName, styles.thText]}>Commune / département</Text>
        <Text style={[styles.td, styles.thText]}>Maison</Text>
        <Text style={[styles.td, styles.thText]}>Appartement</Text>
        {isTablet ? <Text style={[styles.td, styles.thText]}>Ventes</Text> : null}
      </View>
      {rows.map((r) => (
        <Link key={r.key} href={r.href as any} asChild>
          <Pressable accessibilityRole="link" style={({ hovered }: any) => [styles.tr, hovered && styles.trHover]} testID={`price-row-${r.key}`}>
            <View style={[styles.td, styles.tdName]}>
              <Text style={styles.name}>{r.name}</Text>
              {r.sub ? <Text style={styles.sub}>{r.sub}</Text> : null}
            </View>
            <Text style={[styles.td, styles.num]}>{pm2(r.maison)}</Text>
            <Text style={[styles.td, styles.num]}>{pm2(r.appartement)}</Text>
            {isTablet ? <Text style={[styles.td, styles.num, styles.sub]}>{formatInt(r.count)}</Text> : null}
          </Pressable>
        </Link>
      ))}
    </View>
  );
}

export function DeptsPage() {
  const styles = useStyles();
  const q = useQuery({ queryKey: ["public-depts"], queryFn: api.publicDepts, staleTime: 3600_000 });
  const rows = (q.data?.departements ?? []).map((d: PublicDept) => ({ key: d.code, href: `/prix-immobilier/${d.code}`, name: `${d.name} (${d.code})`, maison: d.maison, appartement: d.appartement, count: d.count }));
  return (
    <PublicPage title="Prix immobilier par département et par commune (ventes réelles DVF)" description="Prix médian au m² des maisons et appartements dans chaque département et commune de France, calculé sur les ventes réelles des 3 dernières années (DVF)." path="/prix-immobilier" testID="prices-depts">
      <Text style={styles.h1} accessibilityRole="header">Prix immobilier en France : €/m² par département</Text>
      <Text style={styles.intro}>Médianes calculées sur les ventes réelles publiées par l’État (DVF){q.data ? `, millésimes ${q.data.years[0]}–${q.data.years[1]}` : ""}. Cliquez sur un département pour voir le prix au m² de chaque commune.</Text>
      {q.isLoading ? <Loading /> : <PriceTable rows={rows} testID="depts-table" />}
      <FreeEstimate />
    </PublicPage>
  );
}

export function DeptPage({ dept }: { dept: string }) {
  const styles = useStyles();
  const q = useQuery({ queryKey: ["public-dept", dept], queryFn: () => api.publicDept(dept), staleTime: 3600_000, enabled: !!dept });
  const d = q.data;
  const rows = (d?.communes ?? []).map((c: PublicCommune) => ({ key: c.insee, href: `/prix-immobilier/${dept}/${c.insee}-${c.slug}`, name: c.name, sub: `${c.code_postal}${c.population ? ` · ${formatInt(c.population)} hab.` : ""}`, maison: c.maison, appartement: c.appartement, count: c.count }));
  const name = d?.name ?? `département ${dept}`;
  return (
    <PublicPage title={`Prix immobilier ${name} (${dept}) : prix au m² par commune`} description={`Prix médian au m² des maisons et appartements dans le ${name} et dans chacune de ses communes, d'après les ventes réelles DVF.`} path={`/prix-immobilier/${dept}`} testID="prices-dept">
      <Link href="/prix-immobilier" asChild><Pressable accessibilityRole="link"><Text style={styles.crumb}>← Tous les départements</Text></Pressable></Link>
      <Text style={styles.h1} accessibilityRole="header">Prix immobilier {name} ({dept})</Text>
      {q.isLoading ? <Loading /> : d ? (
        <>
          <View style={styles.stats}>
            <Stat label="Maisons" stat={d.maison} testID="dept-stat-maison" />
            <Stat label="Appartements" stat={d.appartement} testID="dept-stat-appartement" />
          </View>
          <Text style={styles.intro}>Prix au m² par commune ({d.communes.length} communes avec des ventes, millésimes {d.years[0]}–{d.years[1]}), classées par nombre de ventes.</Text>
          <PriceTable rows={rows} testID="communes-table" />
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
  h1: { fontFamily: fonts.bold, fontSize: 30, lineHeight: 38, color: colors.onSurface },
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
  tr: { flexDirection: "row", alignItems: "center", minHeight: 48, paddingHorizontal: spacing.md, borderBottomWidth: 1, borderBottomColor: colors.border, backgroundColor: colors.surface },
  trHover: { backgroundColor: colors.surfaceSecondary },
  th: { backgroundColor: colors.surfaceSecondary },
  thText: { fontFamily: fonts.semibold, fontSize: 12, textTransform: "uppercase", letterSpacing: 0.5, color: colors.muted },
  td: { flex: 1, paddingVertical: spacing.sm },
  tdName: { flex: 2 },
  name: { fontFamily: fonts.semibold, fontSize: 15, color: colors.onSurface },
  sub: { fontFamily: fonts.regular, fontSize: 12, color: colors.muted },
  num: { fontFamily: fonts.semibold, fontSize: 15, color: colors.onSurfaceSecondary, textAlign: "right" },
}));
