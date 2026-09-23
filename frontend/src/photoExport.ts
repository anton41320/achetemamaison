import { File, Paths } from "expo-file-system";
import * as Sharing from "expo-sharing";
import { useState } from "react";
import { Linking, Platform } from "react-native";

// expo-media-library has no web implementation: load it lazily on native only.
const mediaLibrary = () => require("expo-media-library") as typeof import("expo-media-library");

export type ExportStatus = { kind: "saved" | "error" | "blocked"; message: string } | null;

async function download(uri: string, fileName: string): Promise<string> {
  const file = await File.downloadFileAsync(uri, new File(Paths.cache, fileName), { idempotent: true });
  return file.uri;
}

async function ensureWriteAccess(): Promise<"granted" | "denied" | "blocked"> {
  const MediaLibrary = mediaLibrary();
  let perm = await MediaLibrary.getPermissionsAsync(true);
  if (perm.granted) return "granted";
  if (!perm.canAskAgain) return "blocked";
  perm = await MediaLibrary.requestPermissionsAsync(true);
  if (perm.granted) return "granted";
  return perm.canAskAgain ? "denied" : "blocked";
}

/** Save to the phone gallery / share retouched photos. Web falls back to opening the file in a new tab. */
export function usePhotoExport() {
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [status, setStatus] = useState<ExportStatus>(null);

  const run = async (key: string, fn: () => Promise<ExportStatus>) => {
    setBusyKey(key);
    setStatus(null);
    try {
      setStatus(await fn());
    } catch (e) {
      setStatus({ kind: "error", message: (e as Error).message || "Échec de l’export de la photo" });
    } finally {
      setBusyKey(null);
    }
  };

  const saveMany = (items: { uri: string; fileName: string }[], key = "all") =>
    run(key, async () => {
      if (Platform.OS === "web") {
        items.forEach((it) => Linking.openURL(it.uri));
        return { kind: "saved", message: items.length > 1 ? "Photos ouvertes dans de nouveaux onglets : enregistrez-les depuis votre navigateur." : "Photo ouverte : enregistrez-la depuis votre navigateur." };
      }
      const access = await ensureWriteAccess();
      if (access !== "granted") {
        return { kind: "blocked", message: access === "blocked"
          ? "Accès à la galerie refusé. Autorisez l’ajout de photos dans les réglages, ou utilisez « Partager » pour l’enregistrer autrement."
          : "Autorisation refusée : la photo n’a pas été enregistrée. Vous pouvez aussi utiliser « Partager »." };
      }
      for (const it of items) {
        await mediaLibrary().saveToLibraryAsync(await download(it.uri, it.fileName));
      }
      return { kind: "saved", message: items.length > 1 ? `${items.length} photos enregistrées dans votre galerie.` : "Photo enregistrée dans votre galerie." };
    });

  const share = (uri: string, fileName: string, key: string) =>
    run(key, async () => {
      if (Platform.OS === "web" || !(await Sharing.isAvailableAsync())) {
        Linking.openURL(uri);
        return null;
      }
      const local = await download(uri, fileName);
      await Sharing.shareAsync(local, { mimeType: "image/jpeg", UTI: "public.jpeg", dialogTitle: "Partager la photo" });
      return null;
    });

  return { busyKey, status, clearStatus: () => setStatus(null), save: (uri: string, fileName: string, key: string) => saveMany([{ uri, fileName }], key), saveMany, share };
}
