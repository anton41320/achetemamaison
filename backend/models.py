from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any, Literal, Optional

from bson import ObjectId
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator


def _coerce_object_id(v: Any) -> str:
    if isinstance(v, ObjectId):
        return str(v)
    return v


PyObjectId = Annotated[str, BeforeValidator(_coerce_object_id)]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BaseDocument(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: Optional[PyObjectId] = Field(default=None, alias="_id")

    def to_mongo(self) -> dict:
        data = self.model_dump(by_alias=True, exclude_none=True)
        data.pop("_id", None)
        return data

    @classmethod
    def from_mongo(cls, doc: dict):
        return cls.model_validate(doc)


PropertyType = Literal["appartement", "maison"]
Condition = Literal["a_renover", "travaux", "correct", "bon", "tres_bon", "neuf_renove"]


class Features(BaseModel):
    # Extérieur
    pool: Optional[Literal["aucune", "hors_sol", "enterree"]] = None
    fenced: Optional[bool] = None
    motorized_gate: Optional[bool] = None
    terrace: Optional[bool] = None
    garage: Optional[Literal["aucun", "un", "deux_plus"]] = None
    outbuilding: Optional[bool] = None
    orientation: Optional[Literal["nord", "est", "sud", "ouest", "sud_ouest", "sud_est", "nord_est", "nord_ouest"]] = None
    # Configuration
    single_storey: Optional[bool] = None
    basement: Optional[bool] = None
    convertible_attic: Optional[bool] = None
    pantry: Optional[bool] = None  # cellier (maison)
    master_suite: Optional[bool] = None  # suite parentale (maison)
    master_suite_dressing: Optional[bool] = None
    master_suite_bathroom: Optional[bool] = None  # salle d'eau attenante
    master_suite_wc: Optional[bool] = None
    dressing: Optional[bool] = None  # dressing indépendant (maison)
    bathrooms: Optional[int] = Field(default=None, ge=0, le=10)
    # Confort / énergie
    heating: Optional[Literal["pompe_a_chaleur", "gaz", "electrique", "fioul", "bois", "autre"]] = None
    sanitation: Optional[Literal["tout_a_l_egout", "fosse_septique", "fosse_toutes_eaux", "microstation"]] = None
    dpe: Optional[Literal["A", "B", "C", "D", "E", "F", "G"]] = None
    double_glazing: Optional[bool] = None
    air_conditioning: Optional[bool] = None
    solar_panels: Optional[bool] = None
    # Appartement
    floor: Optional[int] = Field(default=None, ge=0, le=60)
    elevator: Optional[bool] = None
    balcony: Optional[bool] = None
    parking: Optional[Literal["aucun", "exterieur", "interieur"]] = None
    cellar: Optional[bool] = None
    caretaker: Optional[bool] = None  # gardien / concierge
    condo_fees: Optional[float] = Field(default=None, ge=0, le=5000)  # charges mensuelles de copropriété (€)
    heating_mode: Optional[Literal["collectif", "individuel"]] = None
    underfloor_heating: Optional[bool] = None  # chauffage au sol

    @field_validator("parking", mode="before")
    @classmethod
    def _legacy_parking(cls, v: Any) -> Any:
        if isinstance(v, bool):  # stored before parking became exterior / interior
            return "exterieur" if v else "aucun"
        return v


class PropertyIn(BaseModel):
    address_label: str
    lat: float
    lon: float
    code_commune: str
    commune: str
    postcode: str
    property_type: PropertyType
    surface: float = Field(gt=8, lt=1000)
    rooms: int = Field(ge=1, le=30)
    bedrooms: int = Field(ge=0, le=20)
    year_built: Optional[int] = Field(default=None, ge=1500, le=2030)
    condition: Condition = "correct"
    land_surface: Optional[float] = Field(default=None, ge=0, le=100000)
    features: Features = Field(default_factory=Features)
    # Legacy Phase 2 fields (kept for stored documents)
    floor: Optional[int] = None
    has_elevator: Optional[bool] = None
    has_parking: Optional[bool] = None
    has_outdoor: Optional[bool] = None
    dpe: Optional[str] = None


class PropertyUpdate(BaseModel):
    surface: Optional[float] = Field(default=None, gt=8, lt=1000)
    rooms: Optional[int] = Field(default=None, ge=1, le=30)
    bedrooms: Optional[int] = Field(default=None, ge=0, le=20)
    year_built: Optional[int] = Field(default=None, ge=1500, le=2030)
    condition: Optional[Condition] = None
    land_surface: Optional[float] = Field(default=None, ge=0, le=100000)
    features: Optional[Features] = None


class Adjustment(BaseModel):
    key: str
    label: str
    pct: float
    amount: float


class MarketLevel(BaseModel):
    label: str
    radius_m: Optional[int] = None
    count: int
    median_pm2: Optional[float] = None


class Comparable(BaseModel):
    date: str
    distance_m: int
    surface: float
    rooms: Optional[int] = None
    price: float
    price_m2: float
    land_surface: Optional[float] = None
    commune: str
    population: Optional[int] = None
    property_type: str
    weight: float


class ConfidenceDetail(BaseModel):
    key: str
    label: str
    score: float
    max_score: float
    hint: str


class Confidence(BaseModel):
    score: int
    level: Literal["eleve", "moyen", "faible"]
    n_comparables: int
    dispersion_pct: float
    median_age_months: int
    radius_label: str
    details: list[ConfidenceDetail]


class HedonicFactor(BaseModel):
    key: str
    label: str
    pct: float
    detail: str
    learned: bool = True


class HedonicResult(BaseModel):
    model_version: str
    value: float
    low: float
    high: float
    price_m2: float
    reference_value: float
    reference_label: str
    factors: list[HedonicFactor]
    delta_vs_comparables_pct: float
    agreement: Literal["convergent", "ecart_modere", "divergent"]
    model_median_ape: Optional[float] = None
    model_n: int


class MlFactor(BaseModel):
    key: str
    label: str
    pct: float


class MlResult(BaseModel):
    model_version: str
    promoted: bool
    value: float
    low: float
    high: float
    price_m2: float
    reference_value: float
    factors: list[MlFactor]
    model_median_ape: Optional[float] = None
    baseline_median_ape: Optional[float] = None


class MarketEstimate(BaseModel):
    value: float
    low: float
    high: float
    price_m2: float
    label: str
    count: int


class Estimation(BaseModel):
    method: str = "comparables_dvf_v1"
    created_at: datetime = Field(default_factory=utcnow)
    value: float
    low: float
    high: float
    price_m2: float
    base_price_m2: float
    confidence: Confidence
    insufficient_data: bool
    notes: list[str]
    adjustments: list[Adjustment]
    market: list[MarketLevel]
    comparables: list[Comparable]
    hedonic: Optional[HedonicResult] = None
    ml: Optional[MlResult] = None
    market_estimate: Optional[MarketEstimate] = None


class Weights(BaseModel):
    comparables: float = Field(default=50, ge=0, le=100)
    hedonic: float = Field(default=30, ge=0, le=100)
    market: float = Field(default=20, ge=0, le=100)
    ml: float = Field(default=0, ge=0, le=100)


class ListingRequest(BaseModel):
    style: Literal["sobre", "chaleureux", "premium", "familial"] = "sobre"
    extra_facts: Optional[str] = Field(default=None, max_length=1200)
    include_price: bool = True


class ListingDoc(BaseDocument):
    property_id: str
    style: str
    title: str
    hook: str
    description: str
    highlights: list[str]
    extra_facts: Optional[str] = None
    model: str
    created_at: datetime = Field(default_factory=utcnow)


class PhotoDoc(BaseDocument):
    property_id: str
    original_path: str
    original_mime: str
    original_size: int
    retouched_path: Optional[str] = None
    retouched_mime: Optional[str] = None
    status: Literal["original", "processing", "done", "error"] = "original"
    error: Optional[str] = None
    model: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)
    retouched_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None


