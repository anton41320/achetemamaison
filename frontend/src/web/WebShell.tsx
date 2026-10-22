import { Image } from "expo-image";
import { usePathname, useRouter } from "expo-router";
import { HouseLineIcon, PlusCircleIcon, SignOutIcon, SquaresFourIcon, UserCircleIcon } from "phosphor-react-native";
import { PropsWithChildren } from "react";
import { Pressable, ScrollView, Text, View } from "react-native";

import { useSession } from "@/src/auth";
import { STAGES } from "@/src/steps";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";
import { CONTENT_MAX_WIDTH, SIDEBAR_WIDTH, useBreakpoint } from "@/src/web/useBreakpoint";

const STEP_SUFFIX = ["", "/vente", "/vendu"] as const;

/**
 * Coque Web « ordinateur » : barre latérale de navigation + colonne de contenu centrée.
 * Ne s'active que dans un navigateur ≥ 1024 px ; sur iOS/Android et sur mobile web, les écrans sont rendus tels quels.
 */
/** Pages publiques (SEO) : elles ont leur propre en-tête et pied de page, la coque ne s'applique pas. */
const PUBLIC_PREFIXES = ["/accueil", "/estimation-maison", "/estimation-immobiliere", "/combien-vaut-ma-maison", "/vendre-sa-maison", "/prix-immobilier", "/privacy", "/mentions-legales", "/cgu", "/faq", "/conseils-vente", "/estimate-free"];

export const isPublicPath = (pathname: string) => PUBLIC_PREFIXES.some((p) => pathname === p || pathname.startsWith(p + "/"));

export function WebShell({ children }: PropsWithChildren) {
  const { isDesktop } = useBreakpoint();
  const { user } = useSession();
  const styles = useStyles();
  const pathname = usePathname();
  if (!isDesktop || isPublicPath(pathname)) return <>{children}</>;
  if (!user) {
    return (
      <View style={styles.authRoot} testID="web-shell-auth">
        <View style={styles.authCard}>{children}</View>
      </View>
    );
  }
  return (
    <View style={styles.root} testID="web-shell">
      <Sidebar email={user.email} />
      <View style={styles.main}>
        <View style={styles.content}>{children}</View>
      </View>
    </View>
  );
}

