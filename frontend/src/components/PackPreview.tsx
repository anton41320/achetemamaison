import { Image } from "expo-image";
import { ArrowsLeftRightIcon, SparkleIcon } from "phosphor-react-native";
import { useState } from "react";
import { Pressable, Text, View } from "react-native";

import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

const BEFORE = require("../../assets/images/demo-before.jpg");
const AFTER = require("../../assets/images/demo-after.jpg");

const SAMPLE_LISTING = {
  style: "Chaleureux",
  title: "Maison familiale de 120 m² avec jardin à Soings-en-Sologne",
  hook: "Une maison où l’on se sent bien dès l’entrée, avec cinq pièces à vivre et un terrain de 800 m².",
  description:
    "Cette maison de 120 m² habitables, en bon état, s’organise autour de cinq pièces dont trois chambres. Construite en 1998, elle bénéficie d’une distribution simple qui facilite la vie de famille au quotidien.\n\nÀ l’extérieur, le terrain de 800 m² offre de l’espace pour un potager, des jeux ou simplement profiter des beaux jours. Une visite s’impose pour mesurer les volumes et vous projeter.",
  highlights: ["3 chambres", "Terrain de 800 m²", "Bon état général", "Construction 1998"],
};

/** Real before/after example (retouched by the same model) + a sample AI listing, shown before payment. */
export function PackPreview() {
  const styles = useStyles();
  const { colors } = useTheme();
  const [after, setAfter] = useState(true);
  return (
    <View style={styles.card} testID="pack-preview">
      <Text style={styles.h3}>Aperçu : ce que vous obtiendrez</Text>

      <Text style={styles.label}>Retouche photo IA — exemple réel</Text>
      <Pressable
        testID="pack-preview-toggle"
        accessibilityRole="button"
        accessibilityLabel={after ? "Voir la photo originale" : "Voir la photo retouchée"}
        onPress={() => setAfter((v) => !v)}
        style={styles.imageWrap}
      >
        <Image source={after ? AFTER : BEFORE} style={styles.image} contentFit="cover" transition={200} />
        <View style={styles.badge}>
          <Text style={styles.badgeText} testID="pack-preview-badge">{after ? "Retouchée par l’IA · non contractuel" : "Photo originale"}</Text>
        </View>
        <View style={styles.swap}>
          <ArrowsLeftRightIcon size={14} color={colors.onBrandPrimary} weight="bold" />
          <Text style={styles.swapText}>{after ? "Voir l’original" : "Voir la retouche"}</Text>
        </View>
      </Pressable>
      <Text style={styles.hint}>Lumière, contraste et perspective améliorés. Aucun élément ajouté : la pièce reste fidèle à la réalité.</Text>

      <Text style={[styles.label, { marginTop: spacing.sm }]}>Annonce IA — exemple (style {SAMPLE_LISTING.style.toLowerCase()})</Text>
      <View style={styles.listing} testID="pack-preview-listing">
        <View style={styles.listingHead}>
          <SparkleIcon size={14} color={colors.onBrandTertiary} weight="fill" />
          <Text style={styles.pill}>{SAMPLE_LISTING.style}</Text>
        </View>
        <Text style={styles.title}>{SAMPLE_LISTING.title}</Text>
        <Text style={styles.hook}>{SAMPLE_LISTING.hook}</Text>
        <Text style={styles.body} numberOfLines={5}>{SAMPLE_LISTING.description}</Text>
        <View style={styles.chips}>
          {SAMPLE_LISTING.highlights.map((h) => (
            <Text key={h} style={styles.chip}>• {h}</Text>
          ))}
        </View>
      </View>
      <Text style={styles.hint}>Rédigée uniquement à partir des faits déclarés : l’IA n’invente ni équipement, ni quartier, ni état.</Text>
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  card: { backgroundColor: colors.surfaceSecondary, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, padding: spacing.lg, gap: spacing.md },
  h3: { fontFamily: fonts.semibold, fontSize: 17, color: colors.onSurfaceSecondary },
  label: { fontFamily: fonts.semibold, fontSize: 12, color: colors.muted, textTransform: "uppercase", letterSpacing: 0.6 },
  imageWrap: { height: 200, borderRadius: radius.md, overflow: "hidden", backgroundColor: colors.skeleton },
  image: { width: "100%", height: "100%" },
  badge: { position: "absolute", left: spacing.md, bottom: spacing.md, backgroundColor: colors.scrimBottom, paddingHorizontal: spacing.md, height: 26, borderRadius: radius.pill, justifyContent: "center" },
  badgeText: { fontFamily: fonts.semibold, fontSize: 11, color: colors.onHero },
  swap: { position: "absolute", right: spacing.md, top: spacing.md, flexDirection: "row", alignItems: "center", gap: 6, backgroundColor: colors.brandPrimary, paddingHorizontal: spacing.md, height: 32, borderRadius: radius.pill },
  swapText: { fontFamily: fonts.semibold, fontSize: 12, color: colors.onBrandPrimary },
  hint: { fontFamily: fonts.regular, fontSize: 12, lineHeight: 17, color: colors.muted },
  listing: { backgroundColor: colors.surface, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, padding: spacing.md, gap: spacing.sm },
  listingHead: { flexDirection: "row", alignItems: "center", gap: 6 },
  pill: { fontFamily: fonts.semibold, fontSize: 11, color: colors.onBrandTertiary, backgroundColor: colors.brandTertiary, paddingHorizontal: spacing.sm, height: 22, lineHeight: 22, borderRadius: radius.pill },
  title: { fontFamily: fonts.bold, fontSize: 16, lineHeight: 21, color: colors.onSurface },
  hook: { fontFamily: fonts.medium, fontSize: 14, lineHeight: 20, color: colors.onSurface },
  body: { fontFamily: fonts.regular, fontSize: 13, lineHeight: 19, color: colors.onSurfaceTertiary },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  chip: { fontFamily: fonts.medium, fontSize: 12, color: colors.onSurfaceTertiary },
}));
