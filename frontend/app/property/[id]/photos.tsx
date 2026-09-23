import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Image } from "expo-image";
import * as ImagePicker from "expo-image-picker";
import { useLocalSearchParams, useRouter } from "expo-router";
import { CameraIcon, CheckCircleIcon, DownloadSimpleIcon, ImagesIcon, LockKeyIcon, ShareNetworkIcon, SparkleIcon, TrashIcon, WarningIcon } from "phosphor-react-native";
import { useState } from "react";
import { ActivityIndicator, Linking, Platform, Pressable, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Photo, api, fileUrl, uploadPhoto } from "@/src/api";
import { PremiumGate, usePackUnlocked } from "@/src/components/PremiumGate";
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
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [showAfter, setShowAfter] = useState<Record<string, boolean>>({});

  const photos = useQuery({
    queryKey: ["photos", id],
    queryFn: () => api.listPhotos(id!),
    enabled: !!id,
    refetchInterval: (q) => (q.state.data?.some((p) => p.status === "processing") ? 3000 : false),
  });

  const upload = useMutation({
    mutationFn: (asset: ImagePicker.ImagePickerAsset) =>
      uploadPhoto(id!, asset.uri, asset.fileName ?? `photo-${Date.now()}.jpg`, asset.mimeType ?? "image/jpeg"),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["photos", id] }),
    onError: (e: Error) => setUploadError(e.message),
  });

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
  const retouched = (photos.data ?? []).filter((p) => p.status === "done" && p.retouched_path);
  const exportName = (index: number, after: boolean) => `achetesmamaison-${id!.slice(-6)}-photo-${index + 1}${after ? "-retouchee" : ""}.jpg`;
  const exportOrUnlock = (fn: () => void) => (pack.unlocked ? fn() : router.push(`/property/${id}/pack`));

  const pick = async (source: Source) => {
    setUploadError(null);
    setPermissionBlocked(null);
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
    const result =
      source === "camera"
        ? await ImagePicker.launchCameraAsync({ mediaTypes: ["images"], quality: 0.85 })
        : await ImagePicker.launchImageLibraryAsync({ mediaTypes: ["images"], quality: 0.85, allowsMultipleSelection: false });
    if (result.canceled || !result.assets?.[0]) return;
    upload.mutate(result.assets[0]);
  };

  return (
    <View style={styles.screen} testID="photos-screen">
      <ScreenHeader
        title="Photos & retouche IA"
        subtitle="Gemini Nano Banana · original toujours conservé"
        onBack={() => router.back()}
      />
      <ScrollView contentContainerStyle={[styles.content, { paddingBottom: insets.bottom + spacing.xl }]}>
        <View style={styles.pickRow}>
          <Pressable testID="photos-pick-library" accessibilityRole="button" onPress={() => pick("library")} style={styles.pickBtn} disabled={upload.isPending}>
            <ImagesIcon size={22} color={colors.onBrandTertiary} weight="duotone" />
            <Text style={styles.pickLabel}>Galerie</Text>
          </Pressable>
          {Platform.OS !== "web" ? (
            <Pressable testID="photos-pick-camera" accessibilityRole="button" onPress={() => pick("camera")} style={styles.pickBtn} disabled={upload.isPending}>
              <CameraIcon size={22} color={colors.onBrandTertiary} weight="duotone" />
              <Text style={styles.pickLabel}>Appareil photo</Text>
            </Pressable>
          ) : null}
        </View>
        <Text style={styles.hint}>
          La retouche améliore lumière, contraste et perspective, et efface uniquement de petits objets. Aucun élément n’est
          ajouté : le visuel retouché reste une représentation fidèle du bien.
        </Text>
        {!pack.loading && !pack.unlocked ? <PremiumGate propertyId={id!} feature="la retouche photo par l’IA" testID="photos-premium-gate" /> : null}

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
        {upload.isPending ? (
          <View style={styles.loadingRow} testID="photos-uploading">
            <ActivityIndicator color={colors.brandPrimary} />
            <Text style={styles.hint}>Envoi de la photo…</Text>
          </View>
        ) : null}
        {uploadError ? (
          <View style={styles.warn} testID="photos-upload-error">
            <WarningIcon size={18} color={colors.error} weight="fill" />
            <Text style={[styles.warnText, { color: colors.error }]}>{uploadError}</Text>
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
                  {p.status === "processing" ? (
                    <View style={styles.overlay} testID={`photo-processing-${i}`}>
                      <ActivityIndicator color={colors.onHero} />
                      <Text style={styles.overlayText}>Retouche en cours…</Text>
                    </View>
                  ) : null}
                </View>
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
  pickRow: { flexDirection: "row", gap: spacing.md },
  pickBtn: { flex: 1, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: spacing.sm, minHeight: 56, borderRadius: radius.md, backgroundColor: colors.brandTertiary },
  pickLabel: { fontFamily: fonts.semibold, fontSize: 15, color: colors.onBrandTertiary },
  hint: { fontFamily: fonts.regular, fontSize: 13, lineHeight: 19, color: colors.muted },
  warn: { flexDirection: "row", gap: spacing.md, alignItems: "flex-start", backgroundColor: colors.warningSoft, borderRadius: radius.md, padding: spacing.lg },
  warnText: { flex: 1, fontFamily: fonts.medium, fontSize: 13, lineHeight: 19, color: colors.warning },
  loadingRow: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  skeleton: { height: 260, borderRadius: radius.lg, backgroundColor: colors.skeleton },
  empty: { alignItems: "center", gap: spacing.sm, paddingVertical: spacing.xxl },
  emptyTitle: { fontFamily: fonts.semibold, fontSize: 17, color: colors.onSurface },
  card: { backgroundColor: colors.surfaceSecondary, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, overflow: "hidden" },
  imageWrap: { height: 240, backgroundColor: colors.skeleton },
  image: { width: "100%", height: "100%" },
  badge: { position: "absolute", left: spacing.md, bottom: spacing.md, backgroundColor: colors.scrimBottom, paddingHorizontal: spacing.md, height: 26, borderRadius: radius.pill, justifyContent: "center" },
  badgeText: { fontFamily: fonts.semibold, fontSize: 11, color: colors.onHero },
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
