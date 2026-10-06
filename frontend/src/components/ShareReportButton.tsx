import { File, Paths } from "expo-file-system";
import * as Sharing from "expo-sharing";
import { FilePdfIcon } from "phosphor-react-native";
import { useState } from "react";
import { ActivityIndicator, Linking, Platform, Pressable, Text } from "react-native";

import { api } from "@/src/api";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

interface Props {
  propertyId: string;
  /** Defaults to the estimation report. */
  url?: string;
  label?: string;
  fileName?: string;
  dialogTitle?: string;
  testID?: string;
}

export function ShareReportButton({ propertyId, url, label = "Partager le rapport PDF", fileName, dialogTitle = "Partager le rapport Achète ma maison", testID = "share-report-button" }: Props) {
  const styles = useStyles();
  const { colors } = useTheme();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const share = async () => {
    setError(null);
    const target = url ?? api.reportUrl(propertyId);
    if (Platform.OS === "web") {
      Linking.openURL(target);
      return;
    }
    setBusy(true);
    try {
      const dest = new File(Paths.cache, fileName ?? `achetemamaison-${propertyId.slice(-6)}.pdf`);
      const file = await File.downloadFileAsync(target, dest, { idempotent: true });
      if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(file.uri, { mimeType: "application/pdf", UTI: "com.adobe.pdf", dialogTitle });
      } else {
        await Linking.openURL(target);
      }
    } catch (e) {
      setError((e as Error).message || "Impossible de générer le document");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <Pressable
        testID={testID}
        accessibilityRole="button"
        onPress={share}
        disabled={busy}
        style={({ pressed }) => [styles.btn, pressed && { opacity: 0.85 }]}
      >
        {busy ? <ActivityIndicator color={colors.onBrandPrimary} /> : <FilePdfIcon size={20} color={colors.onBrandPrimary} weight="fill" />}
        <Text style={styles.label}>{label}</Text>
      </Pressable>
      {error ? <Text style={styles.error} testID={`${testID}-error`}>{error}</Text> : null}
    </>
  );
}

const useStyles = makeStyles((colors) => ({
  btn: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: spacing.sm, minHeight: 52, borderRadius: radius.md, backgroundColor: colors.brandPrimary, paddingHorizontal: spacing.xl },
  label: { fontFamily: fonts.semibold, fontSize: 16, color: colors.onBrandPrimary },
  error: { fontFamily: fonts.medium, fontSize: 13, color: colors.error, textAlign: "center" },
}));
