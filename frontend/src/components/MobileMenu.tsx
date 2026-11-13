import { useRouter } from "expo-router";
import { XIcon } from "phosphor-react-native";
import { Modal, Pressable, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

/** Menu principal (maquette) : Accueil · Estimation · Mise en vente · Documents · Conseils. */
export const MAIN_NAV = [
  { href: "/accueil", label: "Accueil" },
  { href: "/estimation-maison", label: "Estimation" },
  { href: "/etape-mise-en-vente", label: "Mise en vente" },
  { href: "/etape-vendu", label: "Documents" },
  { href: "/conseils-vente", label: "Conseils" },
] as const;

type Props = { visible: boolean; onClose: () => void; signedIn?: boolean };

/** Menu déroulant ouvert par les 3 barres (mobile). */
export function MobileMenu({ visible, onClose, signedIn }: Props) {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const go = (href: string) => {
    onClose();
    router.navigate(href as any);
  };
  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <Pressable style={styles.backdrop} onPress={onClose} accessibilityLabel="Fermer le menu" testID="mobile-menu-backdrop" />
      <View style={[styles.sheet, { paddingTop: insets.top + spacing.md }]} testID="mobile-menu">
        <Pressable onPress={onClose} style={styles.close} accessibilityRole="button" accessibilityLabel="Fermer" testID="mobile-menu-close">
          <XIcon size={26} color={colors.brandPrimary} weight="bold" />
        </Pressable>
        {MAIN_NAV.map((l) => (
          <Pressable key={l.href} onPress={() => go(l.href)} style={({ pressed }) => [styles.item, pressed && { opacity: 0.6 }]} accessibilityRole="link" testID={`mobile-menu-${l.href.replace("/", "")}`}>
            <Text style={styles.itemText}>{l.label}</Text>
          </Pressable>
        ))}
        <View style={styles.sep} />
        {signedIn ? (
          <Pressable onPress={() => go("/")} style={styles.primary} accessibilityRole="button" testID="mobile-menu-account"><Text style={styles.primaryText}>Mon espace</Text></Pressable>
        ) : (
          <>
            <Pressable onPress={() => go("/sign-in")} style={styles.secondary} accessibilityRole="button" testID="mobile-menu-signin"><Text style={styles.secondaryText}>Se connecter</Text></Pressable>
            <Pressable onPress={() => go("/sign-up")} style={styles.primary} accessibilityRole="button" testID="mobile-menu-signup"><Text style={styles.primaryText}>Créer mon compte</Text></Pressable>
          </>
        )}
      </View>
    </Modal>
  );
}

const useStyles = makeStyles((colors) => ({
  backdrop: { position: "absolute", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: colors.scrimTop },
  sheet: { position: "absolute", top: 0, right: 0, width: 300, maxWidth: "85%", bottom: 0, backgroundColor: colors.surfaceSecondary, paddingHorizontal: spacing.lg, gap: spacing.xs },
  close: { alignSelf: "flex-end", width: 44, height: 44, alignItems: "center", justifyContent: "center" },
  item: { paddingVertical: spacing.md },
  itemText: { fontFamily: fonts.bold, fontSize: 20, color: colors.onSurface },
  sep: { height: 1, backgroundColor: colors.border, marginVertical: spacing.md },
  primary: { backgroundColor: colors.brandPrimary, borderRadius: radius.pill, paddingVertical: 14, alignItems: "center" },
  primaryText: { fontFamily: fonts.bold, fontSize: 16, color: colors.onBrandPrimary },
  secondary: { borderWidth: 2, borderColor: colors.brandPrimary, borderRadius: radius.pill, paddingVertical: 12, alignItems: "center", marginBottom: spacing.sm },
  secondaryText: { fontFamily: fonts.bold, fontSize: 16, color: colors.brandPrimary },
}));
