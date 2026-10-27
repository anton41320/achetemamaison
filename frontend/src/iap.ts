import Constants, { ExecutionEnvironment } from "expo-constants";
import { Platform } from "react-native";

import { api } from "@/src/api";

export const PACK_PRODUCT_ID = "pack_premium_49";

/** True when the native store (StoreKit / Play Billing) is usable: iOS/Android real build, not Expo Go, key configured. */
export function nativeStoreAvailable(): boolean {
  if (Platform.OS === "web") return false;
  if (Constants.executionEnvironment === ExecutionEnvironment.StoreClient) return false; // Expo Go: no native module
  return !!storeKey();
}

export function isExpoGo(): boolean {
  return Platform.OS !== "web" && Constants.executionEnvironment === ExecutionEnvironment.StoreClient;
}

function storeKey(): string | undefined {
  return Platform.OS === "ios" ? process.env.EXPO_PUBLIC_RC_IOS_KEY : process.env.EXPO_PUBLIC_RC_ANDROID_KEY;
}

// Lazy require: the module must never be loaded on web or in Expo Go.
function purchases() {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  return require("react-native-purchases").default as typeof import("react-native-purchases").default;
}

let configuredFor: string | null = null;

/** Configure RevenueCat once per signed-in user (appUserID = our user id, so webhooks map to the account). */
export async function configureStore(userId: string): Promise<void> {
  if (!nativeStoreAvailable() || configuredFor === userId) return;
  const Purchases = purchases();
  Purchases.configure({ apiKey: storeKey()!, appUserID: userId });
  configuredFor = userId;
}

export type PurchaseOutcome = { status: "unlocked" } | { status: "pending" } | { status: "cancelled" } | { status: "error"; message: string };

/**
 * Buy the pack for one property: server intent → subscriber attribute → store sheet → server confirmation.
 * The server (webhook / claim) is the source of truth for unlocking.
 */
export async function purchasePack(propertyId: string, userId: string): Promise<PurchaseOutcome> {
  try {
    await configureStore(userId);
    const Purchases = purchases();
    await api.iapIntent(propertyId);
    await Purchases.setAttributes({ property_id: propertyId });
    const offerings = await Purchases.getOfferings();
    const packages = offerings.current?.availablePackages ?? Object.values(offerings.all).flatMap((o) => o.availablePackages);
    const pkg = packages.find((p) => p.product.identifier === PACK_PRODUCT_ID || p.product.identifier.startsWith(`${PACK_PRODUCT_ID}:`)) ?? packages[0];
    if (!pkg) return { status: "error", message: "Le Pack premium n’est pas disponible sur la boutique pour le moment." };
    await Purchases.purchasePackage(pkg);
  } catch (e: any) {
    if (e?.userCancelled) return { status: "cancelled" };
    // Erreurs de configuration boutique (produit pas encore approuvé, offre vide…) : message en français, pas le texte brut du SDK.
    const raw = String(e?.message ?? "");
    if (/configuration|offerings|App Store Connect|StoreKit|products registered/i.test(raw)) {
      return { status: "error", message: "Le Pack premium n’est pas encore disponible sur la boutique. Réessayez plus tard ou utilisez un code." };
    }
    return { status: "error", message: raw || "Achat impossible pour le moment." };
  }
  // Confirmation côté serveur (webhook RevenueCat, ou vérification directe via /iap/claim).
  for (let i = 0; i < 8; i++) {
    try {
      const r = await api.iapClaim(propertyId);
      if (r.unlocked) return { status: "unlocked" };
    } catch {
      // keep polling
    }
    await new Promise((res) => setTimeout(res, 1500));
  }
  return { status: "pending" };
}

/** Restore purchases (Apple guideline): re-syncs the store account, then asks the server to reconcile. */
export async function restorePack(propertyId: string, userId: string): Promise<boolean> {
  await configureStore(userId);
  try {
    await purchases().restorePurchases();
  } catch {
    // reconciliation below still worth trying
  }
  const r = await api.iapClaim(propertyId);
  return r.unlocked;
}
