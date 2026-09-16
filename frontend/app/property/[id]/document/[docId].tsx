import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Image } from "expo-image";
import { useLocalSearchParams, useRouter } from "expo-router";
import { FileTextIcon, SealCheckIcon, TrashIcon, WarningIcon } from "phosphor-react-native";
import { useEffect, useState } from "react";
import { ActivityIndicator, Linking, Pressable, Text, View } from "react-native";
import { KeyboardAwareScrollView, KeyboardStickyView } from "react-native-keyboard-controller";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { OcrResult, api, fileUrl, formatMonth } from "@/src/api";
import { Field } from "@/src/components/Form";
import { PremiumGate, usePackUnlocked } from "@/src/components/PremiumGate";
import { PrimaryButton } from "@/src/components/PrimaryButton";
import { ScreenHeader } from "@/src/components/ScreenHeader";
import { fonts, makeStyles, radius, spacing, useTheme } from "@/src/theme";

const CTA_HEIGHT = 100;

const EMPTY: OcrResult = {
  document_type: "autre", title: "", issuer: null, document_date: null, validity_date: null, address_found: null,
  key_fields: [], warnings: [], summary: "", confidence: 0,
};

export default function DocumentReviewScreen() {
  const { id, docId } = useLocalSearchParams<{ id: string; docId: string }>();
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const queryClient = useQueryClient();

  const doc = useQuery({ queryKey: ["document", docId], queryFn: () => api.getDocument(docId!), enabled: !!docId });
  const [fields, setFields] = useState<OcrResult>(EMPTY);

  useEffect(() => {
    if (doc.data) setFields(doc.data.validated_fields ?? doc.data.ocr ?? { ...EMPTY, title: doc.data.filename });
  }, [doc.data]);

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["document", docId] });
    queryClient.invalidateQueries({ queryKey: ["dossier", id] });
    queryClient.invalidateQueries({ queryKey: ["alerts"] });
  };

  const validate = useMutation({
    mutationFn: () => api.validateDocument(docId!, fields, true),
    onSuccess: () => {
      invalidate();
      router.back();
    },
  });
  const reocr = useMutation({ mutationFn: () => api.reocrDocument(docId!), onSuccess: invalidate });
  const pack = usePackUnlocked(id);
  const remove = useMutation({
    mutationFn: () => api.deleteDocument(docId!),
    onSuccess: () => {
      invalidate();
      router.back();
    },
  });

  const d = doc.data;
  const setField = <K extends keyof OcrResult>(k: K, v: OcrResult[K]) => setFields((f) => ({ ...f, [k]: v }));

  return (
    <View style={styles.screen} testID="document-review-screen">
      <ScreenHeader title="Vérifier le document" subtitle="Corrigez si besoin, puis validez" onBack={() => router.back()} />
      {doc.isLoading || !d ? (
        <View style={styles.center}><ActivityIndicator color={colors.brandPrimary} /></View>
      ) : (
        <>
          <KeyboardAwareScrollView
            contentContainerStyle={[styles.content, { paddingBottom: CTA_HEIGHT + insets.bottom + spacing.lg }]}
            bottomOffset={CTA_HEIGHT + spacing.lg}
            keyboardShouldPersistTaps="handled"
          >
            {d.mime.startsWith("image/") ? (
              <Image source={{ uri: fileUrl(d.file_path) }} style={styles.preview} contentFit="contain" cachePolicy="memory-disk" />
            ) : (
              <Pressable testID="document-open-file" accessibilityRole="button" onPress={() => Linking.openURL(fileUrl(d.file_path))} style={styles.pdfRow}>
                <FileTextIcon size={28} color={colors.brandPrimary} weight="duotone" />
                <View style={{ flex: 1 }}>
                  <Text style={styles.pdfName}>{d.filename}</Text>
                  <Text style={styles.hint}>PDF · {(d.size / 1024).toFixed(0)} Ko · appuyer pour ouvrir</Text>
                </View>
              </Pressable>
            )}

            {d.validated ? (
              <View style={styles.okBanner} testID="document-validated-banner">
                <SealCheckIcon size={18} color={colors.success} weight="fill" />
                <Text style={styles.okText}>Document validé par vous{d.expiry_date ? ` · valide jusqu’au ${formatMonth(d.expiry_date)}` : ""}</Text>
              </View>
            ) : d.ocr_status === "locked" ? (
              pack.unlocked ? (
                <View style={styles.infoBanner} testID="document-ocr-locked-unlocked">
                  <Text style={styles.infoText}>Pack débloqué : lancez la lecture IA pour pré-remplir les champs, ou saisissez-les à la main.</Text>
                  <PrimaryButton title="Lire le document avec l’IA" variant="secondary" onPress={() => reocr.mutate()} loading={reocr.isPending} testID="document-reocr-button" />
                </View>
              ) : (
                <PremiumGate propertyId={id!} feature="la lecture automatique de ce document par l’IA (type, dates, champs clés, alertes)" testID="document-premium-gate" />
              )
            ) : d.ocr_status === "error" ? (
              <View style={styles.warn} testID="document-ocr-error">
                <WarningIcon size={18} color={colors.error} weight="fill" />
                <View style={{ flex: 1, gap: spacing.sm }}>
                  <Text style={[styles.warnText, { color: colors.error }]}>Lecture IA échouée : {d.ocr_error}. Vous pouvez saisir les informations manuellement.</Text>
                  <PrimaryButton title="Relancer la lecture" variant="secondary" onPress={() => reocr.mutate()} loading={reocr.isPending} testID="document-reocr-button" />
                </View>
              </View>
            ) : (
              <View style={styles.infoBanner} testID="document-ocr-banner">
                <Text style={styles.infoText}>
                  Lecture IA (confiance {Math.round((d.ocr?.confidence ?? 0) * 100)} %). Vérifiez chaque champ : rien n’est
                  retenu sans votre validation.
                </Text>
              </View>
            )}

            {(fields.warnings ?? []).length > 0 ? (
              <View style={styles.warn} testID="document-warnings">
                <WarningIcon size={18} color={colors.warning} weight="fill" />
                <View style={{ flex: 1 }}>
                  {fields.warnings.map((w, i) => <Text key={i} style={styles.warnText}>• {w}</Text>)}
                </View>
              </View>
            ) : null}

            {fields.summary ? <Text style={styles.summary}>{fields.summary}</Text> : null}

            <Field label="Intitulé" testID="doc-field-title" value={fields.title} onChangeText={(v) => setField("title", v)} />
            <Field label="Émetteur (diagnostiqueur, notaire…)" testID="doc-field-issuer" value={fields.issuer ?? ""} onChangeText={(v) => setField("issuer", v || null)} />
            <View style={styles.row2}>
              <View style={{ flex: 1 }}>
                <Field label="Date du document" testID="doc-field-date" placeholder="AAAA-MM-JJ" value={fields.document_date ?? ""} onChangeText={(v) => setField("document_date", v || null)} autoCapitalize="none" />
              </View>
              <View style={{ flex: 1 }}>
                <Field label="Valide jusqu’au" testID="doc-field-validity" placeholder="AAAA-MM-JJ" value={fields.validity_date ?? ""} onChangeText={(v) => setField("validity_date", v || null)} autoCapitalize="none" hint="Vide = calculé automatiquement" />
              </View>
            </View>
            <Field label="Adresse lue sur le document" testID="doc-field-address" value={fields.address_found ?? ""} onChangeText={(v) => setField("address_found", v || null)} />

            {fields.key_fields.length > 0 ? (
              <View style={{ gap: spacing.sm }}>
                <Text style={styles.sectionTitle}>Champs extraits</Text>
                {fields.key_fields.map((kf, i) => (
                  <Field
                    key={`${kf.label}-${i}`}
                    label={kf.label}
                    testID={`doc-field-kf-${i}`}
                    value={kf.value}
                    onChangeText={(v) => setFields((f) => ({ ...f, key_fields: f.key_fields.map((x, j) => (j === i ? { ...x, value: v } : x)) }))}
                  />
                ))}
              </View>
            ) : null}

            <Pressable testID="document-delete-button" accessibilityRole="button" onPress={() => remove.mutate()} style={styles.deleteRow}>
              <TrashIcon size={16} color={colors.error} />
              <Text style={styles.deleteLabel}>Supprimer ce document</Text>
            </Pressable>
          </KeyboardAwareScrollView>

          <KeyboardStickyView offset={{ closed: 0, opened: insets.bottom }}>
            <View style={[styles.cta, { paddingBottom: insets.bottom + spacing.lg }]}>
              <PrimaryButton
                title={d.validated ? "Enregistrer les corrections" : "Valider ce document"}
                onPress={() => validate.mutate()}
                loading={validate.isPending}
                disabled={!fields.title.trim()}
                testID="document-validate-button"
              />
              {validate.isError ? <Text style={styles.errorText}>{(validate.error as Error).message}</Text> : null}
            </View>
          </KeyboardStickyView>
        </>
      )}
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  screen: { flex: 1, backgroundColor: colors.surface },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  content: { padding: spacing.lg, gap: spacing.lg },
  preview: { width: "100%", height: 220, borderRadius: radius.lg, backgroundColor: colors.skeleton },
  pdfRow: { flexDirection: "row", alignItems: "center", gap: spacing.md, backgroundColor: colors.surfaceSecondary, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, padding: spacing.lg, minHeight: 64 },
  pdfName: { fontFamily: fonts.semibold, fontSize: 14, color: colors.onSurfaceSecondary },
  hint: { fontFamily: fonts.regular, fontSize: 12, lineHeight: 17, color: colors.muted },
  okBanner: { flexDirection: "row", alignItems: "center", gap: spacing.md, backgroundColor: colors.successSoft, borderRadius: radius.md, padding: spacing.lg },
  okText: { flex: 1, fontFamily: fonts.medium, fontSize: 13, color: colors.success },
  infoBanner: { backgroundColor: colors.brandTertiary, borderRadius: radius.md, padding: spacing.lg, gap: spacing.sm },
  infoText: { fontFamily: fonts.medium, fontSize: 13, lineHeight: 19, color: colors.onBrandTertiary },
  warn: { flexDirection: "row", gap: spacing.md, alignItems: "flex-start", backgroundColor: colors.warningSoft, borderRadius: radius.md, padding: spacing.lg },
  warnText: { flex: 1, fontFamily: fonts.medium, fontSize: 13, lineHeight: 19, color: colors.warning },
  summary: { fontFamily: fonts.regular, fontSize: 14, lineHeight: 20, color: colors.onSurfaceTertiary },
  row2: { flexDirection: "row", gap: spacing.md },
  sectionTitle: { fontFamily: fonts.semibold, fontSize: 13, color: colors.muted, textTransform: "uppercase", letterSpacing: 0.6 },
  deleteRow: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: spacing.sm, minHeight: 48 },
  deleteLabel: { fontFamily: fonts.medium, fontSize: 14, color: colors.error },
  cta: { paddingHorizontal: spacing.lg, paddingTop: spacing.md, backgroundColor: colors.surface, borderTopWidth: 1, borderTopColor: colors.divider, gap: spacing.sm },
  errorText: { fontFamily: fonts.medium, fontSize: 13, color: colors.error, textAlign: "center" },
}));
