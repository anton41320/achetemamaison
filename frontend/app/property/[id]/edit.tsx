import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocalSearchParams, useRouter } from "expo-router";
import { WarningIcon } from "phosphor-react-native";
import { useEffect, useState } from "react";
import { ActivityIndicator, Text, View } from "react-native";
import { KeyboardAwareScrollView, KeyboardStickyView } from "react-native-keyboard-controller";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { CONDITION_LABELS, Condition, EMPTY_FEATURES, Features, api } from "@/src/api";
import { FeaturesForm } from "@/src/components/FeaturesForm";
import { Field, Segmented, Stepper } from "@/src/components/Form";
import { PrimaryButton } from "@/src/components/PrimaryButton";
import { ScreenHeader } from "@/src/components/ScreenHeader";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

const CTA_HEIGHT = 92;

export default function EditPropertyScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const queryClient = useQueryClient();

  const prop = useQuery({ queryKey: ["property", id], queryFn: () => api.getProperty(id!), enabled: !!id });

  const [surface, setSurface] = useState("");
  const [rooms, setRooms] = useState(3);
  const [bedrooms, setBedrooms] = useState(2);
  const [yearBuilt, setYearBuilt] = useState("");
  const [condition, setCondition] = useState<Condition>("correct");
  const [landSurface, setLandSurface] = useState("");
  const [features, setFeatures] = useState<Features>(EMPTY_FEATURES);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (prop.data && !loaded) {
      setSurface(String(prop.data.surface));
      setRooms(prop.data.rooms);
      setBedrooms(prop.data.bedrooms);
      setYearBuilt(prop.data.year_built ? String(prop.data.year_built) : "");
      setCondition(prop.data.condition);
      setLandSurface(prop.data.land_surface ? String(prop.data.land_surface) : "");
      setFeatures({ ...EMPTY_FEATURES, ...(prop.data.features ?? {}) });
      setLoaded(true);
    }
  }, [prop.data, loaded]);

  const save = useMutation({
    mutationFn: () =>
      api.updateProperty(id!, {
        surface: Number(surface.replace(",", ".")),
        rooms,
        bedrooms,
        year_built: yearBuilt ? Number(yearBuilt) : null,
        condition,
        land_surface: landSurface ? Number(landSurface.replace(",", ".")) : null,
        features,
      }),
    onSuccess: (p) => {
      queryClient.setQueryData(["property", id], p);
      queryClient.invalidateQueries({ queryKey: ["properties"] });
      queryClient.invalidateQueries({ queryKey: ["dossier", id] });
      if (router.canGoBack()) router.back();
      else router.replace(`/property/${id}`);
    },
  });

  const surfaceNum = Number(surface.replace(",", "."));
  const valid = !Number.isNaN(surfaceNum) && surfaceNum >= 9 && surfaceNum <= 999;
  const p = prop.data;

  return (
    <View style={styles.screen} testID="edit-property-screen">
      <ScreenHeader title="Caractéristiques" subtitle="Complétez pour affiner l’estimation" onBack={() => router.back()} />
      {!p ? (
        <View style={styles.center}><ActivityIndicator color={colors.brandPrimary} /></View>
      ) : (
        <>
          <KeyboardAwareScrollView
            contentContainerStyle={[styles.content, { paddingBottom: CTA_HEIGHT + insets.bottom + spacing.lg }]}
            bottomOffset={CTA_HEIGHT + spacing.lg}
            keyboardShouldPersistTaps="handled"
          >
            <Text style={styles.address}>{p.address_label}</Text>
            <Text style={styles.section}>Le bien</Text>
            <Field label="Surface habitable" testID="edit-surface-input" suffix="m²" keyboardType="decimal-pad" value={surface} onChangeText={setSurface} error={!valid ? "Surface entre 9 et 999 m²" : undefined} />
            <Stepper label="Pièces" value={rooms} onChange={setRooms} min={1} max={20} testID="edit-rooms-stepper" />
            <Stepper label="Chambres" value={bedrooms} onChange={setBedrooms} min={0} max={15} testID="edit-bedrooms-stepper" />
            <Field label="Année de construction" testID="edit-year-input" keyboardType="number-pad" maxLength={4} value={yearBuilt} onChangeText={setYearBuilt} />
            <Segmented
              label="État général"
              testID="edit-condition-segment"
              scroll
              value={condition}
              onChange={setCondition}
              options={(Object.keys(CONDITION_LABELS) as Condition[]).map((c) => ({ value: c, label: CONDITION_LABELS[c] }))}
            />
            {p.property_type === "maison" ? (
              <Field label="Surface du terrain" testID="edit-land-input" suffix="m²" keyboardType="decimal-pad" value={landSurface} onChangeText={setLandSurface} />
            ) : null}
            <FeaturesForm propertyType={p.property_type} value={features} onChange={setFeatures} />
            {save.isError ? (
              <View style={styles.warn} testID="edit-error">
                <WarningIcon size={18} color={colors.error} weight="fill" />
                <Text style={styles.warnText}>{(save.error as Error).message}</Text>
              </View>
            ) : null}
          </KeyboardAwareScrollView>
          <KeyboardStickyView offset={{ closed: 0, opened: insets.bottom }}>
            <View style={[styles.cta, { paddingBottom: insets.bottom + spacing.lg }]}>
              <PrimaryButton title="Enregistrer et recalculer" onPress={() => save.mutate()} loading={save.isPending} disabled={!valid} testID="edit-save-button" />
            </View>
          </KeyboardStickyView>
        </>
      )}
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  screen: { flex: 1, backgroundColor: colors.surface },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  content: { padding: spacing.lg, gap: spacing.lg },
  address: { fontFamily: fonts.medium, fontSize: 14, color: colors.muted },
  section: { fontFamily: fonts.semibold, fontSize: 13, color: colors.muted, textTransform: "uppercase", letterSpacing: 0.6 },
  warn: { flexDirection: "row", gap: spacing.md, alignItems: "flex-start", backgroundColor: colors.errorSoft, borderRadius: radius.md, padding: spacing.lg },
  warnText: { flex: 1, fontFamily: fonts.medium, fontSize: 13, lineHeight: 19, color: colors.error },
  cta: { paddingHorizontal: spacing.lg, paddingTop: spacing.md, backgroundColor: colors.surface, borderTopWidth: 1, borderTopColor: colors.divider },
}));
