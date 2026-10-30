import { useQuery } from "@tanstack/react-query";
import { StarIcon } from "phosphor-react-native";
import { Text, View } from "react-native";

import { api } from "@/src/api";
import { BrandDash } from "@/src/components/BrandMarks";
import { StoreBadges } from "@/src/components/StoreBadges";
import { SITE_NAME } from "@/src/web/PublicPage";
import { fonts, makeStyles, spacing, radius, useTheme } from "@/src/theme";

function Stars({ n, size = 16 }: { n: number; size?: number }) {
  const { colors } = useTheme();
  return (
    <View style={{ flexDirection: "row", gap: 2 }}>
      {[1, 2, 3, 4, 5].map((i) => <StarIcon key={i} size={size} color={i <= Math.round(n) ? colors.warning : colors.border} weight="fill" />)}
    </View>
  );
}

const fmtDate = (iso: string) => new Date(iso).toLocaleDateString("fr-FR", { month: "long", year: "numeric" });

/** Avis clients réels (approuvés par le gérant) + note moyenne ; invitation à télécharger l'app si aucun avis encore. */
export function ReviewsSection({ row }: { row: boolean }) {
  const styles = useStyles();
  const q = useQuery({ queryKey: ["public-reviews"], queryFn: api.publicReviews, staleTime: 10 * 60 * 1000 });
  const items = q.data?.items ?? [];
  const count = q.data?.count ?? 0;
  const avg = q.data?.average ?? null;

  return (
    <View style={styles.section} testID="landing-reviews">
      <View style={styles.h2Row}><BrandDash size={22} /><Text style={styles.h2} accessibilityRole="header">Ils ont vendu avec {SITE_NAME}</Text></View>
      {count > 0 && avg !== null ? (
        <View style={styles.summary} testID="landing-reviews-summary">
          <Text style={styles.avg}>{avg.toLocaleString("fr-FR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}</Text>
          <View style={{ gap: 2 }}>
            <Stars n={avg} size={18} />
            <Text style={styles.count}>{count} avis vérifié{count > 1 ? "s" : ""} · recueillis dans l’application</Text>
          </View>
        </View>
      ) : null}
      {items.length > 0 ? (
        <View style={[styles.cards, row && { flexDirection: "row" }]}>
          {items.slice(0, 6).map((r) => (
            <View key={r.id} style={styles.quoteCard} testID="landing-review">
              <Stars n={r.rating} />
              {r.comment ? <Text style={styles.quote}>« {r.comment} »</Text> : null}
              <Text style={styles.quoteAuthor}>{r.name} · {fmtDate(r.created_at)}</Text>
            </View>
          ))}
        </View>
      ) : (
        <View style={styles.empty} testID="landing-reviews-empty">
          <Text style={styles.emptyTitle}>{q.isLoading ? "Chargement des avis…" : "Les premiers avis arrivent"}</Text>
          {!q.isLoading ? (
            <Text style={styles.emptyText}>
              Les avis affichés ici sont déposés par de vrais vendeurs depuis l’application, après leur estimation, et vérifiés avant publication.
              Vous avez estimé votre bien avec nous ? Donnez votre avis dans l’application.
            </Text>
          ) : null}
          <StoreBadges compact style={{ justifyContent: "center" }} />
        </View>
      )}
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  section: { gap: spacing.md },
  h2Row: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  h2: { fontFamily: fonts.extrabold, fontSize: 26, lineHeight: 34, color: colors.onSurface, flexShrink: 1 },
  summary: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  avg: { fontFamily: fonts.extrabold, fontSize: 44, color: colors.onSurface, lineHeight: 48 },
  count: { fontFamily: fonts.medium, fontSize: 13, color: colors.muted },
  cards: { gap: spacing.md },
  quoteCard: { flex: 1, backgroundColor: colors.surfaceSecondary, borderRadius: radius.lg, padding: spacing.lg, gap: spacing.sm, borderWidth: 1, borderColor: colors.border },
  quote: { fontFamily: fonts.regular, fontSize: 15, lineHeight: 23, color: colors.onSurfaceSecondary, fontStyle: "italic" },
  quoteAuthor: { fontFamily: fonts.semibold, fontSize: 13, color: colors.muted },
  empty: { backgroundColor: colors.surfaceSecondary, borderRadius: radius.lg, padding: spacing.lg, gap: spacing.md, borderWidth: 1, borderColor: colors.border, alignItems: "center" },
  emptyTitle: { fontFamily: fonts.extrabold, fontSize: 18, color: colors.onSurface, textAlign: "center" },
  emptyText: { fontFamily: fonts.regular, fontSize: 14, lineHeight: 21, color: colors.onSurfaceSecondary, textAlign: "center", maxWidth: 620 },
}));
