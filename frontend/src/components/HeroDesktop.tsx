import { Image } from "expo-image";
import { useRouter } from "expo-router";
import { ChartBarIcon, FolderOpenIcon, ImageIcon } from "phosphor-react-native";
import { useState } from "react";
import { LayoutChangeEvent, Pressable, Text, View, useWindowDimensions } from "react-native";
import Svg, { Rect } from "react-native-svg";

import { StoreBadges } from "@/src/components/StoreBadges";
import { fonts, makeStyles, useTheme } from "@/src/theme";
import { CONTENT_MAX_WIDTH } from "@/src/web/useBreakpoint";

/**
 * Héros ordinateur reproduit depuis la maquette (espace de conception 2000 × 1024, en-tête de 110 px rendu par PublicPage).
 * Chaque calque fourni garde ses coordonnées de maquette, mises à l'échelle de la largeur disponible.
 */
const D = 2000;
const TOP = 110;
const HEIGHT = 1024;

const NOISETTE = require("../../assets/hero/d-noisette.webp"); // 611×612 posé en (1149, 196)
const PLUS = require("../../assets/hero/d-plus.webp"); // 790×796 posé en (1134, 162)
const LOGO_SHAPE = require("../../assets/hero/d-logo-shape.webp"); // 420×333 posé en (370, 0)

export function HeroDesktop({ testID = "hero-desktop" }: { testID?: string }) {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();
  const { width: windowWidth } = useWindowDimensions();
  const [measured, setMeasured] = useState(0);
  const width = measured || Math.min(windowWidth, CONTENT_MAX_WIDTH);
  const s = width / D;
  const px = (v: number) => Math.round(v * s);
  const y = (v: number) => px(v - TOP);
  const steps = [
    { n: 1, label: "Estimation", Icon: ChartBarIcon, top: 338, href: "/estimation-maison" },
    { n: 2, label: "Mise en vente", Icon: ImageIcon, top: 508, href: "/etape-mise-en-vente" },
    { n: 3, label: "Vendu", Icon: FolderOpenIcon, top: 695, href: "/etape-vendu" },
  ] as const;

  return (
    <View style={[styles.root, { height: px(HEIGHT - TOP) }]} onLayout={(e: LayoutChangeEvent) => setMeasured(Math.round(e.nativeEvent.layout.width))} testID={testID}>
      {width > 0 ? (
        <>
          {/* Grand aplat bleu (forme arrondie) */}
          <Svg width={width} height={px(HEIGHT - TOP)} viewBox={`0 ${TOP} ${D} ${HEIGHT - TOP}`} style={{ position: "absolute", left: 0, top: 0, pointerEvents: "none" }}>
            <Rect x={300} y={-140} width={810} height={1340} rx={390} fill={colors.brandPrimary} />
          </Svg>
          <Image source={LOGO_SHAPE} style={{ position: "absolute", left: px(370), top: y(0), width: px(420), height: px(333) }} contentFit="contain" />

          <Text style={[styles.title, { left: px(389), top: y(452), fontSize: px(46), lineHeight: px(54) }]} accessibilityRole="header">
            Prêt à connaître{"\n"}la valeur de votre bien ?
          </Text>
          <Text style={[styles.lead, { left: px(389), top: y(574), width: px(540), fontSize: px(22), lineHeight: px(28) }]}>
            Estimation <Text style={{ fontFamily: fonts.bold }}>gratuite</Text> en 2 minutes, puis créez votre compte pour sauvegarder le bien et préparer la vente sur le site comme dans l’application mobile.
          </Text>
          <Pressable onPress={() => router.navigate("/estimation-maison")} accessibilityRole="button" testID={`${testID}-estimate`} style={({ pressed }) => [styles.btnWhite, { left: px(389), top: y(727), width: px(253), height: px(46), borderRadius: px(10) }, pressed && { opacity: 0.9 }]}>
            <Text style={[styles.btnWhiteText, { fontSize: px(20) }]}>Estimer gratuitement</Text>
          </Pressable>
          <Pressable onPress={() => router.navigate("/sign-up")} accessibilityRole="button" testID={`${testID}-signup`} style={({ pressed }) => [styles.btnSoft, { left: px(662), top: y(727), width: px(259), height: px(46), borderRadius: px(10) }, pressed && { opacity: 0.9 }]}>
            <Text style={[styles.btnSoftText, { fontSize: px(20) }]}>Créer mon compte</Text>
          </Pressable>
          {/* Noisette + forme « plus » (rendus avant les badges pour rester en dessous) */}
          <Image source={PLUS} style={{ position: "absolute", left: px(1134), top: y(162), width: px(790), height: px(796) }} contentFit="contain" />
          <Image source={NOISETTE} style={{ position: "absolute", left: px(1149), top: y(196), width: px(611), height: px(612) }} contentFit="contain" accessibilityLabel="Noisette, la mascotte, pointe vers le message" transition={200} />

          <Text style={[styles.download, { left: px(653), top: y(913), fontSize: px(23) }]}>Ou téléchargez l’application :</Text>
          <StoreBadges style={{ position: "absolute", left: px(1082), top: y(893), width: px(900), justifyContent: "flex-start", zIndex: 2 }} />

          {/* 3 étapes (colonne gauche) */}
          {steps.map(({ n, label, Icon, top, href }) => (
            <Pressable key={n} onPress={() => router.navigate(href)} accessibilityRole="link" testID={`${testID}-step-${n}`} style={{ position: "absolute", left: px(66), top: y(top), width: px(240) }}>
              <View style={[styles.stepCircle, { width: px(42), height: px(42), borderRadius: px(21) }]}>
                <Text style={[styles.stepNum, { fontSize: px(20) }]}>{n}</Text>
              </View>
              <View style={{ height: px(44), justifyContent: "center" }}>
                <Icon size={px(30)} color={colors.brandPrimary} weight="regular" />
              </View>
              <Text style={[styles.stepLabel, { fontSize: px(23) }]} numberOfLines={1}>{label}</Text>
            </Pressable>
          ))}
        </>
      ) : null}
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  root: { width: "100%", backgroundColor: colors.brandTertiary, overflow: "hidden" },
  title: { position: "absolute", fontFamily: fonts.extrabold, color: colors.onBrandPrimary },
  lead: { position: "absolute", fontFamily: fonts.medium, color: colors.onBrandPrimary },
  btnWhite: { position: "absolute", backgroundColor: colors.surfaceSecondary, alignItems: "center", justifyContent: "center" },
  btnWhiteText: { fontFamily: fonts.bold, color: colors.onSurface },
  btnSoft: { position: "absolute", backgroundColor: colors.brandSecondary, alignItems: "center", justifyContent: "center" },
  btnSoftText: { fontFamily: fonts.bold, color: colors.onBrandPrimary },
  download: { position: "absolute", fontFamily: fonts.medium, color: colors.onBrandPrimary },
  stepCircle: { backgroundColor: colors.brandPrimary, alignItems: "center", justifyContent: "center" },
  stepNum: { fontFamily: fonts.bold, color: colors.onBrandPrimary },
  stepLabel: { fontFamily: fonts.bold, color: colors.onSurface },
}));
