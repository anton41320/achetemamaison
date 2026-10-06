import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as Clipboard from "expo-clipboard";
import { useLocalSearchParams, useRouter } from "expo-router";
import { CheckIcon, CopyIcon, ShareNetworkIcon, SparkleIcon, TrashIcon, TreeIcon, WarningIcon } from "phosphor-react-native";
import { useState } from "react";
import { ActivityIndicator, Platform, Pressable, Switch, Text, View } from "react-native";
import { KeyboardAwareScrollView, KeyboardStickyView } from "react-native-keyboard-controller";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { LISTING_STYLES, Listing, ListingStyle, api, formatK, formatMonth } from "@/src/api";
import { Field, Segmented } from "@/src/components/Form";
import { PremiumGate, usePackUnlocked } from "@/src/components/PremiumGate";
import { usePhotoExport } from "@/src/photoExport";
import { PrimaryButton } from "@/src/components/PrimaryButton";
import { ScreenHeader } from "@/src/components/ScreenHeader";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

const CTA_HEIGHT = 92;

const listingText = (l: Listing) => `${l.title}\n\n${l.hook}\n\n${l.description}\n\n${l.highlights.map((h) => `• ${h}`).join("\n")}`;

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
  const [useEnv, setUseEnv] = useState(true);
  const [copied, setCopied] = useState<string | null>(null);
  // Atouts du quartier mesurés par l'analyse d'environnement (cache uniquement : ne déclenche pas d'analyse)
  const envHl = useQuery({ queryKey: ["environment-highlights", id], queryFn: () => api.environmentHighlights(id!), enabled: !!id });

  const listings = useQuery({ queryKey: ["listings", id], queryFn: () => api.listListings(id!), enabled: !!id });
  const prop = useQuery({ queryKey: ["property", id], queryFn: () => api.getProperty(id!), enabled: !!id });
  const pack = usePackUnlocked(id);

  // Prix de vente souhaité : c'est le prix cible du bien (partagé avec la fiche) ; l'annonce l'affiche tel quel au lieu de la fourchette.
  const target = useQuery({ queryKey: ["target", id], queryFn: () => api.getTarget(id!), enabled: !!id });
  const [priceInput, setPriceInput] = useState<string | null>(null);
  const priceText = priceInput ?? (target.data?.target_price ? String(Math.round(target.data.target_price)) : "");
  const parsedPrice = Number(priceText.replace(/[^\d]/g, ""));
  const priceValid = priceText.trim() === "" || (parsedPrice >= 10_000 && parsedPrice <= 20_000_000);
  const savePrice = useMutation({
    mutationFn: (value: number | null) => api.putTarget(id!, value),
    onSuccess: (r) => {
      queryClient.setQueryData(["target", id], r);
      queryClient.invalidateQueries({ queryKey: ["next-steps"] });
      setPriceInput(null);
    },
  });
  const priceDirty = priceInput !== null && priceText.trim() !== (target.data?.target_price ? String(Math.round(target.data.target_price)) : "");

  const generate = useMutation({
    mutationFn: async () => {
      if (includePrice && priceDirty && priceValid) await savePrice.mutateAsync(priceText.trim() === "" ? null : parsedPrice);
      return api.createListing(id!, { style, extra_facts: extra.trim() || null, include_price: includePrice, use_environment: useEnv && !!envHl.data?.available });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["listings", id] }),
  });

  const remove = useMutation({
    mutationFn: (lid: string) => api.deleteListing(id!, lid),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["listings", id] }),
  });

  const copy = async (l: Listing) => {
    await Clipboard.setStringAsync(listingText(l));
    setCopied(l.id);
    setTimeout(() => setCopied(null), 2000);
  };

  const photos = useQuery({ queryKey: ["photos", id], queryFn: () => api.listPhotos(id!), enabled: !!id && pack.unlocked });
  const retouched = (photos.data ?? []).filter((p) => p.status === "done" && p.retouched_path);
  const exporter = usePhotoExport();
  const [exportedId, setExportedId] = useState<string | null>(null);
  const exportAll = (l: Listing) => {
    setExportedId(l.id);
    return exporter.shareListing(
      listingText(l),
      retouched.map((p, i) => ({ uri: api.photoExportUrl(p.id), fileName: `achetemamaison-${id!.slice(-6)}-photo-${i + 1}-retouchee.jpg` })),
      `export-${l.id}`,
    );
  };

  return (
    <View style={styles.screen} testID="listing-screen">
      <ScreenHeader title="Annonce IA" subtitle="Claude Sonnet 4.6 · n’invente aucune information" onBack={() => router.back()} />
      <KeyboardAwareScrollView
        contentContainerStyle={[styles.content, { paddingBottom: CTA_HEIGHT + insets.bottom + spacing.lg }]}
        bottomOffset={CTA_HEIGHT + spacing.lg}
        keyboardShouldPersistTaps="handled"
      >
        {!pack.loading && !pack.unlocked ? <PremiumGate propertyId={id!} feature="la rédaction de l’annonce par l’IA" testID="listing-premium-gate" /> : null}
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
        <View style={styles.envBox} testID="listing-env-box">
          <View style={styles.switchRow}>
            <View style={{ flex: 1, flexDirection: "row", alignItems: "center", gap: spacing.sm }}>
              <TreeIcon size={18} color={colors.onBrandTertiary} />
              <Text style={[styles.switchLabel, { flex: 1 }]}>Citer les atouts du quartier mesurés</Text>
            </View>
            <Switch
              testID="listing-use-environment"
              value={useEnv && !!envHl.data?.available}
              disabled={!envHl.data?.available}
              onValueChange={setUseEnv}
              trackColor={{ true: colors.brandPrimary, false: colors.surfaceTertiary }}
              thumbColor={Platform.OS === "android" ? colors.surfaceSecondary : undefined}
            />
          </View>
          {envHl.data?.available ? (
            useEnv ? (
              envHl.data.highlights.length ? (
                <View style={styles.chips} testID="listing-env-highlights">
                  {envHl.data.highlights.map((h) => <Text key={h.key} style={styles.envChip}>{h.text}</Text>)}
                </View>
              ) : <Text style={styles.envHint}>Aucun atout mesurable dans les rayons analysés : l’annonce ne parlera pas du quartier.</Text>
            ) : <Text style={styles.envHint}>L’annonce ne mentionnera pas le quartier.</Text>
          ) : (
            <Pressable testID="listing-env-run" accessibilityRole="button" onPress={() => router.push(`/property/${id}/environment`)} style={{ minHeight: 44, justifyContent: "center" }}>
              <Text style={styles.envHint}>Lancez d’abord l’analyse de l’environnement du bien pour que l’IA puisse citer commerces, école, gare ou parc avec leur distance réelle. <Text style={styles.envLink}>Lancer l’analyse →</Text></Text>
            </Pressable>
          )}
          <Text style={styles.envHint}>Seules des distances mesurées (IGN, OpenStreetMap) sont citées, sans qualificatif ni invention.</Text>
        </View>
        <View style={styles.switchRow}>
          <Text style={styles.switchLabel}>Mentionner le prix dans l’annonce</Text>
          <Switch
            testID="listing-include-price"
            value={includePrice}
            onValueChange={setIncludePrice}
            trackColor={{ true: colors.brandPrimary, false: colors.surfaceTertiary }}
            thumbColor={Platform.OS === "android" ? colors.surfaceSecondary : undefined}
          />
        </View>
        {includePrice ? (
          <View style={styles.priceBox} testID="listing-price-box">
            <Field
              label="Prix de vente souhaité"
              testID="listing-price-input"
              placeholder={prop.data?.estimation ? String(Math.round(prop.data.estimation.value / 1000) * 1000) : "250000"}
              suffix="€"
              keyboardType="number-pad"
              value={priceText}
              onChangeText={(t) => setPriceInput(t.replace(/[^\d]/g, ""))}
              error={priceValid ? undefined : "Prix entre 10 000 € et 20 000 000 €"}
              hint={
                priceText.trim()
                  ? `L’annonce affichera « ${Number(priceText).toLocaleString("fr-FR")} € » à la place de la fourchette d’estimation.`
                  : prop.data?.estimation
                    ? `Sans prix saisi, l’annonce mentionne la fourchette estimée (${formatK(prop.data.estimation.low)} – ${formatK(prop.data.estimation.high)}).`
                    : "Sans prix saisi, l’annonce mentionne la fourchette estimée."
              }
            />
            {prop.data?.estimation ? (
              <View style={styles.chips}>
                {[prop.data.estimation.low, prop.data.estimation.value, prop.data.estimation.high].map((v, i) => (
                  <Pressable key={i} testID={`listing-price-chip-${i}`} accessibilityRole="button" onPress={() => setPriceInput(String(Math.round(v / 1000) * 1000))} style={styles.chip}>
                    <Text style={styles.chipText}>{["Bas", "Central", "Haut"][i]} · {formatK(v)}</Text>
                  </Pressable>
                ))}
              </View>
            ) : null}
            {priceDirty && priceValid ? (
              <PrimaryButton
                title={priceText.trim() === "" ? "Retirer le prix" : "Enregistrer ce prix"}
                variant="secondary"
                loading={savePrice.isPending}
                onPress={() => savePrice.mutate(priceText.trim() === "" ? null : parsedPrice)}
                testID="listing-price-save"
              />
            ) : null}
            {savePrice.isError ? <Text style={styles.priceError} testID="listing-price-error">{(savePrice.error as Error).message}</Text> : null}
          </View>
        ) : null}
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
                {l.used_environment ? <Text style={styles.envPill} testID={`listing-env-pill-${i}`}>Quartier mesuré</Text> : null}
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
              <Pressable
                testID={`listing-export-${i}`}
                accessibilityRole="button"
                disabled={exporter.busyKey !== null}
                onPress={() => (pack.unlocked ? exportAll(l) : router.push(`/property/${id}/pack`))}
                style={({ pressed }) => [styles.exportBtn, pressed && { opacity: 0.85 }]}
              >
                {exporter.busyKey === `export-${l.id}` ? <ActivityIndicator color={colors.onBrandPrimary} /> : <ShareNetworkIcon size={18} color={colors.onBrandPrimary} weight="bold" />}
                <Text style={styles.exportLabel}>
                  {retouched.length ? `Exporter l’annonce complète · texte + ${retouched.length} photo${retouched.length > 1 ? "s" : ""}` : "Exporter l’annonce (texte)"}
                </Text>
              </Pressable>
              <Text style={styles.exportHint}>Leboncoin, SeLoger, WhatsApp… : le texte est copié et partagé, les photos retouchées (signées du logo) sont enregistrées dans votre galerie.</Text>
              {exporter.status && exporter.busyKey === null && exportedId === l.id ? (
                <View style={[styles.statusRow, exporter.status.kind === "saved" ? styles.statusOk : styles.statusWarn]} testID={`listing-export-status-${i}`}>
                  {exporter.status.kind === "saved" ? <CheckIcon size={16} color={colors.success} weight="bold" /> : <WarningIcon size={16} color={colors.warning} weight="fill" />}
                  <Text style={[styles.statusText, { color: exporter.status.kind === "saved" ? colors.success : colors.warning }]}>{exporter.status.message}</Text>
                </View>
              ) : null}
            </View>
          ))
        )}
      </KeyboardAwareScrollView>

      <KeyboardStickyView offset={{ closed: 0, opened: insets.bottom }}>
        <View style={[styles.cta, { paddingBottom: insets.bottom + spacing.lg }]}>
          <PrimaryButton
            title={pack.unlocked ? (generate.isPending ? "Rédaction en cours…" : "Générer l’annonce") : "Débloquer le Pack premium · 49 €"}
            onPress={() => (pack.unlocked ? generate.mutate() : router.push(`/property/${id}/pack`))}
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
  envBox: { backgroundColor: colors.brandTertiary, borderRadius: radius.lg, padding: spacing.lg, gap: spacing.sm },
  envChip: { fontFamily: fonts.medium, fontSize: 12, color: colors.onBrandTertiary, backgroundColor: colors.surface, paddingHorizontal: spacing.md, paddingVertical: 6, borderRadius: radius.pill, overflow: "hidden" },
  envHint: { fontFamily: fonts.regular, fontSize: 12, lineHeight: 17, color: colors.onBrandTertiary, opacity: 0.85 },
  envLink: { fontFamily: fonts.semibold, color: colors.brandPrimary, opacity: 1 },
  envPill: { fontFamily: fonts.semibold, fontSize: 12, color: colors.success, backgroundColor: colors.successSoft, paddingHorizontal: spacing.md, height: 26, lineHeight: 26, borderRadius: radius.pill, overflow: "hidden" },

  switchLabel: { flex: 1, fontFamily: fonts.medium, fontSize: 14, color: colors.onSurface },
  priceBox: { gap: spacing.md, backgroundColor: colors.surface, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, padding: spacing.lg },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  chip: { minHeight: 36, paddingHorizontal: spacing.md, borderRadius: radius.pill, backgroundColor: colors.brandTertiary, justifyContent: "center" },
  chipText: { fontFamily: fonts.semibold, fontSize: 12, color: colors.onBrandTertiary },
  priceError: { fontFamily: fonts.medium, fontSize: 12, color: colors.error },
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
  exportBtn: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: spacing.sm, minHeight: 48, borderRadius: radius.md, backgroundColor: colors.brandPrimary, paddingHorizontal: spacing.md },
  exportLabel: { fontFamily: fonts.semibold, fontSize: 14, color: colors.onBrandPrimary, textAlign: "center" },
  exportHint: { fontFamily: fonts.regular, fontSize: 12, lineHeight: 17, color: colors.muted },
  statusRow: { flexDirection: "row", gap: spacing.sm, alignItems: "flex-start", borderRadius: radius.md, padding: spacing.md },
  statusOk: { backgroundColor: colors.successSoft },
  statusWarn: { backgroundColor: colors.warningSoft },
  statusText: { flex: 1, fontFamily: fonts.medium, fontSize: 12, lineHeight: 17 },
  cta: { paddingHorizontal: spacing.lg, paddingTop: spacing.md, backgroundColor: colors.surface, borderTopWidth: 1, borderTopColor: colors.divider },
  sparkle: { position: "absolute", right: spacing.xl, top: 120 },
}));
