import { Platform } from "react-native";

import { Estimation, PropertyIn, api } from "@/src/api";

const KEY = "amm_free_estimate_draft";

export interface FreeDraft {
  body: PropertyIn;
  estimation: Estimation;
  saved_at: string;
}

const storage = () => (Platform.OS === "web" && typeof localStorage !== "undefined" ? localStorage : null);

/** Estimation gratuite réalisée sans compte sur le site : conservée dans le navigateur jusqu'à la création du compte. */
export function saveFreeDraft(body: PropertyIn, estimation: Estimation) {
  storage()?.setItem(KEY, JSON.stringify({ body, estimation, saved_at: new Date().toISOString() } satisfies FreeDraft));
}

export function loadFreeDraft(): FreeDraft | null {
  try {
    const raw = storage()?.getItem(KEY);
    return raw ? (JSON.parse(raw) as FreeDraft) : null;
  } catch {
    return null;
  }
}

export function clearFreeDraft() {
  storage()?.removeItem(KEY);
}

/** Après connexion ou inscription : enregistre le brouillon comme bien du compte et renvoie la route à ouvrir (ou null). */
export async function consumeFreeDraft(): Promise<string | null> {
  const draft = loadFreeDraft();
  if (!draft) return null;
  try {
    const prop = await api.createProperty(draft.body);
    clearFreeDraft();
    return `/property/${prop.id}`;
  } catch {
    return null; // le brouillon reste disponible pour une prochaine tentative
  }
}
