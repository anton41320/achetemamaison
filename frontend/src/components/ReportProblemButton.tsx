import Constants from "expo-constants";
import * as ImagePicker from "expo-image-picker";
import { usePathname } from "expo-router";
import { BugBeetleIcon, CheckCircleIcon, ImageIcon, XIcon } from "phosphor-react-native";
import { useState } from "react";
import { ActivityIndicator, Modal, Platform, Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { KeyboardAvoidingView } from "react-native-keyboard-controller";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { sendFeedback } from "@/src/api";
import { useSession } from "@/src/auth";
import { PrimaryButton } from "@/src/components/PrimaryButton";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

const SCREEN_LABELS: [RegExp, string][] = [
  [/^\/$/, "Accueil"], [/^\/new/, "Nouvelle estimation"], [/^\/account/, "Mon compte"], [/^\/data/, "Données du marché"],
  [/\/edit$/, "Modifier le bien"], [/\/photos$/, "Photos & retouche IA"], [/\/listing$/, "Annonce IA"], [/\/pack$/, "Pack premium"],
  [/\/dossier$/, "Dossier de vente"], [/\/document\//, "Document du dossier"], [/\/visites$/, "Conseils visites"], [/^\/property\/[^/]+$/, "Fiche du bien"],
];

/** Header icon → sheet "Signaler un problème": comment + optional screenshot, sent with the current screen, device and account. */
export function ReportProblemButton() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const pathname = usePathname();
  const { user } = useSession();
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [shot, setShot] = useState<{ uri: string; name: string; type: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);

  if (!user) return null;
  const screenLabel = SCREEN_LABELS.find(([re]) => re.test(pathname))?.[1] ?? pathname;

  const pickShot = async () => {
    // Le sélecteur système iOS/Android n'exige pas d'autorisation pour choisir une seule image ; sur le web c'est un <input file>.
    const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ["images"], quality: 0.8, allowsMultipleSelection: false });
    if (result.canceled || !result.assets?.[0]) return;
    const a = result.assets[0];
    setShot({ uri: a.uri, name: a.fileName ?? `capture-${Date.now()}.jpg`, type: a.mimeType ?? "image/jpeg" });
  };

  const close = () => {
    setOpen(false);
    setSent(false);
    setError(null);
  };

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      await sendFeedback({
        message: message.trim(),
        screen: `${screenLabel} (${pathname})`,
        platform: `${Platform.OS === "ios" ? "iOS" : Platform.OS === "android" ? "Android" : "Web"} ${Platform.Version ?? ""}`.trim(),
        appVersion: `${Constants.expoConfig?.version ?? "?"} (${Constants.expoConfig?.ios?.buildNumber ?? Constants.expoConfig?.android?.versionCode ?? "dev"})`,
        screenshot: shot,
      });
      setSent(true);
      setMessage("");
      setShot(null);
    } catch (e) {
      setError((e as Error).message || "Envoi impossible, réessayez");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <Pressable testID="report-problem-button" accessibilityRole="button" accessibilityLabel="Signaler un problème" onPress={() => setOpen(true)} style={({ pressed }) => [styles.iconBtn, pressed && { opacity: 0.8 }]}>
        <BugBeetleIcon size={20} color={colors.onSurfaceSecondary} weight="duotone" />
      </Pressable>

      <Modal visible={open} animationType="slide" transparent onRequestClose={close} statusBarTranslucent>
        <KeyboardAvoidingView behavior="padding" style={styles.backdrop}>
          <Pressable style={{ flex: 1 }} onPress={close} accessibilityLabel="Fermer" />
          <View style={[styles.sheet, { paddingBottom: insets.bottom + spacing.lg }]} testID="report-problem-sheet">
            <View style={styles.sheetHead}>
              <Text style={styles.sheetTitle}>Signaler un problème</Text>
              <Pressable testID="report-problem-close" accessibilityRole="button" accessibilityLabel="Fermer" onPress={close} style={styles.close}>
                <XIcon size={20} color={colors.onSurfaceSecondary} weight="bold" />
              </Pressable>
            </View>
            {sent ? (
              <View style={styles.sentBox} testID="report-problem-sent">
                <CheckCircleIcon size={28} color={colors.success} weight="fill" />
                <Text style={styles.sentTitle}>Merci, signalement envoyé !</Text>
                <Text style={styles.sentText}>Votre message et l’écran « {screenLabel} » ont été transmis à l’équipe.</Text>
                <PrimaryButton title="Fermer" variant="secondary" onPress={close} testID="report-problem-done" />
              </View>
            ) : (
              <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={{ gap: spacing.md }}>
                <Text style={styles.meta}>Écran : {screenLabel} · {user.email}</Text>
                <TextInput
                  testID="report-problem-message"
                  style={styles.input}
                  multiline
                  placeholder="Décrivez ce qui ne fonctionne pas (ce que vous avez fait, ce qui s’est affiché…)"
                  placeholderTextColor={colors.muted}
                  value={message}
                  onChangeText={setMessage}
                  maxLength={2000}
                  textAlignVertical="top"
                />
                <Pressable testID="report-problem-attach" accessibilityRole="button" onPress={pickShot} style={styles.attach}>
                  <ImageIcon size={18} color={colors.onBrandTertiary} />
                  <Text style={styles.attachLabel} numberOfLines={1}>{shot ? `Capture jointe : ${shot.name}` : "Joindre une capture d’écran (facultatif)"}</Text>
                  {shot ? (
                    <Pressable accessibilityRole="button" accessibilityLabel="Retirer la capture" onPress={() => setShot(null)} hitSlop={8}>
                      <XIcon size={16} color={colors.onBrandTertiary} weight="bold" />
                    </Pressable>
                  ) : null}
                </Pressable>
                {error ? <Text style={styles.error} testID="report-problem-error">{error}</Text> : null}
                <PrimaryButton title={busy ? "Envoi…" : "Envoyer le signalement"} onPress={submit} disabled={message.trim().length < 3} loading={busy} testID="report-problem-send" />
                {busy ? <ActivityIndicator color={colors.brandPrimary} /> : null}
              </ScrollView>
            )}
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </>
  );
}

