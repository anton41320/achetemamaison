const BASE = `${process.env.EXPO_PUBLIC_BACKEND_URL}/api`;

export type PropertyType = "appartement" | "maison";
export type Condition = "a_renover" | "travaux" | "correct" | "bon" | "neuf_renove";
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
}

export interface Property extends PropertyIn {
  id: string;
  estimation: Estimation | null;
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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    let message = `Erreur ${res.status}`;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") message = body.detail;
      else if (Array.isArray(body?.detail)) message = body.detail.map((d: any) => d.msg).join(", ");
    } catch {
      // keep default
    }
    throw new Error(message);
  }
  return res.json() as Promise<T>;
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
  trend: (id: string) => request<TrendReport>(`/properties/${id}/trend`),
  reportUrl: (id: string) => `${BASE}/properties/${id}/report.pdf`,
  deleteProperty: (id: string) => request<{ deleted: boolean }>(`/properties/${id}`, { method: "DELETE" }),
  dvfStatus: () => request<DvfStatus>("/dvf/status"),
  dvfIngest: () => request<{ started: boolean; message: string }>("/dvf/ingest", { method: "POST" }),
  validation: (n: number) => request<ValidationReport>(`/validation?n=${n}`),
  hedonicModel: () => request<HedonicModelInfo>("/models/hedonic"),
  hedonicTrain: () => request<{ started: boolean; message: string }>("/models/hedonic/train", { method: "POST" }),
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
  neuf_renove: "Neuf / rénové",
};

export const CONFIDENCE_LABELS: Record<ConfidenceLevel, string> = {
  eleve: "Confiance élevée",
  moyen: "Confiance moyenne",
  faible: "Confiance faible",
};

export const TYPE_LABELS: Record<PropertyType, string> = {
  appartement: "Appartement",
  maison: "Maison",
};
