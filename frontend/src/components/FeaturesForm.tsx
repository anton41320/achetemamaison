import { Text, View } from "react-native";

import { Features, PropertyType } from "@/src/api";
import { Segmented, Stepper } from "@/src/components/Form";
import { fonts, makeStyles, spacing } from "@/src/theme";

interface Props {
  propertyType: PropertyType;
  value: Features;
  onChange: (f: Features) => void;
}

type TriKey = {
  [K in keyof Features]: Features[K] extends boolean | null ? K : never;
}[keyof Features];

const TRI = [
  { value: "na", label: "Non renseigné" },
  { value: "oui", label: "Oui" },
  { value: "non", label: "Non" },
] as const;

export function FeaturesForm({ propertyType, value, onChange }: Props) {
  const styles = useStyles();
  const maison = propertyType === "maison";
  const set = <K extends keyof Features>(k: K, v: Features[K]) => onChange({ ...value, [k]: v });
  const tri = (k: TriKey) => (value[k] === null ? "na" : value[k] ? "oui" : "non");
  const setTri = (k: TriKey) => (v: string) => set(k, v === "na" ? null : v === "oui");
  const Yn = ({ k, label, testID }: { k: TriKey; label: string; testID: string }) => (
    <Segmented label={label} testID={testID} value={tri(k)} onChange={setTri(k)} options={[...TRI]} />
  );

  return (
    <View style={styles.wrap}>
      <Text style={styles.section}>Extérieur</Text>
      {maison ? (
        <Segmented
          label="Piscine"
          testID="feat-pool"
          scroll
          value={value.pool ?? "na"}
          onChange={(v) => set("pool", v === "na" ? null : (v as Features["pool"]))}
          options={[{ value: "na", label: "—" }, { value: "aucune", label: "Aucune" }, { value: "hors_sol", label: "Hors-sol" }, { value: "enterree", label: "Enterrée" }]}
        />
      ) : null}
      {maison ? <Yn k="fenced" label="Terrain clos" testID="feat-fenced" /> : null}
      {maison ? <Yn k="motorized_gate" label="Portail motorisé" testID="feat-gate" /> : null}
      <Yn k="terrace" label="Terrasse" testID="feat-terrace" />
      <Segmented
        label="Garage"
        testID="feat-garage"
        scroll
        value={value.garage ?? "na"}
        onChange={(v) => set("garage", v === "na" ? null : (v as Features["garage"]))}
        options={[{ value: "na", label: "—" }, { value: "aucun", label: "Aucun" }, { value: "un", label: "1" }, { value: "deux_plus", label: "2+" }]}
      />
      {maison ? <Yn k="outbuilding" label="Dépendance / abri" testID="feat-outbuilding" /> : null}
      <Segmented
        label="Exposition principale"
        testID="feat-orientation"
        scroll
        value={value.orientation ?? "na"}
        onChange={(v) => set("orientation", v === "na" ? null : (v as Features["orientation"]))}
        options={[
          { value: "na", label: "—" }, { value: "sud", label: "Sud" }, { value: "sud_ouest", label: "Sud-Ouest" }, { value: "sud_est", label: "Sud-Est" },
          { value: "ouest", label: "Ouest" }, { value: "est", label: "Est" }, { value: "nord", label: "Nord" }, { value: "nord_ouest", label: "Nord-Ouest" }, { value: "nord_est", label: "Nord-Est" },
        ]}
      />

      <Text style={styles.section}>Configuration</Text>
      {maison ? <Yn k="single_storey" label="Plain-pied" testID="feat-single-storey" /> : null}
      {maison ? <Yn k="basement" label="Sous-sol / cave" testID="feat-basement" /> : null}
      {maison ? <Yn k="convertible_attic" label="Combles aménageables" testID="feat-attic" /> : null}
      <Stepper label="Salles de bain" value={value.bathrooms ?? 1} onChange={(v) => set("bathrooms", v)} min={0} max={6} testID="feat-bathrooms" />
      {!maison ? <Stepper label="Étage" value={value.floor ?? 0} onChange={(v) => set("floor", v)} min={0} max={40} testID="feat-floor" /> : null}
      {!maison ? <Yn k="elevator" label="Ascenseur" testID="feat-elevator" /> : null}
      {!maison ? <Yn k="balcony" label="Balcon / terrasse" testID="feat-balcony" /> : null}
      {!maison ? <Yn k="parking" label="Parking / box" testID="feat-parking" /> : null}
      {!maison ? <Yn k="cellar" label="Cave" testID="feat-cellar" /> : null}

      <Text style={styles.section}>Confort & énergie</Text>
      <Segmented
        label="Chauffage"
        testID="feat-heating"
        scroll
        value={value.heating ?? "na"}
        onChange={(v) => set("heating", v === "na" ? null : (v as Features["heating"]))}
        options={[
          { value: "na", label: "—" }, { value: "pompe_a_chaleur", label: "Pompe à chaleur" }, { value: "gaz", label: "Gaz" },
          { value: "electrique", label: "Électrique" }, { value: "fioul", label: "Fioul" }, { value: "bois", label: "Bois / poêle" }, { value: "autre", label: "Autre" },
        ]}
      />
      <Segmented
        label="Classe DPE"
        testID="feat-dpe"
        scroll
        value={value.dpe ?? "na"}
        onChange={(v) => set("dpe", v === "na" ? null : (v as Features["dpe"]))}
        options={[{ value: "na", label: "—" }, ...(["A", "B", "C", "D", "E", "F", "G"] as const).map((d) => ({ value: d, label: d }))]}
      />
      <Yn k="double_glazing" label="Double vitrage" testID="feat-glazing" />
      <Yn k="air_conditioning" label="Climatisation" testID="feat-ac" />
      <Yn k="solar_panels" label="Panneaux solaires" testID="feat-solar" />
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  wrap: { gap: spacing.lg },
  section: { fontFamily: fonts.semibold, fontSize: 13, color: colors.muted, textTransform: "uppercase", letterSpacing: 0.6, marginTop: spacing.sm },
}));
