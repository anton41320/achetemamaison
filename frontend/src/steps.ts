import { NextStep, PropertyNextSteps } from "@/src/api";

export const STAGES = ["Estimation", "Mise en vente", "Vendu"] as const;
export type Stage = 0 | 1 | 2;

/** Route of each step page of the funnel. */
export function stepRoute(propertyId: string, stage: Stage): string {
  return stage === 0 ? `/property/${propertyId}` : stage === 1 ? `/property/${propertyId}/vente` : `/property/${propertyId}/vendu`;
}

/** Stage of the sale derived from the server-side next steps: prix fixé → mise en vente ; dossier complet → vendu. */
export function stageOf(ns: PropertyNextSteps | null | undefined): { stage: Stage; cta: { label: string; route: string } | null; urgent: boolean } {
  if (!ns) return { stage: 0, cta: null, urgent: false };
  const by = (k: NextStep["key"]) => ns.steps.find((s) => s.key === k);
  const target = by("target");
  const dossier = by("dossier");
  if (target && !target.done) {
    const features = by("features");
    return { stage: 0, cta: { label: features && !features.done ? `${features.label}, puis fixer votre prix de vente` : "Fixer votre prix de vente", route: target.route }, urgent: false };
  }
  if (dossier && !dossier.done) {
    const pending = (["photos", "listing", "dossier"] as const).map(by).find((s) => s && !s.done)!;
    return { stage: 1, cta: { label: pending.label, route: pending.route }, urgent: pending.key === "dossier" && pending.label.startsWith("Renouveler") };
  }
  const exp = by("export");
  return { stage: 2, cta: exp ? { label: exp.label, route: exp.route } : null, urgent: false };
}
