// Design tokens for this app. Light theme only.Always modify the colors and theme to Dark, Light or Dark and Light according to the design guidelines.
//
// The keys match the "color" block of /app/design_guidelines.json. Fill the
// values from that file (or from the user's brand colors). Keep every key; do
// not add a second theme or colors file; do not write color literals in
// components.
//
// How the names work: a plain key is a background, and its `on` partner is the
// text or icon color that sits on top of it. Always use them as a pair.
//   <View style={{ backgroundColor: colors.brandPrimary }}>
//     <Text style={{ color: colors.onBrandPrimary }}>Continue</Text>
//   </View>
//
// Styling a screen or component: build the sheet with makeStyles so colors
// and layout live together and follow the active scheme:
//   const useStyles = makeStyles((colors) => ({
//     card: { backgroundColor: colors.surfaceSecondary, padding: 16 },
//     title: { color: colors.onSurfaceSecondary, fontSize: 16 },
//   }));
//   function Screen() {
//     const styles = useStyles();
//     return <View style={styles.card}><Text style={styles.title}>Hi</Text></View>;
//   }
// For color props that are not styles (icon color, placeholderTextColor,
// ActivityIndicator) read useTheme().colors inside the component.
// Never call StyleSheet.create with color values at module level; it cannot
// follow the scheme.
//
// To support dark mode later: add `dark` to `themes` with every key filled.
// Nothing else changes; the device setting takes over automatically.
// Feel free to add as many new colors as you need to support the design guidelines.

import { useMemo } from "react";
import { Appearance, StyleSheet, useColorScheme } from "react-native";

export type ColorScheme = "light" | "dark";

// Brand palette « Achète ma maison » : bleu du logo (#1656C9 → #0B3B8F) sur fonds clairs teintés de bleu.
const light = {
  surface: "#F4F7FC",
  onSurface: "#0F1F3D",
  surfaceSecondary: "#FFFFFF",
  onSurfaceSecondary: "#0F1F3D",
  surfaceTertiary: "#E4ECF8",
  onSurfaceTertiary: "#34486B",
  surfaceInverse: "#0B3B8F",
  onSurfaceInverse: "#FFFFFF",
  muted: "#6B7C99",

  brand: "#1656C9",
  onBrand: "#FFFFFF",
  brandPrimary: "#1656C9",
  onBrandPrimary: "#FFFFFF",
  brandSecondary: "#D4E2FA",
  onBrandSecondary: "#0B3B8F",
  brandTertiary: "#E8F0FD",
  onBrandTertiary: "#1656C9",

  success: "#2E9E4F",
  onSuccess: "#FFFFFF",
  successSoft: "#E3F4E8",
  warning: "#D97A00",
  onWarning: "#FFFFFF",
  warningSoft: "#FFF1DF",
  error: "#D9342B",
  onError: "#FFFFFF",
  errorSoft: "#FDE7E5",
  info: "#1656C9",
  onInfo: "#FFFFFF",

  border: "#DCE5F2",
  borderStrong: "#BFCEE6",
  divider: "#E2E9F4",

  // Hero / photo overlays (identical across schemes)
  onHero: "#FFFFFF",
  onHeroMuted: "rgba(255,255,255,0.78)",
  scrimTop: "rgba(11,59,143,0.20)",
  scrimBottom: "rgba(8,30,70,0.88)",
  glassFill: "rgba(255,255,255,0.22)",
  glassBorder: "rgba(255,255,255,0.45)",
  skeleton: "#E4ECF8",
};

export const fonts = {
  regular: "PlusJakartaSans-Regular",
  medium: "PlusJakartaSans-Medium",
  semibold: "PlusJakartaSans-SemiBold",
  bold: "PlusJakartaSans-Bold",
};

export const spacing = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32, xxxl: 48 };
export const radius = { sm: 6, md: 12, lg: 20, pill: 999 };

export type ThemeColors = typeof light;

export const defaultScheme = "light" satisfies ColorScheme;

export const themes: { light: ThemeColors; dark?: ThemeColors } = { light };

// In-app theme toggle, only after `dark` exists in `themes`. Call
// setColorScheme("dark"), setColorScheme("light"), or setColorScheme(null) to
// follow the device. Every useTheme() consumer re-renders. Persisting the
// choice and re-applying it on launch is the toggle's job.
export function setColorScheme(scheme: ColorScheme | null) {
  Appearance.setColorScheme?.(scheme);
}

// Keep native surfaces (alerts, pickers, navigation chrome) on the schemes this
// app ships: light only forces light; once `dark` exists the device decides.
// Optional call because react-native-web does not implement it.
setColorScheme?.(themes.dark ? null : defaultScheme);

export function useTheme(): { scheme: ColorScheme; colors: ThemeColors } {
  const system = useColorScheme();
  const scheme: ColorScheme = system && themes[system] ? system : defaultScheme;
  return { scheme, colors: themes[scheme] ?? themes.light };
}

// Themed StyleSheet: returns a hook that builds the sheet from the active
// scheme's colors and memoizes it until the scheme changes.
export function makeStyles<T extends StyleSheet.NamedStyles<T> | StyleSheet.NamedStyles<any>>(
  factory: (colors: ThemeColors) => T & StyleSheet.NamedStyles<any>,
): () => T {
  return function useStyles(): T {
    const { colors } = useTheme();
    return useMemo(() => StyleSheet.create(factory(colors)), [colors]);
  };
}


