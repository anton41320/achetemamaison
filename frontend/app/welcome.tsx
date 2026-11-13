import { Redirect } from "expo-router";
import { ScrollView, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useSession } from "@/src/auth";
import { HeroMobile } from "@/src/components/HeroMobile";
import { makeStyles } from "@/src/theme";
import { useBreakpoint } from "@/src/web/useBreakpoint";

/** Écran d'accueil de l'application (avant connexion) : reproduit la maquette mobile (Noisette, 3 étapes, stores). */
export default function WelcomeScreen() {
  const styles = useStyles();
  const insets = useSafeAreaInsets();
  const { user } = useSession();
  const { isDesktop } = useBreakpoint();

  // Sur ordinateur (navigateur), la page d'accueil publique remplace l'écran de bienvenue mobile.
  if (isDesktop && !user) return <Redirect href="/accueil" />;

  return (
    <View style={styles.screen} testID="welcome-screen">
      <ScrollView contentContainerStyle={{ paddingBottom: insets.bottom }} showsVerticalScrollIndicator={false} bounces={false}>
        <HeroMobile withHeader paddingTop={insets.top} signedIn={!!user} testID="welcome-hero" />
      </ScrollView>
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  screen: { flex: 1, backgroundColor: colors.brandTertiary },
}));
