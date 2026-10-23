import { Text, View } from "react-native";

import { Features, PropertyType } from "@/src/api";
import { Field, Segmented, Stepper } from "@/src/components/Form";
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
      <Yn k="veranda" label="Véranda" testID="feat-veranda" />
      {value.veranda ? (
        <View style={styles.sub}>
          <Field
            label="Surface de la véranda"
            testID="feat-veranda-surface"
            placeholder="15"
            suffix="m²"
            keyboardType="number-pad"
            value={value.veranda_surface === null ? "" : String(value.veranda_surface)}
            onChangeText={(t) => {
              const n = Number(t.replace(/[^\d]/g, ""));
              set("veranda_surface", t.trim() === "" || Number.isNaN(n) || n === 0 ? null : Math.min(n, 200));
            }}
          />
          <Yn k="veranda_heated" label="Chauffée" testID="feat-veranda-heated" />
          <Yn k="veranda_air_conditioned" label="Climatisée" testID="feat-veranda-ac" />
        </View>
      ) : null}
      {maison ? (
        <Segmented
          label="Garage"
          testID="feat-garage"
          scroll
          value={value.garage ?? "na"}
          onChange={(v) => set("garage", v === "na" ? null : (v as Features["garage"]))}
          options={[{ value: "na", label: "—" }, { value: "aucun", label: "Aucun" }, { value: "un", label: "1" }, { value: "deux_plus", label: "2+" }]}
        />
      ) : (
        <Segmented
          label="Stationnement (parking, box, garage)"
          testID="feat-parking"
          scroll
          value={value.parking ?? "na"}
          onChange={(v) => set("parking", v === "na" ? null : (v as Features["parking"]))}
          options={[
            { value: "na", label: "—" },
            { value: "aucun", label: "Aucun" },
            { value: "exterieur", label: "Parking extérieur" },
            { value: "interieur", label: "Parking intérieur / box" },
            { value: "garage", label: "Garage fermé" },
          ]}
        />
      )}
      {maison ? <Yn k="outbuilding" label="Dépendance / abri" testID="feat-outbuilding" /> : null}
      {maison && value.outbuilding ? (
        <View style={styles.sub}>
          <Segmented
            label="Type de dépendance"
            testID="feat-outbuilding-type"
            scroll
            value={value.outbuilding_type ?? "na"}
            onChange={(v) => set("outbuilding_type", v === "na" ? null : (v as Features["outbuilding_type"]))}
            options={[
              { value: "na", label: "—" }, { value: "bureau", label: "Bureau" }, { value: "hangar", label: "Hangar" }, { value: "grange", label: "Grange" },
              { value: "abri_jardin", label: "Abri de jardin" }, { value: "pool_house", label: "Pool house" }, { value: "autre", label: "Autre" },
            ]}
          />
          <Field
            label="Surface de la dépendance"
            testID="feat-outbuilding-surface"
            placeholder="20"
            suffix="m²"
            keyboardType="number-pad"
            value={value.outbuilding_surface === null ? "" : String(value.outbuilding_surface)}
            onChangeText={(t) => {
              const n = Number(t.replace(/[^\d]/g, ""));
              set("outbuilding_surface", t.trim() === "" || Number.isNaN(n) || n === 0 ? null : Math.min(n, 2000));
            }}
          />
        </View>
      ) : null}
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
      {maison ? <Yn k="pantry" label="Cellier" testID="feat-pantry" /> : null}
      {maison ? <Yn k="dressing" label="Dressing indépendant" testID="feat-dressing" /> : null}
      <Stepper label="Salles de bain" value={value.bathrooms ?? 1} onChange={(v) => set("bathrooms", v)} min={0} max={6} testID="feat-bathrooms" />
      {!maison ? (
        <>
          <Stepper label="Étage de l’appartement" value={value.floor ?? 0} onChange={(v) => set("floor", v)} min={0} max={40} testID="feat-floor" />
          {(value.floor ?? 0) >= 1 ? <Yn k="top_floor" label="Dernier étage" testID="feat-top-floor" /> : null}
          <Yn k="elevator" label="Ascenseur" testID="feat-elevator" />
          <Yn k="balcony" label="Balcon / terrasse" testID="feat-balcony" />
          <Yn k="cellar" label="Cave" testID="feat-cellar" />

          <Text style={styles.section}>Copropriété</Text>
          <Field
            label="Charges mensuelles de copropriété"
            testID="feat-condo-fees"
            placeholder="150"
            suffix="€ / mois"
            keyboardType="number-pad"
            value={value.condo_fees === null ? "" : String(value.condo_fees)}
            onChangeText={(t) => {
              const n = Number(t.replace(/[^\d]/g, ""));
              set("condo_fees", t.trim() === "" || Number.isNaN(n) ? null : Math.min(n, 5000));
            }}
          />
          <Yn k="caretaker" label="Gardien / concierge" testID="feat-caretaker" />
        </>
      ) : null}
      {maison ? (
        <>
          <Text style={styles.section}>Chambres</Text>
          <Yn k="master_suite" label="Suite parentale" testID="feat-master-suite" />
          {value.master_suite ? (
            <View style={styles.sub}>
              <Yn k="master_suite_dressing" label="Avec dressing" testID="feat-master-dressing" />
              <Yn k="master_suite_bathroom" label="Avec salle d’eau" testID="feat-master-bathroom" />
              <Yn k="master_suite_wc" label="Avec WC" testID="feat-master-wc" />
            </View>
          ) : null}
        </>
      ) : null}

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
      {!maison ? (
        <>
          <Segmented
            label="Mode de chauffage"
            testID="feat-heating-mode"
            value={value.heating_mode ?? "na"}
            onChange={(v) => set("heating_mode", v === "na" ? null : (v as Features["heating_mode"]))}
            options={[{ value: "na", label: "—" }, { value: "collectif", label: "Collectif" }, { value: "individuel", label: "Individuel" }]}
          />
          <Yn k="underfloor_heating" label="Chauffage au sol" testID="feat-underfloor" />
        </>
      ) : null}
      <Segmented
        label="Classe DPE"
        testID="feat-dpe"
        scroll
        value={value.dpe ?? "na"}
        onChange={(v) => set("dpe", v === "na" ? null : (v as Features["dpe"]))}
        options={[{ value: "na", label: "—" }, ...(["A", "B", "C", "D", "E", "F", "G"] as const).map((d) => ({ value: d, label: d }))]}
      />
      {maison ? (
        <Segmented
          label="Assainissement"
          testID="feat-sanitation"
          scroll
          value={value.sanitation ?? "na"}
          onChange={(v) => set("sanitation", v === "na" ? null : (v as Features["sanitation"]))}
          options={[
            { value: "na", label: "—" }, { value: "tout_a_l_egout", label: "Tout-à-l’égout" }, { value: "fosse_septique", label: "Fosse septique" },
            { value: "fosse_toutes_eaux", label: "Fosse toutes eaux" }, { value: "microstation", label: "Micro-station" },
          ]}
        />
      ) : null}
      <Yn k="double_glazing" label="Double vitrage" testID="feat-glazing" />
      <Yn k="air_conditioning" label="Climatisation" testID="feat-ac" />
      <Segmented
        label="Cheminée / poêle"
        testID="feat-fireplace"
        value={value.fireplace === null ? "na" : value.fireplace === "aucune" ? "non" : "oui"}
        onChange={(v) => set("fireplace", v === "na" ? null : v === "non" ? "aucune" : value.fireplace && value.fireplace !== "aucune" ? value.fireplace : "insert")}
        options={[{ value: "na", label: "—" }, { value: "non", label: "Non" }, { value: "oui", label: "Oui" }]}
      />
      {value.fireplace && value.fireplace !== "aucune" ? (
        <View style={styles.sub}>
          <Segmented
            label="Type"
            testID="feat-fireplace-type"
            scroll
            value={value.fireplace}
            onChange={(v) => set("fireplace", v as Features["fireplace"])}
            options={[
              { value: "insert", label: "Insert" },
              { value: "foyer_ouvert", label: "Foyer ouvert" },
              { value: "poele_bois", label: "Poêle à bois" },
              { value: "poele_granules", label: "Poêle à granulés" },
            ]}
          />
        </View>
      ) : null}
      <Yn k="solar_panels" label="Panneaux solaires" testID="feat-solar" />
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  wrap: { gap: spacing.lg },
  section: { fontFamily: fonts.semibold, fontSize: 13, color: colors.muted, textTransform: "uppercase", letterSpacing: 0.6, marginTop: spacing.sm },
  sub: { paddingLeft: spacing.lg, gap: spacing.sm },
}));
