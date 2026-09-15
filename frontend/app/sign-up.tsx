import { Link } from "expo-router";
import { useState } from "react";
import { Text } from "react-native";

import { passwordIssue, useSession } from "@/src/auth";
import { AuthShell } from "@/src/components/AuthShell";
import { Field } from "@/src/components/Form";
import { PrimaryButton } from "@/src/components/PrimaryButton";
import { fonts, makeStyles } from "@/src/theme";

export default function SignUpScreen() {
  const styles = useStyles();
  const { signUp } = useSession();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const pwIssue = password ? passwordIssue(password) : undefined;
  const confirmIssue = confirm && confirm !== password ? "Les mots de passe ne correspondent pas" : undefined;

  const submit = async () => {
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.trim())) {
      setError("Adresse email invalide.");
      return;
    }
    if (passwordIssue(password) || confirm !== password) {
      setError("Vérifiez le mot de passe et sa confirmation.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await signUp(email, password);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell
      testID="signup-screen"
      title="Créer votre compte"
      subtitle="Vos biens, estimations, documents et achats seront rattachés à ce compte."
      error={error}
      footer={
        <Text style={styles.muted}>
          Déjà inscrit ? <Link href="/sign-in" testID="signup-signin-link" style={styles.link}>Se connecter</Link>
        </Text>
      }
    >
      <Field label="Email" testID="signup-email" value={email} onChangeText={setEmail} autoCapitalize="none" autoComplete="email"
        keyboardType="email-address" textContentType="emailAddress" placeholder="vous@exemple.fr" returnKeyType="next" />
      <Field label="Mot de passe" testID="signup-password" value={password} onChangeText={setPassword} secureTextEntry
        autoComplete="new-password" textContentType="newPassword" placeholder="8 caractères, lettres et chiffres" error={pwIssue} />
      <Field label="Confirmer le mot de passe" testID="signup-confirm" value={confirm} onChangeText={setConfirm} secureTextEntry
        autoComplete="new-password" placeholder="••••••••" error={confirmIssue} returnKeyType="done" onSubmitEditing={submit} />
      <PrimaryButton title="Créer mon compte" onPress={submit} loading={busy} testID="signup-submit" />
      <Text style={styles.legal}>En créant un compte vous acceptez que vos données soient utilisées uniquement pour le service Estimo.</Text>
    </AuthShell>
  );
}

const useStyles = makeStyles((colors) => ({
  link: { fontFamily: fonts.semibold, fontSize: 14, color: colors.brandPrimary },
  muted: { fontFamily: fonts.regular, fontSize: 14, color: colors.onSurfaceTertiary },
  legal: { fontFamily: fonts.regular, fontSize: 12, lineHeight: 17, color: colors.muted, textAlign: "center" },
}));
