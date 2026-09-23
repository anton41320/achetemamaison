import { useRouter } from "expo-router";
import { ChartLineUpIcon, FolderOpenIcon, SparkleIcon } from "phosphor-react-native";
import { useRef, useState } from "react";
import { Dimensions, FlatList, Pressable, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { BrandLogo } from "@/src/components/BrandLogo";
import { PrimaryButton } from "@/src/components/PrimaryButton";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

const SLIDES = [
  { key: "estimation", Icon: ChartLineUpIcon, title: "Estimez votre bien au juste prix",
    text: "Une fourchette fiable fondée sur les ventes réelles autour de chez vous (données DVF), expliquée critère par critère." },
  { key: "annonce", Icon: SparkleIcon, title: "Une annonce qui donne envie",
    text: "Texte rédigé par l’IA dans le style de votre choix et photos retouchées, prêts à publier." },
  { key: "dossier", Icon: FolderOpenIcon, title: "Un dossier de vente complet",
    text: "Checklist des diagnostics, lecture automatique de vos documents, rappels d’expiration et export pour le notaire." },
];

export default function WelcomeScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const [index, setIndex] = useState(0);
  const listRef = useRef<FlatList>(null);
  const width = Dimensions.get("window").width;

  return (
    <View style={[styles.screen, { paddingTop: insets.top, paddingBottom: insets.bottom + spacing.lg }]} testID="welcome-screen">
      <View style={styles.brand}>
        <BrandLogo size={96} wordmark="column" testID="welcome-logo" />
      </View>
      <FlatList
        ref={listRef}
        data={SLIDES}
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        keyExtractor={(s) => s.key}
        onMomentumScrollEnd={(e) => setIndex(Math.round(e.nativeEvent.contentOffset.x / width))}
        renderItem={({ item }) => (
          <View style={[styles.slide, { width }]} testID={`welcome-slide-${item.key}`}>
            <View style={styles.iconWrap}>
              <item.Icon size={56} color={colors.brandPrimary} weight="duotone" />
            </View>
            <Text style={styles.title}>{item.title}</Text>
            <Text style={styles.text}>{item.text}</Text>
          </View>
        )}
      />
      <View style={styles.dots}>
        {SLIDES.map((s, i) => (
          <Pressable
            key={s.key}
            accessibilityLabel={`Écran ${i + 1}`}
            onPress={() => {
              listRef.current?.scrollToIndex({ index: i });
              setIndex(i);
            }}
            style={[styles.dot, i === index && styles.dotActive]}
            testID={`welcome-dot-${i}`}
          />
        ))}
      </View>
      <View style={styles.actions}>
        <PrimaryButton title="Créer un compte" onPress={() => router.push("/sign-up")} testID="welcome-signup-button" />
        <PrimaryButton title="J’ai déjà un compte" variant="secondary" onPress={() => router.push("/sign-in")} testID="welcome-signin-button" />
        <Text style={styles.legal}>Estimation gratuite ; dossier de vente et outils IA avec le Pack premium (49 € par bien). Vos données restent privées et liées à votre compte.</Text>
      </View>
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  screen: { flex: 1, backgroundColor: colors.surface },
  brand: { alignItems: "center", marginTop: spacing.lg },
  slide: { flex: 1, alignItems: "center", justifyContent: "center", paddingHorizontal: spacing.xl, gap: spacing.lg },
  iconWrap: { width: 120, height: 120, borderRadius: radius.pill, backgroundColor: colors.brandTertiary, alignItems: "center", justifyContent: "center" },
  title: { fontFamily: fonts.bold, fontSize: 26, lineHeight: 32, textAlign: "center", color: colors.onSurface },
  text: { fontFamily: fonts.regular, fontSize: 15, lineHeight: 22, textAlign: "center", color: colors.onSurfaceTertiary },
  dots: { flexDirection: "row", justifyContent: "center", gap: spacing.sm, marginVertical: spacing.lg },
  dot: { width: 10, height: 10, borderRadius: radius.pill, backgroundColor: colors.border },
  dotActive: { width: 24, backgroundColor: colors.brandPrimary },
  actions: { paddingHorizontal: spacing.lg, gap: spacing.md },
  legal: { fontFamily: fonts.regular, fontSize: 12, lineHeight: 17, textAlign: "center", color: colors.muted },
}));
