# service.py
import io
import json
from enum import Enum
from pathlib import Path
import attr
import numpy as np
import pandas as pd
import yaml
from pydantic import ValidationError
import bentoml
from bentoml.exceptions import InvalidArgument
from schemas import BuildingInput

# =====================================================================
# 1. CORRECTIF BENTOML 1.4 : INJECTION DU NOM MANQUANT AU BUILD
# =====================================================================
import bentoml._internal.bento.bento as bento_pkg

_orig_from_yaml_file = bento_pkg.BaseBentoInfo.from_yaml_file

@classmethod
def _safe_from_yaml_file(cls, stream):
    # Repositionnement au début si c'est un flux déjà ouvert
    if hasattr(stream, "seek"):
        try:
            stream.seek(0)
        except Exception:
            pass

    if hasattr(stream, "read"):
        content = stream.read()
    else:
        content = stream

    data = yaml.safe_load(content) or {}
    if isinstance(data, dict):
        if "name" not in data:
            data["name"] = data.get("entry_service") or "seattle_energy_predictor"
        if "version" not in data:
            data["version"] = "latest"

    # Si le flux provient d'un fichier réel sur le disque, on synchronise le fichier
    if hasattr(stream, "name") and isinstance(stream.name, str):
        try:
            with open(stream.name, "w", encoding="utf-8") as f_disk:
                yaml.dump(data, f_disk)
        except Exception:
            pass

    new_stream = io.StringIO(yaml.dump(data))
    return _orig_from_yaml_file(new_stream)

bento_pkg.BaseBentoInfo.from_yaml_file = _safe_from_yaml_file
if hasattr(bento_pkg, "BentoInfo"):
    bento_pkg.BentoInfo.from_yaml_file = _safe_from_yaml_file

# =====================================================================
# 2. CORRECTIF SWAGGER OPENAPI 3.0 (PYTHON 3.13)
# =====================================================================
import bentoml._internal.service.openapi.specification as bento_spec

def _clean_openapi(obj):
    if isinstance(obj, dict):
        cleaned = {}
        for k, v in obj.items():
            key = "not" if k == "not_" else k
            if v is None:
                continue
            if key in ("allOf", "anyOf", "oneOf"):
                if not isinstance(v, list) or len(v) == 0:
                    continue
            cleaned[key] = _clean_openapi(v)
        return cleaned
    elif isinstance(obj, list):
        return [_clean_openapi(x) for x in obj if x is not None]
    elif attr.has(obj.__class__):
        return _clean_openapi(attr.asdict(obj))
    elif isinstance(obj, Enum):
        return obj.value
    elif hasattr(obj, "asdict"):
        return _clean_openapi(obj.asdict())
    return obj

def _safe_asdict(self):
    try:
        raw = bento_spec.bentoml_cattr.unstructure(self)
    except Exception:
        raw = attr.asdict(self)
    return _clean_openapi(raw)

bento_spec.OpenAPISpecification.asdict = _safe_asdict

_orig_json_default = json.JSONEncoder.default
def _safe_json_default(self, o):
    try:
        return _clean_openapi(o)
    except Exception:
        return _orig_json_default(self, o)

json.JSONEncoder.default = _safe_json_default
# =====================================================================


@bentoml.service(
    name="seattle_energy_predictor",
    resources={"cpu": "1"}
)
class SeattleEnergyService:
    def __init__(self):
        # Chargement du pipeline complet Scikit-Learn
        self.pipeline = bentoml.sklearn.load_model("seattle_energy_pipeline:latest")

    @bentoml.api
    def predict(
        self,
        PropertyGFATotal: float = 88434.0,
        YearBuilt: int = 1927,
        NumberofBuildings: int = 1,
        NumberofFloors: int = 12,
        PropertyGFAParking: float = 0.0,
        PropertyGFABuilding: float = 88434.0,
        LargestPropertyUseTypeGFA: float = 88434.0,
        PrimaryPropertyType: str = "Hotel",
        BuildingType: str = "NonResidential",
        Neighborhood: str = "DOWNTOWN",
        HasGas: int = 1,
        HasSteam: int = 1
    ) -> dict:
        # 1. Validation stricte via Pydantic
        try:
            validated = BuildingInput(
                PropertyGFATotal=PropertyGFATotal,
                YearBuilt=YearBuilt,
                NumberofBuildings=NumberofBuildings,
                NumberofFloors=NumberofFloors,
                PropertyGFAParking=PropertyGFAParking,
                PropertyGFABuilding=PropertyGFABuilding,
                LargestPropertyUseTypeGFA=LargestPropertyUseTypeGFA,
                PrimaryPropertyType=PrimaryPropertyType,
                BuildingType=BuildingType,
                Neighborhood=Neighborhood,
                HasGas=HasGas,
                HasSteam=HasSteam
            )
        except ValidationError as e:
            raise InvalidArgument(f"Données rejetées par Pydantic : {e.errors()}")

        data = validated.model_dump()

        # 2. Feature Engineering calculé en direct
        building_age = 2016 - data['YearBuilt']
        parking_ratio = (data['PropertyGFAParking'] / data['PropertyGFATotal']) if data['PropertyGFATotal'] > 0 else 0.0

        building_gfa = data['PropertyGFABuilding'] if data['PropertyGFABuilding'] > 0 else data['PropertyGFATotal']
        building_ratio = (building_gfa / data['PropertyGFATotal']) if data['PropertyGFATotal'] > 0 else 1.0
        gfa_per_floor = building_gfa / max(data['NumberofFloors'], 1)

        largest_gfa = data['LargestPropertyUseTypeGFA'] if data['LargestPropertyUseTypeGFA'] > 0 else data['PropertyGFATotal']
        largest_use_ratio = (largest_gfa / data['PropertyGFATotal']) if data['PropertyGFATotal'] > 0 else 1.0

        # 3. DataFrame ordonné pour Scikit-Learn
        input_row = pd.DataFrame([{
            'PropertyGFATotal': float(data['PropertyGFATotal']),
            'BuildingAge': float(building_age),
            'NumberofBuildings': float(data['NumberofBuildings']),
            'NumberofFloors': float(data['NumberofFloors']),
            'ParkingRatio': float(parking_ratio),
            'BuildingRatio': float(building_ratio),
            'GFAPerFloor': float(gfa_per_floor),
            'LargestUseRatio': float(largest_use_ratio),
            'PrimaryPropertyType': str(data['PrimaryPropertyType']),
            'BuildingType': str(data['BuildingType']),
            'Neighborhood': str(data['Neighborhood']),
            'HasGas': int(data['HasGas']),
            'HasSteam': int(data['HasSteam'])
        }])

        # 4. Inférence et reconversion exponentielle inverse en kBtu
        pred_log = self.pipeline.predict(input_row)[0]
        predicted_kbtu = float(np.expm1(pred_log))

        return {
            "status": "success",
            "building_type": data['PrimaryPropertyType'],
            "surface_sqft": float(data['PropertyGFATotal']),
            "predicted_energy_consumption_kBtu": round(predicted_kbtu, 2)
        }