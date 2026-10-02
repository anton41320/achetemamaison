import { Platform } from "react-native";

const BASE = `${process.env.EXPO_PUBLIC_BACKEND_URL}/api`;

/** Multipart file part: a Blob on the web, the React Native `{ uri, name, type }` descriptor on iOS/Android.
 *  (Never sniff `document`: it exists in Expo's native runtime too.) */
async function appendFile(form: FormData, uri: string, name: string, type: string) {
  if (Platform.OS === "web") {
    form.append("file", await (await fetch(uri)).blob(), name);
  } else {
    form.append("file", { uri, name, type } as any);
  }
}

/** POST a FormData. On iOS/Android we go through XMLHttpRequest: Expo ≥ 54 replaces the global `fetch` by its WinterCG
 *  implementation, which rejects React Native `{ uri }` file parts ("Unsupported FormDataPart implementation"), whereas
 *  React Native's XHR streams them natively and reports upload progress. The web keeps `fetch` + Blob. */
async function multipart<T>(path: string, form: FormData, onProgress?: (pct: number) => void): Promise<T> {
  const url = `${BASE}${path}`;
  const headers: Record<string, string> = authToken ? { Authorization: `Bearer ${authToken}` } : {};
  if (Platform.OS === "web") {
    const res = await fetch(url, { method: "POST", body: form, headers });
    if (!res.ok) throw new Error(await errorMessage(res));
    return res.json();
  }
  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", url);
    Object.entries(headers).forEach(([k, v]) => xhr.setRequestHeader(k, v));
    if (onProgress) {
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100));
      };
    }
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        onProgress?.(100);
        resolve(JSON.parse(xhr.responseText));
      } else {
        let message = `Erreur ${xhr.status}`;
        try {
          const body = JSON.parse(xhr.responseText);
          if (typeof body?.detail === "string") message = body.detail;
        } catch {
          // keep default
        }
        reject(new Error(message));
      }
    };
    xhr.onerror = () => reject(new Error("Connexion interrompue pendant l’envoi"));
    xhr.ontimeout = () => reject(new Error("Envoi trop long, réessayez"));
    xhr.timeout = 180000;
    xhr.send(form);
  });
}

async function errorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") return body.detail;
  } catch {
    // keep default
  }
  return `Erreur ${res.status}`;
}

// Session token (set by SessionProvider); sent as Bearer header, or as ?t= for links opened by the OS.
let authToken: string | null = null;
let onUnauthorized: (() => void) | null = null;
export function setApiToken(token: string | null) {
  authToken = token;
}
export function setUnauthorizedHandler(fn: (() => void) | null) {
  onUnauthorized = fn;
}
export function withToken(url: string): string {
  if (!authToken) return url;
  return `${url}${url.includes("?") ? "&" : "?"}t=${encodeURIComponent(authToken)}`;
}

export type PropertyType = "appartement" | "maison";
export type Condition = "a_renover" | "travaux" | "correct" | "bon" | "tres_bon" | "neuf_renove";
export type ConfidenceLevel = "eleve" | "moyen" | "faible";

export interface GeocodeResult {
  id: string;
  label: string;
  name: string;
  postcode: string;
  city: string;
  citycode: string;
  type: string;
  lat: number;
  lon: number;
  dept: string;
  covered: boolean;
}

export interface Adjustment {
  key: string;
  label: string;
  pct: number;
  amount: number;
}

export interface MarketLevel {
  label: string;
  radius_m: number | null;
  count: number;
  median_pm2: number | null;
}

export interface Comparable {
  date: string;
  distance_m: number;
  surface: number;
  rooms: number | null;
  price: number;
  price_m2: number;
  land_surface: number | null;
  commune: string;
  population: number | null;
  property_type: string;
  weight: number;
}

export interface ConfidenceDetail {
  key: string;
  label: string;
  score: number;
  max_score: number;
  hint: string;
}

export interface Confidence {
  score: number;
  level: ConfidenceLevel;
  n_comparables: number;
  dispersion_pct: number;
  median_age_months: number;
  radius_label: string;
  details: ConfidenceDetail[];
}

export interface HedonicFactor {
  key: string;
  label: string;
  pct: number;
  detail: string;
  learned: boolean;
}

export interface HedonicResult {
  model_version: string;
  value: number;
  low: number;
  high: number;
  price_m2: number;
  reference_value: number;
  reference_label: string;
  factors: HedonicFactor[];
  delta_vs_comparables_pct: number;
  agreement: "convergent" | "ecart_modere" | "divergent";
  model_median_ape: number | null;
  model_n: number;
}

