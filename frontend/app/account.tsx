import { useRouter } from "expo-router";
import { useState } from "react";
import { Alert, Platform, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { authApi } from "@/src/api";
import { passwordIssue, useSession } from "@/src/auth";
import { Field } from "@/src/components/Form";
import { PrimaryButton } from "@/src/components/PrimaryButton";
import { ScreenHeader } from "@/src/components/ScreenHeader";
import { fonts, makeStyles, radius, spacing } from "@/src/theme";

export default function AccountScreen() {
  const styles = useStyles();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { user, signOut } = useSession();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [pwMsg, setPwMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [pwBusy, setPwBusy] = useState(false);
  const [delPassword, setDelPassword] = useState("");
  const [delMsg, setDelMsg] = useState<string | null>(null);
  const [delBusy, setDelBusy] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const changePassword = async () => {
    const issue = passwordIssue(next);
    if (!current || issue) {
      setPwMsg({ ok: false, text: issue ? `Nouveau mot de passe : ${issue}.` : "Saisissez votre mot de passe actuel." });
      return;
    }
    setPwBusy(true);
    try {
      await authApi.changePassword(current, next);
      setPwMsg({ ok: true, text: "Mot de passe modifié." });
      setCurrent("");
      setNext("");
    } catch (e) {
      setPwMsg({ ok: false, text: (e as Error).message });
    } finally {
      setPwBusy(false);
    }
  };

  const deleteAccount = async () => {
    if (!delPassword) {
      setDelMsg("Saisissez votre mot de passe pour confirmer.");
      return;
    }
    setDelBusy(true);
    setDelMsg(null);
    try {
      await authApi.deleteAccount(delPassword);
      await signOut();
    } catch (e) {
      setDelMsg((e as Error).message);
    } finally {
      setDelBusy(false);
    }
  };

  const askDelete = () => {
    if (Platform.OS === "web") {
      setConfirmDelete(true);
      return;
    }
    Alert.alert("Supprimer le compte ?", "Vos biens, documents et annonces seront supprimés définitivement.", [
      { text: "Annuler", style: "cancel" },
      { text: "Supprimer", style: "destructive", onPress: () => setConfirmDelete(true) },
    ]);
  };

  return (
    <View style={styles.screen} testID="account-screen">
      <ScreenHeader title="Mon compte" subtitle={user?.email} onBack={() => (router.canGoBack() ? router.back() : router.replace("/"))} />
      <ScrollView contentContainerStyle={[styles.content, { paddingBottom: insets.bottom + spacing.xl }]} keyboardShouldPersistTaps="handled">
        <View style={styles.card}>
          <Text style={styles.h3}>Changer le mot de passe</Text>
          <Field label="Mot de passe actuel" testID="account-current-password" value={current} onChangeText={setCurrent} secureTextEntry autoComplete="current-password" />
          <Field label="Nouveau mot de passe" testID="account-new-password" value={next} onChangeText={setNext} secureTextEntry autoComplete="new-password"
            placeholder="8 caractères, lettres et chiffres" error={next ? passwordIssue(next) : undefined} />
          {pwMsg ? <Text style={[styles.msg, pwMsg.ok ? styles.ok : styles.ko]} testID="account-password-message">{pwMsg.text}</Text> : null}
          <PrimaryButton title="Mettre à jour" onPress={changePassword} loading={pwBusy} testID="account-change-password" variant="secondary" />
        </View>

        <View style={styles.card}>
          <Text style={styles.h3}>Session</Text>
          <Text style={styles.p}>Connecté en tant que {user?.email}. Votre session reste active sur cet appareil.</Text>
          <PrimaryButton title="Se déconnecter" onPress={() => signOut()} testID="account-signout" variant="ghost" />
        </View>

        <View style={[styles.card, styles.danger]}>
          <Text style={styles.h3}>Supprimer mon compte</Text>
          <Text style={styles.p}>Suppression définitive de vos biens, estimations, documents, photos et annonces. Les paiements déjà effectués ne sont pas remboursés automatiquement.</Text>
          {confirmDelete ? (
            <>
              <Field label="Confirmez avec votre mot de passe" testID="account-delete-password" value={delPassword} onChangeText={setDelPassword} secureTextEntry />
              {delMsg ? <Text style={[styles.msg, styles.ko]} testID="account-delete-message">{delMsg}</Text> : null}
              <PrimaryButton title="Supprimer définitivement" onPress={deleteAccount} loading={delBusy} testID="account-delete-confirm" variant="danger" />
              <PrimaryButton title="Annuler" onPress={() => setConfirmDelete(false)} testID="account-delete-cancel" variant="ghost" />
            </>
          ) : (
            <PrimaryButton title="Supprimer mon compte" onPress={askDelete} testID="account-delete" variant="danger" />
          )}
        </View>
      </ScrollView>
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  screen: { flex: 1, backgroundColor: colors.surface },
  content: { padding: spacing.lg, gap: spacing.lg },
  card: { backgroundColor: colors.surfaceSecondary, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, padding: spacing.lg, gap: spacing.sm },
  danger: { borderColor: colors.errorSoft },
  h3: { fontFamily: fonts.semibold, fontSize: 17, color: colors.onSurfaceSecondary },
  p: { fontFamily: fonts.regular, fontSize: 14, lineHeight: 20, color: colors.onSurfaceTertiary },
  msg: { fontFamily: fonts.medium, fontSize: 13 },
  ok: { color: colors.success },
  ko: { color: colors.error },
}));
