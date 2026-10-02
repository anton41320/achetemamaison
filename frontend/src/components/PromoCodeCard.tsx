import { useMutation, useQueryClient } from "@tanstack/react-query";
import { TicketIcon } from "phosphor-react-native";
import { useState } from "react";
import { Pressable, Text, TextInput, View } from "react-native";

import { api } from "@/src/api";
import { PrimaryButton } from "@/src/components/PrimaryButton";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

/** « J’ai un code » : un code testeur débloque le Pack premium sur tous les biens du compte. */
export function PromoCodeCard({ propertyId }: { propertyId: string }) {
  const styles = useStyles();
  const { colors } = useTheme();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [code, setCode] = useState("");

  const redeem = useMutation({
    mutationFn: () => api.redeemPromo(code),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["pack", propertyId] }),
        queryClient.invalidateQueries({ queryKey: ["pack-unlocked"] }),
        queryClient.invalidateQueries({ queryKey: ["next-steps"] }),
        queryClient.invalidateQueries({ queryKey: ["dossier", propertyId] }),
      ]);
    },
  });

  if (!open) {
    return (
      <Pressable testID="promo-open" accessibilityRole="button" onPress={() => setOpen(true)} style={styles.linkRow}>
        <TicketIcon size={18} color={colors.brandPrimary} weight="duotone" />
        <Text style={styles.link}>J’ai un code</Text>
      </Pressable>
    );
  }

  return (
    <View style={styles.card} testID="promo-card">
      <View style={styles.head}>
        <TicketIcon size={20} color={colors.brandPrimary} weight="duotone" />
        <Text style={styles.title}>Code d’accès</Text>
      </View>
      <TextInput
        testID="promo-input"
        value={code}
        onChangeText={(t) => setCode(t.toUpperCase())}
        placeholder="AMM-XXXX-XX"
        placeholderTextColor={colors.muted}
        autoCapitalize="characters"
        autoCorrect={false}
        autoFocus
        returnKeyType="done"
        onSubmitEditing={() => code.trim() && redeem.mutate()}
        style={styles.input}
      />
      {redeem.isError ? <Text style={styles.error} testID="promo-error">{(redeem.error as Error).message}</Text> : null}
      <View style={styles.row}>
        <PrimaryButton title="Annuler" variant="ghost" onPress={() => setOpen(false)} testID="promo-cancel" style={{ flex: 1 }} />
        <PrimaryButton title="Activer" onPress={() => redeem.mutate()} loading={redeem.isPending} disabled={code.trim().length < 4} testID="promo-submit" style={{ flex: 1 }} />
      </View>
      <Text style={styles.hint}>Un code débloque le Pack premium sur tous les biens de votre compte.</Text>
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  linkRow: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: spacing.sm, minHeight: 44 },
  link: { fontFamily: fonts.medium, fontSize: 14, color: colors.brandPrimary },
  card: { backgroundColor: colors.surfaceSecondary, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, padding: spacing.lg, gap: spacing.md },
  head: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  title: { fontFamily: fonts.semibold, fontSize: 16, color: colors.onSurfaceSecondary },
  input: {
    fontFamily: fonts.semibold, fontSize: 18, letterSpacing: 2, color: colors.onSurfaceSecondary, textAlign: "center",
    backgroundColor: colors.surface, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, minHeight: 52, paddingHorizontal: spacing.lg,
  },
  error: { fontFamily: fonts.medium, fontSize: 13, color: colors.error },
  row: { flexDirection: "row", gap: spacing.md },
  hint: { fontFamily: fonts.regular, fontSize: 12, lineHeight: 17, color: colors.muted, textAlign: "center" },
}));
