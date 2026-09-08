from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any, Literal, Optional

from bson import ObjectId
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


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
Condition = Literal["a_renover", "travaux", "correct", "bon", "neuf_renove"]


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
    # Phase 2 foundations (hedonic features) — stored, not yet used by the engine
    floor: Optional[int] = None
    has_elevator: Optional[bool] = None
    has_parking: Optional[bool] = None
    has_outdoor: Optional[bool] = None
    dpe: Optional[str] = None


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
    floor: Optional[int] = None
    has_elevator: Optional[bool] = None
    has_parking: Optional[bool] = None
    has_outdoor: Optional[bool] = None
    dpe: Optional[str] = None
    estimation: Optional[Estimation] = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    deleted_at: Optional[datetime] = None
