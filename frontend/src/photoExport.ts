import * as Clipboard from "expo-clipboard";
import { File, Paths } from "expo-file-system";
import * as Sharing from "expo-sharing";
import { useState } from "react";
import { Linking, Platform, Share } from "react-native";

// expo-media-library has no web implementation: load it lazily on native only.
const mediaLibrary = () => require("expo-media-library") as typeof import("expo-media-library");

export type ExportStatus = { kind: "saved" | "error" | "blocked"; message: string } | null;

/** Web : vrai téléchargement de fichier (pas de galerie sur PC) via un lien `download`. */
async function webDownloadUrl(uri: string, fileName: string): Promise<void> {
  const res = await fetch(uri);
  if (!res.ok) throw new Error("Téléchargement impossible");
  webDownloadBlob(await res.blob(), fileName);
}

function webDownloadBlob(blob: Blob, fileName: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}

async function webDownloadMany(items: { uri: string; fileName: string }[]): Promise<number> {
  let n = 0;
  for (const it of items) {
    await webDownloadUrl(it.uri, it.fileName);
    n += 1;
    if (items.length > 1) await new Promise((r) => setTimeout(r, 400)); // laisse le navigateur enchaîner les téléchargements
  }
  return n;
}

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
        const n = await webDownloadMany(items);
        return { kind: "saved", message: n > 1 ? `${n} photos téléchargées (dossier Téléchargements de votre navigateur).` : "Photo téléchargée (dossier Téléchargements de votre navigateur)." };
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
      if (Platform.OS === "web") {
        await webDownloadUrl(uri, fileName);
        return { kind: "saved", message: "Photo téléchargée : partagez-la depuis votre ordinateur (e-mail, WhatsApp Web, Leboncoin…)." };
      }
      if (!(await Sharing.isAvailableAsync())) {
        Linking.openURL(uri);
        return null;
      }
      const local = await download(uri, fileName);
      await Sharing.shareAsync(local, { mimeType: "image/jpeg", UTI: "public.jpeg", dialogTitle: "Partager la photo" });
      return null;
    });

  /** One-tap listing export: text copied, retouched photos saved to the gallery, then the system share sheet with the text
   *  (and the first photo on iOS) for Leboncoin, SeLoger, WhatsApp, e-mail… Photos are attached from the gallery by the target app. */
  const shareListing = (text: string, photos: { uri: string; fileName: string }[], key: string, textFileName = "annonce") =>
    run(key, async () => {
      await Clipboard.setStringAsync(text);
      if (Platform.OS === "web") {
        webDownloadBlob(new Blob([text], { type: "text/plain;charset=utf-8" }), `${textFileName}.txt`);
        const n = photos.length ? await webDownloadMany(photos) : 0;
        return { kind: "saved", message: n
          ? `Texte de l’annonce copié et téléchargé (.txt) · ${n} photo${n > 1 ? "s" : ""} téléchargée${n > 1 ? "s" : ""} dans votre dossier Téléchargements.`
          : "Texte de l’annonce copié dans le presse-papiers et téléchargé (.txt)." };
      }
      let saved = 0;
      let firstLocal: string | null = null;
      if (photos.length && (await ensureWriteAccess()) === "granted") {
        for (const p of photos) {
          const local = await download(p.uri, p.fileName);
          firstLocal ??= local;
          await mediaLibrary().saveToLibraryAsync(local);
          saved += 1;
        }
      }
      await Share.share(
        Platform.OS === "ios" && firstLocal ? { message: text, url: firstLocal } : { message: text },
        { dialogTitle: "Partager l’annonce", subject: text.split("\n")[0] },
      );
      const photosNote = photos.length === 0 ? "" : saved
        ? ` · ${saved} photo${saved > 1 ? "s" : ""} retouchée${saved > 1 ? "s" : ""} enregistrée${saved > 1 ? "s" : ""} dans votre galerie, à sélectionner dans Leboncoin, SeLoger ou WhatsApp`
        : " · accès galerie refusé : les photos n’ont pas été enregistrées (utilisez « Partager » sur l’écran Photos)";
      return { kind: saved || !photos.length ? "saved" : "blocked", message: `Texte de l’annonce copié${photosNote}.` };
    });

  return { busyKey, status, clearStatus: () => setStatus(null), save: (uri: string, fileName: string, key: string) => saveMany([{ uri, fileName }], key), saveMany, share, shareListing };
}
