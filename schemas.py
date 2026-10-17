# schemas.py
from typing import Literal
from pydantic import BaseModel, Field

# 1. Je définis les catégories strictes autorisées (issues des données de Seattle 2016)
VALID_PRIMARY_TYPES = Literal[
    "Hotel",
    "Large Office",
    "Small- and Mid-Sized Office",
    "Retail Store",
    "Warehouse",
    "K-12 School",
    "Mixed Use Property",
    "Worship Facility",
    "Medical Office",
    "Other",
]

VALID_BUILDING_TYPES = Literal[
    "NonResidential", "Nonresidential COS", "SPS-District K-12", "Campus"
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
    "DELRIDGE",
]


class BuildingInput(BaseModel):
  # Je contrôle les caractéristiques dimensionnelles avec les bornes métier de mon étude
  PropertyGFATotal: float = Field(
      ...,
      ge=100.0,
      le=10_000_000.0,
      description=(
          "Surface totale brute du bâtiment (en sq ft, min: 100, max:"
          " 10 000 000)"
      ),
  )
  YearBuilt: int = Field(
      ...,
      ge=1900,
      le=2026,
      description="Année de construction (entre 1900 et 2026)",
  )
  NumberofBuildings: int = Field(
      default=1,
      ge=1,
      le=10,
      description=(
          "Nombre de bâtiments sur la parcelle (1 à 10 max, hors méga-campus)"
      ),
  )
  NumberofFloors: int = Field(
      default=1,
      ge=1,
      le=76,
      description=(
          "Nombre d'étages (1 à 76 max, hauteur du Columbia Center à Seattle)"
      ),
  )
  PropertyGFAParking: float = Field(
      default=0.0,
      ge=0.0,
      le=5_000_000.0,
      description="Surface du parking (en sq ft, min: 0)",
  )
  PropertyGFABuilding: float = Field(
      default=0.0,
      ge=0.0,
      le=10_000_000.0,
      description="Surface bâtie hors parking (en sq ft, min: 0)",
  )
  LargestPropertyUseTypeGFA: float = Field(
      default=0.0,
      ge=0.0,
      le=10_000_000.0,
      description="Surface de l'activité principale (en sq ft, min: 0)",
  )

  # Je contrôle les catégories qualitatives via mes listes blanches
  PrimaryPropertyType: VALID_PRIMARY_TYPES = Field(
      default="Hotel", description="Usage principal du bâtiment"
  )
  BuildingType: VALID_BUILDING_TYPES = Field(
      default="NonResidential", description="Type de structure non résidentielle"
  )
  Neighborhood: VALID_NEIGHBORHOODS = Field(
      default="DOWNTOWN", description="Quartier de Seattle"
  )

  # Je contrôle les indicateurs binaires d'équipement énergétique (0 ou 1)
  HasGas: int = Field(
      default=0,
      ge=0,
      le=1,
      description="Raccordement au gaz naturel (0 = Non, 1 = Oui)",
  )
  HasSteam: int = Field(
      default=0,
      ge=0,
      le=1,
      description="Raccordement au réseau de vapeur (0 = Non, 1 = Oui)",
  )