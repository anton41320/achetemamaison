import { Platform, useWindowDimensions } from "react-native";

export const BREAKPOINTS = { tablet: 768, desktop: 1024 } as const;
/** Largeur maximale de la colonne de contenu sur grand écran. */
export const CONTENT_MAX_WIDTH = 1120;
export const SIDEBAR_WIDTH = 264;

/** Points de rupture responsive. Les variantes « desktop » ne s'activent que dans un navigateur (jamais sur iOS/Android). */
export function useBreakpoint() {
  const { width, height } = useWindowDimensions();
  const isWeb = Platform.OS === "web";
  return {
    width,
    height,
    isWeb,
    isTablet: width >= BREAKPOINTS.tablet,
    isDesktop: isWeb && width >= BREAKPOINTS.desktop,
    /** Nombre de colonnes conseillé pour les grilles de cartes. */
    columns: isWeb && width >= BREAKPOINTS.desktop ? 3 : width >= BREAKPOINTS.tablet ? 2 : 1,
  };
}
