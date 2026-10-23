import { useQuery } from "@tanstack/react-query";
import * as Haptics from "expo-haptics";
import { BuildingsIcon, CheckCircleIcon, HouseIcon, MapPinIcon, WarningIcon } from "phosphor-react-native";
import { ReactNode, useEffect, useMemo, useState } from "react";
import { ActivityIndicator, Platform, Pressable, Text, View } from "react-native";
import Animated, { FadeIn } from "react-native-reanimated";

import { CONDITION_LABELS, Condition, EMPTY_FEATURES, Features, GeocodeResult, PropertyIn, PropertyType, api } from "@/src/api";
import { FeaturesForm } from "@/src/components/FeaturesForm";
import { WorksForm } from "@/src/components/WorksForm";
import { Field, Segmented, Stepper } from "@/src/components/Form";
import { PrimaryButton } from "@/src/components/PrimaryButton";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

export const WIZARD_STEPS = ["Adresse", "Le bien", "Détails", "Équipements"] as const;
const LAST = WIZARD_STEPS.length - 1;

function useDebounced(value: string, delay = 350) {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return v;
}

interface Props {
  /** Appelé à la dernière étape avec le bien complet (adresse, caractéristiques, équipements). */
  onSubmit: (body: PropertyIn) => void;
  submitLabel: string;
  loading?: boolean;
  errorMessage?: string | null;
  /** Étape courante contrôlée de l'extérieur (en-tête, barre de progression, bouton retour). */
  step: number;
  onStepChange: (step: number) => void;
  /** Mise en page : par défaut contenu puis bouton ; le parent peut placer le contenu dans un défilement et le bouton dans une barre collante. */
  renderLayout?: (content: ReactNode, cta: ReactNode) => ReactNode;
}

/**
 * Questionnaire complet d'estimation en 4 étapes (adresse → bien → détails → équipements), partagé par l'écran
 * « Nouvelle estimation » de l'application et par l'estimation gratuite du site Web.
 */
