import { Link } from "expo-router";
import { useState } from "react";
import { Text } from "react-native";

import { useSession } from "@/src/auth";
import { AuthShell } from "@/src/components/AuthShell";
import { Field } from "@/src/components/Form";
import { PrimaryButton } from "@/src/components/PrimaryButton";
import { fonts, makeStyles } from "@/src/theme";

export default function SignInScreen() {
  const styles = useStyles();
  const { signIn } = useSession();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    if (!email.trim() || !password) {
      setError("Saisissez votre email et votre mot de passe.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await signIn(email, password);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell
      testID="signin-screen"
      title="Bon retour"
      subtitle="Connectez-vous pour retrouver vos biens, estimations et documents."
      error={error}
      footer={
        <>
          <Link href="/forgot-password" testID="signin-forgot-link" style={styles.link}>Mot de passe oublié ?</Link>
          <Text style={styles.muted}>
            Pas encore de compte ? <Link href="/sign-up" testID="signin-signup-link" style={styles.link}>Créer un compte</Link>
          </Text>
        </>
      }
    >
      <Field label="Email" testID="signin-email" value={email} onChangeText={setEmail} autoCapitalize="none" autoComplete="email"
        keyboardType="email-address" textContentType="emailAddress" placeholder="vous@exemple.fr" returnKeyType="next" />
      <Field label="Mot de passe" testID="signin-password" value={password} onChangeText={setPassword} secureTextEntry
        autoComplete="current-password" textContentType="password" placeholder="••••••••" returnKeyType="done" onSubmitEditing={submit} />
      <PrimaryButton title="Se connecter" onPress={submit} loading={busy} testID="signin-submit" />
    </AuthShell>
  );
}

const useStyles = makeStyles((colors) => ({
  link: { fontFamily: fonts.semibold, fontSize: 14, color: colors.brandPrimary },
  muted: { fontFamily: fonts.regular, fontSize: 14, color: colors.onSurfaceTertiary },
}));
