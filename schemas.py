# schemas.py
from pydantic import BaseModel, Field

class BuildingInput(BaseModel):
    PropertyGFATotal: float = Field(..., gt=100, description="Surface totale > 100 sq ft")
    YearBuilt: int = Field(..., ge=1900, le=2026, description="Année de construction")
    NumberofBuildings: int = Field(default=1, ge=1, le=50)
    NumberofFloors: int = Field(default=1, ge=1, le=120)
    PropertyGFAParking: float = Field(default=0.0, ge=0.0)
    PropertyGFABuilding: float = Field(default=0.0, ge=0.0)
    LargestPropertyUseTypeGFA: float = Field(default=0.0, ge=0.0)
    PrimaryPropertyType: str = Field(default="Hotel")
    BuildingType: str = Field(default="NonResidential")
    Neighborhood: str = Field(default="DOWNTOWN")
    HasGas: int = Field(default=0, ge=0, le=1)
    HasSteam: int = Field(default=0, ge=0, le=1)