# schemas.py
from typing import Literal
from pydantic import BaseModel, Field

# 1. Catégories strictes autorisées (issues des données de Seattle 2016)
VALID_PRIMARY_TYPES = Literal[
    "Hotel",
    "Large Office",
    "Small- and Mid-Sized Office",
    "Retail Store",
    "Warehouse",
    "K-12 School",
    "Medical Office",
    "Mixed Use Property",
    "Other"
]

VALID_BUILDING_TYPES = Literal[
    "NonResidential",
    "Nonresidential COS",
    "SPS-District K-12",
    "Campus"
]

VALID_NEIGHBORHOODS = Literal[
    "DOWNTOWN",
    "GREATER DUWAMISH",
    "LAKE UNION",
    "MAGNOLIA / QUEEN ANNE",
    "EAST",
    "NORTHEAST",
    "NORTHWEST",
    "CENTRAL",
    "BALLARD",
    "SOUTHWEST",
    "SOUTHEAST",
    "DELRIDGE"
]


class BuildingInput(BaseModel):
    # Caractéristiques dimensionnelles (avec bornes minimales et maximales)
    PropertyGFATotal: float = Field(
        ...,
        ge=100.0,
        le=10_000_000.0,
        description="Surface totale du bâtiment (en sq ft, min: 100, max: 10 000 000)"
    )
    YearBuilt: int = Field(
        ...,
        ge=1900,
        le=2026,
        description="Année de construction (entre 1900 et 2026)"
    )
    NumberofBuildings: int = Field(
        default=1,
        ge=1,
        le=50,
        description="Nombre de bâtiments sur la parcelle (1 à 50)"
    )
    NumberofFloors: int = Field(
        default=1,
        ge=1,
        le=120,
        description="Nombre d'étages (1 à 120)"
    )
    PropertyGFAParking: float = Field(
        default=0.0,
        ge=0.0,
        le=5_000_000.0,
        description="Surface de parking (en sq ft, min: 0)"
    )
    PropertyGFABuilding: float = Field(
        default=0.0,
        ge=0.0,
        le=10_000_000.0,
        description="Surface du bâtiment hors parking (en sq ft, min: 0)"
    )
    LargestPropertyUseTypeGFA: float = Field(
        default=0.0,
        ge=0.0,
        le=10_000_000.0,
        description="Surface du plus grand usage (en sq ft, min: 0)"
    )

    # Catégories qualitatives
    PrimaryPropertyType: VALID_PRIMARY_TYPES = Field(
        default="Hotel",
        description="Usage principal du bâtiment"
    )
    BuildingType: VALID_BUILDING_TYPES = Field(
        default="NonResidential",
        description="Type de structure"
    )
    Neighborhood: VALID_NEIGHBORHOODS = Field(
        default="DOWNTOWN",
        description="Quartier de Seattle"
    )

    # Énergies (variables binaires 0 ou 1)
    HasGas: int = Field(
        default=0,
        ge=0,
        le=1,
        description="Présence de gaz naturel (0 = Non, 1 = Oui)"
    )
    HasSteam: int = Field(
        default=0,
        ge=0,
        le=1,
        description="Raccordement au réseau de vapeur (0 = Non, 1 = Oui)"
    )