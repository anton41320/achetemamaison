import * as StoreReview from "expo-store-review";
import { StarIcon } from "phosphor-react-native";
import { useEffect, useState } from "react";
import { KeyboardAvoidingView, Linking, Modal, Platform, Pressable, Text, TextInput, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api } from "@/src/api";
import { PrimaryButton } from "@/src/components/PrimaryButton";
import { deviceKey, markReviewDone, markReviewPrompted, reviewSource, shouldPromptReview } from "@/src/reviewPrompt";
import { APP_STORE_URL, PLAY_STORE_URL } from "@/src/stores";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

const LABELS = ["", "Décevant", "Moyen", "Bien", "Très bien", "Excellent"];

/** Demande d'avis affichée une fois, 2,5 s après que `ready` passe à vrai (première estimation terminée). */
export function ReviewPromptModal({ ready }: { ready: boolean }) {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const [visible, setVisible] = useState(false);
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [name, setName] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const [storeAvailable, setStoreAvailable] = useState(false);

  useEffect(() => {
    if (!ready) return;
    let cancelled = false;
    const t = setTimeout(async () => {
      if (cancelled || !(await shouldPromptReview())) return;
      await markReviewPrompted();
      if (!cancelled) setVisible(true);
    }, 2500);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [ready]);

  const later = () => setVisible(false);

  const submit = async () => {
    if (!rating) return;
    setSending(true);
    setError(null);
    try {
      await api.submitReview({ rating, comment: comment.trim(), name: name.trim(), source: reviewSource(), device_key: await deviceKey() });
      await markReviewDone();
      setSent(true);
      if (rating >= 4 && Platform.OS !== "web") {
        const ok = await StoreReview.isAvailableAsync().catch(() => false);
        setStoreAvailable(ok);
        if (ok) StoreReview.requestReview().catch(() => undefined);
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSending(false);
    }
  };

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={later}>
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={styles.backdrop}>
        <Pressable style={styles.backdropTap} onPress={later} accessibilityLabel="Fermer" />
        <View style={[styles.sheet, { paddingBottom: Math.max(insets.bottom, spacing.lg) }]} testID="review-prompt">
          {sent ? (
            <>
              <Text style={styles.title}>Merci pour votre avis 🙏</Text>
              <Text style={styles.subtitle}>
                {rating >= 4
                  ? Platform.OS === "web"
                    ? "Un dernier coup de pouce ? Une note sur le store aide d'autres vendeurs à nous trouver."
                    : storeAvailable
                      ? "Si la fenêtre de notation s'est affichée, un simple appui sur les étoiles nous aide énormément."
                      : "Votre retour nous aide à améliorer l'application."
                  : "Votre retour nous aide à améliorer l'application. Nous le lisons avec attention."}
              </Text>
              {rating >= 4 && Platform.OS === "web" ? (
                <>
                  <PrimaryButton title="Noter sur l’App Store" onPress={() => Linking.openURL(APP_STORE_URL)} testID="review-store-link-ios" />
                  <PrimaryButton title="Noter sur Google Play" variant="secondary" onPress={() => Linking.openURL(PLAY_STORE_URL)} testID="review-store-link" />
                </>
              ) : null}
              <PrimaryButton title="Fermer" variant="ghost" onPress={later} testID="review-close" />
            </>
          ) : (
            <>
              <Text style={styles.title}>Que pensez-vous d’Achète ma maison ?</Text>
              <Text style={styles.subtitle}>Votre estimation est prête. Un avis en 10 secondes nous aide à nous améliorer.</Text>
              <View style={styles.stars} accessibilityRole="radiogroup">
                {[1, 2, 3, 4, 5].map((n) => (
                  <Pressable key={n} onPress={() => setRating(n)} hitSlop={6} accessibilityRole="radio" accessibilityState={{ selected: n <= rating }}
                    accessibilityLabel={`${n} étoile${n > 1 ? "s" : ""}`} testID={`review-star-${n}`} style={styles.star}>
                    <StarIcon size={40} color={n <= rating ? colors.warning : colors.border} weight={n <= rating ? "fill" : "regular"} />
                  </Pressable>
                ))}
              </View>
              <Text style={styles.ratingLabel}>{rating ? LABELS[rating] : " "}</Text>
              {rating ? (
                <>
                  <TextInput value={name} onChangeText={setName} placeholder="Votre prénom (facultatif)" placeholderTextColor={colors.muted}
                    maxLength={40} autoCapitalize="words" style={styles.input} testID="review-name" />
                  <TextInput value={comment} onChangeText={setComment} placeholder={rating >= 4 ? "Qu'avez-vous apprécié ? (facultatif)" : "Que pourrions-nous améliorer ? (facultatif)"}
                    placeholderTextColor={colors.muted} multiline maxLength={800} style={[styles.input, styles.textarea]} testID="review-comment" />
                </>
              ) : null}
              {error ? <Text style={styles.error}>{error}</Text> : null}
              <View style={styles.row}>
                <PrimaryButton title="Plus tard" variant="ghost" onPress={later} testID="review-later" style={{ flex: 1 }} />
                <PrimaryButton title="Envoyer" onPress={submit} loading={sending} disabled={!rating} testID="review-submit" style={{ flex: 1 }} />
              </View>
            </>
          )}
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

const useStyles = makeStyles((colors) => ({
  backdrop: { flex: 1, justifyContent: "flex-end", backgroundColor: colors.scrimBottom },
  backdropTap: { ...Platform.select({ web: { position: "absolute" as const, top: 0, left: 0, right: 0, bottom: 0 }, default: { flex: 1 } }) },
  sheet: {
    backgroundColor: colors.surface, borderTopLeftRadius: radius.lg, borderTopRightRadius: radius.lg, padding: spacing.lg, gap: spacing.md,
    maxWidth: 560, width: "100%", alignSelf: "center",
  },
  title: { fontFamily: fonts.extrabold, fontSize: 20, color: colors.onSurface, textAlign: "center" },
  subtitle: { fontFamily: fonts.regular, fontSize: 14, lineHeight: 20, color: colors.onSurfaceSecondary, textAlign: "center" },
  stars: { flexDirection: "row", justifyContent: "center", gap: spacing.xs },
  star: { minWidth: 48, minHeight: 48, alignItems: "center", justifyContent: "center" },
  ratingLabel: { fontFamily: fonts.semibold, fontSize: 14, color: colors.brandPrimary, textAlign: "center", minHeight: 18 },
  input: {
    fontFamily: fonts.regular, fontSize: 15, color: colors.onSurface, backgroundColor: colors.surfaceSecondary, borderRadius: radius.md,
    borderWidth: 1, borderColor: colors.border, minHeight: 48, paddingHorizontal: spacing.md, paddingVertical: spacing.sm,
  },
  textarea: { minHeight: 88, textAlignVertical: "top" },
  error: { fontFamily: fonts.medium, fontSize: 13, color: colors.error, textAlign: "center" },
  row: { flexDirection: "row", gap: spacing.md },
}));
