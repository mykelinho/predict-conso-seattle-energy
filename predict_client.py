# predict_client.py
import requests

# URL de l'API déployée sur Render
API_URL = "https://predict-conso-seattle-energy.onrender.com/predict"
# En local décommenter la ligne suivante
# API_URL = "http://localhost:3000/predict"

def ask_choice(title, choices, default_idx=0):
    """Affiche un menu à choix multiples numéroté."""
    print(f"\n{title} (par défaut: {choices[default_idx]}) :")
    for idx, choice in enumerate(choices, 1):
        print(f"  [{idx}] {choice}")
    
    while True:
        raw = input(f"Votre choix [1-{len(choices)}] (Entrée pour {choices[default_idx]}) : ").strip()
        if not raw:
            return choices[default_idx]
        if raw.isdigit():
            val = int(raw)
            if 1 <= val <= len(choices):
                return choices[val - 1]
        print(f"Option invalide. Veuillez entrer un nombre entre 1 et {len(choices)}.")

def ask_number(prompt, default, is_int=False):
    """Demande un nombre avec gestion de la valeur par défaut."""
    while True:
        raw = input(f"{prompt} [défaut: {default}] : ").strip()
        if not raw:
            return default
        try:
            return int(raw) if is_int else float(raw)
        except ValueError:
            print("Erreur : veuillez renseigner une valeur numérique valide.")

def ask_yes_no(prompt, default=1):
    """Demande Oui (1) ou Non (0)."""
    default_str = "O" if default == 1 else "N"
    while True:
        raw = input(f"{prompt} (O/N) [défaut: {default_str}] : ").strip().upper()
        if not raw:
            return default
        if raw in ("O", "OUI", "Y", "YES", "1"):
            return 1
        if raw in ("N", "NON", "NO", "0"):
            return 0
        print("Répondez par 'O' (Oui) ou 'N' (Non).")


def main():
    print("=" * 65)
    print("      SIMULATEUR DE CONSOMMATION ÉNERGÉTIQUE - SEATTLE")
    print("=" * 65)
    print("Saisissez les caractéristiques du bâtiment.")
    print("(Appuyez sur Entrée pour utiliser la valeur proposée par défaut)\n")

    # 1. Caractéristiques dimensionnelles
    gfa_total = ask_number("1. Surface totale du bâtiment (sq ft)", 88434.0)
    year_built = ask_number("2. Année de construction (ex: 1985)", 1927, is_int=True)
    nb_buildings = ask_number("3. Nombre de bâtiments sur la parcelle", 1, is_int=True)
    nb_floors = ask_number("4. Nombre d'étages", 12, is_int=True)
    gfa_parking = ask_number("5. Surface dédiée au parking (sq ft)", 0.0)
    
    # Surface hors parking
    gfa_building_default = max(gfa_total - gfa_parking, 0.0)
    gfa_building = ask_number("6. Surface du bâtiment hors parking (sq ft)", gfa_building_default)
    largest_gfa = ask_number("7. Surface du plus grand usage (sq ft)", gfa_building)

    # 2. Listes de choix
    property_types = [
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
    primary_type = ask_choice("8. Usage principal du bâtiment", property_types, default_idx=0)

    building_types = [
        "NonResidential",
        "Nonresidential COS",
        "SPS-District K-12",
        "Campus"
    ]
    building_type = ask_choice("9. Type de structure", building_types, default_idx=0)

    neighborhoods = [
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
    neighborhood = ask_choice("10. Quartier de Seattle", neighborhoods, default_idx=0)

    # 3. Énergies raccordées
    has_gas = ask_yes_no("11. Le bâtiment utilise-t-il le gaz naturel ?", default=1)
    has_steam = ask_yes_no("12. Le bâtiment est-il raccordé au réseau vapeur ?", default=1)

    # Construction du dictionnaire
    payload = {
        "PropertyGFATotal": gfa_total,
        "YearBuilt": year_built,
        "NumberofBuildings": nb_buildings,
        "NumberofFloors": nb_floors,
        "PropertyGFAParking": gfa_parking,
        "PropertyGFABuilding": gfa_building,
        "LargestPropertyUseTypeGFA": largest_gfa,
        "PrimaryPropertyType": primary_type,
        "BuildingType": building_type,
        "Neighborhood": neighborhood,
        "HasGas": has_gas,
        "HasSteam": has_steam
    }

    print("\n" + "-" * 65)
    print("Envoi de la requête à l'API Cloud...")
    print("-" * 65)

    try:
        response = requests.post(API_URL, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            conso = result.get("predicted_energy_consumption_kBtu", 0)
            print("\nRÉSULTAT DE L'ESTIMATION :")
            print(f"  Usage du bâtiment        : {result.get('building_type')}")
            print(f"  Surface totale           : {result.get('surface_sqft'):,.0f} sq ft")
            print(f"  Consommation estimée     : {conso:,.2f} kBtu / an")
            print("=" * 65)
        else:
            print(f"\nRejet de la requête (Code HTTP {response.status_code}) :")
            print(response.text)
            
    except requests.exceptions.RequestException as err:
        print(f"\nImpossible de joindre le serveur : {err}")

if __name__ == "__main__":
    main()