class PropertyDoc(BaseDocument):
    address_label: str
    lat: float
    lon: float
    code_commune: str
    commune: str
    postcode: str
    property_type: PropertyType
    surface: float
    rooms: int
    bedrooms: int
    year_built: Optional[int] = None
    condition: Condition
    land_surface: Optional[float] = None
    features: Features = Field(default_factory=Features)
    floor: Optional[int] = None
    has_elevator: Optional[bool] = None
    has_parking: Optional[bool] = None
    has_outdoor: Optional[bool] = None
    dpe: Optional[str] = None
    target_price: Optional[float] = None
    estimation: Optional[Estimation] = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    deleted_at: Optional[datetime] = None



class OcrResult(BaseModel):
    document_type: str
    title: str
    issuer: Optional[str] = None
    document_date: Optional[str] = None
    validity_date: Optional[str] = None
    address_found: Optional[str] = None
    key_fields: list[dict] = []
    warnings: list[str] = []
    summary: str = ""
    confidence: float = 0.0


class DocumentDoc(BaseDocument):
    property_id: str
    item_key: str
    file_path: str
    mime: str
    filename: str
    size: int
    ocr_status: Literal["pending", "done", "error", "locked"] = "pending"
    ocr: Optional[OcrResult] = None
    ocr_error: Optional[str] = None
    validated: bool = False
    validated_fields: Optional[OcrResult] = None
    expiry_date: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)
    validated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None


class DocumentValidate(BaseModel):
    fields: OcrResult
    validated: bool = True


class ChecklistOverride(BaseModel):
    status_override: Optional[Literal["non_applicable"]] = None
    note: Optional[str] = Field(default=None, max_length=300)


class TargetPriceIn(BaseModel):
    target_price: Optional[float] = Field(default=None, ge=10_000, le=20_000_000)
