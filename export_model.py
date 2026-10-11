# export_model.py
import numpy as np
import pandas as pd
import bentoml
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.ensemble import RandomForestRegressor

print("1. Chargement et préparation des données...")
# Lecture des données nettoyées
df = pd.read_csv("2016_Building_Energy_Benchmarking.csv")

# Filtrage identique à la Partie 1
types_habitation = ['Multifamily LR (1-4)', 'Multifamily MR (5-9)', 'Multifamily HR (10+)']
df = df[~df['BuildingType'].isin(types_habitation)]
if 'Outlier' in df.columns:
    df = df[~df['Outlier'].isin(['Low outlier', 'High outlier'])]
if 'ComplianceStatus' in df.columns:
    df = df[df['ComplianceStatus'] == 'Compliant']
df = df.dropna(subset=['SiteEnergyUse(kBtu)', 'PropertyGFATotal'])
df = df[(df['SiteEnergyUse(kBtu)'] > 0) & (df['PropertyGFATotal'] > 0)].copy()

# Feature Engineering
df['BuildingAge'] = 2016 - df['YearBuilt']
df['ParkingRatio'] = (df['PropertyGFAParking'] / df['PropertyGFATotal']).fillna(0)
df['BuildingRatio'] = (df['PropertyGFABuilding(s)'] / df['PropertyGFATotal']).fillna(1)
df['GFAPerFloor'] = df['PropertyGFABuilding(s)'] / np.maximum(df['NumberofFloors'], 1)
df['HasGas'] = (df['NaturalGas(kBtu)'].fillna(0) > 0).astype(int)
df['HasSteam'] = (df['SteamUse(kBtu)'].fillna(0) > 0).astype(int)
df['LargestUseRatio'] = (df['LargestPropertyUseTypeGFA'] / df['PropertyGFATotal']).fillna(0)

features_quanti = [
    'PropertyGFATotal', 'BuildingAge', 'NumberofBuildings',
    'NumberofFloors', 'ParkingRatio', 'BuildingRatio',
    'GFAPerFloor', 'LargestUseRatio'
]
features_quali = [
    'PrimaryPropertyType', 'BuildingType', 'Neighborhood',
    'HasGas', 'HasSteam'
]

X = df[features_quanti + features_quali]
y = np.log1p(df['SiteEnergyUse(kBtu)'])

print("2. Construction du Pipeline complet...")
preprocessor = ColumnTransformer(
    transformers=[
        ('num', StandardScaler(), features_quanti),
        ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), features_quali)
    ]
)

# Meilleur modèle issu du GridSearchCV
rf_model = RandomForestRegressor(
    n_estimators=150,
    max_depth=15,
    min_samples_split=2,
    random_state=42,
    n_jobs=-1
)

full_pipeline = Pipeline([
    ('preprocessor', preprocessor),
    ('regressor', rf_model)
])

# Entraînement du pipeline complet
full_pipeline.fit(X, y)

print("3. Sauvegarde dans le magasin de modèles BentoML...")
# Sauvegarde officielle BentoML
bento_model = bentoml.sklearn.save_model(
    "seattle_energy_pipeline",
    full_pipeline,
    signatures={"predict": {"batchable": False}}
)

print(f" Modèle enregistré avec succès : {bento_model.tag}")