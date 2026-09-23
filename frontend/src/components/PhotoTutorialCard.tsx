import { Image } from "expo-image";
import { ArrowsOutIcon, GraduationCapIcon, XIcon } from "phosphor-react-native";
import { useState } from "react";
import { Modal, Pressable, ScrollView, Text, View, useWindowDimensions } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

const TUTO = require("../../assets/images/photo-tuto.jpg");
const RATIO = 1536 / 1024;

/** Illustrated guide "Comment prendre une maison en photo ?" — thumbnail card, tap for a zoomable full-screen view. */
export function PhotoTutorialCard() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const { width, height } = useWindowDimensions();
  const [open, setOpen] = useState(false);
  // Landscape poster: in full screen, fit the height so the text stays legible; the user scrolls horizontally / pinches to zoom.
  const fullH = Math.min(height - insets.top - insets.bottom - 96, (width * 2) / RATIO);
  const fullW = fullH * RATIO;

  return (
    <>
      <Pressable testID="photo-tuto-card" accessibilityRole="button" accessibilityLabel="Ouvrir le tuto photo" onPress={() => setOpen(true)} style={({ pressed }) => [styles.card, pressed && { opacity: 0.9 }]}>
        <View style={styles.head}>
          <GraduationCapIcon size={20} color={colors.brandPrimary} weight="duotone" />
          <Text style={styles.title}>Comment prendre une maison en photo ?</Text>
          <ArrowsOutIcon size={18} color={colors.muted} />
        </View>
        <Image source={TUTO} style={styles.thumb} contentFit="cover" transition={200} accessibilityLabel="Tuto : comment prendre une maison en photo" />
        <Text style={styles.hint}>Téléphone à l’horizontale, grand angle (0,5x), pleine lumière, à 1 m 50 du sol… Touchez pour agrandir le tuto.</Text>
      </Pressable>

      <Modal visible={open} animationType="fade" onRequestClose={() => setOpen(false)} statusBarTranslucent>
        <View style={[styles.viewer, { paddingTop: insets.top }]} testID="photo-tuto-viewer">
          <View style={styles.viewerBar}>
            <Text style={styles.viewerTitle}>Tuto photo · pincez pour zoomer</Text>
            <Pressable testID="photo-tuto-close" accessibilityRole="button" accessibilityLabel="Fermer" onPress={() => setOpen(false)} style={styles.close}>
              <XIcon size={22} color={colors.onHero} weight="bold" />
            </Pressable>
          </View>
          <ScrollView maximumZoomScale={4} minimumZoomScale={1} bouncesZoom centerContent contentContainerStyle={styles.zoomArea}>
            <ScrollView horizontal showsHorizontalScrollIndicator contentContainerStyle={{ alignItems: "center", paddingBottom: insets.bottom + spacing.lg }}>
              <Image source={TUTO} style={{ width: fullW, height: fullH }} contentFit="contain" />
            </ScrollView>
          </ScrollView>
        </View>
      </Modal>
    </>
  );
}

const useStyles = makeStyles((colors) => ({
  card: { backgroundColor: colors.surface, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, padding: spacing.lg, gap: spacing.md },
  head: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  title: { flex: 1, fontFamily: fonts.bold, fontSize: 15, color: colors.onSurface },
  thumb: { width: "100%", aspectRatio: RATIO, borderRadius: radius.md, backgroundColor: colors.brandTertiary },
  hint: { fontFamily: fonts.regular, fontSize: 12, lineHeight: 17, color: colors.muted },
  viewer: { flex: 1, backgroundColor: colors.scrimBottom },
  viewerBar: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: spacing.lg, height: 56 },
  viewerTitle: { fontFamily: fonts.semibold, fontSize: 14, color: colors.onHero },
  close: { width: 44, height: 44, alignItems: "center", justifyContent: "center", borderRadius: radius.pill },
  zoomArea: { flexGrow: 1, justifyContent: "center" },
}));
