import { Image } from "expo-image";
import { useRouter } from "expo-router";
import { ChartBarIcon, FolderOpenIcon, ImageIcon } from "phosphor-react-native";
import { useEffect, useState } from "react";
import { Pressable, Text, View, useWindowDimensions } from "react-native";

import { MobileMenu } from "@/src/components/MobileMenu";
import { StoreBadges } from "@/src/components/StoreBadges";
import { fonts, makeStyles, useTheme } from "@/src/theme";

/**
 * Héros mobile reproduit depuis la maquette (espace de conception 1000 px de large) :
 * chaque élément garde les coordonnées de la maquette, mises à l'échelle de la largeur d'écran.
 */
const D = 1000; // largeur de la maquette
const TOP = 140; // hauteur de l'en-tête dans la maquette (rendu séparément)
const HEIGHT = 2000;

const NOISETTE = require("../../assets/hero/m-noisette.webp"); // 388×429 posé en (319, 276)
const WAVE_MID = require("../../assets/hero/m-wave-mid.webp"); // 1000×420 posé en y = 917
const WAVE_BOTTOM = require("../../assets/hero/m-wave-bottom.webp"); // 1000×288 posé en y = 1712
const MENU = require("../../assets/hero/m-menu.webp"); // 140×78 (3 barres)
const PLUS = require("../../assets/hero/m-plus.webp"); // 540×541 posé en (287, 183)

type Props = {
  /** Affiche l'en-tête de la maquette (logo · Se connecter · 3 barres). Sur le site, l'en-tête vient de PublicPage. */
  withHeader?: boolean;
  paddingTop?: number;
  signedIn?: boolean;
  testID?: string;
};

