import { useMutation } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { ActivityIndicator, Pressable, Text, TextInput, View } from "react-native";

import { EMPTY_FEATURES, Estimation, GeocodeResult, api, formatEuro, formatInt } from "@/src/api";
import { useSession } from "@/src/auth";
import { PrimaryButton } from "@/src/components/PrimaryButton";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";
import { useBreakpoint } from "@/src/web/useBreakpoint";

const CONDITIONS = [["a_renover", "À rénover"], ["travaux", "Travaux"], ["correct", "Correct"], ["bon", "Bon"], ["tres_bon", "Très bon"], ["neuf_renove", "Neuf / rénové"]] as const;

/** Estimation gratuite sans compte : adresse + 5 questions → fourchette ; la création de compte débloque le détail et la sauvegarde. */
export function FreeEstimate() {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();
  const { user } = useSession();
  const { isTablet } = useBreakpoint();
  const [q, setQ] = useState("");
  const [suggestions, setSuggestions] = useState<GeocodeResult[]>([]);
  const [addr, setAddr] = useState<GeocodeResult | null>(null);
  const [type, setType] = useState<"maison" | "appartement">("maison");
  const [surface, setSurface] = useState("");
  const [rooms, setRooms] = useState("4");
  const [year, setYear] = useState("");
  const [land, setLand] = useState("");
  const [condition, setCondition] = useState<(typeof CONDITIONS)[number][0]>("bon");

  useEffect(() => {
    if (addr || q.trim().length < 4) return setSuggestions([]);
    const t = setTimeout(() => api.geocode(q).then((r) => setSuggestions(r.results.slice(0, 5))).catch(() => setSuggestions([])), 300);
    return () => clearTimeout(t);
  }, [q, addr]);

  const estimate = useMutation({
    mutationFn: () =>
      api.estimatePreview({
        address_label: addr!.label, lat: addr!.lat, lon: addr!.lon, code_commune: addr!.citycode, commune: addr!.city, postcode: addr!.postcode,
        property_type: type, surface: Number(surface), rooms: Math.max(1, Number(rooms) || 3), bedrooms: Math.max(0, (Number(rooms) || 3) - 2),
        year_built: year ? Number(year) : null,
        condition, land_surface: type === "maison" && land ? Number(land) : null, features: EMPTY_FEATURES,
      }),
  });
  const canSubmit = !!addr && Number(surface) >= 9 && !estimate.isPending;
  const est: Estimation | undefined = estimate.data;

  return (
    <View style={styles.card} testID="free-estimate">
      <Text style={styles.title}>Estimez votre bien gratuitement, sans compte</Text>
      <Text style={styles.sub}>Fourchette calculée à partir des ventes réelles enregistrées autour de l’adresse (données DVF).</Text>

      <Text style={styles.label}>Adresse du bien</Text>
      <TextInput
        testID="free-address"
        style={styles.input}
        placeholder="12 rue des Lilas, 41000 Blois"
        placeholderTextColor={colors.muted}
        value={addr ? addr.label : q}
        onChangeText={(t) => { setAddr(null); setQ(t); }}
        autoCorrect={false}
      />
      {suggestions.length > 0 ? (
        <View style={styles.suggestions} testID="free-suggestions">
          {suggestions.map((s) => (
            <Pressable key={s.id} testID={`free-suggestion-${s.id}`} accessibilityRole="button" onPress={() => { setAddr(s); setSuggestions([]); }} style={({ hovered }: any) => [styles.suggestion, hovered && { backgroundColor: colors.surfaceSecondary }]}>
              <Text style={styles.suggestionText}>{s.label}</Text>
            </Pressable>
          ))}
        </View>
      ) : null}

      <View style={[styles.grid, isTablet && { flexDirection: "row" }]}>
        <View style={styles.col}>
          <Text style={styles.label}>Type de bien</Text>
          <View style={styles.seg}>
            {(["maison", "appartement"] as const).map((t) => (
              <Pressable key={t} testID={`free-type-${t}`} accessibilityRole="button" onPress={() => setType(t)} style={[styles.segItem, type === t && styles.segItemActive]}>
                <Text style={[styles.segText, type === t && styles.segTextActive]} numberOfLines={1} adjustsFontSizeToFit>{t === "maison" ? "Maison" : "Appartement"}</Text>
              </Pressable>
            ))}
          </View>
        </View>
        <View style={styles.col}>
          <Text style={styles.label}>Surface habitable (m²)</Text>
          <TextInput testID="free-surface" style={styles.input} keyboardType="numeric" inputMode="numeric" placeholder="110" placeholderTextColor={colors.muted} value={surface} onChangeText={setSurface} />
        </View>
        <View style={styles.col}>
          <Text style={styles.label}>Pièces</Text>
          <TextInput testID="free-rooms" style={styles.input} keyboardType="numeric" inputMode="numeric" value={rooms} onChangeText={setRooms} />
        </View>
      </View>
      <View style={[styles.grid, isTablet && { flexDirection: "row" }]}>
        <View style={styles.col}>
          <Text style={styles.label}>Année de construction (facultatif)</Text>
          <TextInput testID="free-year" style={styles.input} keyboardType="numeric" inputMode="numeric" placeholder="1985" placeholderTextColor={colors.muted} value={year} onChangeText={setYear} />
        </View>
        {type === "maison" ? (
          <View style={styles.col}>
            <Text style={styles.label}>Terrain (m², facultatif)</Text>
            <TextInput testID="free-land" style={styles.input} keyboardType="numeric" inputMode="numeric" placeholder="800" placeholderTextColor={colors.muted} value={land} onChangeText={setLand} />
          </View>
        ) : null}
      </View>
      <Text style={styles.label}>État général</Text>
      <View style={styles.chips}>
        {CONDITIONS.map(([k, l]) => (
          <Pressable key={k} testID={`free-cond-${k}`} accessibilityRole="button" onPress={() => setCondition(k)} style={[styles.chip, condition === k && styles.chipActive]}>
            <Text style={[styles.chipText, condition === k && styles.chipTextActive]}>{l}</Text>
          </Pressable>
        ))}
      </View>

      <PrimaryButton title={estimate.isPending ? "Calcul en cours…" : "Obtenir ma fourchette gratuite"} onPress={() => estimate.mutate()} disabled={!canSubmit} testID="free-submit" />
      {estimate.isPending ? <ActivityIndicator color={colors.brandPrimary} /> : null}
      {estimate.isError ? <Text style={styles.error} testID="free-error">{(estimate.error as Error).message || "Estimation indisponible pour cette adresse."}</Text> : null}

      {est ? (
        <View style={styles.result} testID="free-result">
          <Text style={styles.resultLabel}>Valeur estimée</Text>
          <Text style={styles.resultValue} testID="free-result-value">{formatEuro(est.value)}</Text>
          <Text style={styles.resultRange}>Fourchette {formatEuro(est.low)} – {formatEuro(est.high)} · {formatInt(est.price_m2)} €/m² · {est.confidence.n_comparables} ventes comparables ({est.confidence.radius_label})</Text>
          <Text style={styles.resultHint}>
            Créez un compte gratuit pour sauvegarder cette estimation, détailler les équipements, consulter les ventes comparables, l’analyse de
            l’environnement et préparer la vente (photos, annonce, dossier).
          </Text>
          <PrimaryButton title={user ? "Enregistrer ce bien dans mon espace" : "Créer mon compte gratuit"} onPress={() => router.navigate(user ? "/new" : "/sign-up")} testID="free-result-cta" />
        </View>
      ) : null}
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  card: { backgroundColor: colors.surface, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, padding: spacing.lg, gap: spacing.sm, shadowColor: colors.onSurface, shadowOpacity: 0.06, shadowRadius: 16, shadowOffset: { width: 0, height: 6 } },
  title: { fontFamily: fonts.bold, fontSize: 22, color: colors.onSurface },
  sub: { fontFamily: fonts.regular, fontSize: 14, lineHeight: 20, color: colors.onSurfaceTertiary, marginBottom: spacing.sm },
  label: { fontFamily: fonts.semibold, fontSize: 13, color: colors.onSurfaceSecondary, marginTop: spacing.xs },
  input: { minHeight: 48, borderWidth: 1, borderColor: colors.border, borderRadius: radius.md, paddingHorizontal: spacing.md, fontFamily: fonts.regular, fontSize: 15, color: colors.onSurface, backgroundColor: colors.surface },
  suggestions: { borderWidth: 1, borderColor: colors.border, borderRadius: radius.md, overflow: "hidden" },
  suggestion: { minHeight: 44, justifyContent: "center", paddingHorizontal: spacing.md, borderBottomWidth: 1, borderBottomColor: colors.border },
  suggestionText: { fontFamily: fonts.regular, fontSize: 14, color: colors.onSurface },
  grid: { flexDirection: "column", gap: spacing.md },
  col: { flex: 1, gap: spacing.xs },
  seg: { flexDirection: "row", backgroundColor: colors.surfaceSecondary, borderRadius: radius.md, padding: 4, minHeight: 48 },
  segItem: { flex: 1, alignItems: "center", justifyContent: "center", borderRadius: radius.sm, paddingHorizontal: 4, overflow: "hidden" },
  segItemActive: { backgroundColor: colors.brandPrimary },
  segText: { fontFamily: fonts.semibold, fontSize: 13, color: colors.onSurfaceSecondary },
  segTextActive: { color: colors.onBrandPrimary },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  chip: { minHeight: 40, paddingHorizontal: spacing.md, justifyContent: "center", borderRadius: radius.pill, borderWidth: 1, borderColor: colors.border },
  chipActive: { backgroundColor: colors.brandPrimary, borderColor: colors.brandPrimary },
  chipText: { fontFamily: fonts.medium, fontSize: 13, color: colors.onSurface },
  chipTextActive: { color: colors.onBrandPrimary },
  error: { fontFamily: fonts.regular, fontSize: 13, color: colors.error },
  result: { marginTop: spacing.md, backgroundColor: colors.brandTertiary, borderRadius: radius.lg, padding: spacing.lg, gap: spacing.sm },
  resultLabel: { fontFamily: fonts.semibold, fontSize: 12, letterSpacing: 1, textTransform: "uppercase", color: colors.onBrandTertiary },
  resultValue: { fontFamily: fonts.bold, fontSize: 36, color: colors.onBrandTertiary },
  resultRange: { fontFamily: fonts.medium, fontSize: 14, lineHeight: 20, color: colors.onBrandTertiary },
  resultHint: { fontFamily: fonts.regular, fontSize: 13, lineHeight: 19, color: colors.onBrandTertiary },
}));
