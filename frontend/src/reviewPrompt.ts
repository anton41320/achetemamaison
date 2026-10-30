import AsyncStorage from "@react-native-async-storage/async-storage";
import { Platform } from "react-native";

/** Règles d'affichage de la demande d'avis : une fois après la première estimation ; « Plus tard » → nouvelle demande 7 jours après, une seule fois. */
const KEY = "review_prompt_v1";
const DEVICE_KEY = "review_device_key";
const SNOOZE_MS = 7 * 24 * 3600 * 1000;
const MAX_PROMPTS = 2;

type State = { prompts: number; done?: boolean; last?: number };

async function read(): Promise<State> {
  try {
    const raw = await AsyncStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as State) : { prompts: 0 };
  } catch {
    return { prompts: 0 };
  }
}

export async function shouldPromptReview(): Promise<boolean> {
  const s = await read();
  if (s.done || s.prompts >= MAX_PROMPTS) return false;
  if (s.last && Date.now() - s.last < SNOOZE_MS) return false;
  return true;
}

export async function markReviewPrompted(): Promise<void> {
  const s = await read();
  await AsyncStorage.setItem(KEY, JSON.stringify({ ...s, prompts: s.prompts + 1, last: Date.now() }));
}

export async function markReviewDone(): Promise<void> {
  const s = await read();
  await AsyncStorage.setItem(KEY, JSON.stringify({ ...s, done: true }));
}

/** Identifiant anonyme stable par appareil (un avis par appareil pour les visiteurs sans compte). */
export async function deviceKey(): Promise<string> {
  let k = await AsyncStorage.getItem(DEVICE_KEY);
  if (!k) {
    k = Array.from({ length: 32 }, () => Math.floor(Math.random() * 16).toString(16)).join("");
    await AsyncStorage.setItem(DEVICE_KEY, k);
  }
  return k;
}

export const reviewSource = (): "ios" | "android" | "web" => (Platform.OS === "ios" ? "ios" : Platform.OS === "android" ? "android" : "web");

export const PLAY_STORE_URL = "https://play.google.com/store/apps/details?id=achetesmamaison.app";
