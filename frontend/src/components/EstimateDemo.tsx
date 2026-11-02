import { CheckCircleIcon, MagnifyingGlassIcon, MapPinIcon, ArrowCounterClockwiseIcon } from "phosphor-react-native";
import { useEffect, useState } from "react";
import { Pressable, Text, View } from "react-native";
import Animated, { FadeIn, FadeInDown } from "react-native-reanimated";

import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

/** Démo animée (~20 s, en boucle) du parcours d'estimation, dessinée dans un téléphone : adresse → caractéristiques → analyse → résultat. */
const ADDRESS = "12 rue des Lilas, Blois";
const SCENES = [
  { from: 0, to: 5000, label: "Saisissez l’adresse" },
  { from: 5000, to: 10000, label: "Décrivez le bien en 4 questions" },
  { from: 10000, to: 14000, label: "Nous analysons les ventes réelles" },
  { from: 14000, to: 21000, label: "Votre fourchette de prix, expliquée" },
];
const TOTAL = SCENES[SCENES.length - 1].to;
const TICK = 60;
const PRICE = 248000;
const fmt = (n: number) => `${Math.round(n).toLocaleString("fr-FR")} €`;
const clamp01 = (v: number) => Math.max(0, Math.min(1, v));

export function EstimateDemo() {
  const styles = useStyles();
  const { colors } = useTheme();
  const [t, setT] = useState(0);
  const [run, setRun] = useState(0);

  useEffect(() => {
    setT(0);
    const start = Date.now();
    const id = setInterval(() => setT((Date.now() - start) % TOTAL), TICK);
    return () => clearInterval(id);
  }, [run]);

  const scene = SCENES.findIndex((s) => t >= s.from && t < s.to);
  const local = t - SCENES[Math.max(scene, 0)].from;

  const renderScreen = () => {
    if (scene === 0) {
      const typed = ADDRESS.slice(0, Math.floor(clamp01(local / 2600) * ADDRESS.length));
      const showList = local > 1400;
      const picked = local > 3600;
      return (
        <Animated.View key="s0" entering={FadeIn.duration(300)} style={styles.screenBody}>
          <Text style={styles.screenTitle}>Où se trouve votre bien ?</Text>
          <View style={[styles.field, picked && { borderColor: colors.brandPrimary }]}>
            <MagnifyingGlassIcon size={14} color={colors.muted} />
            <Text style={styles.fieldText}>{typed}{!picked && local % 1000 < 500 ? "|" : ""}</Text>
          </View>
          {showList ? (
            <View style={styles.suggestions}>
              {["12 Rue des Lilas, 41000 Blois", "12 Rue des Lilas, 41350 Vineuil"].map((s, i) => (
                <View key={s} style={[styles.suggestion, picked && i === 0 && { backgroundColor: colors.brandTertiary }]}>
                  <MapPinIcon size={12} color={colors.brandPrimary} weight="fill" />
                  <Text style={styles.suggestionText} numberOfLines={1}>{s}</Text>
                </View>
              ))}
            </View>
          ) : null}
        </Animated.View>
      );
    }
    if (scene === 1) {
      const step = Math.floor(local / 1200); // 0..3 : type, surface, pièces, état
      const rows: { q: string; opts: string[]; pick: number }[] = [
        { q: "Type de bien", opts: ["Maison", "Appartement"], pick: 0 },
        { q: "Surface habitable", opts: ["110 m²"], pick: 0 },
        { q: "Pièces · chambres", opts: ["5 pièces", "3 chambres"], pick: -1 },
        { q: "État général", opts: ["À rafraîchir", "Correct", "Rénové"], pick: 1 },
      ];
      return (
        <Animated.View key="s1" entering={FadeIn.duration(300)} style={styles.screenBody}>
          <Text style={styles.screenTitle}>Quelques caractéristiques</Text>
          {rows.slice(0, Math.min(step + 1, rows.length)).map((r, i) => (
            <Animated.View key={r.q} entering={FadeInDown.duration(260)} style={{ gap: 4 }}>
              <Text style={styles.q}>{r.q}</Text>
              <View style={{ flexDirection: "row", gap: 4, flexWrap: "wrap" }}>
                {r.opts.map((o, j) => {
                  const on = r.pick === -1 || j === r.pick;
                  return (
                    <View key={o} style={[styles.chip, on && i <= step && { backgroundColor: colors.brandPrimary, borderColor: colors.brandPrimary }]}>
                      <Text style={[styles.chipText, on && i <= step && { color: colors.onBrandPrimary }]}>{o}</Text>
                    </View>
                  );
                })}
              </View>
            </Animated.View>
          ))}
        </Animated.View>
      );
    }
    if (scene === 2) {
      const p = clamp01(local / 3600);
      const items = ["27 ventes comparables trouvées (DVF)", "Modèle statistique appliqué", "Environnement analysé : écoles, gare, commerces", "Tendance du marché local intégrée"];
      return (
        <Animated.View key="s2" entering={FadeIn.duration(300)} style={styles.screenBody}>
          <Text style={styles.screenTitle}>Analyse en cours…</Text>
          <View style={styles.track}><View style={[styles.fill, { width: `${Math.round(p * 100)}%` }]} /></View>
          {items.map((it, i) => {
            const done = p > (i + 1) / (items.length + 0.5);
            return (
              <View key={it} style={styles.checkRow}>
                <CheckCircleIcon size={14} color={done ? colors.success : colors.border} weight="fill" />
                <Text style={[styles.checkText, !done && { color: colors.muted }]}>{it}</Text>
              </View>
            );
          })}
        </Animated.View>
      );
    }
    const p = clamp01(local / 1800);
    const eased = 1 - Math.pow(1 - p, 3);
    const show = (ms: number) => local > ms;
    return (
      <Animated.View key="s3" entering={FadeIn.duration(300)} style={styles.screenBody}>
        <Text style={styles.screenTitle}>Votre estimation</Text>
        <View style={styles.priceCard}>
          <Text style={styles.priceKicker}>PRIX DE VENTE CONSEILLÉ</Text>
          <Text style={styles.price}>{fmt(PRICE * eased)}</Text>
          <Text style={styles.range}>Fourchette 235 000 – 262 000 €</Text>
          <View style={styles.rangeTrack}>
            <View style={styles.rangeInner} />
            <View style={[styles.rangeCursor, { left: `${18 + 60 * eased}%` }]} />
          </View>
          {show(1600) ? <Animated.View entering={FadeIn.duration(250)} style={styles.confidence}><Text style={styles.confidenceText}>Confiance élevée</Text></Animated.View> : null}
        </View>
        {[["Maison 110 m², 5 pièces", "+ 0 €"], ["Terrain 500 m², exposition sud", "+ 9 500 €"], ["État correct, sans travaux", "+ 4 000 €"]].map(([k, v], i) =>
          show(2400 + i * 700) ? (
            <Animated.View key={k} entering={FadeInDown.duration(260)} style={styles.explainRow}>
              <Text style={styles.explainKey}>{k}</Text>
              <Text style={styles.explainVal}>{v}</Text>
            </Animated.View>
          ) : null,
        )}
      </Animated.View>
    );
  };

  return (
    <View style={styles.wrap} testID="estimate-demo">
      <View style={styles.phone}>
        <View style={styles.notch} />
        {renderScreen()}
      </View>
      <View style={styles.legend}>
        {SCENES.map((s, i) => (
          <View key={s.label} style={styles.legendRow}>
            <View style={[styles.legendDot, i === scene && { backgroundColor: colors.brandPrimary }, i < scene && { backgroundColor: colors.success }]}>
              <Text style={[styles.legendNum, i <= scene && { color: colors.onBrandPrimary }]}>{i + 1}</Text>
            </View>
            <Text style={[styles.legendText, i === scene && { color: colors.onBrandPrimary, fontFamily: fonts.bold }]}>{s.label}</Text>
          </View>
        ))}
        <View style={styles.footer}>
          <View style={styles.progress}><View style={[styles.fill, { width: `${Math.round((t / TOTAL) * 100)}%` }]} /></View>
          <Pressable onPress={() => setRun((r) => r + 1)} style={styles.replay} accessibilityRole="button" accessibilityLabel="Rejouer la démonstration" testID="estimate-demo-replay" hitSlop={8}>
            <ArrowCounterClockwiseIcon size={16} color={colors.brandPrimary} weight="bold" />
            <Text style={styles.replayText}>Rejouer · 20 s</Text>
          </Pressable>
        </View>
      </View>
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  // Fond bleu profond identique en clair et sombre (mockup marketing).
  wrap: { backgroundColor: "#0B3B8F", borderRadius: radius.lg, padding: spacing.lg, gap: spacing.lg, alignItems: "center", width: "100%" },
  phone: { width: 240, minHeight: 380, backgroundColor: colors.surface, borderRadius: 28, borderWidth: 6, borderColor: "#0F1B2D", padding: 14, paddingTop: 26, overflow: "hidden" },
  notch: { position: "absolute", top: 6, alignSelf: "center", width: 70, height: 14, borderRadius: 7, backgroundColor: "#0F1B2D" },
  screenBody: { gap: 8, flex: 1 },
  screenTitle: { fontFamily: fonts.extrabold, fontSize: 14, color: colors.onSurface, marginBottom: 2 },
  field: { flexDirection: "row", alignItems: "center", gap: 6, borderWidth: 1, borderColor: colors.border, borderRadius: radius.md, paddingHorizontal: 8, minHeight: 34, backgroundColor: colors.surfaceSecondary },
  fieldText: { fontFamily: fonts.medium, fontSize: 11, color: colors.onSurface, flex: 1 },
  suggestions: { borderWidth: 1, borderColor: colors.border, borderRadius: radius.md, overflow: "hidden" },
  suggestion: { flexDirection: "row", alignItems: "center", gap: 6, paddingHorizontal: 8, minHeight: 30 },
  suggestionText: { fontFamily: fonts.regular, fontSize: 10, color: colors.onSurfaceSecondary, flex: 1 },
  q: { fontFamily: fonts.semibold, fontSize: 10, color: colors.muted },
  chip: { borderWidth: 1, borderColor: colors.border, borderRadius: radius.pill, paddingHorizontal: 8, minHeight: 22, justifyContent: "center", backgroundColor: colors.surfaceSecondary },
  chipText: { fontFamily: fonts.medium, fontSize: 10, color: colors.onSurface },
  track: { height: 6, borderRadius: 3, backgroundColor: colors.border, overflow: "hidden" },
  fill: { height: "100%", backgroundColor: colors.brandPrimary, borderRadius: 3 },
  checkRow: { flexDirection: "row", alignItems: "center", gap: 6 },
  checkText: { fontFamily: fonts.medium, fontSize: 10, color: colors.onSurface, flex: 1 },
  priceCard: { backgroundColor: colors.surfaceSecondary, borderWidth: 1, borderColor: colors.border, borderRadius: radius.md, padding: 10, gap: 4 },
  priceKicker: { fontFamily: fonts.bold, fontSize: 8, letterSpacing: 0.5, color: colors.muted },
  price: { fontFamily: fonts.extrabold, fontSize: 24, color: colors.brandPrimary },
  range: { fontFamily: fonts.medium, fontSize: 9, color: colors.muted },
  rangeTrack: { height: 6, borderRadius: 3, backgroundColor: colors.brandTertiary, marginTop: 4, position: "relative" },
  rangeInner: { position: "absolute", left: "18%", right: "22%", top: 0, bottom: 0, backgroundColor: colors.brandSecondary, borderRadius: 3 },
  rangeCursor: { position: "absolute", top: -4, width: 6, height: 14, borderRadius: 3, backgroundColor: colors.brandPrimary },
  confidence: { alignSelf: "flex-start", backgroundColor: colors.successSoft, borderRadius: radius.pill, paddingHorizontal: 8, paddingVertical: 3, marginTop: 4 },
  confidenceText: { fontFamily: fonts.bold, fontSize: 9, color: colors.success },
  explainRow: { flexDirection: "row", justifyContent: "space-between", gap: 6 },
  explainKey: { fontFamily: fonts.medium, fontSize: 10, color: colors.onSurfaceSecondary, flex: 1 },
  explainVal: { fontFamily: fonts.bold, fontSize: 10, color: colors.success },
  legend: { width: "100%", gap: spacing.sm },
  legendRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  legendDot: { width: 22, height: 22, borderRadius: 11, backgroundColor: "rgba(255,255,255,0.18)", alignItems: "center", justifyContent: "center" },
  legendNum: { fontFamily: fonts.bold, fontSize: 11, color: colors.brandTertiary },
  legendText: { fontFamily: fonts.medium, fontSize: 13, color: colors.brandTertiary, flex: 1 },
  footer: { flexDirection: "row", alignItems: "center", gap: spacing.md, marginTop: spacing.xs },
  progress: { flex: 1, height: 4, borderRadius: 2, backgroundColor: "rgba(255,255,255,0.2)", overflow: "hidden" },
  replay: { flexDirection: "row", alignItems: "center", gap: 6, minHeight: 36, paddingHorizontal: spacing.sm, backgroundColor: colors.surface, borderRadius: radius.pill },
  replayText: { fontFamily: fonts.bold, fontSize: 12, color: colors.brandPrimary },
}));
