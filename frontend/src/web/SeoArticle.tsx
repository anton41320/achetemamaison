import { Link } from "expo-router";
import { Pressable, Text, View } from "react-native";

import { fonts, makeStyles, spacing } from "@/src/theme";
import { FreeEstimate } from "@/src/web/FreeEstimate";
import { PublicPage } from "@/src/web/PublicPage";
import { LEGAL_PAGES } from "@/src/web/legalContent";
import { SEO_PAGES, SeoPageContent } from "@/src/web/seoContent";
import { useBreakpoint } from "@/src/web/useBreakpoint";

export const ALL_PAGES: Record<string, SeoPageContent> = { ...SEO_PAGES, ...LEGAL_PAGES };

/** Page publique éditoriale (SEO) : H1 + estimation gratuite, sections, FAQ (schema.org FAQPage). */
export function SeoArticle({ slug }: { slug: keyof typeof ALL_PAGES }) {
  const c = ALL_PAGES[slug];
  const styles = useStyles();
  const { isDesktop } = useBreakpoint();
  const showEstimate = c.showEstimate !== false;
  const jsonLd = c.faq.length
    ? {
      "@context": "https://schema.org",
      "@type": "FAQPage",
      mainEntity: c.faq.map((f) => ({ "@type": "Question", name: f.q, acceptedAnswer: { "@type": "Answer", text: f.a } })),
    }
    : undefined;
  return (
    <PublicPage title={c.title} description={c.description} path={c.path} jsonLd={jsonLd} testID={`seo-${slug}`}>
      <View style={[styles.hero, showEstimate && isDesktop && { flexDirection: "row", alignItems: "flex-start" }]}>
        <View style={[{ gap: spacing.md }, isDesktop && { flex: 1 }]}>
          <Text style={styles.h1} accessibilityRole="header">{c.h1}</Text>
          <Text style={styles.intro}>{c.intro}</Text>
        </View>
        {showEstimate ? (
          <View style={[{ width: "100%" }, isDesktop && { flex: 1 }]}>
            <FreeEstimate />
          </View>
        ) : null}
      </View>
      {c.sections.map((s) => (
        <View key={s.h2} style={styles.section}>
          <Text style={styles.h2} accessibilityRole="header">{s.h2}</Text>
          {s.paragraphs.map((p, i) => <Text key={i} style={styles.p}>{p}</Text>)}
          {s.bullets?.map((b) => <Text key={b} style={styles.p}>• {b}</Text>)}
        </View>
      ))}
      {c.faq.length ? (
        <View style={styles.section}>
          {c.sections.length ? <Text style={styles.h2} accessibilityRole="header">Questions fréquentes</Text> : null}
          {c.faq.map((f) => (
            <View key={f.q} style={{ gap: 4 }}>
              <Text style={styles.q}>{f.q}</Text>
              <Text style={styles.p}>{f.a}</Text>
            </View>
          ))}
        </View>
      ) : null}
      <View style={styles.links}>
        {Object.values(ALL_PAGES).filter((p) => p.path !== c.path && !p.footerOnly).map((p) => (
          <Link key={p.path} href={p.path as any} asChild>
            <Pressable accessibilityRole="link"><Text style={styles.link}>{p.h1} →</Text></Pressable>
          </Link>
        ))}
        <Link href="/prix-immobilier" asChild>
          <Pressable accessibilityRole="link"><Text style={styles.link}>Prix immobilier par commune et département →</Text></Pressable>
        </Link>
      </View>
    </PublicPage>
  );
}

const useStyles = makeStyles((colors) => ({
  hero: { gap: spacing.xl, paddingTop: spacing.lg },
  h1: { fontFamily: fonts.bold, fontSize: 32, lineHeight: 40, color: colors.onSurface },
  intro: { fontFamily: fonts.regular, fontSize: 17, lineHeight: 26, color: colors.onSurfaceTertiary },
  section: { gap: spacing.sm },
  h2: { fontFamily: fonts.bold, fontSize: 22, lineHeight: 30, color: colors.onSurface, marginTop: spacing.sm },
  p: { fontFamily: fonts.regular, fontSize: 15, lineHeight: 24, color: colors.onSurfaceSecondary },
  q: { fontFamily: fonts.semibold, fontSize: 16, color: colors.onSurface, marginTop: spacing.sm },
  links: { gap: spacing.sm, borderTopWidth: 1, borderTopColor: colors.border, paddingTop: spacing.lg },
  link: { fontFamily: fonts.semibold, fontSize: 15, color: colors.brandPrimary, minHeight: 36, lineHeight: 36 },
}));