export function PropertyWizard({ onSubmit, submitLabel, loading, errorMessage, step, onStepChange, renderLayout }: Props) {
  const styles = useStyles();
  const { colors } = useTheme();

  const [query, setQuery] = useState("");
  const [address, setAddress] = useState<GeocodeResult | null>(null);
  const [propertyType, setPropertyType] = useState<PropertyType>("maison");
  const [surface, setSurface] = useState("");
  const [rooms, setRooms] = useState(3);
  const [bedrooms, setBedrooms] = useState(2);
  const [yearBuilt, setYearBuilt] = useState("");
  const [condition, setCondition] = useState<Condition>("correct");
  const [landSurface, setLandSurface] = useState("");
  const [features, setFeatures] = useState<Features>(EMPTY_FEATURES);
  const [touched, setTouched] = useState(false);

  const debounced = useDebounced(query);
  const geocode = useQuery({
    queryKey: ["geocode", debounced],
    queryFn: () => api.geocode(debounced),
    enabled: debounced.trim().length >= 3 && !address,
    staleTime: 60_000,
  });

  const surfaceNum = Number(surface.replace(",", "."));
  const surfaceError = touched && (!surface || Number.isNaN(surfaceNum) || surfaceNum < 9 || surfaceNum > 999)
    ? "Indiquez une surface entre 9 et 999 m²"
    : undefined;
  const yearNum = yearBuilt ? Number(yearBuilt) : null;
  const yearError = touched && yearBuilt && (Number.isNaN(yearNum) || yearNum! < 1500 || yearNum! > 2030)
    ? "Année invalide"
    : undefined;
  const landNum = landSurface ? Number(landSurface.replace(",", ".")) : null;
  const landError = touched && landSurface && (Number.isNaN(landNum) || landNum! < 0) ? "Surface invalide" : undefined;

  const canContinue = useMemo(() => {
    if (step === 0) return !!address && address.covered;
    if (step === 1) return !!surface && !Number.isNaN(surfaceNum) && surfaceNum >= 9 && surfaceNum <= 999;
    if (step === 2) return !yearError && !landError;
    return true;
  }, [step, address, surface, surfaceNum, yearError, landError]);

  const next = () => {
    setTouched(true);
    if (!canContinue) return;
    if (Platform.OS !== "web") Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium).catch(() => {});
    if (step < LAST) {
      onStepChange(step + 1);
      setTouched(false);
      return;
    }
    if (!address) return;
    onSubmit({
      address_label: address.label,
      lat: address.lat,
      lon: address.lon,
      code_commune: address.citycode,
      commune: address.city,
      postcode: address.postcode,
      property_type: propertyType,
      surface: surfaceNum,
      rooms,
      bedrooms,
      year_built: yearNum,
      condition,
      land_surface: propertyType === "maison" && landNum !== null ? landNum : null,
      features,
    });
  };

  const errorBanner = errorMessage ? (
    <View style={styles.warnBanner} testID="create-error">
      <WarningIcon size={18} color={colors.error} weight="fill" />
      <Text style={[styles.warnText, { color: colors.error }]}>{errorMessage}</Text>
    </View>
  ) : null;

  const cta = (
    <PrimaryButton
      title={step < LAST ? "Continuer" : submitLabel}
      onPress={next}
      disabled={!canContinue && touched}
      loading={loading}
      testID={step < LAST ? "step-continue-button" : "estimate-submit-button"}
    />
  );

  const content = (
    <>
      {step === 0 ? (
        <Animated.View entering={FadeIn.duration(250)} style={styles.section}>
          <Text style={styles.h2}>Où se situe le bien ?</Text>
          <Text style={styles.p}>
            Toute la France (métropole, Corse et DOM) sauf l’Alsace-Moselle (57, 67, 68), dont les ventes ne sont pas
            publiées par l’État. L’adresse est géolocalisée via la Base Adresse Nationale.
          </Text>
          <Field
            label="Adresse"
            testID="address-input"
            placeholder="12 rue de la Gare, Blois"
            value={address ? address.label : query}
            onChangeText={(t) => {
              setAddress(null);
              setQuery(t);
            }}
            autoCorrect={false}
            autoCapitalize="none"
            returnKeyType="search"
          />
          {address ? (
            <View style={styles.selectedCard} testID="address-selected">
              <CheckCircleIcon size={22} color={colors.success} weight="fill" />
              <View style={{ flex: 1 }}>
                <Text style={styles.selectedLabel}>{address.label}</Text>
                <Text style={styles.selectedMeta}>
                  {address.city} · Dépt {address.dept}{address.covered ? "" : " · hors zone couverte"}
                </Text>
              </View>
            </View>
          ) : geocode.isFetching ? (
            <View style={styles.loadingRow}>
              <ActivityIndicator color={colors.brandPrimary} />
              <Text style={styles.p}>Recherche d’adresses…</Text>
            </View>
          ) : geocode.data ? (
            <View style={styles.results} testID="address-results">
              {geocode.data.results.length === 0 ? (
                <Text style={styles.p}>Aucune adresse trouvée.</Text>
              ) : (
                geocode.data.results.map((r, i) => (
                  <Pressable
                    key={r.id ?? `${r.label}-${i}`}
                    testID={`address-result-${i}`}
                    accessibilityRole="button"
                    onPress={() => {
                      setAddress(r);
                      setQuery(r.label);
                    }}
                    style={({ pressed }) => [styles.resultRow, pressed && styles.resultPressed]}
                  >
                    <MapPinIcon size={18} color={r.covered ? colors.brandPrimary : colors.muted} weight="duotone" />
                    <View style={{ flex: 1 }}>
                      <Text style={styles.resultLabel}>{r.label}</Text>
                      <Text style={styles.resultMeta}>
                        {r.covered ? `Dépt ${r.dept} · zone couverte` : `Dépt ${r.dept} · hors zone couverte`}
                      </Text>
                    </View>
                  </Pressable>
                ))
              )}
            </View>
          ) : geocode.isError ? (
            <Text style={styles.errorText}>Service d’adresses indisponible. Réessayez.</Text>
          ) : null}
          {address && !address.covered ? (
            <View style={styles.warnBanner} testID="address-uncovered-warning">
              <WarningIcon size={18} color={colors.warning} weight="fill" />
              <Text style={styles.warnText}>
                Cette adresse est hors de la zone couverte (Alsace-Moselle : ventes non publiées par l’État). Aucune
                vente de référence n’est disponible pour l’estimer.
              </Text>
            </View>
          ) : null}
        </Animated.View>
      ) : null}

      {step === 1 ? (
        <Animated.View entering={FadeIn.duration(250)} style={styles.section}>
          <Text style={styles.h2}>Décrivez le bien</Text>
          <Segmented
            label="Type de bien"
            testID="type-segment"
            value={propertyType}
            onChange={setPropertyType}
            options={[
              {
                value: "maison",
                label: "Maison",
                icon: <HouseIcon size={18} color={propertyType === "maison" ? colors.onBrandPrimary : colors.onSurfaceSecondary} />,
              },
              {
                value: "appartement",
                label: "Appartement",
                icon: <BuildingsIcon size={18} color={propertyType === "appartement" ? colors.onBrandPrimary : colors.onSurfaceSecondary} />,
              },
            ]}
          />
          <Field
            label="Surface habitable"
            testID="surface-input"
            placeholder="65"
            suffix="m²"
            keyboardType="decimal-pad"
            value={surface}
            onChangeText={setSurface}
            error={surfaceError}
            hint="Surface loi Carrez ou surface habitable"
          />
          <Stepper label="Pièces" value={rooms} onChange={setRooms} min={1} max={20} testID="rooms-stepper" />
          <Stepper label="Chambres" value={bedrooms} onChange={setBedrooms} min={0} max={15} testID="bedrooms-stepper" />
        </Animated.View>
      ) : null}

      {step === 2 ? (
        <Animated.View entering={FadeIn.duration(250)} style={styles.section}>
          <Text style={styles.h2}>Quelques détails</Text>
          <Text style={styles.p}>Ces éléments ajustent l’estimation de façon transparente (chaque ajustement est affiché).</Text>
          <Field
            label="Année de construction (optionnel)"
            testID="year-input"
            placeholder="1985"
            keyboardType="number-pad"
            maxLength={4}
            value={yearBuilt}
            onChangeText={setYearBuilt}
            error={yearError}
          />
          <Segmented
            label="État général"
            testID="condition-segment"
            scroll
            value={condition}
            onChange={setCondition}
            options={(Object.keys(CONDITION_LABELS) as Condition[]).map((c) => ({ value: c, label: CONDITION_LABELS[c] }))}
          />
          <WorksForm value={features} onChange={setFeatures} />
          {propertyType === "maison" ? (
            <Field
              label="Surface du terrain (optionnel)"
              testID="land-input"
              placeholder="450"
              suffix="m²"
              keyboardType="decimal-pad"
              value={landSurface}
              onChangeText={setLandSurface}
              error={landError}
            />
          ) : null}
          <View style={styles.summary} testID="summary-card">
            <Text style={styles.summaryTitle}>Récapitulatif</Text>
            <Text style={styles.summaryLine}>{address?.label}</Text>
            <Text style={styles.summaryLine}>
              {propertyType === "maison" ? "Maison" : "Appartement"} · {surface} m² · {rooms} pièces · {bedrooms} ch.
            </Text>
          </View>
          {errorBanner}
        </Animated.View>
      ) : null}

      {step === 3 ? (
        <Animated.View entering={FadeIn.duration(250)} style={styles.section}>
          <Text style={styles.h2}>Équipements & confort</Text>
          <Text style={styles.p}>
            Tout est optionnel. Chaque critère renseigné devient un ajustement affiché en % et en € dans le résultat.
          </Text>
          <FeaturesForm propertyType={propertyType} value={features} onChange={setFeatures} />
          {errorBanner}
        </Animated.View>
      ) : null}

    </>
  );

  if (renderLayout) return <>{renderLayout(content, cta)}</>;
  return (
    <>
      {content}
      <View style={styles.inlineCta}>{cta}</View>
    </>
  );
}

