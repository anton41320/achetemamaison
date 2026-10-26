import { View } from "react-native";
import Svg, { Ellipse, Line } from "react-native-svg";

import { useTheme } from "@/src/theme";

type Tone = "primary" | "secondary" | "tertiary";

function toneColor(colors: ReturnType<typeof useTheme>["colors"], tone: Tone) {
  return tone === "primary" ? colors.brandPrimary : tone === "secondary" ? colors.brandSecondary : colors.brandTertiary;
}

/** Élément graphique de la charte : le « trait » incliné aux bouts ronds, utilisé devant les titres de section. */
export function BrandDash({ size = 18, tone = "primary" }: { size?: number; tone?: Tone }) {
  const { colors } = useTheme();
  return (
    <View accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
      <Svg width={size} height={Math.round(size * 0.5)} viewBox="0 0 36 18">
        <Line x1="6" y1="13" x2="30" y2="5" stroke={toneColor(colors, tone)} strokeWidth="7" strokeLinecap="round" />
      </Svg>
    </View>
  );
}

/** Élément graphique de la charte : le « plus » arrondi, utilisé en puce ou en décoration. */
export function BrandPlus({ size = 16, tone = "secondary" }: { size?: number; tone?: Tone }) {
  const { colors } = useTheme();
  const fill = toneColor(colors, tone);
  return (
    <View accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
      <Svg width={size} height={size} viewBox="0 0 40 40">
        <Ellipse cx="20" cy="20" rx="6" ry="18" fill={fill} />
        <Ellipse cx="20" cy="20" rx="18" ry="6" fill={fill} />
      </Svg>
    </View>
  );
}
