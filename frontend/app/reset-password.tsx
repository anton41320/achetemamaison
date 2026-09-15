import { useLocalSearchParams, useRouter } from "expo-router";
import { useState } from "react";

import { authApi } from "@/src/api";
import { passwordIssue, useSession } from "@/src/auth";
import { AuthShell } from "@/src/components/AuthShell";
import { Field } from "@/src/components/Form";
import { PrimaryButton } from "@/src/components/PrimaryButton";

export default function ResetPasswordScreen() {
  const { token } = useLocalSearchParams<{ token?: string }>();
  const router = useRouter();
  const { acceptAuth, user } = useSession();
  const [code, setCode] = useState(token ?? "");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const pwIssue = password ? passwordIssue(password) : undefined;
  const confirmIssue = confirm && confirm !== password ? "Les mots de passe ne correspondent pas" : undefined;

  const submit = async () => {
    if (code.trim().length < 6) {
      setError("Saisissez le code reçu par email (ou ouvrez le lien de l’email).");
      return;
    }
    if (passwordIssue(password) || confirm !== password) {
      setError("Vérifiez le nouveau mot de passe et sa confirmation.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const r = await authApi.resetPassword(code.trim(), password);
      await acceptAuth(r);
      router.replace("/");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell
      testID="reset-screen"
      backTo={user ? "/" : "/sign-in"}
      title="Nouveau mot de passe"
      subtitle={token ? "Lien reconnu : choisissez votre nouveau mot de passe." : "Saisissez le code à 6 chiffres reçu par email puis votre nouveau mot de passe."}
      error={error}
    >
      {!token ? (
        <Field label="Code reçu par email" testID="reset-code" value={code} onChangeText={setCode} keyboardType="number-pad"
          placeholder="123456" maxLength={200} autoCapitalize="none" />
      ) : null}
      <Field label="Nouveau mot de passe" testID="reset-password" value={password} onChangeText={setPassword} secureTextEntry
        autoComplete="new-password" textContentType="newPassword" placeholder="8 caractères, lettres et chiffres" error={pwIssue} />
      <Field label="Confirmer" testID="reset-confirm" value={confirm} onChangeText={setConfirm} secureTextEntry placeholder="••••••••"
        error={confirmIssue} returnKeyType="done" onSubmitEditing={submit} />
      <PrimaryButton title="Enregistrer et me connecter" onPress={submit} loading={busy} testID="reset-submit" />
    </AuthShell>
  );
}