const useStyles = makeStyles((colors) => ({
  section: { gap: spacing.lg },
  h2: { fontFamily: fonts.bold, fontSize: 24, color: colors.onSurface },
  p: { fontFamily: fonts.regular, fontSize: 14, lineHeight: 20, color: colors.onSurfaceTertiary },
  errorText: { fontFamily: fonts.medium, fontSize: 13, color: colors.error },
  loadingRow: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  results: { backgroundColor: colors.surfaceSecondary, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, overflow: "hidden" },
  resultRow: { flexDirection: "row", alignItems: "center", gap: spacing.md, padding: spacing.lg, borderBottomWidth: 1, borderBottomColor: colors.divider },
  resultPressed: { backgroundColor: colors.surfaceTertiary },
  resultLabel: { fontFamily: fonts.medium, fontSize: 15, color: colors.onSurfaceSecondary },
  resultMeta: { fontFamily: fonts.regular, fontSize: 12, color: colors.muted, marginTop: 2 },
  selectedCard: { flexDirection: "row", alignItems: "center", gap: spacing.md, backgroundColor: colors.brandTertiary, borderRadius: radius.md, padding: spacing.lg },
  selectedLabel: { fontFamily: fonts.semibold, fontSize: 15, color: colors.onBrandTertiary },
  selectedMeta: { fontFamily: fonts.regular, fontSize: 12, color: colors.onBrandTertiary, marginTop: 2 },
  warnBanner: { flexDirection: "row", gap: spacing.md, alignItems: "flex-start", backgroundColor: colors.warningSoft, borderRadius: radius.md, padding: spacing.lg },
  warnText: { flex: 1, fontFamily: fonts.medium, fontSize: 13, lineHeight: 19, color: colors.warning },
  summary: { backgroundColor: colors.surfaceSecondary, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, padding: spacing.lg, gap: 4 },
  summaryTitle: { fontFamily: fonts.semibold, fontSize: 13, color: colors.muted, textTransform: "uppercase", letterSpacing: 0.6 },
  summaryLine: { fontFamily: fonts.medium, fontSize: 14, color: colors.onSurfaceSecondary },
  inlineCta: { marginTop: spacing.lg },
}));
