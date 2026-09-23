import { useRouter } from "expo-router";
import { CaretLeftIcon } from "phosphor-react-native";
import { Pressable, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { APP_NAME, BrandLogo } from "@/src/components/BrandLogo";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

const UPDATED = "17 septembre 2026";
const SUPPORT_EMAIL = "contact@achetesmamaison.fr";

const SECTIONS: { title: string; body: string[] }[] = [
  {
    title: "1. Qui sommes-nous ?",
    body: [
      `${APP_NAME} est une application destinée aux particuliers qui souhaitent estimer puis préparer la vente de leur logement. L’éditeur de l’application est responsable du traitement de vos données. Contact : ${SUPPORT_EMAIL}.`,
    ],
  },
  {
    title: "2. Données que nous collectons",
    body: [
      "Compte : adresse e-mail et mot de passe (stocké uniquement sous forme hachée).",
      "Biens : adresse du logement, caractéristiques déclarées (surface, pièces, état, équipements…), prix cible éventuel.",
      "Documents et photos que vous importez volontairement (diagnostics, titre de propriété, photos du bien).",
      "Achats : référence de commande et e-mail de reçu transmis par notre prestataire de paiement. Aucun numéro de carte n’est stocké par l’application.",
      "Données techniques nécessaires au fonctionnement (journaux serveur, jeton de session).",
    ],
  },
  {
    title: "3. Pourquoi nous les utilisons",
    body: [
      "Calculer et expliquer l’estimation de votre bien à partir des ventes immobilières publiques enregistrées et des risques publics (Géorisques).",
      "Constituer votre dossier de vente : checklist, lecture automatique des documents, rappels d’expiration, export pour le notaire.",
      "Fournir les outils IA du Pack premium (rédaction d’annonce, retouche photo, lecture de documents).",
      "Assurer le paiement, l’envoi de votre reçu et la gestion de votre compte (réinitialisation du mot de passe).",
    ],
  },
  {
    title: "4. Intelligence artificielle",
    body: [
      "Les textes d’annonce, retouches photo et lectures de documents sont produits par des modèles d’IA tiers hébergés hors de l’appareil. Seuls les éléments nécessaires (faits déclarés, photo ou document concerné) leur sont transmis, sans votre adresse e-mail. Les résultats sont des propositions : vous les vérifiez et les validez avant toute utilisation. Les visuels retouchés portent la mention « non contractuel ».",
    ],
  },
  {
    title: "5. Partage et sous-traitants",
    body: [
      "Vos données ne sont ni vendues ni louées. Elles sont traitées par nos prestataires techniques strictement pour les finalités ci-dessus : hébergement et base de données, stockage des fichiers, paiement (Stripe), envoi d’e-mails, fournisseurs de modèles d’IA, géocodage des adresses (Base Adresse Nationale).",
    ],
  },
  {
    title: "6. Durée de conservation",
    body: [
      "Vos données sont conservées tant que votre compte est actif. La suppression du compte depuis l’écran « Mon compte » efface vos biens, documents, photos et annonces ; les justificatifs de paiement sont conservés le temps des obligations comptables légales.",
    ],
  },
  {
    title: "7. Vos droits",
    body: [
      "Conformément au RGPD, vous disposez d’un droit d’accès, de rectification, d’effacement, de limitation et de portabilité. Vous pouvez supprimer votre compte à tout moment dans l’application ou nous écrire à l’adresse ci-dessous. Vous pouvez également saisir la CNIL (cnil.fr).",
    ],
  },
  {
    title: "8. Sécurité",
    body: [
      "Connexions chiffrées (HTTPS), mots de passe hachés, jetons de session à durée limitée, accès aux fichiers réservé au propriétaire du compte. Aucune donnée n’est stockée sur des serveurs sans chiffrement au repos.",
    ],
  },
  {
    title: "9. Support",
    body: [
      `Une question, un problème ou une demande concernant vos données : écrivez-nous à ${SUPPORT_EMAIL}. Nous répondons sous 72 heures ouvrées.`,
    ],
  },
];

/** Public page: privacy policy + support (linked from App Store Connect). */
export default function PrivacyScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  return (
    <View style={[styles.screen, { paddingTop: insets.top }]} testID="privacy-screen">
      <ScrollView contentContainerStyle={[styles.content, { paddingBottom: insets.bottom + spacing.xxl }]}>
        <View style={styles.headRow}>
          {router.canGoBack() ? (
            <Pressable testID="privacy-back" accessibilityRole="button" accessibilityLabel="Retour" onPress={() => router.back()} style={styles.back}>
              <CaretLeftIcon size={22} color={colors.onSurface} />
            </Pressable>
          ) : null}
          <BrandLogo size={40} testID="privacy-logo" />
        </View>
        <Text style={styles.h1}>Politique de confidentialité et support</Text>
        <Text style={styles.meta}>Dernière mise à jour : {UPDATED}</Text>
        {SECTIONS.map((s) => (
          <View key={s.title} style={styles.section}>
            <Text style={styles.h2}>{s.title}</Text>
            {s.body.map((p, i) => (
              <Text key={i} style={styles.p}>{s.body.length > 1 ? "• " : ""}{p}</Text>
            ))}
          </View>
        ))}
      </ScrollView>
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  screen: { flex: 1, backgroundColor: colors.surface },
  content: { padding: spacing.lg, gap: spacing.md, maxWidth: 760, width: "100%", alignSelf: "center" },
  headRow: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  back: { width: 44, height: 44, borderRadius: radius.pill, alignItems: "center", justifyContent: "center", backgroundColor: colors.surfaceSecondary },
  h1: { fontFamily: fonts.bold, fontSize: 26, lineHeight: 32, color: colors.onSurface, marginTop: spacing.sm },
  meta: { fontFamily: fonts.regular, fontSize: 13, color: colors.muted },
  section: { backgroundColor: colors.surfaceSecondary, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, padding: spacing.lg, gap: spacing.sm },
  h2: { fontFamily: fonts.semibold, fontSize: 16, color: colors.onSurfaceSecondary },
  p: { fontFamily: fonts.regular, fontSize: 14, lineHeight: 21, color: colors.onSurfaceTertiary },
}));
