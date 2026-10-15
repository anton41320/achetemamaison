import { useRouter } from "expo-router";
import { ArrowRightIcon, ChartLineUpIcon, FolderOpenIcon, HandshakeIcon } from "phosphor-react-native";
import { useRef, useState } from "react";
import { Dimensions, FlatList, Pressable, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useSession } from "@/src/auth";
import { BrandLogo } from "@/src/components/BrandLogo";
import { PrimaryButton } from "@/src/components/PrimaryButton";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

/** The three stages of a sale, in the seller's order. Tapping a stage moves to the next one. */
const STEPS = [
  { key: "estimation", Icon: ChartLineUpIcon, label: "Estimation", title: "Estimez votre bien au juste prix",
    text: "Une valeur fiable fondée sur les ventes réelles autour de chez vous, expliquée critère par critère. Gratuit et sans engagement." },
  { key: "vente", Icon: HandshakeIcon, label: "Mise en vente", title: "Accompagnement et outils professionnels",
    text: "Fixez votre prix de vente, obtenez une annonce rédigée par l’IA, des photos retouchées et des conseils pour les visites." },
  { key: "vendu", Icon: FolderOpenIcon, label: "Vendu", title: "Un dossier de vente complet",
    text: "Checklist des diagnostics, lecture automatique de vos documents, rappels d’expiration et export prêt pour le notaire." },
];

