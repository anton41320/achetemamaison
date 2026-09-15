import { useRouter } from "expo-router";
import { useState } from "react";
import { Text } from "react-native";

import { appOrigin } from "@/src/auth";
import { authApi } from "@/src/api";
import { AuthShell } from "@/src/components/AuthShell";
import { Field } from "@/src/components/Form";
import { PrimaryButton } from "@/src/components/PrimaryButton";
import { fonts, makeStyles } from "@/src/theme";

export default function ForgotPasswordScreen() {
  const styles = useStyles();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.trim())) {
      setError("Adresse email invalide.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await authApi.forgotPassword(email.trim().toLowerCase(), appOrigin());
      setSent(true);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell
      testID="forgot-screen"
      backTo="/sign-in"
      title="Mot de passe oublié"
      subtitle="Indiquez votre email : vous recevrez un lien et un code à 6 chiffres valables 15 minutes."
      error={error}
      success={sent ? "Si un compte existe pour cet email, un lien et un code viennent d’être envoyés. Vérifiez aussi vos spams." : null}
    >
      <Field label="Email" testID="forgot-email" value={email} onChangeText={setEmail} autoCapitalize="none" autoComplete="email"
        keyboardType="email-address" textContentType="emailAddress" placeholder="vous@exemple.fr" returnKeyType="done" onSubmitEditing={submit} />
      {sent ? (
        <PrimaryButton title="J’ai reçu le code" onPress={() => router.push("/reset-password")} testID="forgot-goto-reset" />
      ) : (
        <PrimaryButton title="Envoyer le lien" onPress={submit} loading={busy} testID="forgot-submit" />
      )}
      <Text style={styles.muted}>Pas d’email au bout de quelques minutes ? Vérifiez l’adresse saisie ou créez un compte.</Text>
    </AuthShell>
  );
}

const useStyles = makeStyles((colors) => ({
  muted: { fontFamily: fonts.regular, fontSize: 13, lineHeight: 18, color: colors.muted, textAlign: "center" },
}));
