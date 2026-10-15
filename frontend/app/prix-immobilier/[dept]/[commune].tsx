import { useLocalSearchParams } from "expo-router";

import { CommunePage } from "@/src/web/PricePages";

/** URL : /prix-immobilier/41/41061-cormeray → le code INSEE est la partie avant le premier tiret (le slug n'est que décoratif). */
export default function Page() {
  const { dept, commune } = useLocalSearchParams<{ dept: string; commune: string }>();
  const insee = String(commune ?? "").split("-")[0];
  return <CommunePage dept={String(dept ?? "").toUpperCase()} insee={insee} />;
}
