# service.py
from datetime import datetime
from enum import Enum
import io
import json
import attr
import bentoml
import bentoml._internal.bento.bento as bento_pkg
import bentoml._internal.service.openapi.specification as bento_spec
from bentoml.exceptions import InvalidArgument
import numpy as np
import pandas as pd
from pydantic import ValidationError
from schemas import BuildingInput
import yaml


# =====================================================================
# 1. BENTOML 1.4 : INJECTION DU NOM MANQUANT AU BUILD
# =====================================================================

_orig_from_yaml_file = bento_pkg.BaseBentoInfo.from_yaml_file


@classmethod
def _safe_from_yaml_file(cls, stream):
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
# 2. CORRECTIF SWAGGER OPENAPI 3.0
# =====================================================================


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


@bentoml.service(name="seattle_energy_predictor", resources={"cpu": "1"})
class SeattleEnergyService:

    def __init__(self):
        # Je charge mon pipeline complet Scikit-Learn depuis le magasin BentoML
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
        HasSteam: int = 1,
    ) -> dict:
        # 1. Je valide les données d'entrée avec Pydantic et je détaille les erreurs éventuelles
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
                HasSteam=HasSteam,
            )
        except ValidationError as e:
            details = []
            for err in e.errors():
                field = ".".join(str(loc) for loc in err.get("loc", []))
                valeur = err.get("input")
                err_type = err.get("type", "")
                ctx = err.get("ctx", {})

                if "greater_than_equal" in err_type:
                    details.append(
                        f"[{field}] Valeur reçue : {valeur} -> la valeur minimale tolérée est {ctx.get('ge')}."
                    )
                elif "greater_than" in err_type:
                    details.append(
                        f"[{field}] Valeur reçue : {valeur} -> la valeur doit être strictement supérieure à {ctx.get('gt')}."
                    )
                elif "less_than_equal" in err_type:
                    details.append(
                        f"[{field}] Valeur reçue : {valeur} -> la valeur maximale tolérée est {ctx.get('le')}."
                    )
                elif "less_than" in err_type:
                    details.append(
                        f"[{field}] Valeur reçue : {valeur} -> la valeur doit être strictement inférieure à {ctx.get('lt')}."
                    )
                elif "literal_error" in err_type:
                    attendus = ctx.get("expected", "")
                    details.append(
                        f"[{field}] Valeur reçue : '{valeur}' non reconnue -> options valides : {attendus}."
                    )
                else:
                    details.append(
                        f"[{field}] Valeur reçue : {valeur} -> {err.get('msg')}."
                    )

            message_complet = "Données rejetées par l'API :\n" + "\n".join(details)
            raise InvalidArgument(message_complet)

        data = validated.model_dump()

        # 2. Je calcule mes variables de Feature Engineering en direct
        # Calcul dynamique de l'âge par rapport à l'année en cours (permet aux années >= 2016 de faire varier la prédiction)
        current_year = datetime.now().year
        building_age = max(current_year - data["YearBuilt"], 0)

        parking_ratio = (
            np.clip(data["PropertyGFAParking"] / data["PropertyGFATotal"], 0.0, 1.0)
            if data["PropertyGFATotal"] > 0
            else 0.0
        )

        building_gfa = (
            data["PropertyGFABuilding"]
            if data["PropertyGFABuilding"] > 0
            else max(data["PropertyGFATotal"] - data["PropertyGFAParking"], 0.0)
        )
        gfa_per_floor = building_gfa / max(data["NumberofFloors"], 1)

        largest_gfa = (
            data["LargestPropertyUseTypeGFA"]
            if data["LargestPropertyUseTypeGFA"] > 0
            else data["PropertyGFATotal"]
        )
        largest_use_ratio = (
            np.clip(largest_gfa / data["PropertyGFATotal"], 0.0, 1.0)
            if data["PropertyGFATotal"] > 0
            else 1.0
        )

        # 3. Je prépare le DataFrame avec mes 12 variables exactes (7 quantitatives + 5 qualitatives)
        input_row = pd.DataFrame([{
            "PropertyGFATotal": float(data["PropertyGFATotal"]),
            "NumberofBuildings": float(data["NumberofBuildings"]),
            "NumberofFloors": float(data["NumberofFloors"]),
            "BuildingAge": float(building_age),
            "ParkingRatio": float(parking_ratio),
            "GFAPerFloor": float(gfa_per_floor),
            "LargestUseRatio": float(largest_use_ratio),
            "BuildingType": str(data["BuildingType"]),
            "PrimaryPropertyType": str(data["PrimaryPropertyType"]),
            "Neighborhood": str(data["Neighborhood"]),
            "HasGas": int(data["HasGas"]),
            "HasSteam": int(data["HasSteam"]),
        }])

        # 4. Je lance la prédiction (en log) et je reconvertis en kBtu réels avec expm1
        pred_log = self.pipeline.predict(input_row)[0]
        predicted_kbtu = float(np.expm1(pred_log))

        return {
            "status": "success",
            "target_predicted": "SiteEnergyUseWN(kBtu)",
            "building_type": data["PrimaryPropertyType"],
            "surface_sqft": float(data["PropertyGFATotal"]),
            "predicted_energy_consumption_kBtu": round(predicted_kbtu, 2),
        }