export interface TrendPoint {
  year: number;
  count: number;
  median_pm2: number | null;
}

export interface TrendReport {
  commune: string;
  property_type: PropertyType;
  years: number[];
  commune_series: TrendPoint[];
  quartier_series: TrendPoint[];
  commune_change_pct: number | null;
  quartier_change_pct: number | null;
}

export interface MlFactor {
  key: string;
  label: string;
  pct: number;
}

export interface MlResult {
  model_version: string;
  promoted: boolean;
  value: number;
  low: number;
  high: number;
  price_m2: number;
  reference_value: number;
  factors: MlFactor[];
  model_median_ape: number | null;
  baseline_median_ape: number | null;
}

export interface MarketEstimate {
  value: number;
  low: number;
  high: number;
  price_m2: number;
  label: string;
  count: number;
}

export interface Weights {
  comparables: number;
  hedonic: number;
  market: number;
  ml: number;
}

export const DEFAULT_WEIGHTS: Weights = { comparables: 50, hedonic: 30, market: 20, ml: 0 };

export interface BlendComponent {
  key: keyof Weights;
  label: string;
  value: number | null;
  low: number | null;
  high: number | null;
  weight: number;
  available: boolean;
  effective_weight: number;
}

export interface BlendResult {
  value: number;
  low: number;
  high: number;
  components: BlendComponent[];
}

/** Mirrors backend blend.py so sliders update instantly. */
export function blendEstimation(est: Estimation, weights: Weights): BlendResult {
  const components: BlendComponent[] = [
    { key: "comparables", label: "Ventes comparables", value: est.value, low: est.low, high: est.high, weight: weights.comparables, available: true, effective_weight: 0 },
    { key: "hedonic", label: "Modèle hédonique", value: est.hedonic?.value ?? null, low: est.hedonic?.low ?? null, high: est.hedonic?.high ?? null, weight: weights.hedonic, available: !!est.hedonic, effective_weight: 0 },
    { key: "market", label: est.market_estimate?.label ?? "Marché local", value: est.market_estimate?.value ?? null, low: est.market_estimate?.low ?? null, high: est.market_estimate?.high ?? null, weight: weights.market, available: !!est.market_estimate, effective_weight: 0 },
    { key: "ml", label: "Machine learning (LightGBM)", value: est.ml?.value ?? null, low: est.ml?.low ?? null, high: est.ml?.high ?? null, weight: weights.ml, available: !!est.ml?.promoted, effective_weight: 0 },
  ];
  let active = components.filter((c) => c.available && c.weight > 0);
  if (active.length === 0) active = [components[0]];
  const total = active.reduce((s, c) => s + c.weight, 0) || 1;
  const sum = (k: "value" | "low" | "high") => active.reduce((s, c) => s + (c[k] ?? 0) * c.weight, 0) / total;
  for (const c of components) c.effective_weight = active.includes(c) ? c.weight / total : 0;
  const r = (v: number) => Math.round(v / 1000) * 1000;
  return { value: r(sum("value")), low: r(sum("low")), high: r(sum("high")), components };
}

export interface MarketSignal {
  available: boolean;
  score?: number;
  verdict?: "favorable" | "neutre" | "attentiste";
  scope?: string;
  as_of?: string;
  trend_pct?: number | null;
  volume_ratio?: number | null;
  days_since_last?: number | null;
  recent_count?: number;
  reasons?: { key: string; label: string; text: string; score: number; max_score: number }[];
}

export type ListingStyle = "sobre" | "chaleureux" | "premium" | "familial";
export const LISTING_STYLES: { value: ListingStyle; label: string }[] = [
  { value: "sobre", label: "Sobre" },
  { value: "chaleureux", label: "Chaleureux" },
  { value: "premium", label: "Premium" },
  { value: "familial", label: "Familial" },
];

export interface Listing {
  used_environment?: boolean;
  id: string;
  property_id: string;
  style: ListingStyle;
  title: string;
  hook: string;
  description: string;
  highlights: string[];
  extra_facts: string | null;
  model: string;
  created_at: string;
}

export interface MlModelInfo {
  available: boolean;
  training: boolean;
  n?: number;
  n_train?: number;
  n_test?: number;
  holdout?: { n: number; mape: number; median_ape: number; within_15pct: number; rmse_log: number; test_year: number };
  by_type?: Record<string, { n: number; median_ape: number; mape: number }>;
  by_dept?: Record<string, { n: number; median_ape: number; mape: number }>;
  gate?: { n: number; ml_median_ape: number | null; baseline_median_ape: number | null; ml_mape: number | null; baseline_mape: number | null };
  promoted?: boolean;
  feature_importance?: Record<string, number>;
  trained_at?: string;
}

