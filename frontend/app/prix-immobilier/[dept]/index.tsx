import { useLocalSearchParams } from "expo-router";

import { DeptPage } from "@/src/web/PricePages";

export default function Page() {
  const { dept } = useLocalSearchParams<{ dept: string }>();
  return <DeptPage dept={String(dept ?? "").toUpperCase()} />;
}