export default function WelcomeScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { user } = useSession();
  const [index, setIndex] = useState(0);
  const listRef = useRef<FlatList>(null);
  // Largeur mesurée du conteneur (sur le Web « ordinateur », l'écran est affiché dans une carte centrée plus étroite que la fenêtre).
  const [width, setWidth] = useState(Dimensions.get("window").width);

  const goTo = (i: number) => {
    listRef.current?.scrollToIndex({ index: i, animated: true });
    setIndex(i);
  };
  const next = () => (index < STEPS.length - 1 ? goTo(index + 1) : router.push(user ? "/" : "/sign-up"));

  return (
    <View style={[styles.screen, { paddingTop: insets.top, paddingBottom: insets.bottom + spacing.lg }]} testID="welcome-screen">
      <View style={styles.brand}>
        <BrandLogo size={84} wordmark="column" testID="welcome-logo" />
      </View>

      <View style={styles.stepper} testID="welcome-stepper">
        {STEPS.map((s, i) => (
          <Pressable key={s.key} testID={`welcome-step-${i}`} accessibilityRole="button" accessibilityLabel={`Étape ${i + 1} : ${s.label}`} onPress={() => goTo(i)} style={styles.stepItem}>
            <View style={[styles.stepCircle, i <= index && styles.stepCircleActive]}>
              <Text style={[styles.stepNum, i <= index && styles.stepNumActive]}>{i + 1}</Text>
            </View>
            <Text style={[styles.stepLabel, i === index && styles.stepLabelActive]} numberOfLines={1}>{s.label}</Text>
            {i < STEPS.length - 1 ? <View style={[styles.stepLine, i < index && styles.stepLineActive]} /> : null}
          </Pressable>
        ))}
      </View>

      <FlatList
        key={width}
        onLayout={(e) => setWidth(Math.round(e.nativeEvent.layout.width) || width)}
        ref={listRef}
        data={STEPS}
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        keyExtractor={(s) => s.key}
        getItemLayout={(_, i) => ({ length: width, offset: width * i, index: i })}
        onMomentumScrollEnd={(e) => setIndex(Math.round(e.nativeEvent.contentOffset.x / width))}
        renderItem={({ item, index: i }) => (
          <Pressable
            testID={`welcome-slide-${item.key}`}
            accessibilityRole="button"
            accessibilityLabel={i < STEPS.length - 1 ? "Passer à l’étape suivante" : user ? "Accéder à mes biens" : "Créer un compte"}
            onPress={next}
            style={({ pressed }) => [styles.slide, { width }, pressed && { opacity: 0.92 }]}
          >
            <View style={styles.iconWrap}>
              <item.Icon size={52} color={colors.brandPrimary} weight="duotone" />
            </View>
            <Text style={styles.kicker}>Étape {i + 1} · {item.label}</Text>
            <Text style={styles.title}>{item.title}</Text>
            <Text style={styles.text}>{item.text}</Text>
            <View style={styles.nextHint}>
              <Text style={styles.nextHintText}>{i < STEPS.length - 1 ? `Étape suivante : ${STEPS[i + 1].label}` : user ? "Accéder à mes biens" : "Commencer gratuitement"}</Text>
              <ArrowRightIcon size={16} color={colors.brandPrimary} weight="bold" />
            </View>
          </Pressable>
        )}
      />

      <View style={styles.actions}>
        {user ? (
          <>
            <PrimaryButton title="Accéder à mes biens" onPress={() => router.replace("/")} testID="welcome-home-button" />
            <Text style={styles.legal}>Connecté en tant que {user.email}. Pour changer de compte, déconnectez-vous depuis « Mon compte ».</Text>
          </>
        ) : (
          <>
            <PrimaryButton title="Créer un compte" onPress={() => router.push("/sign-up")} testID="welcome-signup-button" />
            <PrimaryButton title="J’ai déjà un compte" variant="secondary" onPress={() => router.push("/sign-in")} testID="welcome-signin-button" />
            <Text style={styles.legal}>Estimation gratuite ; outils IA et dossier de vente avec le Pack premium (49 € par bien). Vos données restent privées et liées à votre compte.</Text>
          </>
        )}
      </View>
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  screen: { flex: 1, backgroundColor: colors.surface },
  brand: { alignItems: "center", marginTop: spacing.md },
  stepper: { flexDirection: "row", paddingHorizontal: spacing.lg, marginTop: spacing.lg },
  stepItem: { flex: 1, alignItems: "center", gap: 6, minHeight: 56, position: "relative" },
  stepCircle: { width: 32, height: 32, borderRadius: radius.pill, backgroundColor: colors.surfaceTertiary, alignItems: "center", justifyContent: "center", zIndex: 1 },
  stepCircleActive: { backgroundColor: colors.brandPrimary },
  stepNum: { fontFamily: fonts.bold, fontSize: 14, color: colors.onSurfaceSecondary },
  stepNumActive: { color: colors.onBrandPrimary },
  stepLabel: { fontFamily: fonts.medium, fontSize: 12, color: colors.muted },
  stepLabelActive: { color: colors.brandPrimary, fontFamily: fonts.bold },
  stepLine: { position: "absolute", top: 16, left: "50%", right: "-50%", height: 2, backgroundColor: colors.border },
  stepLineActive: { backgroundColor: colors.brandPrimary },
  slide: { flex: 1, alignItems: "center", justifyContent: "center", paddingHorizontal: spacing.xl, gap: spacing.md },
  iconWrap: { width: 104, height: 104, borderRadius: radius.pill, backgroundColor: colors.brandTertiary, alignItems: "center", justifyContent: "center" },
  kicker: { fontFamily: fonts.semibold, fontSize: 13, color: colors.brandPrimary, textTransform: "uppercase", letterSpacing: 0.8 },
  title: { fontFamily: fonts.bold, fontSize: 24, lineHeight: 30, textAlign: "center", color: colors.onSurface },
  text: { fontFamily: fonts.regular, fontSize: 15, lineHeight: 22, textAlign: "center", color: colors.onSurfaceTertiary },
  nextHint: { flexDirection: "row", alignItems: "center", gap: 6, marginTop: spacing.sm, paddingHorizontal: spacing.md, minHeight: 36, borderRadius: radius.pill, backgroundColor: colors.brandTertiary },
  nextHintText: { fontFamily: fonts.semibold, fontSize: 13, color: colors.brandPrimary },
  actions: { paddingHorizontal: spacing.lg, gap: spacing.md },
  legal: { fontFamily: fonts.regular, fontSize: 12, lineHeight: 17, textAlign: "center", color: colors.muted },
}));
