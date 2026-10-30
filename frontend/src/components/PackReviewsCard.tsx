import { useQuery } from "@tanstack/react-query";
import { SealCheckIcon, StarIcon } from "phosphor-react-native";
import { ScrollView, Text, View } from "react-native";

import { api } from "@/src/api";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

/** Réassurance avant paiement : note moyenne et avis vérifiés (approuvés). Ne s'affiche pas tant qu'il n'y a aucun avis. */
export function PackReviewsCard() {
  const styles = useStyles();
  const { colors } = useTheme();
  const q = useQuery({ queryKey: ["public-reviews"], queryFn: api.publicReviews, staleTime: 10 * 60 * 1000 });
  const avg = q.data?.average;
  const count = q.data?.count ?? 0;
  if (!q.data || !avg || count === 0) return null;
  const quotes = q.data.items.filter((r) => r.comment).slice(0, 5);

  return (
    <View style={styles.card} testID="pack-reviews">
      <View style={styles.head}>
        <Text style={styles.avg}>{avg.toLocaleString("fr-FR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}</Text>
        <View style={{ gap: 3, flex: 1 }}>
          <View style={styles.stars}>
            {[1, 2, 3, 4, 5].map((i) => <StarIcon key={i} size={18} color={i <= Math.round(avg) ? colors.warning : colors.border} weight="fill" />)}
          </View>
          <View style={styles.verified}>
            <SealCheckIcon size={14} color={colors.success} weight="fill" />
            <Text style={styles.count}>{count} avis vérifié{count > 1 ? "s" : ""} de vendeurs</Text>
          </View>
        </View>
      </View>
      {quotes.length ? (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.quotes}>
          {quotes.map((r) => (
            <View key={r.id} style={styles.quote} testID="pack-review-item">
              <View style={styles.stars}>
                {[1, 2, 3, 4, 5].map((i) => <StarIcon key={i} size={12} color={i <= r.rating ? colors.warning : colors.border} weight="fill" />)}
              </View>
              <Text style={styles.quoteText} numberOfLines={4}>« {r.comment} »</Text>
              <Text style={styles.author}>{r.name}</Text>
            </View>
          ))}
        </ScrollView>
      ) : null}
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  card: { backgroundColor: colors.surfaceSecondary, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, padding: spacing.lg, gap: spacing.md },
  head: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  avg: { fontFamily: fonts.extrabold, fontSize: 40, lineHeight: 44, color: colors.onSurface },
  stars: { flexDirection: "row", gap: 2 },
  verified: { flexDirection: "row", alignItems: "center", gap: 4 },
  count: { fontFamily: fonts.medium, fontSize: 13, color: colors.onSurfaceSecondary },
  quotes: { gap: spacing.sm, paddingRight: spacing.sm },
  quote: { width: 240, backgroundColor: colors.surface, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, padding: spacing.md, gap: 6 },
  quoteText: { fontFamily: fonts.regular, fontSize: 13, lineHeight: 19, color: colors.onSurfaceSecondary, fontStyle: "italic" },
  author: { fontFamily: fonts.semibold, fontSize: 12, color: colors.muted },
}));