function Sidebar({ email }: { email: string }) {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();
  const pathname = usePathname();
  const { signOut } = useSession();
  const propertyId = pathname.match(/^\/property\/([^/]+)/)?.[1] ?? null;
  const stepIndex = propertyId ? (pathname.endsWith("/vente") ? 1 : pathname.endsWith("/vendu") ? 2 : pathname === `/property/${propertyId}` ? 0 : -1) : -1;

  const Item = ({ label, icon: Icon, active, onPress, testID, sub }: { label: string; icon: typeof HouseLineIcon; active: boolean; onPress: () => void; testID: string; sub?: string }) => (
    <Pressable testID={testID} accessibilityRole="link" onPress={onPress} style={({ pressed, hovered }: any) => [styles.item, (hovered || pressed) && styles.itemHover, active && styles.itemActive]}>
      <Icon size={20} color={active ? colors.onBrandPrimary : colors.onSurfaceSecondary} weight={active ? "fill" : "regular"} />
      <View style={{ flex: 1 }}>
        <Text style={[styles.itemLabel, active && styles.itemLabelActive]} numberOfLines={1}>{label}</Text>
        {sub ? <Text style={[styles.itemSub, active && styles.itemLabelActive]} numberOfLines={1}>{sub}</Text> : null}
      </View>
    </Pressable>
  );

  return (
    <View style={styles.sidebar} testID="web-sidebar">
      <Pressable accessibilityRole="link" onPress={() => router.navigate("/")} style={styles.brand} testID="web-brand">
        <Image source={require("../../assets/images/icon.png")} style={styles.brandIcon} contentFit="cover" />
        <View>
          <Text style={styles.brandName}>Achète ma maison</Text>
          <Text style={styles.brandTag}>De l’estimation à la vente</Text>
        </View>
      </Pressable>
      <ScrollView style={{ flex: 1 }} contentContainerStyle={styles.nav} showsVerticalScrollIndicator={false}>
        <Item label="Tableau de bord" icon={SquaresFourIcon} active={pathname === "/"} onPress={() => router.navigate("/")} testID="nav-home" />
        <Item label="Nouveau bien" icon={PlusCircleIcon} active={pathname === "/new"} onPress={() => router.navigate("/new")} testID="nav-new" />
        {propertyId ? (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Bien en cours</Text>
            {STAGES.map((label, i) => (
              <Item
                key={label}
                label={`Étape ${i + 1} · ${label}`}
                icon={HouseLineIcon}
                active={stepIndex === i}
                onPress={() => router.navigate(`/property/${propertyId}${STEP_SUFFIX[i]}` as any)}
                testID={`nav-step-${i + 1}`}
              />
            ))}
          </View>
        ) : null}
        <View style={styles.section}>
          <Item label="Mon compte" icon={UserCircleIcon} active={pathname === "/account" || pathname === "/data"} onPress={() => router.navigate("/account")} testID="nav-account" sub={email} />
        </View>
      </ScrollView>
      <Pressable testID="nav-signout" accessibilityRole="button" onPress={() => signOut()} style={({ hovered }: any) => [styles.item, hovered && styles.itemHover]}>
        <SignOutIcon size={20} color={colors.onSurfaceTertiary} />
        <Text style={[styles.itemLabel, { color: colors.onSurfaceTertiary }]}>Se déconnecter</Text>
      </Pressable>
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  root: { flex: 1, flexDirection: "row", backgroundColor: colors.surfaceSecondary },
  sidebar: { width: SIDEBAR_WIDTH, backgroundColor: colors.surface, borderRightWidth: 1, borderRightColor: colors.border, paddingVertical: spacing.lg, paddingHorizontal: spacing.md, gap: spacing.md },
  brand: { flexDirection: "row", alignItems: "center", gap: spacing.sm, paddingHorizontal: spacing.sm, paddingBottom: spacing.md, borderBottomWidth: 1, borderBottomColor: colors.border },
  brandIcon: { width: 40, height: 40, borderRadius: radius.md },
  brandName: { fontFamily: fonts.bold, fontSize: 16, color: colors.onSurface },
  brandTag: { fontFamily: fonts.regular, fontSize: 12, color: colors.muted },
  nav: { gap: 4 },
  section: { marginTop: spacing.lg, gap: 4 },
  sectionTitle: { fontFamily: fonts.semibold, fontSize: 11, letterSpacing: 1, textTransform: "uppercase", color: colors.muted, paddingHorizontal: spacing.sm, marginBottom: 4 },
  item: { flexDirection: "row", alignItems: "center", gap: spacing.sm, minHeight: 44, paddingHorizontal: spacing.sm, borderRadius: radius.md },
  itemHover: { backgroundColor: colors.surfaceSecondary },
  itemActive: { backgroundColor: colors.brandPrimary },
  itemLabel: { fontFamily: fonts.semibold, fontSize: 14, color: colors.onSurfaceSecondary },
  itemLabelActive: { color: colors.onBrandPrimary },
  itemSub: { fontFamily: fonts.regular, fontSize: 11, color: colors.muted },
  main: { flex: 1, alignItems: "center" },
  content: { flex: 1, width: "100%", maxWidth: CONTENT_MAX_WIDTH, backgroundColor: colors.surface, borderLeftWidth: 1, borderRightWidth: 1, borderColor: colors.border },
  authRoot: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.surfaceSecondary, padding: spacing.xl },
  authCard: { width: "100%", maxWidth: 560, height: "100%", maxHeight: 860, backgroundColor: colors.surface, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, overflow: "hidden" },
}));