export interface Estimation {
  method: string;
  created_at: string;
  value: number;
  low: number;
  high: number;
  price_m2: number;
  base_price_m2: number;
  confidence: Confidence;
  insufficient_data: boolean;
  notes: string[];
  adjustments: Adjustment[];
  market: MarketLevel[];
  comparables: Comparable[];
  hedonic: HedonicResult | null;
  ml: MlResult | null;
  market_estimate: MarketEstimate | null;
}

export interface Features {
  pool: "aucune" | "hors_sol" | "enterree" | null;
  fenced: boolean | null;
  motorized_gate: boolean | null;
  terrace: boolean | null;
  garage: "aucun" | "un" | "deux_plus" | null;
  outbuilding: boolean | null;
  orientation: "nord" | "est" | "sud" | "ouest" | "sud_ouest" | "sud_est" | "nord_est" | "nord_ouest" | null;
  single_storey: boolean | null;
  basement: boolean | null;
  convertible_attic: boolean | null;
  pantry: boolean | null;
  master_suite: boolean | null;
  master_suite_dressing: boolean | null;
  master_suite_bathroom: boolean | null;
  master_suite_wc: boolean | null;
  dressing: boolean | null;
  bathrooms: number | null;
  heating: "pompe_a_chaleur" | "gaz" | "electrique" | "fioul" | "bois" | "autre" | null;
  sanitation: "tout_a_l_egout" | "fosse_septique" | "fosse_toutes_eaux" | "microstation" | null;
  dpe: "A" | "B" | "C" | "D" | "E" | "F" | "G" | null;
  double_glazing: boolean | null;
  air_conditioning: boolean | null;
  fireplace: "aucune" | "insert" | "foyer_ouvert" | "poele_bois" | "poele_granules" | null;
  solar_panels: boolean | null;
  floor: number | null;
  elevator: boolean | null;
  balcony: boolean | null;
  parking: "aucun" | "exterieur" | "interieur" | null;
  cellar: boolean | null;
  caretaker: boolean | null;
  condo_fees: number | null;
  heating_mode: "collectif" | "individuel" | null;
  underfloor_heating: boolean | null;
}

export const EMPTY_FEATURES: Features = {
  pool: null, fenced: null, motorized_gate: null, terrace: null, garage: null, outbuilding: null, orientation: null,
  single_storey: null, basement: null, convertible_attic: null, pantry: null, master_suite: null, master_suite_dressing: null, master_suite_bathroom: null, master_suite_wc: null, dressing: null, bathrooms: null, heating: null, sanitation: null, dpe: null,
  double_glazing: null, air_conditioning: null, fireplace: null, solar_panels: null, floor: null, elevator: null, balcony: null,
  parking: null, cellar: null, caretaker: null, condo_fees: null, heating_mode: null, underfloor_heating: null,
};

export interface PropertyUpdate {
  surface?: number;
  rooms?: number;
  bedrooms?: number;
  year_built?: number | null;
  condition?: Condition;
  land_surface?: number | null;
  features?: Features;
}

export interface PropertyIn {
  address_label: string;
  lat: number;
  lon: number;
  code_commune: string;
  commune: string;
  postcode: string;
  property_type: PropertyType;
  surface: number;
  rooms: number;
  bedrooms: number;
  year_built: number | null;
  condition: Condition;
  land_surface: number | null;
  features: Features;
}

export interface Completion {
  pct: number;
  filled: number;
  total: number;
  missing: string[];
}

export interface Property extends PropertyIn {
  id: string;
  features: Features;
  estimation: Estimation | null;
  completion: Completion;
  created_at: string;
  updated_at: string;
}

export interface DvfDepartment {
  dept: string;
  appartement: number;
  maison: number;
  total: number;
  min_date: string | null;
  max_date: string | null;
}

export interface DvfStatus {
  state: "running" | "idle" | "empty" | "error";
  progress: number;
  error: string | null;
  finished_at: string | null;
  configured_departments: string[];
  years: number[];
  total: number;
  departments: DvfDepartment[];
}

export interface ValidationAgg {
  n: number;
  mape: number;
  median_ape: number;
  coverage: number;
  within_15pct: number;
}

