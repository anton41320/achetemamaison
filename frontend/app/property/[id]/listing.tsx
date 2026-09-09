import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as Clipboard from "expo-clipboard";
import { useLocalSearchParams, useRouter } from "expo-router";
import { CheckIcon, CopyIcon, SparkleIcon, TrashIcon, WarningIcon } from "phosphor-react-native";
import { useState } from "react";
import { Platform, Pressable, Switch, Text, View } from "react-native";
import { KeyboardAwareScrollView, KeyboardStickyView } from "react-native-keyboard-controller";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { LISTING_STYLES, Listing, ListingStyle, api, formatMonth } from "@/src/api";
import { Field, Segmented } from "@/src/components/Form";
import { PrimaryButton } from "@/src/components/PrimaryButton";
import { ScreenHeader } from "@/src/components/ScreenHeader";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

const CTA_HEIGHT = 92;

export default function ListingScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const queryClient = useQueryClient();

  const [style, setStyle] = useState<ListingStyle>("sobre");
  const [extra, setExtra] = useState("");
  const [includePrice, setIncludePrice] = useState(true);
  const [copied, setCopied] = useState<string | null>(null);

  const listings = useQuery({ queryKey: ["listings", id], queryFn: () => api.listListings(id!), enabled: !!id });

  const generate = useMutation({
    mutationFn: () => api.createListing(id!, { style, extra_facts: extra.trim() || null, include_price: includePrice }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["listings", id] }),
  });

  const remove = useMutation({
    mutationFn: (lid: string) => api.deleteListing(id!, lid),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["listings", id] }),
  });

  const copy = async (l: Listing) => {
    const text = `${l.title}\n\n${l.hook}\n\n${l.description}\n\n${l.highlights.map((h) => `• ${h}`).join("\n")}`;
    await Clipboard.setStringAsync(text);
    setCopied(l.id);
    setTimeout(() => setCopied(null), 2000);
  };

  return (
    <View style={styles.screen} testID="listing-screen">
      <ScreenHeader title="Annonce IA" subtitle="Claude Sonnet 4.6 · n’invente aucune information" onBack={() => router.back()} />
      <KeyboardAwareScrollView
        contentContainerStyle={[styles.content, { paddingBottom: CTA_HEIGHT + insets.bottom + spacing.lg }]}
        bottomOffset={CTA_HEIGHT + spacing.lg}
        keyboardShouldPersistTaps="handled"
      >
        <Segmented label="Style" testID="listing-style" scroll value={style} onChange={setStyle} options={LISTING_STYLES} />
        <Field
          label="Atouts et précisions (optionnel)"
          testID="listing-extra-input"
          placeholder="Ex. : cuisine rénovée en 2021, garage, exposition sud…"
          value={extra}
          onChangeText={setExtra}
          multiline
          numberOfLines={3}
          style={{ minHeight: 72, textAlignVertical: "top" }}
          hint="Seuls les faits ci-dessus et ceux du bien seront utilisés. Rien d’autre ne sera inventé."
        />
        <View style={styles.switchRow}>
          <Text style={styles.switchLabel}>Mentionner la fourchette de prix Estimo</Text>
          <Switch
            testID="listing-include-price"
            value={includePrice}
            onValueChange={setIncludePrice}
            trackColor={{ true: colors.brandPrimary, false: colors.surfaceTertiary }}
            thumbColor={Platform.OS === "android" ? colors.surfaceSecondary : undefined}
          />
        </View>
        {generate.isError ? (
          <View style={styles.warn} testID="listing-error">
            <WarningIcon size={18} color={colors.error} weight="fill" />
            <Text style={styles.warnText}>{(generate.error as Error).message}</Text>
          </View>
        ) : null}

        <Text style={styles.sectionTitle}>Annonces générées</Text>
        {listings.isLoading ? (
          <View style={styles.skeleton} />
        ) : !listings.data || listings.data.length === 0 ? (
          <Text style={styles.p} testID="listing-empty">Aucune annonce pour ce bien. Choisissez un style et générez votre première version.</Text>
        ) : (
          listings.data.map((l, i) => (
            <View key={l.id} style={styles.listing} testID={`listing-card-${i}`}>
              <View style={styles.listingHead}>
                <Text style={styles.stylePill}>{LISTING_STYLES.find((s) => s.value === l.style)?.label ?? l.style}</Text>
                <Text style={styles.date}>{formatMonth(l.created_at)}</Text>
              </View>
              <Text style={styles.title} testID={`listing-title-${i}`}>{l.title}</Text>
              <Text style={styles.hook}>{l.hook}</Text>
              <Text style={styles.body}>{l.description}</Text>
              <View style={{ gap: 4 }}>
                {l.highlights.map((h, j) => (
                  <Text key={j} style={styles.highlight}>• {h}</Text>
                ))}
              </View>
              <View style={styles.actions}>
                <Pressable testID={`listing-copy-${i}`} accessibilityRole="button" onPress={() => copy(l)} style={styles.actionBtn}>
                  {copied === l.id ? <CheckIcon size={16} color={colors.success} weight="bold" /> : <CopyIcon size={16} color={colors.onBrandTertiary} />}
                  <Text style={styles.actionLabel}>{copied === l.id ? "Copié" : "Copier"}</Text>
                </Pressable>
                <Pressable testID={`listing-delete-${i}`} accessibilityRole="button" onPress={() => remove.mutate(l.id)} style={styles.actionBtn}>
                  <TrashIcon size={16} color={colors.error} />
                  <Text style={[styles.actionLabel, { color: colors.error }]}>Supprimer</Text>
                </Pressable>
              </View>
            </View>
          ))
        )}
      </KeyboardAwareScrollView>

      <KeyboardStickyView offset={{ closed: 0, opened: insets.bottom }}>
        <View style={[styles.cta, { paddingBottom: insets.bottom + spacing.lg }]}>
          <PrimaryButton
            title={generate.isPending ? "Rédaction en cours…" : "Générer l’annonce"}
            onPress={() => generate.mutate()}
            loading={generate.isPending}
            testID="listing-generate-button"
          />
        </View>
      </KeyboardStickyView>
      {generate.isPending ? (
        <View style={styles.sparkle} pointerEvents="none">
          <SparkleIcon size={16} color={colors.brandPrimary} weight="fill" />
        </View>
      ) : null}
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  screen: { flex: 1, backgroundColor: colors.surface },
  content: { padding: spacing.lg, gap: spacing.lg },
  p: { fontFamily: fonts.regular, fontSize: 14, lineHeight: 20, color: colors.onSurfaceTertiary },
  switchRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: spacing.md, minHeight: 44 },
  switchLabel: { flex: 1, fontFamily: fonts.medium, fontSize: 14, color: colors.onSurface },
  warn: { flexDirection: "row", gap: spacing.md, alignItems: "flex-start", backgroundColor: colors.errorSoft, borderRadius: radius.md, padding: spacing.lg },
  warnText: { flex: 1, fontFamily: fonts.medium, fontSize: 13, lineHeight: 19, color: colors.error },
  sectionTitle: { fontFamily: fonts.semibold, fontSize: 13, color: colors.muted, textTransform: "uppercase", letterSpacing: 0.6 },
  skeleton: { height: 160, borderRadius: radius.lg, backgroundColor: colors.skeleton },
  listing: { backgroundColor: colors.surfaceSecondary, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, padding: spacing.lg, gap: spacing.md },
  listingHead: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  stylePill: { fontFamily: fonts.semibold, fontSize: 12, color: colors.onBrandTertiary, backgroundColor: colors.brandTertiary, paddingHorizontal: spacing.md, height: 26, lineHeight: 26, borderRadius: radius.pill },
  date: { fontFamily: fonts.regular, fontSize: 12, color: colors.muted },
  title: { fontFamily: fonts.bold, fontSize: 18, color: colors.onSurfaceSecondary },
  hook: { fontFamily: fonts.medium, fontSize: 15, lineHeight: 22, color: colors.onSurfaceSecondary },
  body: { fontFamily: fonts.regular, fontSize: 14, lineHeight: 21, color: colors.onSurfaceTertiary },
  highlight: { fontFamily: fonts.medium, fontSize: 13, lineHeight: 19, color: colors.onSurfaceSecondary },
  actions: { flexDirection: "row", gap: spacing.md, borderTopWidth: 1, borderTopColor: colors.divider, paddingTop: spacing.md },
  actionBtn: { flexDirection: "row", alignItems: "center", gap: 6, minHeight: 44, paddingHorizontal: spacing.md, borderRadius: radius.md, backgroundColor: colors.brandTertiary },
  actionLabel: { fontFamily: fonts.semibold, fontSize: 13, color: colors.onBrandTertiary },
  cta: { paddingHorizontal: spacing.lg, paddingTop: spacing.md, backgroundColor: colors.surface, borderTopWidth: 1, borderTopColor: colors.divider },
  sparkle: { position: "absolute", right: spacing.xl, top: 120 },
}));
