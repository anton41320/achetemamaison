import { File, Paths } from "expo-file-system";
import * as Sharing from "expo-sharing";
import { FilePdfIcon } from "phosphor-react-native";
import { useState } from "react";
import { ActivityIndicator, Linking, Platform, Pressable, Text } from "react-native";

import { api } from "@/src/api";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

interface Props {
  propertyId: string;
}

export function ShareReportButton({ propertyId }: Props) {
  const styles = useStyles();
  const { colors } = useTheme();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const share = async () => {
    setError(null);
    const url = api.reportUrl(propertyId);
    if (Platform.OS === "web") {
      Linking.openURL(url);
      return;
    }
    setBusy(true);
    try {
      const target = new File(Paths.cache, `estimo-${propertyId.slice(-6)}.pdf`);
      const file = await File.downloadFileAsync(url, target, { idempotent: true });
      if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(file.uri, { mimeType: "application/pdf", UTI: "com.adobe.pdf", dialogTitle: "Partager le rapport Estimo" });
      } else {
        await Linking.openURL(url);
      }
    } catch (e) {
      setError((e as Error).message || "Impossible de générer le rapport");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <Pressable
        testID="share-report-button"
        accessibilityRole="button"
        onPress={share}
        disabled={busy}
        style={({ pressed }) => [styles.btn, pressed && { opacity: 0.85 }]}
      >
        {busy ? <ActivityIndicator color={colors.onBrandPrimary} /> : <FilePdfIcon size={20} color={colors.onBrandPrimary} weight="fill" />}
        <Text style={styles.label}>Partager le rapport PDF</Text>
      </Pressable>
      {error ? <Text style={styles.error} testID="share-report-error">{error}</Text> : null}
    </>
  );
}

const useStyles = makeStyles((colors) => ({
  btn: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: spacing.sm, minHeight: 52, borderRadius: radius.md, backgroundColor: colors.brandPrimary, paddingHorizontal: spacing.xl },
  label: { fontFamily: fonts.semibold, fontSize: 16, color: colors.onBrandPrimary },
  error: { fontFamily: fonts.medium, fontSize: 13, color: colors.error, textAlign: "center" },
}));
