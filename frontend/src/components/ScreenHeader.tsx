import { CaretLeftIcon } from "phosphor-react-native";
import { ReactNode } from "react";
import { Pressable, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { ReportProblemButton } from "@/src/components/ReportProblemButton";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

interface Props {
  title: string;
  subtitle?: string;
  onBack?: () => void;
  right?: ReactNode;
  /** Optional element rendered before the titles (e.g. brand logo on the home screen). */
  leading?: ReactNode;
  testID?: string;
}

export function ScreenHeader({ title, subtitle, onBack, right, leading, testID }: Props) {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  return (
    <View style={[styles.header, { paddingTop: insets.top + spacing.sm }]} testID={testID}>
      <View style={styles.row}>
        {onBack ? (
          <Pressable
            testID="header-back-button"
            accessibilityRole="button"
            accessibilityLabel="Retour"
            onPress={onBack}
            style={styles.backBtn}
          >
            <CaretLeftIcon size={22} color={colors.onSurface} weight="bold" />
          </Pressable>
        ) : null}
        {leading}
        <View style={styles.titles}>
          <Text style={styles.title} numberOfLines={1}>{title}</Text>
          {subtitle ? <Text style={styles.subtitle} numberOfLines={1}>{subtitle}</Text> : null}
        </View>
        <ReportProblemButton />
        {right}
      </View>
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  header: {
    backgroundColor: colors.surface,
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.divider,
  },
  row: { flexDirection: "row", alignItems: "center", gap: spacing.md, minHeight: 44 },
  backBtn: {
    width: 44,
    height: 44,
    borderRadius: radius.pill,
    backgroundColor: colors.surfaceTertiary,
    alignItems: "center",
    justifyContent: "center",
  },
  titles: { flex: 1 },
  title: { fontFamily: fonts.bold, fontSize: 22, color: colors.onSurface },
  subtitle: { fontFamily: fonts.regular, fontSize: 13, color: colors.muted, marginTop: 2 },
}));
