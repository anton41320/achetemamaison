import { Image, ImageSource } from "expo-image";
import { XIcon } from "phosphor-react-native";
import { useState } from "react";
import { ActivityIndicator, Modal, Platform, Pressable, StatusBar, Text, View, useWindowDimensions } from "react-native";
import { Gesture, GestureDetector, GestureHandlerRootView } from "react-native-gesture-handler";
import Animated, { useAnimatedStyle, useSharedValue, withTiming } from "react-native-reanimated";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

const MAX_SCALE = 5;

interface Props {
  visible: boolean;
  onClose: () => void;
  source: ImageSource | number;
  title: string;
  /** Largeur / hauteur de l'image (adapté automatiquement dès que l'image est chargée). */
  ratio?: number;
  caption?: string;
  testID?: string;
}

/**
 * Visionneuse plein écran : pincer pour zoomer (jusqu'à ×5), glisser pour se déplacer, double-toucher pour alterner ×1 / ×2,5 ;
 * croix de fermeture dans la barre du haut + bouton « Fermer » en bas (toujours visibles, iOS et Android).
 */
export function ImageViewerModal({ visible, onClose, source, title, ratio: ratioProp = 1.5, caption, testID = "image-viewer" }: Props) {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const { width, height } = useWindowDimensions();
  const [ratio, setRatio] = useState(ratioProp);
  const [loading, setLoading] = useState(true);
  // Dans un Modal Android, les insets peuvent valoir 0 : on retombe sur la hauteur de la barre d'état.
  const top = Math.max(insets.top, Platform.OS === "android" ? StatusBar.currentHeight ?? 0 : 0);
  const bottom = Math.max(insets.bottom, spacing.lg);

  const scale = useSharedValue(1);
  const savedScale = useSharedValue(1);
  const tx = useSharedValue(0);
  const ty = useSharedValue(0);
  const savedTx = useSharedValue(0);
  const savedTy = useSharedValue(0);

  const reset = () => {
    scale.value = 1;
    savedScale.value = 1;
    tx.value = 0;
    ty.value = 0;
    savedTx.value = 0;
    savedTy.value = 0;
  };

  const pinch = Gesture.Pinch()
    .onUpdate((e) => {
      scale.value = Math.min(MAX_SCALE, Math.max(1, savedScale.value * e.scale));
    })
    .onEnd(() => {
      savedScale.value = scale.value;
      if (scale.value <= 1.02) {
        tx.value = withTiming(0);
        ty.value = withTiming(0);
        savedTx.value = 0;
        savedTy.value = 0;
      }
    });
  const pan = Gesture.Pan()
    .minPointers(1)
    .maxPointers(2)
    .onUpdate((e) => {
      if (scale.value <= 1) return;
      tx.value = savedTx.value + e.translationX;
      ty.value = savedTy.value + e.translationY;
    })
    .onEnd(() => {
      savedTx.value = tx.value;
      savedTy.value = ty.value;
    });
  const doubleTap = Gesture.Tap()
    .numberOfTaps(2)
    .onEnd(() => {
      const target = scale.value > 1.5 ? 1 : 2.5;
      scale.value = withTiming(target);
      savedScale.value = target;
      if (target === 1) {
        tx.value = withTiming(0);
        ty.value = withTiming(0);
        savedTx.value = 0;
        savedTy.value = 0;
      }
    });
  const gesture = Gesture.Simultaneous(pinch, pan, doubleTap);
  const animated = useAnimatedStyle(() => ({
    transform: [{ translateX: tx.value }, { translateY: ty.value }, { scale: scale.value }],
  }));

  // Image ajustée à l'écran (largeur ou hauteur limitante), au-dessus de la barre et sous le pied de page.
  const availW = width;
  const availH = height - top - 56 - bottom - 72;
  const fitW = Math.min(availW, availH * ratio);
  const fitH = fitW / ratio;

  const close = () => {
    reset();
    onClose();
  };

  return (
    <Modal visible={visible} animationType="fade" onRequestClose={close} statusBarTranslucent>
      <GestureHandlerRootView style={{ flex: 1 }}>
        <View style={[styles.viewer, { paddingTop: top }]} testID={testID}>
          <View style={styles.bar}>
            <Text style={styles.barTitle} numberOfLines={1}>{title}</Text>
            <Pressable testID={`${testID}-close`} accessibilityRole="button" accessibilityLabel="Fermer" onPress={close} style={styles.closeBtn} hitSlop={8}>
              <XIcon size={22} color={colors.onHero} weight="bold" />
            </Pressable>
          </View>
          <GestureDetector gesture={gesture}>
            <View style={styles.stage}>
              <Animated.View style={animated}>
                <Image
                  source={source}
                  style={{ width: fitW, height: fitH }}
                  contentFit="contain"
                  transition={200}
                  onLoadStart={() => setLoading(true)}
                  onLoad={(e) => {
                    const { width: w, height: h } = e.source;
                    if (w && h) setRatio(w / h);
                    setLoading(false);
                  }}
                  onError={() => setLoading(false)}
                />
              </Animated.View>
              {loading ? (
                <View style={styles.loading} pointerEvents="none">
                  <ActivityIndicator color={colors.onHero} size="large" />
                  <Text style={styles.hint}>Chargement de l’image haute définition…</Text>
                </View>
              ) : null}
            </View>
          </GestureDetector>
          <View style={[styles.footer, { paddingBottom: bottom }]}>
            <Text style={styles.hint} numberOfLines={2}>{caption ?? "Pincez pour zoomer · double-touchez pour agrandir · glissez pour vous déplacer"}</Text>
            <Pressable testID={`${testID}-close-bottom`} accessibilityRole="button" onPress={close} style={({ pressed }) => [styles.footerBtn, pressed && { opacity: 0.85 }]}>
              <XIcon size={18} color={colors.onBrandPrimary} weight="bold" />
              <Text style={styles.footerBtnText}>Fermer</Text>
            </Pressable>
          </View>
        </View>
      </GestureHandlerRootView>
    </Modal>
  );
}

const useStyles = makeStyles((colors) => ({
  viewer: { flex: 1, backgroundColor: colors.surfaceInverse },
  bar: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingLeft: spacing.lg, paddingRight: spacing.sm, height: 56, gap: spacing.md },
  barTitle: { flex: 1, fontFamily: fonts.semibold, fontSize: 14, color: colors.onHero },
  closeBtn: { width: 44, height: 44, alignItems: "center", justifyContent: "center", borderRadius: radius.pill, backgroundColor: colors.scrimTop, borderWidth: 1, borderColor: colors.onHeroMuted },
  stage: { flex: 1, alignItems: "center", justifyContent: "center", overflow: "hidden" },
  loading: { position: "absolute", alignItems: "center", gap: spacing.md },
  footer: { paddingHorizontal: spacing.lg, paddingTop: spacing.md, gap: spacing.md, alignItems: "center" },
  hint: { fontFamily: fonts.regular, fontSize: 12, lineHeight: 17, color: colors.onHeroMuted, textAlign: "center" },
  footerBtn: { flexDirection: "row", alignItems: "center", gap: spacing.sm, minHeight: 48, paddingHorizontal: spacing.xl, borderRadius: radius.pill, backgroundColor: colors.brandPrimary },
  footerBtnText: { fontFamily: fonts.semibold, fontSize: 15, color: colors.onBrandPrimary },
}));
