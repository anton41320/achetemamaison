import { useMutation, useQueryClient } from "@tanstack/react-query";
import * as Haptics from "expo-haptics";
import { useRouter } from "expo-router";
import { useState } from "react";
import { Platform, View } from "react-native";
import { KeyboardAwareScrollView, KeyboardStickyView } from "react-native-keyboard-controller";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { PropertyIn, api } from "@/src/api";
import { PropertyWizard, WIZARD_STEPS } from "@/src/components/PropertyWizard";
import { ScreenHeader } from "@/src/components/ScreenHeader";
import { makeStyles, radius, spacing } from "@/src/theme";

const CTA_HEIGHT = 92;

export default function NewPropertyScreen() {
  const styles = useStyles();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [step, setStep] = useState(0);

  const create = useMutation({
    mutationFn: (body: PropertyIn) => api.createProperty(body),
    onSuccess: (prop) => {
      queryClient.invalidateQueries({ queryKey: ["properties"] });
      if (Platform.OS !== "web") Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
      router.replace(`/property/${prop.id}`);
    },
  });

  const back = () => {
    if (step === 0) router.back();
    else setStep(step - 1);
  };

  return (
    <View style={styles.screen} testID="new-property-screen">
      <ScreenHeader title="Nouvelle estimation" subtitle={`Étape ${step + 1} sur ${WIZARD_STEPS.length} · ${WIZARD_STEPS[step]}`} onBack={back} />
      <View style={styles.progress}>
        {WIZARD_STEPS.map((s, i) => (
          <View key={s} style={[styles.progressSeg, i <= step && styles.progressSegActive]} />
        ))}
      </View>

      <PropertyWizard
        step={step}
        onStepChange={setStep}
        onSubmit={(body) => create.mutate(body)}
        submitLabel="Estimer ce bien"
        loading={create.isPending}
        errorMessage={create.isError ? (create.error as Error).message : null}
        renderLayout={(content, cta) => (
          <>
            <KeyboardAwareScrollView
              style={styles.scroll}
              contentContainerStyle={[styles.content, { paddingBottom: CTA_HEIGHT + insets.bottom + spacing.lg }]}
              bottomOffset={CTA_HEIGHT + spacing.lg}
              keyboardShouldPersistTaps="handled"
            >
              {content}
            </KeyboardAwareScrollView>
            <KeyboardStickyView offset={{ closed: 0, opened: insets.bottom }}>
              <View style={[styles.cta, { paddingBottom: insets.bottom + spacing.lg }]}>{cta}</View>
            </KeyboardStickyView>
          </>
        )}
      />
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  screen: { flex: 1, backgroundColor: colors.surface },
  progress: { flexDirection: "row", gap: spacing.sm, paddingHorizontal: spacing.lg, paddingTop: spacing.md },
  progressSeg: { flex: 1, height: 4, borderRadius: radius.pill, backgroundColor: colors.surfaceTertiary },
  progressSegActive: { backgroundColor: colors.brandPrimary },
  scroll: { flex: 1 },
  content: { padding: spacing.lg, paddingTop: spacing.xl },
  cta: { paddingHorizontal: spacing.lg, paddingTop: spacing.md, backgroundColor: colors.surface, borderTopWidth: 1, borderTopColor: colors.divider },
}));
