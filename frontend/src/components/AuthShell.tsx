import { useRouter } from "expo-router";
import { CaretLeftIcon, WarningIcon } from "phosphor-react-native";
import { ReactNode } from "react";
import { Pressable, ScrollView, Text, View } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

interface Props {
  title: string;
  subtitle?: string;
  children: ReactNode;
  error?: string | null;
  success?: string | null;
  footer?: ReactNode;
  testID: string;
  backTo?: string;
}

/** Shared layout for the authentication screens (welcome → sign-in / sign-up / reset). */
export function AuthShell({ title, subtitle, children, error, success, footer, testID, backTo }: Props) {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const Scroll = KeyboardAwareScrollView ?? ScrollView;
  return (
    <View style={[styles.screen, { paddingTop: insets.top }]} testID={testID}>
      <Scroll contentContainerStyle={[styles.content, { paddingBottom: insets.bottom + spacing.xl }]} keyboardShouldPersistTaps="handled">
        <Pressable
          testID={`${testID}-back`}
          accessibilityRole="button"
          accessibilityLabel="Retour"
          onPress={() => (router.canGoBack() ? router.back() : router.replace((backTo ?? "/welcome") as any))}
          style={styles.back}
        >
          <CaretLeftIcon size={22} color={colors.onSurface} />
        </Pressable>
        <Text style={styles.brand}>Estimo</Text>
        <Text style={styles.title}>{title}</Text>
        {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
        <View style={styles.form}>{children}</View>
        {error ? (
          <View style={styles.banner} testID={`${testID}-error`}>
            <WarningIcon size={18} color={colors.error} weight="fill" />
            <Text style={[styles.bannerText, { color: colors.error }]}>{error}</Text>
          </View>
        ) : null}
        {success ? (
          <View style={[styles.banner, { backgroundColor: colors.successSoft }]} testID={`${testID}-success`}>
            <Text style={[styles.bannerText, { color: colors.success }]}>{success}</Text>
          </View>
        ) : null}
        {footer ? <View style={styles.footer}>{footer}</View> : null}
      </Scroll>
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  screen: { flex: 1, backgroundColor: colors.surface },
  content: { padding: spacing.lg, gap: spacing.md },
  back: { width: 44, height: 44, borderRadius: radius.pill, alignItems: "center", justifyContent: "center", backgroundColor: colors.surfaceSecondary, marginBottom: spacing.sm },
  brand: { fontFamily: fonts.bold, fontSize: 14, letterSpacing: 1.5, textTransform: "uppercase", color: colors.brandPrimary },
  title: { fontFamily: fonts.bold, fontSize: 28, lineHeight: 34, color: colors.onSurface },
  subtitle: { fontFamily: fonts.regular, fontSize: 15, lineHeight: 22, color: colors.onSurfaceTertiary },
  form: { marginTop: spacing.md, gap: spacing.sm },
  banner: { flexDirection: "row", alignItems: "center", gap: spacing.sm, backgroundColor: colors.errorSoft, borderRadius: radius.md, padding: spacing.md },
  bannerText: { flex: 1, fontFamily: fonts.medium, fontSize: 13, lineHeight: 19 },
  footer: { alignItems: "center", gap: spacing.sm, marginTop: spacing.md },
}));