export interface ValidationReport extends ValidationAgg {
  by_confidence: Record<string, ValidationAgg>;
  by_type: Record<string, ValidationAgg>;
  results: {
    commune: string;
    type: string;
    surface: number;
    actual: number;
    estimated: number;
    low: number;
    high: number;
    ape: number;
    in_range: boolean;
    confidence: ConfidenceLevel;
  }[];
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

// Silent retry on transient outages (Cloudflare 520-524, 502/503/504, network failure) so brief server
// restarts stay invisible. Reads are always retried; writes only when the origin was demonstrably not
// reached (connection failed, 503, 521-523) to avoid duplicating a request the server may have handled.
const RETRY_DELAYS_MS = [700, 1800];
const READ_RETRY_STATUSES = new Set([500, 502, 503, 504, 520, 521, 522, 523, 524]);
const WRITE_RETRY_STATUSES = new Set([503, 521, 522, 523]);
const NO_RETRY_PATHS = ["/pack/checkout"];

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

function shouldRetry(path: string, method: string, status: number, attempt: number): boolean {
  if (attempt >= RETRY_DELAYS_MS.length) return false;
  if (NO_RETRY_PATHS.some((p) => path.includes(p))) return false;
  const isRead = method === "GET" || method === "HEAD";
  if (status === 0) return true; // fetch threw: nothing reached the server
  return isRead ? READ_RETRY_STATUSES.has(status) : WRITE_RETRY_STATUSES.has(status);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const method = (init?.method ?? "GET").toUpperCase();
  for (let attempt = 0; ; attempt++) {
    let res: Response | null = null;
    try {
      res = await fetch(`${BASE}${path}`, {
        ...init,
        headers: {
          "Content-Type": "application/json",
          ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
          ...(init?.headers ?? {}),
        },
      });
    } catch {
      res = null;
    }
    const status = res?.status ?? 0;
    if ((res === null || status >= 500) && shouldRetry(path, method, status, attempt)) {
      await sleep(RETRY_DELAYS_MS[attempt]);
      continue;
    }
    if (res === null) throw new ApiError("Serveur injoignable. Vérifiez votre connexion et réessayez.", 0);
    if (res.status === 401 && authToken && !path.startsWith("/auth/")) onUnauthorized?.();
    if (!res.ok) {
      let message = res.status >= 500 ? `Le serveur est momentanément indisponible (erreur ${res.status}). Réessayez dans un instant.` : `Erreur ${res.status}`;
      try {
        const body = await res.json();
        if (typeof body?.detail === "string") message = body.detail;
        else if (Array.isArray(body?.detail)) message = body.detail.map((d: any) => d.msg).join(", ");
      } catch {
        // keep default
      }
      throw new ApiError(message, res.status);
    }
    return res.json() as Promise<T>;
  }
}

export interface Photo {
  id: string;
  property_id: string;
  original_path: string;
  original_mime: string;
  original_size: number;
  retouched_path: string | null;
  retouched_mime: string | null;
  status: "original" | "processing" | "done" | "error";
  error: string | null;
  model: string | null;
  position: number;
  created_at: string;
  retouched_at: string | null;
}

export function fileUrl(path: string): string {
  return `${BASE}/files/${path}`;
}

export async function uploadPhoto(propertyId: string, uri: string, name: string, type: string, onProgress?: (pct: number) => void): Promise<Photo> {
  const form = new FormData();
  await appendFile(form, uri, name, type);
  return multipart<Photo>(`/properties/${propertyId}/photos`, form, onProgress);
}

export async function sendFeedback(p: { message: string; screen: string; platform: string; appVersion: string; screenshot?: { uri: string; name: string; type: string } | null }): Promise<{ ok: boolean; emailed: boolean }> {
  const form = new FormData();
  form.append("message", p.message);
  form.append("screen", p.screen);
  form.append("platform", p.platform);
  form.append("app_version", p.appVersion);
  if (p.screenshot) await appendFile(form, p.screenshot.uri, p.screenshot.name, p.screenshot.type);
  return multipart(`/feedback`, form);
}

export type DocStatus = "a_verifier" | "valide" | "expire" | "erreur_ocr";
export type ItemStatus = "manquant" | "a_verifier" | "valide" | "expire" | "non_applicable";

export interface OcrResult {
  document_type: string;
  title: string;
  issuer: string | null;
  document_date: string | null;
  validity_date: string | null;
  address_found: string | null;
  key_fields: { label: string; value: string }[];
  warnings: string[];
  summary: string;
  confidence: number;
}

export interface SaleDocument {
  id: string;
  property_id: string;
  item_key: string;
  file_path: string;
  mime: string;
  filename: string;
  size: number;
  ocr_status: "pending" | "done" | "error" | "locked";
  ocr: OcrResult | null;
  ocr_error: string | null;
  validated: boolean;
  validated_fields: OcrResult | null;
  expiry_date: string | null;
  created_at: string;
  status: DocStatus;
}

export interface ChecklistItem {
  key: string;
  label: string;
  description: string;
  category: "obligatoire" | "conditionnel" | "copropriete" | "recommande";
  validity_months: number | null;
  required: boolean;
  reason: string;
  status: ItemStatus;
  note: string | null;
  documents: SaleDocument[];
}

export type RiskLevel = "none" | "low" | "medium" | "high" | "info";
export interface RiskItem {
  key: string;
  label: string;
  family: "naturel" | "technologique";
  present: boolean;
  scope: "adresse" | "commune";
  status_address: string | null;
  status_commune: string | null;
  level: RiskLevel;
  detail?: string;
}
export interface Risks {
  property_id: string;
  fetched_at: string;
  partial: boolean;
  source_url: string;
  commune: { libelle?: string; codePostal?: string; codeInsee?: string };
  items: RiskItem[];
  argile: { code: string; level: RiskLevel; label: string };
  radon: { code: string; level: RiskLevel; label: string };
  catnat: { count: number; by_type: Record<string, number>; last: { type: string; start: string; end: string }[] };
  icpe: { count: number; radius_m: number; sites: { name: string; regime: string | null; seveso: string | null }[] };
  dossier_flags: { erp_required: boolean; geotechnique_required: boolean; radon_significant: boolean; catnat_secheresse: boolean };
}

export interface Dossier {
  property_id: string;
  items: ChecklistItem[];
  unassigned: SaleDocument[];
  locked: boolean;
  risks: Risks | null;
  progress: { done: number; total_required: number; pct: number };
}

export type TargetZone = "sous_fourchette" | "bas" | "central" | "haut" | "au_dessus";

export interface TargetAnalysis {
  target_price: number;
  target_price_m2: number;
  low: number;
  high: number;
  value: number;
  position: number;
  delta_pct: number;
  zone: TargetZone;
  label: string;
  advice: string;
  net_after_negotiation: number;
  negotiation_pct: number;
  vs_market_pm2_pct: number | null;
  market_verdict: "favorable" | "neutre" | "attentiste" | null;
  tips: string[];
}

export interface TargetResponse {
  target_price: number | null;
  analysis: TargetAnalysis | null;
}

export type AlertLevel = "expire" | "urgent" | "bientot";

export interface ExpiryAlert {
  property_id: string;
  address_label: string;
  document_id: string;
  item_key: string;
  label: string;
  expiry_date: string;
  days_left: number;
  level: AlertLevel;
}

export interface AlertsResponse {
  as_of: string;
  horizon_days: number;
  alerts: ExpiryAlert[];
}

export interface NextStep {
  key: "features" | "target" | "dossier" | "photos" | "listing" | "export";
  label: string;
  done: boolean;
  route: string;
  detail: string;
}

export interface PropertyNextSteps {
  property_id: string;
  steps: NextStep[];
  next: NextStep | null;
  done: number;
  total: number;
}

// ---- Analyse de l'environnement ----
export interface EnvItem {
  name?: string | null;
  nature?: string | null;
  type?: string | null;
  category?: string;
  label?: string;
  importance?: string | null;
  importance_label?: string;
  distance_m: number;
  ring?: string;
  direction?: string;
  source: string;
  url?: string;
  area_m2?: number | null;
  built?: boolean;
}
export interface EnvSource {
  id: string; name: string; kind: "official" | "open"; licence: string; doc_url: string; request_url?: string;
  fetched_at: string; status: "ok" | "unavailable" | "partial"; cached?: boolean; stale?: boolean; what?: string; precision?: string | null;
}
export interface EnvAnalysis {
  generated_at: string;
  radii_m: number[];
  address: { input?: string | null; label?: string | null; precision?: string | null; code_insee?: string | null };
  coordinates: { lon: number; lat: number };
  parcel: { id: string; section: string; numero: string; contenance_m2?: number | null } | null;
  building: { nature?: string; usage_1?: string; hauteur?: number | null; nombre_d_etages?: number | null; nombre_de_logements?: number | null; footprint_m2?: number } | null;
  neighbours: { distance_m: number; nature?: string; usage?: string; hauteur_m?: number | null; etages?: number | null; footprint_m2: number }[];
  density: { radius_m: number; buildings: number; built_ratio_pct: number; within_50m: number; nearest_m: number | null };
  terrain: { altitude_m: number | null; slope_pct: number | null; aspect: string | null; elevation_range_m?: number; nearest_water_m: number | null; nearest_forest_m: number | null;
    vegetation_ratio_250m_pct: number | null; landcover: { code: string; label: string; precision: string } | null };
  urbanism: { zones: { libelle?: string; libelong?: string; typezone?: string; reglement?: string; url?: string | null }[]; prescriptions: { libelle?: string; type?: string }[];
    infos: { libelle?: string }[]; servitudes: { libelle?: string }[]; documents: { type?: string; name?: string; approval_date?: string; url?: string }[];
    summary: { typezone: string[]; constructible_hint: boolean; agricole_ou_naturel: boolean }; notice: string } | null;
  risks: { at_address: { key: string; label: string; level: string; detail?: string }[]; commune_only: { key: string; label: string; level: string }[];
    argile?: { label: string; level: string } | null; radon?: { label: string; level: string } | null; catnat?: { count: number } | null; partial?: boolean; source_url?: string } | null;
  roads: EnvItem[]; railways: EnvItem[]; water: EnvItem[]; green_spaces: EnvItem[]; services: EnvItem[]; transport: EnvItem[];
  industrial_sites: EnvItem[]; aerodromes: EnvItem[]; nuisances: EnvItem[];
  nearby_parcels: { id: string; section: string; numero: string; surface_m2: number; built: boolean; distance_m: number; adjacent: boolean }[];
  rings: { label: string; buildings: number; roads: number; services: number; transport: number; green: number; water: number; industrial: number; unbuilt_parcels: number }[];
  sources: EnvSource[];
  unavailable: string[];
  limits: string[];
}
export interface EnvReport {
  model?: string;
  sections: Record<string, string | string[]> | null;
  titles?: Record<string, string>;
  order?: string[];
  disclaimer?: string;
  error?: string;
}
export interface EnvironmentResult {
  property_id: string;
  created_at: string;
  cached: boolean;
  analysis: EnvAnalysis;
  report: EnvReport | null;
  estimation_adjustments: Adjustment[];
}

export interface PackStatus {
  property_id: string;
  unlocked: boolean;
  promo_active: boolean;
  price_cents: number;
  currency: string;
  payments_available: boolean;
  mode: "test" | "live";
  webhook_configured: boolean;
  email_ready: boolean;
  free_retouches: number;
  retouches_used: number;
  photos: number;
  listings: number;
  last_order: { order_id: string; status: "pending" | "paid" | "failed"; customer_email: string | null; receipt_sent: boolean; paid_at: string | null } | null;
}

export async function uploadDocument(propertyId: string, itemKey: string, uri: string, name: string, type: string): Promise<SaleDocument> {
  const form = new FormData();
  await appendFile(form, uri, name, type);
  form.append("item_key", itemKey);
  return multipart<SaleDocument>(`/properties/${propertyId}/documents`, form);
}

export const api = {
  geocode: (q: string) => request<{ results: GeocodeResult[]; covered_departments: string[] }>(
    `/geocode?q=${encodeURIComponent(q)}`,
  ),
  listProperties: () => request<Property[]>("/properties"),
  getProperty: (id: string) => request<Property>(`/properties/${id}`),
  createProperty: (body: PropertyIn) =>
    request<Property>("/properties", { method: "POST", body: JSON.stringify(body) }),
  reestimate: (id: string) => request<Property>(`/properties/${id}/reestimate`, { method: "POST" }),
  updateProperty: (id: string, body: PropertyUpdate) =>
    request<Property>(`/properties/${id}`, { method: "PUT", body: JSON.stringify(body) }),
  trend: (id: string) => request<TrendReport>(`/properties/${id}/trend`),
  reportUrl: (id: string) => withToken(`${BASE}/properties/${id}/report.pdf`),
  deleteProperty: (id: string) => request<{ deleted: boolean }>(`/properties/${id}`, { method: "DELETE" }),
  dvfStatus: () => request<DvfStatus>("/dvf/status"),
  dvfIngest: () => request<{ started: boolean; message: string }>("/dvf/ingest", { method: "POST" }),
  validation: (n: number) => request<ValidationReport>(`/validation?n=${n}`),
  hedonicModel: () => request<HedonicModelInfo>("/models/hedonic"),
  hedonicTrain: () => request<{ started: boolean; message: string }>("/models/hedonic/train", { method: "POST" }),
  mlModel: () => request<MlModelInfo>("/models/ml"),
  mlTrain: () => request<{ started: boolean; message: string }>("/models/ml/train", { method: "POST" }),
  getWeights: () => request<Weights>("/settings/weights"),
  putWeights: (w: Weights) => request<Weights>("/settings/weights", { method: "PUT", body: JSON.stringify(w) }),
  marketSignal: (id: string) => request<MarketSignal>(`/properties/${id}/market-signal`),
  listListings: (id: string) => request<Listing[]>(`/properties/${id}/listings`),
  environmentHighlights: (id: string) => request<{ available: boolean; created_at?: string; highlights: { key: string; text: string; distance_m: number; source: string }[] }>(`/properties/${id}/environment/highlights`),
  createListing: (id: string, body: { style: ListingStyle; extra_facts: string | null; include_price: boolean; use_environment: boolean }) =>
    request<Listing>(`/properties/${id}/listings`, { method: "POST", body: JSON.stringify(body) }),
  deleteListing: (id: string, lid: string) => request<{ deleted: boolean }>(`/properties/${id}/listings/${lid}`, { method: "DELETE" }),
  listPhotos: (id: string) => request<Photo[]>(`/properties/${id}/photos`),
  reorderPhotos: (id: string, ids: string[]) => request<Photo[]>(`/properties/${id}/photos/order`, { method: "PUT", body: JSON.stringify({ ids }) }),
  setCoverPhoto: (photoId: string) => request<Photo[]>(`/photos/${photoId}/cover`, { method: "POST" }),
  retouchPhoto: (photoId: string) => request<Photo>(`/photos/${photoId}/retouch`, { method: "POST" }),
  photoExportUrl: (photoId: string, version: "retouched" | "original" = "retouched") => withToken(`${BASE}/photos/${photoId}/export.jpg?version=${version}`),
  deletePhoto: (photoId: string) => request<{ deleted: boolean }>(`/photos/${photoId}`, { method: "DELETE" }),
  dossier: (id: string) => request<Dossier>(`/properties/${id}/dossier`),
  overrideItem: (id: string, key: string, body: { status_override: "non_applicable" | null; note?: string | null }) =>
    request<Dossier>(`/properties/${id}/dossier/${key}`, { method: "PUT", body: JSON.stringify(body) }),
  getDocument: (did: string) => request<SaleDocument>(`/documents/${did}`),
  reocrDocument: (did: string) => request<SaleDocument>(`/documents/${did}/reocr`, { method: "POST" }),
  validateDocument: (did: string, fields: OcrResult, validated = true) =>
    request<SaleDocument>(`/documents/${did}/validate`, { method: "PUT", body: JSON.stringify({ fields, validated }) }),
  deleteDocument: (did: string) => request<{ deleted: boolean }>(`/documents/${did}`, { method: "DELETE" }),
  getTarget: (id: string) => request<TargetResponse>(`/properties/${id}/target`),
  risks: (id: string) => request<Risks>(`/properties/${id}/risks`),
  iapIntent: (propertyId: string) => request<{ ok: boolean; product_id: string }>("/iap/intents", { method: "POST", body: JSON.stringify({ property_id: propertyId }) }),
  iapClaim: (propertyId: string) => request<{ unlocked: boolean; pending?: boolean; message?: string }>("/iap/claim", { method: "POST", body: JSON.stringify({ property_id: propertyId }) }),
  putTarget: (id: string, target_price: number | null) =>
    request<TargetResponse>(`/properties/${id}/target`, { method: "PUT", body: JSON.stringify({ target_price }) }),
  notaireUrl: (id: string) => withToken(`${BASE}/properties/${id}/notaire.pdf`),
  alerts: () => request<AlertsResponse>("/alerts"),
  nextSteps: () => request<{ properties: PropertyNextSteps[] }>("/next-steps"),
  propertyNextSteps: (id: string) => request<PropertyNextSteps>(`/properties/${id}/next-steps`),
  packStatus: (id: string) => request<PackStatus>(`/properties/${id}/pack/status`),
  environment: (id: string, refresh = false) => request<EnvironmentResult>(`/properties/${id}/environment${refresh ? "?refresh=true" : ""}`),
  /** Orthophoto IGN + parcellaire (WMS Géoplateforme) centrée sur le bien — rendu statique, sans clé. */
  environmentMapUrl: (lon: number, lat: number, zoomM = 130, w = 640, h = 400) => {
    const dLat = zoomM / 111_320;
    const dLon = dLat / Math.cos((lat * Math.PI) / 180) * (w / h);
    return `https://data.geopf.fr/wms-r/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=ORTHOIMAGERY.ORTHOPHOTOS,CADASTRALPARCELS.PARCELLAIRE_EXPRESS&STYLES=&CRS=EPSG:4326&BBOX=${lat - dLat},${lon - dLon},${lat + dLat},${lon + dLon}&WIDTH=${w}&HEIGHT=${h}&FORMAT=image/png`;
  },
  redeemPromo: (code: string) => request<{ unlocked: boolean; code: string }>(`/promo/redeem`, { method: "POST", body: JSON.stringify({ code }) }),
  packCheckout: (id: string, return_url: string) =>
    request<{ order_id: string; checkout_url: string }>(`/properties/${id}/pack/checkout`, { method: "POST", body: JSON.stringify({ return_url }) }),
  packPdfUrl: (id: string, style: ListingStyle) => withToken(`${BASE}/properties/${id}/pack.pdf?style=${style}`),
};

export interface HedonicModelInfo {
  available: boolean;
  training: boolean;
  name?: string;
  trained_at?: string | null;
  n?: number;
  coefficients?: Record<string, number>;
  in_sample?: { n: number; mape: number; median_ape: number; within_15pct: number; r2_log: number | null } | null;
  holdout?: { n: number; mape: number; median_ape: number; within_15pct: number; r2_log: number | null; test_year: number } | null;
  holdout_local?: {
    n: number; mape: number; median_ape: number; within_15pct: number; r2_log: number | null; test_year: number;
    without_local?: { n: number; mape: number; median_ape: number; within_15pct: number; r2_log: number | null };
  } | null;
  communes_with_effect?: number;
}

// ---- Formatting helpers (fr-FR) ----
const NBSP = "\u202F";

export function formatInt(n: number): string {
  const rounded = Math.round(n);
  const sign = rounded < 0 ? "-" : "";
  const digits = Math.abs(rounded).toString();
  return sign + digits.replace(/\B(?=(\d{3})+(?!\d))/g, NBSP);
}

export function formatEuro(n: number): string {
  return `${formatInt(n)}${NBSP}€`;
}

export function formatK(n: number): string {
  if (Math.abs(n) >= 1_000_000) {
    const m = n / 1_000_000;
    return `${m.toFixed(m >= 10 ? 1 : 2).replace(".", ",")}${NBSP}M€`;
  }
  return `${formatInt(n / 1000)}${NBSP}k€`;
}

export function formatPct(p: number, digits = 0): string {
  const v = p * 100;
  const s = v.toFixed(digits).replace(".", ",");
  return `${v > 0 ? "+" : ""}${s}${NBSP}%`;
}

const MONTHS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."];

export function formatMonth(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return `${MONTHS[d.getMonth()]} ${d.getFullYear()}`;
}

export function formatDistance(m: number): string {
  if (m < 1000) return `${Math.round(m)}${NBSP}m`;
  return `${(m / 1000).toFixed(1).replace(".", ",")}${NBSP}km`;
}

export const CONDITION_LABELS: Record<Condition, string> = {
  a_renover: "À rénover",
  travaux: "Travaux",
  correct: "Correct",
  bon: "Bon état",
  tres_bon: "Très bon état",
  neuf_renove: "Neuf / rénové",
};

export const TYPE_LABELS: Record<PropertyType, string> = {
  appartement: "Appartement",
  maison: "Maison",
};

// ---------------- Auth ----------------
export interface AuthUser {
  id: string;
  email: string;
  created_at: string;
}
export interface AuthResponse {
  access_token: string;
  token_type: "bearer";
  user: AuthUser;
}
export const authApi = {
  register: (email: string, password: string) =>
    request<AuthResponse>("/auth/register", { method: "POST", body: JSON.stringify({ email, password }) }),
  login: (email: string, password: string) =>
    request<AuthResponse>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  me: () => request<AuthUser>("/auth/me"),
  changePassword: (current_password: string, new_password: string) =>
    request<{ ok: boolean }>("/auth/change-password", { method: "POST", body: JSON.stringify({ current_password, new_password }) }),
  forgotPassword: (email: string, origin: string) =>
    request<{ ok: boolean; message: string }>("/auth/forgot-password", { method: "POST", body: JSON.stringify({ email, origin }) }),
  resetPassword: (token_or_code: string, new_password: string) =>
    request<AuthResponse & { ok: boolean }>("/auth/reset-password", { method: "POST", body: JSON.stringify({ token_or_code, new_password }) }),
  deleteAccount: (password: string) =>
    request<{ ok: boolean }>("/auth/account", { method: "DELETE", body: JSON.stringify({ password }) }),
};
