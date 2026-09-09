import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as DocumentPicker from "expo-document-picker";
import * as ImagePicker from "expo-image-picker";
import { useLocalSearchParams, useRouter } from "expo-router";
import {
  CameraIcon, CaretDownIcon, CaretRightIcon, CaretUpIcon, CheckCircleIcon, ClockIcon, FilePlusIcon, FileTextIcon,
  ImagesIcon, ProhibitIcon, WarningIcon, XCircleIcon,
} from "phosphor-react-native";
import { useState } from "react";
import { ActivityIndicator, Linking, Platform, Pressable, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { ChecklistItem, ItemStatus, SaleDocument, api, formatMonth, uploadDocument } from "@/src/api";
import { PrimaryButton } from "@/src/components/PrimaryButton";
import { ScreenHeader } from "@/src/components/ScreenHeader";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

const CATEGORY_LABELS = {
  obligatoire: "Obligatoire",
  copropriete: "Copropriété",
  conditionnel: "Selon votre situation",
  recommande: "Recommandé",
};
const CATEGORY_ORDER = ["obligatoire", "copropriete", "conditionnel", "recommande"] as const;

export default function DossierScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const queryClient = useQueryClient();

  const [open, setOpen] = useState<Record<string, boolean>>({});
  const [uploadingKey, setUploadingKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [blocked, setBlocked] = useState(false);

  const dossier = useQuery({ queryKey: ["dossier", id], queryFn: () => api.dossier(id!), enabled: !!id });

  const upload = useMutation({
    mutationFn: (p: { key: string; uri: string; name: string; type: string }) => uploadDocument(id!, p.key, p.uri, p.name, p.type),
    onMutate: (p) => {
      setError(null);
      setUploadingKey(p.key);
    },
    onSettled: () => setUploadingKey(null),
    onSuccess: (doc) => {
      queryClient.invalidateQueries({ queryKey: ["dossier", id] });
      router.push(`/property/${id}/document/${doc.id}`);
    },
    onError: (e: Error) => setError(e.message),
  });

  const override = useMutation({
    mutationFn: (p: { key: string; na: boolean }) => api.overrideItem(id!, p.key, { status_override: p.na ? "non_applicable" : null }),
    onSuccess: (d) => queryClient.setQueryData(["dossier", id], d),
  });

  const pickImage = async (key: string, source: "camera" | "library") => {
    setBlocked(false);
    const get = source === "camera" ? ImagePicker.getCameraPermissionsAsync : ImagePicker.getMediaLibraryPermissionsAsync;
    const ask = source === "camera" ? ImagePicker.requestCameraPermissionsAsync : ImagePicker.requestMediaLibraryPermissionsAsync;
    let perm = await get();
    if (!perm.granted) {
      if (!perm.canAskAgain && Platform.OS !== "web") {
        setBlocked(true);
        return;
      }
      perm = await ask();
      if (!perm.granted) {
        if (!perm.canAskAgain) setBlocked(true);
        return;
      }
    }
    const result = source === "camera"
      ? await ImagePicker.launchCameraAsync({ mediaTypes: ["images"], quality: 0.9 })
      : await ImagePicker.launchImageLibraryAsync({ mediaTypes: ["images"], quality: 0.9 });
    if (result.canceled || !result.assets?.[0]) return;
    const a = result.assets[0];
    upload.mutate({ key, uri: a.uri, name: a.fileName ?? `document-${Date.now()}.jpg`, type: a.mimeType ?? "image/jpeg" });
  };

  const pickFile = async (key: string) => {
    const result = await DocumentPicker.getDocumentAsync({ type: ["application/pdf", "image/*"], copyToCacheDirectory: true, multiple: false });
    if (result.canceled || !result.assets?.[0]) return;
    const a = result.assets[0];
    upload.mutate({ key, uri: a.uri, name: a.name, type: a.mimeType ?? "application/pdf" });
  };

  const d = dossier.data;

  return (
    <View style={styles.screen} testID="dossier-screen">
      <ScreenHeader title="Dossier de vente" subtitle="Checklist adaptée à votre bien · lecture IA validée par vous" onBack={() => router.back()} />
      <ScrollView contentContainerStyle={[styles.content, { paddingBottom: insets.bottom + spacing.xl }]}>
        {dossier.isLoading ? (
          <ActivityIndicator color={colors.brandPrimary} />
        ) : dossier.isError || !d ? (
          <PrimaryButton title="Réessayer" variant="secondary" onPress={() => dossier.refetch()} testID="dossier-retry-button" />
        ) : (
          <>
            <View style={styles.progressCard} testID="dossier-progress">
              <View style={styles.progressHead}>
                <Text style={styles.progressTitle}>Documents obligatoires validés</Text>
                <Text style={styles.progressValue} testID="dossier-progress-value">{d.progress.done}/{d.progress.total_required}</Text>
              </View>
              <View style={styles.bar}>
                <View style={[styles.barFill, { width: `${d.progress.pct}%` as `${number}%` }]} />
              </View>
              <Text style={styles.hint}>
                Chaque document importé est lu par l’IA (Gemini 3 Flash) puis doit être vérifié et validé par vous avant de
                compter dans le dossier.
              </Text>
            </View>

            {blocked ? (
              <View style={styles.warn} testID="dossier-permission-blocked">
                <WarningIcon size={18} color={colors.warning} weight="fill" />
                <View style={{ flex: 1, gap: spacing.sm }}>
                  <Text style={styles.warnText}>Accès refusé. Autorisez l’appareil photo ou la galerie dans les réglages.</Text>
                  <PrimaryButton title="Ouvrir les réglages" variant="secondary" onPress={() => Linking.openSettings()} testID="dossier-open-settings" />
                </View>
              </View>
            ) : null}
            {error ? (
              <View style={styles.warn} testID="dossier-upload-error">
                <WarningIcon size={18} color={colors.error} weight="fill" />
                <Text style={[styles.warnText, { color: colors.error }]}>{error}</Text>
              </View>
            ) : null}

            {CATEGORY_ORDER.map((cat) => {
              const items = d.items.filter((i) => i.category === cat);
              if (items.length === 0) return null;
              return (
                <View key={cat} style={{ gap: spacing.sm }}>
                  <Text style={styles.sectionTitle}>{CATEGORY_LABELS[cat]}</Text>
                  {items.map((it) => (
                    <ItemCard
                      key={it.key}
                      item={it}
                      open={!!open[it.key]}
                      onToggle={() => setOpen((o) => ({ ...o, [it.key]: !o[it.key] }))}
                      uploading={uploadingKey === it.key}
                      onCamera={() => pickImage(it.key, "camera")}
                      onLibrary={() => pickImage(it.key, "library")}
                      onFile={() => pickFile(it.key)}
                      onNa={(na) => override.mutate({ key: it.key, na })}
                      onOpenDoc={(doc) => router.push(`/property/${id}/document/${doc.id}`)}
                    />
                  ))}
                </View>
              );
            })}
            <Text style={styles.hint}>
              Liste indicative fondée sur la réglementation française (dossier de diagnostic technique, loi ALUR). Votre
              notaire reste l’interlocuteur de référence.
            </Text>
          </>
        )}
      </ScrollView>
    </View>
  );
}

function StatusChip({ status }: { status: ItemStatus | SaleDocument["status"] }) {
  const styles = useStyles();
  const { colors } = useTheme();
  const map: Record<string, { label: string; fg: string; bg: string; Icon: typeof CheckCircleIcon }> = {
    manquant: { label: "Manquant", fg: colors.muted, bg: colors.surfaceTertiary, Icon: ClockIcon },
    a_verifier: { label: "À vérifier", fg: colors.warning, bg: colors.warningSoft, Icon: WarningIcon },
    valide: { label: "Validé", fg: colors.success, bg: colors.successSoft, Icon: CheckCircleIcon },
    expire: { label: "Expiré", fg: colors.error, bg: colors.errorSoft, Icon: XCircleIcon },
    non_applicable: { label: "Non applicable", fg: colors.muted, bg: colors.surfaceTertiary, Icon: ProhibitIcon },
    erreur_ocr: { label: "Lecture échouée", fg: colors.error, bg: colors.errorSoft, Icon: XCircleIcon },
  };
  const m = map[status];
  return (
    <View style={[styles.chip, { backgroundColor: m.bg }]}>
      <m.Icon size={12} color={m.fg} weight="fill" />
      <Text style={[styles.chipText, { color: m.fg }]}>{m.label}</Text>
    </View>
  );
}

interface ItemCardProps {
  item: ChecklistItem;
  open: boolean;
  uploading: boolean;
  onToggle: () => void;
  onCamera: () => void;
  onLibrary: () => void;
  onFile: () => void;
  onNa: (na: boolean) => void;
  onOpenDoc: (doc: SaleDocument) => void;
}

function ItemCard({ item, open, uploading, onToggle, onCamera, onLibrary, onFile, onNa, onOpenDoc }: ItemCardProps) {
  const styles = useStyles();
  const { colors } = useTheme();
  const na = item.status === "non_applicable";
  return (
    <View style={[styles.item, na && { opacity: 0.6 }]} testID={`checklist-item-${item.key}`}>
      <Pressable testID={`checklist-toggle-${item.key}`} accessibilityRole="button" onPress={onToggle} style={styles.itemHead}>
        <View style={{ flex: 1, gap: 4 }}>
          <Text style={styles.itemLabel}>{item.label}{item.required ? " *" : ""}</Text>
          <Text style={styles.itemReason}>{item.reason}</Text>
        </View>
        <StatusChip status={item.status} />
        {open ? <CaretUpIcon size={16} color={colors.muted} /> : <CaretDownIcon size={16} color={colors.muted} />}
      </Pressable>
      {open ? (
        <View style={styles.itemBody}>
          <Text style={styles.description}>{item.description}</Text>
          {item.documents.map((doc, i) => (
            <Pressable key={doc.id} testID={`document-row-${item.key}-${i}`} accessibilityRole="button" onPress={() => onOpenDoc(doc)} style={styles.docRow}>
              <FileTextIcon size={20} color={colors.brandPrimary} weight="duotone" />
              <View style={{ flex: 1 }}>
                <Text style={styles.docTitle} numberOfLines={1}>{(doc.validated_fields ?? doc.ocr)?.title ?? doc.filename}</Text>
                <Text style={styles.docMeta}>
                  {formatMonth(doc.created_at)}{doc.expiry_date ? ` · valide jusqu’au ${formatMonth(doc.expiry_date)}` : ""}
                </Text>
              </View>
              <StatusChip status={doc.status} />
              <CaretRightIcon size={14} color={colors.muted} />
            </Pressable>
          ))}
          {uploading ? (
            <View style={styles.uploading} testID={`document-uploading-${item.key}`}>
              <ActivityIndicator color={colors.brandPrimary} />
              <Text style={styles.hint}>Envoi et lecture du document…</Text>
            </View>
          ) : !na ? (
            <View style={styles.addRow}>
              {Platform.OS !== "web" ? (
                <Pressable testID={`document-add-camera-${item.key}`} accessibilityRole="button" onPress={onCamera} style={styles.addBtn}>
                  <CameraIcon size={18} color={colors.onBrandTertiary} />
                  <Text style={styles.addLabel}>Photo</Text>
                </Pressable>
              ) : null}
              <Pressable testID={`document-add-library-${item.key}`} accessibilityRole="button" onPress={onLibrary} style={styles.addBtn}>
                <ImagesIcon size={18} color={colors.onBrandTertiary} />
                <Text style={styles.addLabel}>Galerie</Text>
              </Pressable>
              <Pressable testID={`document-add-file-${item.key}`} accessibilityRole="button" onPress={onFile} style={styles.addBtn}>
                <FilePlusIcon size={18} color={colors.onBrandTertiary} />
                <Text style={styles.addLabel}>Fichier / PDF</Text>
              </Pressable>
            </View>
          ) : null}
          <Pressable testID={`checklist-na-${item.key}`} accessibilityRole="button" onPress={() => onNa(!na)} style={styles.naBtn}>
            <ProhibitIcon size={14} color={colors.muted} />
            <Text style={styles.naLabel}>{na ? "Rétablir cet élément" : "Non applicable à mon bien"}</Text>
          </Pressable>
        </View>
      ) : null}
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  screen: { flex: 1, backgroundColor: colors.surface },
  content: { padding: spacing.lg, gap: spacing.lg },
  progressCard: { backgroundColor: colors.brandTertiary, borderRadius: radius.lg, padding: spacing.lg, gap: spacing.sm },
  progressHead: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  progressTitle: { fontFamily: fonts.semibold, fontSize: 14, color: colors.onBrandTertiary },
  progressValue: { fontFamily: fonts.bold, fontSize: 20, color: colors.onBrandTertiary, fontVariant: ["tabular-nums"] },
  bar: { height: 8, borderRadius: radius.pill, backgroundColor: colors.surfaceSecondary, overflow: "hidden" },
  barFill: { height: 8, borderRadius: radius.pill, backgroundColor: colors.brandPrimary },
  hint: { fontFamily: fonts.regular, fontSize: 12, lineHeight: 17, color: colors.muted },
  warn: { flexDirection: "row", gap: spacing.md, alignItems: "flex-start", backgroundColor: colors.warningSoft, borderRadius: radius.md, padding: spacing.lg },
  warnText: { flex: 1, fontFamily: fonts.medium, fontSize: 13, lineHeight: 19, color: colors.warning },
  sectionTitle: { fontFamily: fonts.semibold, fontSize: 13, color: colors.muted, textTransform: "uppercase", letterSpacing: 0.6, marginTop: spacing.sm },
  item: { backgroundColor: colors.surfaceSecondary, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, overflow: "hidden" },
  itemHead: { flexDirection: "row", alignItems: "center", gap: spacing.md, padding: spacing.lg, minHeight: 64 },
  itemLabel: { fontFamily: fonts.semibold, fontSize: 14, color: colors.onSurfaceSecondary },
  itemReason: { fontFamily: fonts.regular, fontSize: 12, color: colors.muted },
  itemBody: { paddingHorizontal: spacing.lg, paddingBottom: spacing.lg, gap: spacing.md, borderTopWidth: 1, borderTopColor: colors.divider, paddingTop: spacing.md },
  description: { fontFamily: fonts.regular, fontSize: 13, lineHeight: 19, color: colors.onSurfaceTertiary },
  docRow: { flexDirection: "row", alignItems: "center", gap: spacing.md, backgroundColor: colors.surfaceTertiary, borderRadius: radius.md, padding: spacing.md, minHeight: 56 },
  docTitle: { fontFamily: fonts.medium, fontSize: 13, color: colors.onSurfaceTertiary },
  docMeta: { fontFamily: fonts.regular, fontSize: 11, color: colors.muted, marginTop: 2 },
  uploading: { flexDirection: "row", alignItems: "center", gap: spacing.md, minHeight: 44 },
  addRow: { flexDirection: "row", gap: spacing.sm },
  addBtn: { flex: 1, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6, minHeight: 44, borderRadius: radius.md, backgroundColor: colors.brandTertiary, paddingHorizontal: spacing.sm },
  addLabel: { fontFamily: fonts.semibold, fontSize: 13, color: colors.onBrandTertiary },
  naBtn: { flexDirection: "row", alignItems: "center", gap: 6, minHeight: 40 },
  naLabel: { fontFamily: fonts.medium, fontSize: 12, color: colors.muted },
  chip: { flexDirection: "row", alignItems: "center", gap: 4, height: 24, paddingHorizontal: spacing.sm, borderRadius: radius.pill, flexShrink: 0 },
  chipText: { fontFamily: fonts.semibold, fontSize: 11 },
}));
