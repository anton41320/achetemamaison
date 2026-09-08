import * as Haptics from "expo-haptics";
import { ActivityIndicator, Platform, Pressable, Text, ViewStyle } from "react-native";

import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

interface Props {
  title: string;
  onPress: () => void;
  testID: string;
  disabled?: boolean;
  loading?: boolean;
  variant?: "primary" | "secondary" | "ghost" | "danger";
  style?: ViewStyle;
}

export function PrimaryButton({ title, onPress, testID, disabled, loading, variant = "primary", style }: Props) {
  const styles = useStyles();
  const { colors } = useTheme();
  const isDisabled = disabled || loading;
  const textColor =
    variant === "primary" ? colors.onBrandPrimary
      : variant === "danger" ? colors.error
        : variant === "secondary" ? colors.onBrandSecondary
          : colors.brandPrimary;

  const handlePress = () => {
    if (Platform.OS !== "web") Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
    onPress();
  };

  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      disabled={isDisabled}
      onPress={handlePress}
      style={({ pressed }) => [
        styles.base,
        styles[variant],
        isDisabled && styles.disabled,
        pressed && !isDisabled && styles.pressed,
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={textColor} />
      ) : (
        <Text style={[styles.label, { color: textColor }]}>{title}</Text>
      )}
    </Pressable>
  );
}

const useStyles = makeStyles((colors) => ({
  base: {
    minHeight: 52,
    borderRadius: radius.md,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: spacing.xl,
  },
  primary: { backgroundColor: colors.brandPrimary },
  secondary: { backgroundColor: colors.brandSecondary },
  ghost: { backgroundColor: colors.brandTertiary },
  danger: { backgroundColor: colors.errorSoft },
  disabled: { opacity: 0.45 },
  pressed: { opacity: 0.85, transform: [{ scale: 0.99 }] },
  label: { fontFamily: fonts.semibold, fontSize: 16 },
}));
