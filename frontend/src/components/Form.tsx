import * as Haptics from "expo-haptics";
import { EyeIcon, EyeSlashIcon, MinusIcon, PlusIcon } from "phosphor-react-native";
import { ReactNode, useState } from "react";
import { Platform, Pressable, ScrollView, Text, TextInput, TextInputProps, View } from "react-native";

import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

// ---- Field (label + input) ----
interface FieldProps extends TextInputProps {
  label: string;
  hint?: string;
  suffix?: string;
  error?: string;
  testID: string;
}

export function Field({ label, hint, suffix, error, testID, style, secureTextEntry, ...rest }: FieldProps) {
  const styles = useStyles();
  const { colors } = useTheme();
  const [revealed, setRevealed] = useState(false);
  return (
    <View style={styles.fieldWrap}>
      <Text style={styles.label}>{label}</Text>
      <View style={[styles.inputRow, error ? styles.inputError : null]}>
        <TextInput
          testID={testID}
          placeholderTextColor={colors.muted}
          style={[styles.input, style]}
          secureTextEntry={secureTextEntry && !revealed}
          {...rest}
        />
        {suffix ? <Text style={styles.suffix}>{suffix}</Text> : null}
        {secureTextEntry ? (
          <Pressable
            testID={`${testID}-toggle-visibility`}
            accessibilityRole="button"
            accessibilityLabel={revealed ? "Masquer le mot de passe" : "Afficher le mot de passe"}
            onPress={() => setRevealed((v) => !v)}
            hitSlop={8}
            style={styles.eyeBtn}
          >
            {revealed ? <EyeSlashIcon size={22} color={colors.muted} /> : <EyeIcon size={22} color={colors.muted} />}
          </Pressable>
        ) : null}
      </View>
      {error ? (
        <Text style={styles.errorText} testID={`${testID}-error`}>{error}</Text>
      ) : hint ? (
        <Text style={styles.hint}>{hint}</Text>
      ) : null}
    </View>
  );
}

// ---- Segmented / chips ----
interface Option<T extends string> {
  value: T;
  label: string;
  icon?: ReactNode;
}

interface SegmentedProps<T extends string> {
  label?: string;
  options: Option<T>[];
  value: T;
  onChange: (v: T) => void;
  testID: string;
  scroll?: boolean;
}

export function Segmented<T extends string>({ label, options, value, onChange, testID, scroll }: SegmentedProps<T>) {
  const styles = useStyles();
  const select = (v: T) => {
    if (Platform.OS !== "web") Haptics.selectionAsync().catch(() => {});
    onChange(v);
  };
  const chips = options.map((o) => {
    const active = o.value === value;
    return (
      <Pressable
        key={o.value}
        testID={`${testID}-${o.value}`}
        accessibilityRole="button"
        accessibilityState={{ selected: active }}
        onPress={() => select(o.value)}
        style={[styles.chip, scroll ? styles.chipFixed : styles.chipFill, active && styles.chipActive]}
      >
        {o.icon}
        <Text style={[styles.chipLabel, active && styles.chipLabelActive]}>{o.label}</Text>
      </Pressable>
    );
  });
  return (
    <View style={styles.fieldWrap}>
      {label ? <Text style={styles.label}>{label}</Text> : null}
      {scroll ? (
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          style={styles.chipScroller}
          contentContainerStyle={styles.chipRowScroll}
        >
          {chips}
        </ScrollView>
      ) : (
        <View style={styles.chipRow}>{chips}</View>
      )}
    </View>
  );
}

// ---- Stepper ----
interface StepperProps {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
  testID: string;
}

export function Stepper({ label, value, onChange, min, max, testID }: StepperProps) {
  const styles = useStyles();
  const { colors } = useTheme();
  const bump = (d: number) => {
    const next = Math.min(max, Math.max(min, value + d));
    if (next !== value) {
      if (Platform.OS !== "web") Haptics.selectionAsync().catch(() => {});
      onChange(next);
    }
  };
  return (
    <View style={styles.stepperRow}>
      <Text style={styles.stepperLabel}>{label}</Text>
      <View style={styles.stepperControls}>
        <Pressable
          testID={`${testID}-minus`}
          accessibilityRole="button"
          onPress={() => bump(-1)}
          disabled={value <= min}
          style={[styles.stepperBtn, value <= min && styles.stepperBtnDisabled]}
        >
          <MinusIcon size={18} color={colors.onBrandTertiary} weight="bold" />
        </Pressable>
        <Text style={styles.stepperValue} testID={`${testID}-value`}>{value}</Text>
        <Pressable
          testID={`${testID}-plus`}
          accessibilityRole="button"
          onPress={() => bump(1)}
          disabled={value >= max}
          style={[styles.stepperBtn, value >= max && styles.stepperBtnDisabled]}
        >
          <PlusIcon size={18} color={colors.onBrandTertiary} weight="bold" />
        </Pressable>
      </View>
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  fieldWrap: { gap: spacing.sm },
  label: { fontFamily: fonts.semibold, fontSize: 14, color: colors.onSurface },
  hint: { fontFamily: fonts.regular, fontSize: 12, color: colors.muted },
  errorText: { fontFamily: fonts.medium, fontSize: 12, color: colors.error },
  inputRow: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.surfaceSecondary,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    paddingHorizontal: spacing.lg,
    minHeight: 52,
  },
  inputError: { borderColor: colors.error },
  input: { flex: 1, fontFamily: fonts.medium, fontSize: 16, color: colors.onSurfaceSecondary, paddingVertical: 12 },
  suffix: { fontFamily: fonts.medium, fontSize: 15, color: colors.muted, marginLeft: spacing.sm },
  eyeBtn: { width: 44, height: 44, alignItems: "center", justifyContent: "center", marginRight: -spacing.sm },
  chipRow: { flexDirection: "row", gap: spacing.sm },
  chipScroller: { height: 56, marginHorizontal: -spacing.lg },
  chipRowScroll: { gap: spacing.sm, paddingHorizontal: spacing.lg, alignItems: "center" },
  chip: {
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    gap: 6,
    height: 44,
    paddingHorizontal: spacing.lg,
    borderRadius: radius.md,
    backgroundColor: colors.surfaceSecondary,
    borderWidth: 1,
    borderColor: colors.border,
  },
  chipFill: { flex: 1 },
  chipFixed: { flexGrow: 0, flexShrink: 0, flexBasis: "auto", width: "auto", height: 36, borderRadius: radius.pill },
  chipActive: { backgroundColor: colors.brandPrimary, borderColor: colors.brandPrimary },
  chipLabel: { fontFamily: fonts.medium, fontSize: 14, color: colors.onSurfaceSecondary },
  chipLabelActive: { color: colors.onBrandPrimary },
  stepperRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: colors.surfaceSecondary,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    minHeight: 56,
  },
  stepperLabel: { fontFamily: fonts.semibold, fontSize: 14, color: colors.onSurfaceSecondary },
  stepperControls: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  stepperBtn: {
    width: 40,
    height: 40,
    borderRadius: radius.pill,
    backgroundColor: colors.brandTertiary,
    alignItems: "center",
    justifyContent: "center",
  },
  stepperBtnDisabled: { opacity: 0.4 },
  stepperValue: { fontFamily: fonts.bold, fontSize: 18, color: colors.onSurfaceSecondary, minWidth: 24, textAlign: "center" },
}));
