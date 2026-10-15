import { Image } from "expo-image";
import { Link, useRouter } from "expo-router";
import Head from "expo-router/head";
import { PropsWithChildren } from "react";
import { Platform, Pressable, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useSession } from "@/src/auth";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";
import { CONTENT_MAX_WIDTH, useBreakpoint } from "@/src/web/useBreakpoint";

export const SITE_NAME = "Achète ma maison";
export const NAV_LINKS = [
  { href: "/estimation-maison", label: "Estimation gratuite" },
  { href: "/prix-immobilier", label: "Prix immobilier" },
  { href: "/vendre-sa-maison", label: "Vendre sa maison" },
] as const;

interface Props {
  title: string;
  description: string;
  path: string;
  /** JSON-LD schema.org (FAQ, Article…) — Web uniquement. */
  jsonLd?: object;
  testID?: string;
}

/** Gabarit des pages publiques (SEO) : en-tête de navigation, colonne de contenu centrée, pied de page, balises <head>. */
export function PublicPage({ title, description, path, jsonLd, testID, children }: PropsWithChildren<Props>) {
  const styles = useStyles();
  const { colors } = useTheme();
  const { isTablet } = useBreakpoint();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { user } = useSession();
  const canonical = Platform.OS === "web" && typeof window !== "undefined" ? `${window.location.origin}${path}` : path;

  return (
    <View style={styles.screen} testID={testID ?? "public-page"}>
      <Head>
        <title>{`${title} | ${SITE_NAME}`}</title>
        <meta name="description" content={description} />
        <link rel="canonical" href={canonical} />
        <meta property="og:title" content={title} />
        <meta property="og:description" content={description} />
        <meta property="og:url" content={canonical} />
        {jsonLd ? <script type="application/ld+json">{JSON.stringify(jsonLd)}</script> : null}
      </Head>
      <View style={[styles.header, { paddingTop: insets.top + spacing.sm }]}>
        <View style={styles.headerInner}>
          <Link href={user ? "/" : "/accueil"} asChild>
            <Pressable style={styles.brand} accessibilityRole="link" testID="public-brand">
              <Image source={require("../../assets/images/icon.png")} style={styles.brandIcon} contentFit="cover" />
              <Text style={styles.brandName}>{SITE_NAME}</Text>
            </Pressable>
          </Link>
          {isTablet ? (
            <View style={styles.navRow}>
              {NAV_LINKS.map((l) => (
                <Link key={l.href} href={l.href} asChild>
                  <Pressable accessibilityRole="link" style={({ hovered }: any) => [styles.navItem, hovered && styles.navItemHover]}>
                    <Text style={styles.navText}>{l.label}</Text>
                  </Pressable>
                </Link>
              ))}
            </View>
          ) : null}
          <Pressable
            testID="public-cta-account"
            accessibilityRole="button"
            onPress={() => router.navigate(user ? "/" : "/sign-in")}
            style={({ pressed }) => [styles.cta, pressed && { opacity: 0.9 }]}
          >
            <Text style={styles.ctaText}>{user ? "Mon espace" : "Se connecter"}</Text>
          </Pressable>
        </View>
      </View>
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <View style={styles.content}>{children}</View>
        <View style={styles.footer}>
          <View style={styles.footerInner}>
            <Text style={styles.footerBrand}>{SITE_NAME}</Text>
            <Text style={styles.footerText}>Estimation immobilière gratuite fondée sur les ventes réelles (DVF), puis accompagnement jusqu’à la vente entre particuliers.</Text>
            <View style={styles.footerLinks}>
              {[...NAV_LINKS, { href: "/combien-vaut-ma-maison", label: "Combien vaut ma maison ?" }, { href: "/estimation-immobiliere", label: "Estimation immobilière" }, { href: "/privacy", label: "Confidentialité" }].map((l) => (
                <Link key={l.href} href={l.href as any} asChild>
                  <Pressable accessibilityRole="link"><Text style={styles.footerLink}>{l.label}</Text></Pressable>
                </Link>
              ))}
            </View>
            <Text style={[styles.footerText, { color: colors.muted }]}>Les estimations sont indicatives et ne constituent pas une expertise. Sources : DVF (Etalab), BAN, IGN, Géorisques, OpenStreetMap.</Text>
          </View>
        </View>
      </ScrollView>
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  screen: { flex: 1, backgroundColor: colors.surface },
  header: { backgroundColor: colors.surface, borderBottomWidth: 1, borderBottomColor: colors.border, paddingBottom: spacing.sm, paddingHorizontal: spacing.lg, alignItems: "center" },
  headerInner: { width: "100%", maxWidth: CONTENT_MAX_WIDTH, flexDirection: "row", alignItems: "center", gap: spacing.md },
  brand: { flexDirection: "row", alignItems: "center", gap: spacing.sm, flexShrink: 1 },
  brandIcon: { width: 36, height: 36, borderRadius: radius.sm },
  brandName: { fontFamily: fonts.bold, fontSize: 17, color: colors.brandPrimary },
  navRow: { flex: 1, flexDirection: "row", justifyContent: "center", gap: spacing.xs },
  navItem: { paddingHorizontal: spacing.md, minHeight: 44, justifyContent: "center", borderRadius: radius.md },
  navItemHover: { backgroundColor: colors.surfaceSecondary },
  navText: { fontFamily: fonts.semibold, fontSize: 14, color: colors.onSurfaceSecondary },
  cta: { marginLeft: "auto", minHeight: 44, paddingHorizontal: spacing.lg, borderRadius: radius.pill, backgroundColor: colors.brandPrimary, justifyContent: "center" },
  ctaText: { fontFamily: fonts.semibold, fontSize: 14, color: colors.onBrandPrimary },
  scroll: { alignItems: "stretch" },
  content: { width: "100%", maxWidth: CONTENT_MAX_WIDTH, alignSelf: "center", padding: spacing.lg, gap: spacing.xl },
  footer: { backgroundColor: colors.surfaceSecondary, borderTopWidth: 1, borderTopColor: colors.border, alignItems: "center", padding: spacing.xl, marginTop: spacing.xl },
  footerInner: { width: "100%", maxWidth: CONTENT_MAX_WIDTH, gap: spacing.sm },
  footerBrand: { fontFamily: fonts.bold, fontSize: 16, color: colors.onSurface },
  footerText: { fontFamily: fonts.regular, fontSize: 13, lineHeight: 19, color: colors.onSurfaceTertiary },
  footerLinks: { flexDirection: "row", flexWrap: "wrap", gap: spacing.md, paddingVertical: spacing.sm },
  footerLink: { fontFamily: fonts.semibold, fontSize: 13, color: colors.brandPrimary, minHeight: 32, lineHeight: 32 },
}));
