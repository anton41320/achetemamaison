import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Image } from "expo-image";
import * as DocumentPicker from "expo-document-picker";
import * as ImagePicker from "expo-image-picker";
import { useLocalSearchParams, useRouter } from "expo-router";
import { ArrowDownIcon, ArrowUpIcon, CameraIcon, CheckCircleIcon, DownloadSimpleIcon, FolderOpenIcon, ImagesIcon, LockKeyIcon, ShareNetworkIcon, SparkleIcon, StarIcon, TrashIcon, WarningIcon } from "phosphor-react-native";
import { useState } from "react";
import { ActivityIndicator, Linking, Platform, Pressable, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Photo, api, fileUrl, uploadPhoto } from "@/src/api";
import { PremiumGate, usePackUnlocked } from "@/src/components/PremiumGate";
import { PhotoTutorialCard } from "@/src/components/PhotoTutorialCard";
import { usePhotoExport } from "@/src/photoExport";
import { PrimaryButton } from "@/src/components/PrimaryButton";
import { ScreenHeader } from "@/src/components/ScreenHeader";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

type Source = "library" | "camera";

export default function PhotosScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const queryClient = useQueryClient();

  const [permissionBlocked, setPermissionBlocked] = useState<Source | null>(null);
  const [pickError, setPickError] = useState<string | null>(null);
  const [showAfter, setShowAfter] = useState<Record<string, boolean>>({});

  const photos = useQuery({
    queryKey: ["photos", id],
    queryFn: () => api.listPhotos(id!),
    enabled: !!id,
    refetchInterval: (q) => (q.state.data?.some((p) => p.status === "processing") ? 3000 : false),
  });

  type QueueItem = { key: string; name: string; pct: number; status: "waiting" | "uploading" | "done" | "error"; error?: string };
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const uploading = queue.some((q) => q.status === "waiting" || q.status === "uploading");
  const patchQueue = (key: string, patch: Partial<QueueItem>) => setQueue((q) => q.map((it) => (it.key === key ? { ...it, ...patch } : it)));

  /** Sequential uploads (one connection at a time on mobile networks), each with its own progress bar. */
  const uploadAll = async (assets: ImagePicker.ImagePickerAsset[]) => {
    const items = assets.map((a, i) => ({ asset: a, key: `${Date.now()}-${i}`, name: a.fileName ?? `photo-${i + 1}.jpg` }));
    setQueue(items.map(({ key, name }) => ({ key, name, pct: 0, status: "waiting" as const })));
    for (const it of items) {
      patchQueue(it.key, { status: "uploading" });
      try {
        await uploadPhoto(id!, it.asset.uri, it.name, it.asset.mimeType ?? "image/jpeg", (pct) => patchQueue(it.key, { pct }));
        patchQueue(it.key, { status: "done", pct: 100 });
        queryClient.invalidateQueries({ queryKey: ["photos", id] });
      } catch (e) {
        patchQueue(it.key, { status: "error", error: (e as Error).message });
      }
    }
    setTimeout(() => setQueue((q) => (q.some((x) => x.status === "error") ? q : [])), 1500);
  };

  const retouch = useMutation({
    mutationFn: (photoId: string) => api.retouchPhoto(photoId),
    onMutate: (photoId) => {
      queryClient.setQueryData<Photo[]>(["photos", id], (old) =>
        old?.map((p) => (p.id === photoId ? { ...p, status: "processing" } : p)),
      );
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["photos", id] }),
    onSuccess: (p) => setShowAfter((s) => ({ ...s, [p.id]: true })),
    onError: (e: Error) => setPaywall(e.message.includes("Pack annonce") ? e.message : null),
  });
  const [paywall, setPaywall] = useState<string | null>(null);
  const pack = usePackUnlocked(id);

  const remove = useMutation({
    mutationFn: (photoId: string) => api.deletePhoto(photoId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["photos", id] }),
  });

  const exporter = usePhotoExport();

  const reorder = useMutation({
    mutationFn: (ids: string[]) => api.reorderPhotos(id!, ids),
    onMutate: (ids) => {
      const byId = new Map((photos.data ?? []).map((p) => [p.id, p]));
      queryClient.setQueryData<Photo[]>(["photos", id], ids.map((x) => byId.get(x)!).filter(Boolean));
    },
    onSuccess: (data) => queryClient.setQueryData(["photos", id], data),
    onError: () => queryClient.invalidateQueries({ queryKey: ["photos", id] }),
  });
  const move = (index: number, delta: -1 | 1) => {
    const ids = (photos.data ?? []).map((p) => p.id);
    const [moved] = ids.splice(index, 1);
    ids.splice(index + delta, 0, moved);
    reorder.mutate(ids);
  };
  const setCover = (photoId: string) => reorder.mutate([photoId, ...(photos.data ?? []).map((p) => p.id).filter((x) => x !== photoId)]);
  const retouched = (photos.data ?? []).filter((p) => p.status === "done" && p.retouched_path);
  const exportName = (index: number, after: boolean) => `achetesmamaison-${id!.slice(-6)}-photo-${index + 1}${after ? "-retouchee" : ""}.jpg`;
  const exportOrUnlock = (fn: () => void) => (pack.unlocked ? fn() : router.push(`/property/${id}/pack`));

  // Sélecteur de fichiers système (Storage Access Framework) : fonctionne sur tout Android, sans autorisation.
  const pickFiles = async () => {
    setPickError(null);
    try {
      const res = await DocumentPicker.getDocumentAsync({ type: "image/*", multiple: true, copyToCacheDirectory: true });
      if (res.canceled || !res.assets?.length) return;
      uploadAll(res.assets.map((a) => ({ uri: a.uri, fileName: a.name, mimeType: a.mimeType ?? "image/jpeg", width: 0, height: 0 })));
    } catch (e) {
      setPickError((e as Error).message);
    }
  };

  const pick = async (source: Source) => {
    setPermissionBlocked(null);
    setPickError(null);
    const get = source === "camera" ? ImagePicker.getCameraPermissionsAsync : ImagePicker.getMediaLibraryPermissionsAsync;
    const ask = source === "camera" ? ImagePicker.requestCameraPermissionsAsync : ImagePicker.requestMediaLibraryPermissionsAsync;
    // Android : le sélecteur de photos système (Photo Picker) ne requiert aucune autorisation ; seul l'appareil photo en a besoin.
    const needsPermission = source === "camera" || Platform.OS !== "android";
    let perm = needsPermission ? await get() : { granted: true, canAskAgain: true };
    if (!perm.granted) {
      if (!perm.canAskAgain && Platform.OS !== "web") {
        setPermissionBlocked(source);
        return;
      }
      perm = await ask();
      if (!perm.granted) {
        if (!perm.canAskAgain) setPermissionBlocked(source);
        return;
      }
    }
    try {
      const result =
        source === "camera"
          ? await ImagePicker.launchCameraAsync({ mediaTypes: ["images"], quality: 0.85 })
          : await ImagePicker.launchImageLibraryAsync({ mediaTypes: ["images"], quality: 0.85, allowsMultipleSelection: true, selectionLimit: 20, orderedSelection: true });
      if (result.canceled || !result.assets?.length) return;
      uploadAll(result.assets);
    } catch (e) {
      if (source === "camera") {
        setPickError((e as Error).message);
        return;
      }
      // Android sans « Photo Picker » (ancienne version / sans services Google) : bascule sur le sélecteur de fichiers.
      await pickFiles();
    }
  };

  return (
    <View style={styles.screen} testID="photos-screen">
      <ScreenHeader
        title="Photos & retouche IA"
        subtitle="Gemini Nano Banana · original toujours conservé"
        onBack={() => router.back()}
      />
      <ScrollView contentContainerStyle={[styles.content, { paddingBottom: insets.bottom + spacing.xl }]}>
        <PhotoTutorialCard />
        <View style={styles.pickRow}>
          <Pressable testID="photos-pick-library" accessibilityRole="button" onPress={() => pick("library")} style={styles.pickBtn} disabled={uploading}>
            <ImagesIcon size={22} color={colors.onBrandTertiary} weight="duotone" />
            <Text style={styles.pickLabel}>Galerie</Text>
          </Pressable>
          {Platform.OS !== "web" ? (
            <Pressable testID="photos-pick-camera" accessibilityRole="button" onPress={() => pick("camera")} style={styles.pickBtn} disabled={uploading}>
              <CameraIcon size={22} color={colors.onBrandTertiary} weight="duotone" />
              <Text style={styles.pickLabel}>Appareil photo</Text>
            </Pressable>
          ) : null}
          {Platform.OS === "android" ? (
            <Pressable testID="photos-pick-files" accessibilityRole="button" onPress={pickFiles} style={styles.pickBtn} disabled={uploading}>
              <FolderOpenIcon size={22} color={colors.onBrandTertiary} weight="duotone" />
              <Text style={styles.pickLabel}>Fichiers</Text>
            </Pressable>
          ) : null}
        </View>
        <Text style={styles.hint}>
          La retouche améliore lumière, contraste et perspective, et efface uniquement de petits objets. Aucun élément n’est
          ajouté : le visuel retouché reste une représentation fidèle du bien. La première photo sert de couverture dans
          l’annonce et les PDF : utilisez les flèches ou « Couverture » pour ordonner vos photos.
        </Text>
        {!pack.loading && !pack.unlocked ? <PremiumGate propertyId={id!} feature="la retouche photo par l’IA" testID="photos-premium-gate" /> : null}
        {pickError ? (
          <View style={styles.warn} testID="photos-pick-error">
            <WarningIcon size={18} color={colors.error} weight="fill" />
            <Text style={[styles.warnText, { color: colors.error }]}>Impossible d’ouvrir la galerie : {pickError}</Text>
          </View>
        ) : null}

        {retouched.length >= 2 ? (
          <Pressable
            testID="photos-save-all"
            accessibilityRole="button"
            disabled={exporter.busyKey !== null}
            onPress={() => exportOrUnlock(() => exporter.saveMany(
              retouched.map((p) => ({ uri: api.photoExportUrl(p.id), fileName: exportName(photos.data!.indexOf(p), true) })),
            ))}
            style={({ pressed }) => [styles.saveAll, pressed && { opacity: 0.85 }]}
          >
            {exporter.busyKey === "all" ? <ActivityIndicator color={colors.onBrandTertiary} /> : pack.unlocked ? <DownloadSimpleIcon size={20} color={colors.onBrandTertiary} weight="bold" /> : <LockKeyIcon size={20} color={colors.onBrandTertiary} weight="fill" />}
            <Text style={styles.saveAllLabel}>
              {pack.unlocked ? `Enregistrer les ${retouched.length} photos retouchées dans la galerie` : "Télécharger les photos retouchées · Pack premium"}
            </Text>
          </Pressable>
        ) : null}
        {exporter.status ? (
          <View style={[styles.warn, exporter.status.kind === "saved" && styles.ok]} testID="photos-export-status">
            {exporter.status.kind === "saved" ? <CheckCircleIcon size={18} color={colors.success} weight="fill" /> : <WarningIcon size={18} color={exporter.status.kind === "error" ? colors.error : colors.warning} weight="fill" />}
            <View style={{ flex: 1, gap: spacing.sm }}>
              <Text style={[styles.warnText, exporter.status.kind === "saved" && { color: colors.success }, exporter.status.kind === "error" && { color: colors.error }]}>
                {exporter.status.message}
              </Text>
              {exporter.status.kind === "blocked" && Platform.OS !== "web" ? (
                <PrimaryButton title="Ouvrir les réglages" variant="secondary" onPress={() => Linking.openSettings()} testID="photos-export-open-settings" />
              ) : null}
            </View>
          </View>
        ) : null}

        {permissionBlocked ? (
          <View style={styles.warn} testID="photos-permission-blocked">
            <WarningIcon size={18} color={colors.warning} weight="fill" />
            <View style={{ flex: 1, gap: spacing.sm }}>
              <Text style={styles.warnText}>
                Accès {permissionBlocked === "camera" ? "à l’appareil photo" : "à la galerie"} refusé. Autorisez-le dans les réglages pour
                ajouter des photos de votre bien.
              </Text>
              <PrimaryButton title="Ouvrir les réglages" variant="secondary" onPress={() => Linking.openSettings()} testID="photos-open-settings" />
            </View>
          </View>
        ) : null}
        {queue.length ? (
          <View style={styles.queue} testID="photos-upload-queue">
            <Text style={styles.queueTitle}>
              {uploading ? `Envoi ${queue.filter((q) => q.status === "done").length + 1}/${queue.length}…` : `${queue.filter((q) => q.status === "done").length}/${queue.length} photo(s) envoyée(s)`}
            </Text>
            {queue.map((q, i) => (
              <View key={q.key} style={styles.queueRow} testID={`photos-upload-item-${i}`}>
                <View style={styles.queueHead}>
                  <Text style={styles.queueName} numberOfLines={1}>{q.name}</Text>
                  {q.status === "done" ? <CheckCircleIcon size={16} color={colors.success} weight="fill" />
                    : q.status === "error" ? <WarningIcon size={16} color={colors.error} weight="fill" />
                    : <Text style={styles.queuePct}>{q.status === "waiting" ? "En attente" : `${q.pct} %`}</Text>}
                </View>
                <View style={styles.track}>
                  <View style={[styles.fill, { width: `${q.status === "done" ? 100 : q.pct}%`, backgroundColor: q.status === "error" ? colors.error : colors.brandPrimary }]} />
                </View>
                {q.error ? <Text style={styles.queueError}>{q.error}</Text> : null}
              </View>
            ))}
            {!uploading && queue.some((q) => q.status === "error") ? (
              <PrimaryButton title="Masquer" variant="ghost" onPress={() => setQueue([])} testID="photos-upload-dismiss" />
            ) : null}
          </View>
        ) : null}
        {paywall ? (
          <View style={styles.warn} testID="photos-paywall">
            <SparkleIcon size={18} color={colors.warning} weight="fill" />
            <View style={{ flex: 1, gap: spacing.sm }}>
              <Text style={styles.warnText}>{paywall}</Text>
              <PrimaryButton title="Débloquer le Pack premium · 49 €" onPress={() => router.push(`/property/${id}/pack`)} testID="photos-paywall-button" />
            </View>
          </View>
        ) : null}

        {photos.isLoading ? (
          <View style={styles.skeleton} />
        ) : !photos.data || photos.data.length === 0 ? (
          <View style={styles.empty} testID="photos-empty">
            <ImagesIcon size={40} color={colors.muted} weight="thin" />
            <Text style={styles.emptyTitle}>Aucune photo</Text>
            <Text style={styles.hint}>Ajoutez une photo de votre bien pour la retoucher avec l’IA.</Text>
          </View>
        ) : (
          photos.data.map((p, i) => {
            const after = (showAfter[p.id] ?? true) && p.status === "done" && !!p.retouched_path;
            const uri = fileUrl(after ? p.retouched_path! : p.original_path);
            return (
              <View key={p.id} style={styles.card} testID={`photo-card-${i}`}>
                <View style={styles.imageWrap}>
                  <Image source={{ uri }} style={styles.image} contentFit="cover" transition={250} cachePolicy="memory-disk" />
                  {after ? (
                    <View style={styles.badge} testID={`photo-badge-${i}`}>
                      <Text style={styles.badgeText}>Visuel retouché par IA · non contractuel</Text>
                    </View>
                  ) : null}
                  {i === 0 ? (
                    <View style={styles.coverBadge} testID="photo-cover-badge">
                      <StarIcon size={12} color={colors.onBrandPrimary} weight="fill" />
                      <Text style={styles.coverText}>Photo de couverture</Text>
                    </View>
                  ) : null}
                  {p.status === "processing" ? (
                    <View style={styles.overlay} testID={`photo-processing-${i}`}>
                      <ActivityIndicator color={colors.onHero} />
                      <Text style={styles.overlayText}>Retouche en cours…</Text>
                    </View>
                  ) : null}
                </View>
                {photos.data!.length > 1 ? (
                  <View style={styles.orderRow}>
                    <Text style={styles.orderPos}>Photo {i + 1}/{photos.data!.length}</Text>
                    <View style={styles.orderBtns}>
                      {i > 0 ? (
                        <Pressable testID={`photo-cover-${i}`} accessibilityRole="button" accessibilityLabel="Mettre en couverture" disabled={reorder.isPending} onPress={() => setCover(p.id)} style={styles.orderBtn}>
                          <StarIcon size={16} color={colors.onBrandTertiary} />
                          <Text style={styles.orderLabel}>Couverture</Text>
                        </Pressable>
                      ) : null}
                      <Pressable testID={`photo-up-${i}`} accessibilityRole="button" accessibilityLabel="Monter la photo" disabled={i === 0 || reorder.isPending} onPress={() => move(i, -1)} style={[styles.orderIcon, i === 0 && styles.orderDisabled]}>
                        <ArrowUpIcon size={18} color={colors.onBrandTertiary} weight="bold" />
                      </Pressable>
                      <Pressable testID={`photo-down-${i}`} accessibilityRole="button" accessibilityLabel="Descendre la photo" disabled={i === photos.data!.length - 1 || reorder.isPending} onPress={() => move(i, 1)} style={[styles.orderIcon, i === photos.data!.length - 1 && styles.orderDisabled]}>
                        <ArrowDownIcon size={18} color={colors.onBrandTertiary} weight="bold" />
                      </Pressable>
                    </View>
                  </View>
                ) : null}
                {p.status === "done" && p.retouched_path ? (
                  <View style={styles.toggle}>
                    {(["Original", "Retouchée"] as const).map((label, j) => {
                      const active = (j === 1) === !!after;
                      return (
                        <Pressable
                          key={label}
                          testID={`photo-toggle-${i}-${j === 0 ? "before" : "after"}`}
                          accessibilityRole="button"
                          onPress={() => setShowAfter((s) => ({ ...s, [p.id]: j === 1 }))}
                          style={[styles.toggleBtn, active && styles.toggleBtnActive]}
                        >
                          <Text style={[styles.toggleLabel, active && styles.toggleLabelActive]}>{label}</Text>
                        </Pressable>
                      );
                    })}
                  </View>
                ) : null}
                {p.status === "done" && p.retouched_path ? (
                  <View style={styles.exportRow}>
                    <Pressable
                      testID={`photo-save-${i}`}
                      accessibilityRole="button"
                      disabled={exporter.busyKey !== null}
                      onPress={() => exportOrUnlock(() => exporter.save(api.photoExportUrl(p.id, after ? "retouched" : "original"), exportName(i, !!after), `save-${p.id}`))}
                      style={({ pressed }) => [styles.exportBtn, pressed && { opacity: 0.85 }]}
                    >
                      {exporter.busyKey === `save-${p.id}` ? <ActivityIndicator color={colors.onBrandTertiary} /> : pack.unlocked ? <DownloadSimpleIcon size={16} color={colors.onBrandTertiary} weight="bold" /> : <LockKeyIcon size={16} color={colors.onBrandTertiary} weight="fill" />}
                      <Text style={styles.exportLabel}>{Platform.OS === "web" ? "Télécharger" : "Enregistrer dans la galerie"}</Text>
                    </Pressable>
                    <Pressable
                      testID={`photo-share-${i}`}
                      accessibilityRole="button"
                      disabled={exporter.busyKey !== null}
                      onPress={() => exportOrUnlock(() => exporter.share(api.photoExportUrl(p.id, after ? "retouched" : "original"), exportName(i, !!after), `share-${p.id}`))}
                      style={({ pressed }) => [styles.exportBtn, pressed && { opacity: 0.85 }]}
                    >
                      {exporter.busyKey === `share-${p.id}` ? <ActivityIndicator color={colors.onBrandTertiary} /> : pack.unlocked ? <ShareNetworkIcon size={16} color={colors.onBrandTertiary} weight="bold" /> : <LockKeyIcon size={16} color={colors.onBrandTertiary} weight="fill" />}
                      <Text style={styles.exportLabel}>Partager</Text>
                    </Pressable>
                  </View>
                ) : null}
                {p.status === "error" ? (
                  <Text style={styles.errorText} testID={`photo-error-${i}`}>Échec de la retouche : {p.error}</Text>
                ) : null}
                <View style={styles.actions}>
                  {p.status !== "processing" ? (
                    <Pressable testID={`photo-retouch-${i}`} accessibilityRole="button" onPress={() => (pack.unlocked ? retouch.mutate(p.id) : router.push(`/property/${id}/pack`))}
                      style={[styles.actionPrimary, !pack.unlocked && styles.actionLocked]}>
                      {pack.unlocked ? <SparkleIcon size={16} color={colors.onBrandPrimary} weight="fill" /> : <LockKeyIcon size={16} color={colors.onBrandTertiary} weight="fill" />}
                      <Text style={[styles.actionPrimaryLabel, !pack.unlocked && styles.actionLockedLabel]}>
                        {!pack.unlocked ? "Retouche IA · Pack premium" : p.status === "done" ? "Retoucher à nouveau" : "Retoucher avec l’IA"}
                      </Text>
                    </Pressable>
                  ) : null}
                  <Pressable testID={`photo-delete-${i}`} accessibilityRole="button" onPress={() => remove.mutate(p.id)} style={styles.actionBtn}>
                    <TrashIcon size={16} color={colors.error} />
                  </Pressable>
                </View>
              </View>
            );
          })
        )}
      </ScrollView>
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  screen: { flex: 1, backgroundColor: colors.surface },
  content: { padding: spacing.lg, gap: spacing.lg },
  pickRow: { flexDirection: "row", flexWrap: "wrap", gap: spacing.md },
  pickBtn: { flexGrow: 1, flexBasis: 100, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: spacing.sm, minHeight: 56, paddingHorizontal: spacing.sm, borderRadius: radius.md, backgroundColor: colors.brandTertiary },
  pickLabel: { fontFamily: fonts.semibold, fontSize: 15, color: colors.onBrandTertiary },
  hint: { fontFamily: fonts.regular, fontSize: 13, lineHeight: 19, color: colors.muted },
  warn: { flexDirection: "row", gap: spacing.md, alignItems: "flex-start", backgroundColor: colors.warningSoft, borderRadius: radius.md, padding: spacing.lg },
  warnText: { flex: 1, fontFamily: fonts.medium, fontSize: 13, lineHeight: 19, color: colors.warning },
  queue: { gap: spacing.sm, backgroundColor: colors.surface, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, padding: spacing.lg },
  queueTitle: { fontFamily: fonts.semibold, fontSize: 14, color: colors.onSurface },
  queueRow: { gap: 4 },
  queueHead: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: spacing.sm },
  queueName: { flex: 1, fontFamily: fonts.regular, fontSize: 12, color: colors.onSurfaceSecondary },
  queuePct: { fontFamily: fonts.semibold, fontSize: 12, color: colors.brandPrimary },
  queueError: { fontFamily: fonts.regular, fontSize: 11, color: colors.error },
  track: { height: 6, borderRadius: radius.pill, backgroundColor: colors.surfaceTertiary, overflow: "hidden" },
  fill: { height: 6, borderRadius: radius.pill },
  skeleton: { height: 260, borderRadius: radius.lg, backgroundColor: colors.skeleton },
  empty: { alignItems: "center", gap: spacing.sm, paddingVertical: spacing.xxl },
  emptyTitle: { fontFamily: fonts.semibold, fontSize: 17, color: colors.onSurface },
  card: { backgroundColor: colors.surfaceSecondary, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, overflow: "hidden" },
  imageWrap: { height: 240, backgroundColor: colors.skeleton },
  image: { width: "100%", height: "100%" },
  badge: { position: "absolute", left: spacing.md, bottom: spacing.md, backgroundColor: colors.scrimBottom, paddingHorizontal: spacing.md, height: 26, borderRadius: radius.pill, justifyContent: "center" },
  badgeText: { fontFamily: fonts.semibold, fontSize: 11, color: colors.onHero },
  coverBadge: { position: "absolute", left: spacing.md, top: spacing.md, flexDirection: "row", alignItems: "center", gap: 4, backgroundColor: colors.brandPrimary, paddingHorizontal: spacing.md, height: 26, borderRadius: radius.pill },
  coverText: { fontFamily: fonts.semibold, fontSize: 11, color: colors.onBrandPrimary },
  orderRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: spacing.lg, paddingTop: spacing.md, gap: spacing.sm },
  orderPos: { fontFamily: fonts.medium, fontSize: 13, color: colors.muted },
  orderBtns: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  orderBtn: { flexDirection: "row", alignItems: "center", gap: 6, minHeight: 44, paddingHorizontal: spacing.md, borderRadius: radius.md, backgroundColor: colors.brandTertiary },
  orderLabel: { fontFamily: fonts.semibold, fontSize: 13, color: colors.onBrandTertiary },
  orderIcon: { width: 44, height: 44, borderRadius: radius.md, backgroundColor: colors.brandTertiary, alignItems: "center", justifyContent: "center" },
  orderDisabled: { opacity: 0.35 },
  overlay: { position: "absolute", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: colors.scrimBottom, alignItems: "center", justifyContent: "center", gap: spacing.sm },
  overlayText: { fontFamily: fonts.medium, fontSize: 14, color: colors.onHero },
  toggle: { flexDirection: "row", margin: spacing.lg, marginBottom: 0, backgroundColor: colors.surfaceTertiary, borderRadius: radius.md, padding: 3 },
  toggleBtn: { flex: 1, height: 36, alignItems: "center", justifyContent: "center", borderRadius: radius.sm },
  toggleBtnActive: { backgroundColor: colors.surfaceSecondary },
  toggleLabel: { fontFamily: fonts.medium, fontSize: 13, color: colors.muted },
  toggleLabelActive: { color: colors.onSurfaceSecondary, fontFamily: fonts.semibold },
  errorText: { fontFamily: fonts.medium, fontSize: 12, color: colors.error, paddingHorizontal: spacing.lg, paddingTop: spacing.md },
  actions: { flexDirection: "row", gap: spacing.md, padding: spacing.lg },
  actionPrimary: { flex: 1, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: spacing.sm, minHeight: 48, borderRadius: radius.md, backgroundColor: colors.brandPrimary },
  actionPrimaryLabel: { fontFamily: fonts.semibold, fontSize: 14, color: colors.onBrandPrimary },
  actionLocked: { backgroundColor: colors.brandTertiary, borderWidth: 1, borderColor: colors.brandSecondary },
  actionLockedLabel: { color: colors.onBrandTertiary },
  actionBtn: { width: 48, height: 48, borderRadius: radius.md, backgroundColor: colors.errorSoft, alignItems: "center", justifyContent: "center" },
  exportRow: { flexDirection: "row", gap: spacing.md, paddingHorizontal: spacing.lg, paddingTop: spacing.md },
  exportBtn: { flex: 1, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: spacing.sm, minHeight: 44, borderRadius: radius.md, backgroundColor: colors.brandTertiary, paddingHorizontal: spacing.sm },
  exportLabel: { fontFamily: fonts.semibold, fontSize: 13, color: colors.onBrandTertiary, textAlign: "center" },
  saveAll: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: spacing.sm, minHeight: 52, borderRadius: radius.md, backgroundColor: colors.brandTertiary, borderWidth: 1, borderColor: colors.brandSecondary, paddingHorizontal: spacing.lg },
  saveAllLabel: { fontFamily: fonts.semibold, fontSize: 14, color: colors.onBrandTertiary, textAlign: "center" },
  ok: { backgroundColor: colors.successSoft },
}));
