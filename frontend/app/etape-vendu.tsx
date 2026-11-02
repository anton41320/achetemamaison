import { StepPage } from "@/src/web/StepPage";
import { stepBySlug } from "@/src/web/stepContent";

export default function Page() {
  return <StepPage step={stepBySlug("etape-vendu")} />;
}