const useStyles = makeStyles((colors) => ({
  iconBtn: { width: 44, height: 44, borderRadius: radius.pill, backgroundColor: colors.surfaceTertiary, alignItems: "center", justifyContent: "center" },
  backdrop: { flex: 1, backgroundColor: colors.scrimBottom, justifyContent: "flex-end" },
  sheet: { backgroundColor: colors.surface, borderTopLeftRadius: radius.lg, borderTopRightRadius: radius.lg, padding: spacing.lg, gap: spacing.md, maxHeight: "85%" },
  sheetHead: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  sheetTitle: { fontFamily: fonts.bold, fontSize: 18, color: colors.onSurface },
  close: { width: 44, height: 44, alignItems: "center", justifyContent: "center", borderRadius: radius.pill },
  meta: { fontFamily: fonts.medium, fontSize: 12, color: colors.muted },
  input: { minHeight: 120, borderWidth: 1, borderColor: colors.border, borderRadius: radius.md, padding: spacing.md, fontFamily: fonts.regular, fontSize: 15, color: colors.onSurface, backgroundColor: colors.surfaceSecondary },
  attach: { flexDirection: "row", alignItems: "center", gap: spacing.sm, minHeight: 44, paddingHorizontal: spacing.md, borderRadius: radius.md, backgroundColor: colors.brandTertiary },
  attachLabel: { flex: 1, fontFamily: fonts.semibold, fontSize: 13, color: colors.onBrandTertiary },
  error: { fontFamily: fonts.medium, fontSize: 13, color: colors.error },
  sentBox: { alignItems: "center", gap: spacing.sm, paddingVertical: spacing.lg },
  sentTitle: { fontFamily: fonts.bold, fontSize: 16, color: colors.onSurface },
  sentText: { fontFamily: fonts.regular, fontSize: 13, color: colors.onSurfaceSecondary, textAlign: "center", marginBottom: spacing.sm },
}));