export function HeroMobile({ withHeader = false, paddingTop = 0, signedIn = false, testID = "hero-mobile" }: Props) {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();
  const win = useWindowDimensions();
  // Largeur fixée après montage : au pré-rendu statique (SSG) la fenêtre mesure 0 et React n'actualise pas
  // les styles « 0px » à l'hydratation ; ce setState force un rendu client avec la vraie largeur.
  const [width, setWidth] = useState(0);
  useEffect(() => setWidth(win.width), [win.width]);
  const [menu, setMenu] = useState(false);
  const s = width / D;
  const px = (v: number) => Math.round(v * s);
  const top0 = withHeader ? 0 : TOP;
  const y = (v: number) => px(v - top0);
  const steps = [
    { n: 1, label: "Estimation", Icon: ChartBarIcon, cx: 275, href: "/estimation-maison" },
    { n: 2, label: "Mise en vente", Icon: ImageIcon, cx: 500, href: "/etape-mise-en-vente" },
    { n: 3, label: "Vendu", Icon: FolderOpenIcon, cx: 722, href: "/etape-vendu" },
  ] as const;

  return (
    <View style={[styles.root, { width, height: px(HEIGHT - top0) + paddingTop }]} testID={testID}>
      {withHeader ? (
        <View style={[styles.header, { height: px(TOP) + paddingTop, paddingTop }]} testID={`${testID}-header`}>
          <Pressable onPress={() => router.navigate("/accueil")} accessibilityRole="link" accessibilityLabel="Achète ma maison" style={{ left: px(30), width: px(350), height: px(90), position: "absolute", top: paddingTop + px(25) }}>
            <Image source={require("../../assets/images/logo-wordmark.png")} style={{ width: "100%", height: "100%" }} contentFit="contain" />
          </Pressable>
          <Pressable
            onPress={() => router.navigate(signedIn ? "/" : "/sign-in")}
            accessibilityRole="button"
            testID={`${testID}-signin`}
            style={({ pressed }) => [styles.signin, { left: px(455), top: paddingTop + px(18), width: px(306), height: px(104), borderRadius: px(52) }, pressed && { opacity: 0.9 }]}
          >
            <Text style={[styles.signinText, { fontSize: px(36) }]}>{signedIn ? "Mon espace" : "Se connecter"}</Text>
          </Pressable>
          <Pressable onPress={() => setMenu(true)} accessibilityRole="button" accessibilityLabel="Menu" testID={`${testID}-menu`} hitSlop={12} style={{ position: "absolute", left: px(860), top: paddingTop + px(42), width: px(140), height: px(78) }}>
            <Image source={MENU} style={{ width: "100%", height: "100%" }} contentFit="contain" />
          </Pressable>
          <MobileMenu visible={menu} onClose={() => setMenu(false)} signedIn={signedIn} />
        </View>
      ) : null}

      <Image source={PLUS} style={{ position: "absolute", left: px(287), top: paddingTop + y(183), width: px(540), height: px(541) }} contentFit="contain" />
      <Image source={NOISETTE} style={{ position: "absolute", left: px(319), top: paddingTop + y(276), width: px(388), height: px(429) }} contentFit="contain" accessibilityLabel="Noisette, la mascotte, vous accueille" transition={200} />

      <Text style={[styles.title, { top: paddingTop + y(775), fontSize: px(60), lineHeight: px(74) }]} accessibilityRole="header" allowFontScaling={false}>
        Prêt à connaître{"\n"}la valeur de votre bien ?
      </Text>

      <Image source={WAVE_MID} style={{ position: "absolute", left: 0, top: paddingTop + y(917), width, height: px(420) }} contentFit="fill" />
      {/* Texte + boutons en flux : si le texte prend une ligne de plus (Android), les boutons descendent au lieu de le recouvrir */}
      <View style={{ position: "absolute", left: px(60), width: px(880), top: paddingTop + y(1010), alignItems: "center", gap: px(36) }}>
        <Text style={[styles.lead, { fontSize: px(34), lineHeight: px(43) }]} allowFontScaling={false}>
          Estimation <Text style={{ fontFamily: fonts.bold }}>gratuite</Text> en 2 minutes, puis créez votre compte pour sauvegarder le bien et préparer la vente sur le site comme dans l’application mobile.
        </Text>
        <View style={{ flexDirection: "row", gap: px(18) }}>
          <Pressable onPress={() => router.navigate("/estimation-maison")} accessibilityRole="button" testID={`${testID}-estimate`} hitSlop={8} style={({ pressed }) => [styles.btnWhite, { width: px(352), height: px(90), borderRadius: px(20) }, pressed && { opacity: 0.9 }]}>
            <Text style={[styles.btnWhiteText, { fontSize: px(32) }]} allowFontScaling={false}>Estimer gratuitement</Text>
          </Pressable>
          <Pressable onPress={() => router.navigate("/sign-up")} accessibilityRole="button" testID={`${testID}-signup`} hitSlop={8} style={({ pressed }) => [styles.btnSoft, { width: px(357), height: px(90), borderRadius: px(20) }, pressed && { opacity: 0.9 }]}>
            <Text style={[styles.btnSoftText, { fontSize: px(32) }]} allowFontScaling={false}>Créer mon compte</Text>
          </Pressable>
        </View>
      </View>

      {steps.map(({ n, label, Icon, cx, href }) => (
        <Pressable key={n} onPress={() => router.navigate(href)} accessibilityRole="link" testID={`${testID}-step-${n}`} style={{ position: "absolute", left: px(cx - 125), top: paddingTop + y(1435), width: px(250), alignItems: "center" }}>
          <View style={[styles.stepCircle, { width: px(62), height: px(62), borderRadius: px(31) }]}>
            <Text style={[styles.stepNum, { fontSize: px(30) }]}>{n}</Text>
          </View>
          <View style={{ height: px(70), justifyContent: "center" }}>
            <Icon size={px(46)} color={colors.brandPrimary} weight="regular" />
          </View>
          <Text style={[styles.stepLabel, { fontSize: px(32) }]} numberOfLines={1}>{label}</Text>
        </Pressable>
      ))}

      <Image source={WAVE_BOTTOM} style={{ position: "absolute", left: 0, top: paddingTop + y(1712), width, height: px(288) }} contentFit="fill" />
      <Text style={[styles.download, { top: paddingTop + y(1795), fontSize: px(32) }]}>Ou téléchargez l’application :</Text>
      <StoreBadges style={{ position: "absolute", left: 0, right: 0, top: paddingTop + y(1850), justifyContent: "center" }} />
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  root: { backgroundColor: colors.brandTertiary, overflow: "hidden" },
  header: { position: "absolute", left: 0, right: 0, top: 0, backgroundColor: colors.surfaceSecondary, zIndex: 2 },
  signin: { position: "absolute", backgroundColor: colors.brandPrimary, alignItems: "center", justifyContent: "center" },
  signinText: { fontFamily: fonts.semibold, color: colors.onBrandPrimary },
  title: { position: "absolute", left: 0, right: 0, textAlign: "center", fontFamily: fonts.extrabold, color: colors.brandPrimary },
  lead: { textAlign: "center", fontFamily: fonts.medium, color: colors.onBrandPrimary },
  btnWhite: { backgroundColor: colors.surfaceSecondary, alignItems: "center", justifyContent: "center" },
  btnWhiteText: { fontFamily: fonts.bold, color: colors.onSurface },
  btnSoft: { backgroundColor: colors.brandSecondary, alignItems: "center", justifyContent: "center" },
  btnSoftText: { fontFamily: fonts.bold, color: colors.onBrandPrimary },
  stepCircle: { backgroundColor: colors.brandPrimary, alignItems: "center", justifyContent: "center" },
  stepNum: { fontFamily: fonts.bold, color: colors.onBrandPrimary },
  stepLabel: { fontFamily: fonts.bold, color: colors.brandPrimary },
  download: { position: "absolute", left: 0, right: 0, textAlign: "center", fontFamily: fonts.bold, color: colors.onSurface },
}));
