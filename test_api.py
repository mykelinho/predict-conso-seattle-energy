# test_api.py
import requests

# URL locale du serveur BentoML
#URL = "http://localhost:3000/predict"
URL = "https://predict-conso-seattle-energy.onrender.com/"

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
print("Réponse de l'API :")
print(res_1.json())


print("\n" + "=" * 60)
print("TEST 2 : Données aberrantes (Vérification du rejet Pydantic)")
print("=" * 60)

payload_invalide = {
    "PropertyGFATotal": -500.0,  # Surface négative interdite
    "YearBuilt": 1820            # Bâtiment avant 1900 interdit
}

res_2 = requests.post(URL, json=payload_invalide)
print(f"Code HTTP reçu : {res_2.status_code} (Attendu: 400 ou 422)")
print("Réponse de l'API :")
print(res_2.json())