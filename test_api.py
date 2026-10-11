# test_api.py
import requests

# Ne pas oublier "https://" et le "/predict" à la fin
# (Remplacez par http://localhost:3000/predict en local)
URL = "https://predict-conso-seattle-energy.onrender.com/predict"

print("=" * 60)
print("TEST 1 : Données valides (Cas nominal d'un hôtel à Seattle)")
print("=" * 60)

payload_valide = {
    "PropertyGFATotal": 88434.0,
    "YearBuilt": 1927,
    "NumberofBuildings": 1,
    "NumberofFloors": 12,
    "PropertyGFAParking": 0.0,
    "PropertyGFABuilding": 88434.0,
    "LargestPropertyUseTypeGFA": 88434.0,
    "PrimaryPropertyType": "Hotel",
    "BuildingType": "NonResidential",
    "Neighborhood": "DOWNTOWN",
    "HasGas": 1,
    "HasSteam": 1
}

res_1 = requests.post(URL, json=payload_valide)
print(f"Code HTTP reçu : {res_1.status_code} (Attendu: 200)")

try:
    print("Réponse JSON :", res_1.json())
except Exception:
    print("Réponse brute (Texte) :", res_1.text)


print("\n" + "=" * 60)
print("TEST 2 : Données aberrantes (Vérification du rejet Pydantic)")
print("=" * 60)

payload_invalide = {
    "PropertyGFATotal": -500.0,  # Surface négative interdite
    "YearBuilt": 1820            # Bâtiment avant 1900 interdit
}

res_2 = requests.post(URL, json=payload_invalide)
print(f"Code HTTP reçu : {res_2.status_code} (Attendu: 400 ou 422)")

try:
    print("Réponse JSON :", res_2.json())
except Exception:
    print("Réponse brute (Texte) :", res_2.text)