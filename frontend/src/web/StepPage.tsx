import { Image } from "expo-image";
import { Link, useRouter } from "expo-router";
import { ArrowLeftIcon, ArrowRightIcon, CheckCircleIcon } from "phosphor-react-native";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { EstimateDemo } from "@/src/components/EstimateDemo";
import { PrimaryButton } from "@/src/components/PrimaryButton";
import { ReviewsSection } from "@/src/components/ReviewsSection";
import { StoreBadges } from "@/src/components/StoreBadges";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";
import { PublicPage } from "@/src/web/PublicPage";
import { STEP_PAGES, type StepBlock, type StepContent } from "@/src/web/stepContent";
import { useBreakpoint } from "@/src/web/useBreakpoint";

function Block({ b, flip, row }: { b: StepBlock; flip: boolean; row: boolean }) {
  const styles = useStyles();
  const { colors } = useTheme();
  return (
    <View style={[styles.block, row && { flexDirection: flip ? "row-reverse" : "row", alignItems: "center" }]} testID="step-block">
      <View style={[styles.blockMedia, row && { flex: 1 }]}>
        {b.after ? (
          <View style={styles.beforeAfter}>
            <View style={{ flex: 1, gap: 6 }}>
              <Image source={b.image} style={styles.baImage} contentFit="cover" accessibilityLabel="Photo avant retouche" />
              <Text style={styles.baLabel}>AVANT</Text>
            </View>
            <View style={{ flex: 1, gap: 6 }}>
              <Image source={b.after} style={styles.baImage} contentFit="cover" accessibilityLabel="Photo après retouche IA" />
              <Text style={[styles.baLabel, { color: colors.brandPrimary }]}>APRÈS · RETOUCHE IA</Text>
            </View>
          </View>
        ) : (
          <Image source={b.image} style={styles.blockImage} contentFit="cover" accessibilityLabel={b.title} />
        )}
        {b.caption ? <Text style={styles.caption}>{b.caption}</Text> : null}
      </View>
      <View style={[styles.blockText, row && { flex: 1 }]}>
        <Text style={styles.h2} accessibilityRole="header">{b.title}</Text>
        <Text style={styles.p}>{b.text}</Text>
        {b.bullets?.map((x) => (
          <View key={x} style={styles.bullet}>
            <CheckCircleIcon size={20} color={colors.success} weight="fill" />
            <Text style={styles.bulletText}>{x}</Text>
          </View>
        ))}
      </View>
    </View>
  );
}

/** Page argumentaire d'une étape du parcours (1 Estimation · 2 Mise en vente · 3 Vendu), avec retour et navigation entre étapes. */
export function StepPage({ step }: { step: StepContent }) {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();
  const { isDesktop, isTablet } = useBreakpoint();
  const prev = STEP_PAGES.find((s) => s.n === step.n - 1);
  const next = STEP_PAGES.find((s) => s.n === step.n + 1);
  const back = () => (router.canGoBack() ? router.back() : router.replace("/accueil"));

  return (
    <PublicPage title={step.title} description={step.description} path={step.path} testID={`step-page-${step.n}`}>
      <Pressable onPress={back} style={styles.back} accessibilityRole="button" accessibilityLabel="Retour" testID="step-back" hitSlop={8}>
        <ArrowLeftIcon size={18} color={colors.brandPrimary} weight="bold" />
        <Text style={styles.backText}>Retour</Text>
      </Pressable>

      <View style={[styles.hero, isDesktop && { flexDirection: "row", alignItems: "center" }]}>
        <View style={[{ gap: spacing.md }, isDesktop && { flex: 1 }]}>
          <View style={styles.stepRow}>
            {STEP_PAGES.map((s) => (
              <Link key={s.n} href={s.path as any} asChild>
                <Pressable style={StyleSheet.flatten([styles.stepDot, s.n === step.n && styles.stepDotActive])} accessibilityRole="link" accessibilityLabel={`Étape ${s.n}`} testID={`step-dot-${s.n}`}>
                  <Text style={[styles.stepDotText, s.n === step.n && { color: colors.onBrandPrimary }]}>{s.n}</Text>
                </Pressable>
              </Link>
            ))}
            <Text style={styles.tagline}>{step.tagline}</Text>
          </View>
          <Text style={styles.h1} accessibilityRole="header">{step.h1}</Text>
          <Text style={styles.intro}>{step.intro}</Text>
          <PrimaryButton title={step.cta.label} onPress={() => router.navigate(step.cta.href as any)} testID="step-cta-top" />
        </View>
        {step.n === 1 ? (
          <View style={[{ width: "100%" }, isDesktop && { flex: 1.1 }]}><EstimateDemo /></View>
        ) : (
          <Image source={step.hero} style={[styles.heroImage, isDesktop && { flex: 1.1 }]} contentFit="cover" accessibilityLabel={step.h1} testID="step-hero-image" />
        )}
      </View>

      {step.blocks.map((b, i) => <Block key={b.title} b={b} flip={i % 2 === 1} row={isTablet} />)}

      {step.n === 3 ? <ReviewsSection row={isTablet} /> : null}

      <View style={styles.nav}>
        {prev ? (
          <Link href={prev.path as any} asChild>
            <Pressable style={styles.navCard} accessibilityRole="link" testID="step-prev">
              <ArrowLeftIcon size={18} color={colors.brandPrimary} />
              <View style={{ flex: 1 }}>
                <Text style={styles.navKicker}>Étape {prev.n}</Text>
                <Text style={styles.navTitle}>{prev.h1}</Text>
              </View>
            </Pressable>
          </Link>
        ) : <View style={{ flex: 1 }} />}
        {next ? (
          <Link href={next.path as any} asChild>
            <Pressable style={StyleSheet.flatten([styles.navCard, { alignItems: "flex-end" }])} accessibilityRole="link" testID="step-next">
              <View style={{ flex: 1, alignItems: "flex-end" }}>
                <Text style={styles.navKicker}>Étape {next.n}</Text>
                <Text style={[styles.navTitle, { textAlign: "right" }]}>{next.h1}</Text>
              </View>
              <ArrowRightIcon size={18} color={colors.brandPrimary} />
            </Pressable>
          </Link>
        ) : <View style={{ flex: 1 }} />}
      </View>

      <View style={styles.ctaBlock} testID="step-cta">
        <Text style={styles.ctaTitle}>Prêt à passer à l’action ?</Text>
        <Text style={styles.ctaText}>Estimation gratuite, sans inscription. Le Pack premium à 49 € une fois débloque ensuite photos IA, annonce, environnement et dossier de vente.</Text>
        <View style={styles.ctaRow}>
          <PrimaryButton title={step.cta.label} variant="secondary" onPress={() => router.navigate(step.cta.href as any)} testID="step-cta-bottom" />
        </View>
        <StoreBadges style={{ justifyContent: "center" }} />
      </View>
    </PublicPage>
  );
}

