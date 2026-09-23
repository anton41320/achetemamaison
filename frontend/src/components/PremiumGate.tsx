import { useQuery } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { LockKeyIcon } from "phosphor-react-native";
import { Text, View } from "react-native";

import { api } from "@/src/api";
import { PrimaryButton } from "@/src/components/PrimaryButton";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

/** Pack status of a property; every AI tool is locked until the 49 € pack is paid. */
export function usePackUnlocked(propertyId: string | undefined) {
  const q = useQuery({ queryKey: ["pack", propertyId], queryFn: () => api.packStatus(propertyId!), enabled: !!propertyId });
  return { unlocked: q.data?.unlocked === true, loading: q.isLoading, status: q.data };
}

interface Props {
  propertyId: string;
  /** What the pack unlocks on this screen, e.g. « la rédaction de l’annonce par l’IA ». */
  feature: string;
  testID?: string;
}

/** Paywall card shown in place of an AI action when the property has not unlocked the premium pack. */
export function PremiumGate({ propertyId, feature, testID = "premium-gate" }: Props) {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();
  return (
    <View style={styles.card} testID={testID}>
      <View style={styles.iconWrap}>
        <LockKeyIcon size={22} color={colors.onBrandPrimary} weight="fill" />
      </View>
      <View style={{ flex: 1, gap: spacing.sm }}>
        <Text style={styles.title}>Outil IA réservé au Pack premium</Text>
        <Text style={styles.text}>
          Débloquez {feature} pour ce bien, ainsi que tout le reste du pack (annonce IA, retouches photo illimitées, dossier de vente
          complet avec lecture IA des documents et export notaire, PDF d’annonce premium). Paiement unique de 49 €, sans abonnement.
        </Text>
        <PrimaryButton title="Débloquer le Pack premium · 49 €" onPress={() => router.push(`/property/${propertyId}/pack`)} testID={`${testID}-button`} />
      </View>
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  card: { flexDirection: "row", gap: spacing.md, alignItems: "flex-start", backgroundColor: colors.brandTertiary, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.brandSecondary, padding: spacing.lg },
  iconWrap: { width: 40, height: 40, borderRadius: radius.pill, backgroundColor: colors.brandPrimary, alignItems: "center", justifyContent: "center" },
  title: { fontFamily: fonts.semibold, fontSize: 15, color: colors.onBrandTertiary },
  text: { fontFamily: fonts.regular, fontSize: 13, lineHeight: 19, color: colors.onSurfaceTertiary },
}));
