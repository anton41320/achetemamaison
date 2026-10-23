import { Pressable, Text, View } from "react-native";

import { Features, WORK_ITEM_LABELS, WorkItem } from "@/src/api";
import { Field, Segmented } from "@/src/components/Form";
import { fonts, makeStyles, radius, spacing } from "@/src/theme";

interface Props {
  value: Features;
  onChange: (f: Features) => void;
  testID?: string;
}

/** « Travaux à prévoir ? » — complète l'état général : oui/non, puis postes concernés (choix multiple) et précision si « Autre ». */
export function WorksForm({ value, onChange, testID = "works" }: Props) {
  const styles = useStyles();
  const items = value.works_items ?? [];
  const toggle = (w: WorkItem) => {
    const next = items.includes(w) ? items.filter((x) => x !== w) : [...items, w];
    onChange({ ...value, works_items: next, works_other: next.includes("autre") ? value.works_other : null });
  };
  return (
    <View style={styles.wrap}>
      <Segmented
        label="Travaux à prévoir ?"
        testID={`${testID}-segment`}
        value={value.works === null ? "na" : value.works ? "oui" : "non"}
        onChange={(v) => onChange({ ...value, works: v === "na" ? null : v === "oui", ...(v === "oui" ? {} : { works_items: [], works_other: null }) })}
        options={[{ value: "na", label: "Non renseigné" }, { value: "oui", label: "Oui" }, { value: "non", label: "Non" }]}
      />
      {value.works ? (
        <View style={styles.sub}>
          <Text style={styles.label}>Quels travaux ? (plusieurs choix possibles)</Text>
          <View style={styles.chips} testID={`${testID}-items`}>
            {(Object.keys(WORK_ITEM_LABELS) as WorkItem[]).map((w) => {
              const active = items.includes(w);
              return (
                <Pressable
                  key={w}
                  testID={`${testID}-item-${w}`}
                  accessibilityRole="checkbox"
                  accessibilityState={{ checked: active }}
                  onPress={() => toggle(w)}
                  style={[styles.chip, active && styles.chipActive]}
                >
                  <Text style={[styles.chipLabel, active && styles.chipLabelActive]}>{WORK_ITEM_LABELS[w]}</Text>
                </Pressable>
              );
            })}
          </View>
          {items.includes("autre") ? (
            <Field
              label="Précisez les travaux"
              testID={`${testID}-other`}
              placeholder="Ex. : menuiseries, isolation des combles…"
              maxLength={200}
              value={value.works_other ?? ""}
              onChangeText={(t) => onChange({ ...value, works_other: t.trim() === "" ? null : t })}
            />
          ) : null}
        </View>
      ) : null}
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  wrap: { gap: spacing.md },
  sub: { paddingLeft: spacing.lg, gap: spacing.sm },
  label: { fontFamily: fonts.medium, fontSize: 14, color: colors.onSurfaceSecondary },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  chip: { minHeight: 40, paddingHorizontal: spacing.lg, justifyContent: "center", borderRadius: radius.pill, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surfaceSecondary },
  chipActive: { backgroundColor: colors.brandPrimary, borderColor: colors.brandPrimary },
  chipLabel: { fontFamily: fonts.medium, fontSize: 14, color: colors.onSurfaceSecondary },
  chipLabelActive: { color: colors.onBrandPrimary },
}));