const useStyles = makeStyles((colors) => ({
  back: { flexDirection: "row", alignItems: "center", gap: 6, alignSelf: "flex-start", minHeight: 44, paddingRight: spacing.sm },
  backText: { fontFamily: fonts.semibold, fontSize: 15, color: colors.brandPrimary },
  hero: { gap: spacing.xl },
  stepRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  stepDot: { width: 32, height: 32, borderRadius: 16, borderWidth: 1.5, borderColor: colors.brandPrimary, alignItems: "center", justifyContent: "center" },
  stepDotActive: { backgroundColor: colors.brandPrimary },
  stepDotText: { fontFamily: fonts.bold, fontSize: 14, color: colors.brandPrimary },
  tagline: { fontFamily: fonts.bold, fontSize: 12, letterSpacing: 1, color: colors.brandPrimary, marginLeft: spacing.sm },
  h1: { fontFamily: fonts.extrabold, fontSize: 34, lineHeight: 42, color: colors.onSurface },
  intro: { fontFamily: fonts.regular, fontSize: 17, lineHeight: 26, color: colors.onSurfaceTertiary },
  heroImage: { width: "100%", aspectRatio: 3 / 2, borderRadius: radius.lg, backgroundColor: colors.surfaceSecondary },
  block: { gap: spacing.lg, paddingVertical: spacing.md },
  blockMedia: { gap: spacing.sm },
  blockImage: { width: "100%", aspectRatio: 3 / 2, borderRadius: radius.lg, backgroundColor: colors.surfaceSecondary },
  beforeAfter: { flexDirection: "row", gap: spacing.sm },
  baImage: { width: "100%", aspectRatio: 4 / 3, borderRadius: radius.md, backgroundColor: colors.surfaceSecondary },
  baLabel: { fontFamily: fonts.bold, fontSize: 11, letterSpacing: 1, color: colors.muted },
  caption: { fontFamily: fonts.medium, fontSize: 13, lineHeight: 19, color: colors.muted },
  blockText: { gap: spacing.sm },
  h2: { fontFamily: fonts.extrabold, fontSize: 24, lineHeight: 32, color: colors.onSurface },
  p: { fontFamily: fonts.regular, fontSize: 15, lineHeight: 24, color: colors.onSurfaceSecondary },
  bullet: { flexDirection: "row", alignItems: "flex-start", gap: spacing.sm },
  bulletText: { flex: 1, fontFamily: fonts.medium, fontSize: 15, lineHeight: 22, color: colors.onSurface },
  nav: { flexDirection: "row", gap: spacing.md, paddingTop: spacing.lg, borderTopWidth: 1, borderTopColor: colors.border },
  navCard: { flex: 1, flexDirection: "row", alignItems: "center", gap: spacing.sm, backgroundColor: colors.surfaceSecondary, borderRadius: radius.lg, padding: spacing.md, borderWidth: 1, borderColor: colors.border, minHeight: 64 },
  navKicker: { fontFamily: fonts.bold, fontSize: 11, letterSpacing: 1, color: colors.muted },
  navTitle: { fontFamily: fonts.semibold, fontSize: 14, lineHeight: 20, color: colors.onSurface },
  ctaBlock: { backgroundColor: colors.brandPrimary, borderRadius: radius.lg, padding: spacing.xl, gap: spacing.md, alignItems: "center" },
  ctaTitle: { fontFamily: fonts.extrabold, fontSize: 24, color: colors.onBrandPrimary, textAlign: "center" },
  ctaText: { fontFamily: fonts.regular, fontSize: 15, lineHeight: 23, color: colors.onBrandPrimary, textAlign: "center", maxWidth: 620, opacity: 0.92 },
  ctaRow: { flexDirection: "row", justifyContent: "center" },
}));
