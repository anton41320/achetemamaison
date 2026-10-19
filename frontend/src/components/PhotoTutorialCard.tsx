import { Image } from "expo-image";
import { ArrowsOutIcon, GraduationCapIcon } from "phosphor-react-native";
import { useState } from "react";
import { Pressable, Text, View } from "react-native";

import { ImageViewerModal } from "@/src/components/ImageViewerModal";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

const TUTO = require("../../assets/images/photo-tuto.jpg");
const RATIO = 1536 / 1024;

/** Illustrated guide "Comment prendre une maison en photo ?" — thumbnail card, tap for a zoomable full-screen view. */
export function PhotoTutorialCard() {
  const styles = useStyles();
  const { colors } = useTheme();
  const [open, setOpen] = useState(false);

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

      <ImageViewerModal visible={open} onClose={() => setOpen(false)} source={TUTO} ratio={RATIO} title="Tuto photo" testID="photo-tuto-viewer" />
    </>
  );
}

const useStyles = makeStyles((colors) => ({
  card: { backgroundColor: colors.surface, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, padding: spacing.lg, gap: spacing.md },
  head: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  title: { flex: 1, fontFamily: fonts.bold, fontSize: 15, color: colors.onSurface },
  thumb: { width: "100%", aspectRatio: RATIO, borderRadius: radius.md, backgroundColor: colors.brandTertiary },
  hint: { fontFamily: fonts.regular, fontSize: 12, lineHeight: 17, color: colors.muted },
}));
