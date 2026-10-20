import { useLocalSearchParams } from "expo-router";

import { CommunePage } from "@/src/web/PricePages";

/** URL : /prix-immobilier/41/41061-cormeray (INSEE + slug décoratif) ou /prix-immobilier/41/cormeray (slug seul, résolu par l'API). */
export default function Page() {
  const { dept, commune } = useLocalSearchParams<{ dept: string; commune: string }>();
  const raw = String(commune ?? "");
  const insee = /^\d/.test(raw) ? raw.split("-")[0] : raw;
  return <CommunePage dept={String(dept ?? "").toUpperCase()} insee={insee} />;
}
