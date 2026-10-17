# export_model.py
import bentoml
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

print("1. Je charge et je nettoie les données (Phase A et Phase B)...")
df = pd.read_csv("2016_Building_Energy_Benchmarking.csv")
target_col = "SiteEnergyUseWN(kBtu)"

# --- PHASE A : Mes filtres métier ---
# Étape 1 : Je retire le résidentiel
types_habitation = [
    "Multifamily LR (1-4)",
    "Multifamily MR (5-9)",
    "Multifamily HR (10+)",
]
df_filtre = df[
    ~df["BuildingType"].isin(types_habitation)
    & ~df["PrimaryPropertyType"].str.contains("Multifamily", na=False)
].copy()

# Étape 2 : Je retire les anomalies signalées par la mairie
if "Outlier" in df_filtre.columns:
  df_filtre = df_filtre[~df_filtre["Outlier"].isin(["Low outlier", "High outlier"])]

# Étape 3 : Je conserve uniquement les dossiers conformes
if "ComplianceStatus" in df_filtre.columns:
  df_filtre = df_filtre[df_filtre["ComplianceStatus"] == "Compliant"]

# Étape 4 : Je supprime les consommations et surfaces nulles, négatives ou manquantes
df_filtre = df_filtre.dropna(subset=[target_col, "PropertyGFATotal"])
df_clean = df_filtre[
    (df_filtre[target_col] > 0) & (df_filtre["PropertyGFATotal"] > 0)
].copy()

# --- PHASE B : Mes filtres d'outliers physiques et statistiques ---
# 1. Je remplace les valeurs à 0 par 1 sur les étages et le nombre de bâtiments
df_clean["NumberofFloors"] = df_clean["NumberofFloors"].replace(0, 1)
df_clean["NumberofBuildings"] = (
    df_clean["NumberofBuildings"].fillna(1).replace(0, 1)
)

# 2. Je retire les aberrations physiques (plus de 76 étages ou plus de 10 bâtiments)
df_clean = df_clean[
    (df_clean["NumberofFloors"] >= 1)
    & (df_clean["NumberofFloors"] <= 76)
    & (df_clean["NumberofBuildings"] >= 1)
    & (df_clean["NumberofBuildings"] <= 10)
].copy()

# 3. J'applique le filtre statistique par quantiles (1% - 99%) sur la cible et la surface
q_low_energy, q_high_energy = df_clean[target_col].quantile([0.01, 0.99])
q_high_surface = df_clean["PropertyGFATotal"].quantile(0.99)

df_clean = df_clean[
    (df_clean[target_col] >= q_low_energy)
    & (df_clean[target_col] <= q_high_energy)
    & (df_clean["PropertyGFATotal"] <= q_high_surface)
].copy()

print(f"   -> Périmètre final nettoyé : {len(df_clean)} bâtiments tertiaires.")

# --- FEATURE ENGINEERING ---
# 1. Je calcule l'âge du bâtiment
df_clean["BuildingAge"] = (df_clean["DataYear"] - df_clean["YearBuilt"]).clip(
    lower=0
)

# 2. Je calcule le ratio de parking (BuildingRatio est écarté car colinéaire à -1.00)
df_clean["ParkingRatio"] = (
    df_clean["PropertyGFAParking"] / df_clean["PropertyGFATotal"]
).clip(0, 1)

# 3. Je calcule la surface moyenne par étage
nb_etages_sain = np.maximum(df_clean["NumberofFloors"], 1)
df_clean["GFAPerFloor"] = df_clean["PropertyGFABuilding(s)"] / nb_etages_sain

# 4. Je calcule la part de l'activité principale
gfa_usage_principal = df_clean["LargestPropertyUseTypeGFA"].fillna(
    df_clean["PropertyGFATotal"]
)
df_clean["LargestUseRatio"] = (
    gfa_usage_principal / df_clean["PropertyGFATotal"]
).clip(0, 1)

# 5. J'indique la présence d'équipements énergétiques (0 = Non, 1 = Oui)
df_clean["HasGas"] = (df_clean["NaturalGas(kBtu)"].fillna(0) > 0).astype(int)
df_clean["HasSteam"] = (df_clean["SteamUse(kBtu)"].fillna(0) > 0).astype(int)

# 6. Je regroupe les usages rares dans 'Other' (conservation du Top 8)
top_8_usages = df_clean["PrimaryPropertyType"].value_counts().nlargest(8).index
df_clean["PrimaryPropertyType"] = df_clean["PrimaryPropertyType"].where(
    df_clean["PrimaryPropertyType"].isin(top_8_usages), "Other"
)

# Ma sélection finale de variables (7 quantitatives + 5 qualitatives/binaires)
features_quanti = [
    "PropertyGFATotal",
    "NumberofBuildings",
    "NumberofFloors",
    "BuildingAge",
    "ParkingRatio",
    "GFAPerFloor",
    "LargestUseRatio",
]

features_quali = [
    "BuildingType",
    "PrimaryPropertyType",
    "Neighborhood",
    "HasGas",
    "HasSteam",
]

X = df_clean[features_quanti + features_quali].copy()
y = np.log1p(df_clean[target_col])

print("2. Je construis et j'entraîne le Pipeline complet...")
preprocessor = ColumnTransformer(
    transformers=[
        ("num", StandardScaler(), features_quanti),
        (
            "cat",
            OneHotEncoder(handle_unknown="ignore", sparse_output=False),
            features_quali,
        ),
    ]
)

# Je configure le Random Forest avec les meilleurs hyperparamètres issus de mon GridSearchCV
rf_model = RandomForestRegressor(
    n_estimators=200,
    max_depth=15,
    min_samples_split=10,
    min_samples_leaf=1,
    random_state=42,
    n_jobs=-1,
)

full_pipeline = Pipeline(
    [("preprocessor", preprocessor), ("regressor", rf_model)]
)

full_pipeline.fit(X, y)

print("3. Je sauvegarde le pipeline dans le magasin de modèles BentoML...")
bento_model = bentoml.sklearn.save_model(
    "seattle_energy_pipeline",
    full_pipeline,
    signatures={"predict": {"batchable": False}},
)

print(f"Modèle enregistré avec succès : {bento_model.tag}")