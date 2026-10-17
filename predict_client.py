# predict_client.py
import requests

# Je définis l'URL Cloud Render (ou http://localhost:3000/predict en local)
API_URL = "https://predict-conso-seattle-energy.onrender.com/predict"


def ask_number(prompt, default, min_val=None, max_val=None, is_int=False):
  """Je demande un nombre à l'utilisateur et je vérifie immédiatement les bornes."""
  bounds_txt = ""
  if min_val is not None and max_val is not None:
    bounds_txt = f" [min: {min_val}, max: {max_val}]"
  elif min_val is not None:
    bounds_txt = f" [min: {min_val}]"

  while True:
    raw = input(f"{prompt}{bounds_txt} (défaut: {default}) : ").strip()
    if not raw:
      return default

    try:
      val = int(raw) if is_int else float(raw)
    except ValueError:
      print("  -> Erreur : veuillez saisir un nombre valide.")
      continue

    if min_val is not None and val < min_val:
      print(
          "  -> Saisie refusée : la valeur doit être supérieure ou égale à"
          f" {min_val}."
      )
      continue
    if max_val is not None and val > max_val:
      print(
          "  -> Saisie refusée : la valeur doit être inférieure ou égale à"
          f" {max_val}."
      )
      continue

    return val


def ask_choice(title, choices, default_idx=0):
  """J'affiche un menu numéroté et je valide le choix."""
  print(f"\n{title} (défaut: {choices[default_idx]}) :")
  for idx, choice in enumerate(choices, 1):
    print(f"  [{idx}] {choice}")

  while True:
    raw = input(
        f"Votre choix [1-{len(choices)}] (Entrée pour"
        f" {choices[default_idx]}) : "
    ).strip()
    if not raw:
      return choices[default_idx]
    if raw.isdigit():
      val = int(raw)
      if 1 <= val <= len(choices):
        return choices[val - 1]
    print(f"  -> Option invalide : entrez un chiffre entre 1 et {len(choices)}.")


def ask_yes_no(prompt, default=1):
  """Je valide une réponse binaire Oui/Non (1 ou 0)."""
  default_str = "O" if default == 1 else "N"
  while True:
    raw = input(f"{prompt} (O/N) [défaut: {default_str}] : ").strip().upper()
    if not raw:
      return default
    if raw in ("O", "OUI", "Y", "YES", "1"):
      return 1
    if raw in ("N", "NON", "NO", "0"):
      return 0
    print("  -> Répondez par 'O' (Oui) ou 'N' (Non).")


def main():
  print("=" * 65)
  print("      SIMULATEUR DE CONSOMMATION ÉNERGÉTIQUE - SEATTLE")
  print("=" * 65)
  print(
      "Validation en direct activée. Appuyez sur Entrée pour la valeur par"
      " défaut.\n"
  )

  # 1. Je récupère les caractéristiques dimensionnelles (bornes alignées avec mon étude)
  gfa_total = ask_number(
      "1. Surface totale (sq ft)",
      default=88434.0,
      min_val=100.0,
      max_val=10_000_000.0,
  )
  year_built = ask_number(
      "2. Année de construction",
      default=1927,
      min_val=1900,
      max_val=2026,
      is_int=True,
  )
  nb_buildings = ask_number(
      "3. Nombre de bâtiments", default=1, min_val=1, max_val=10, is_int=True
  )
  nb_floors = ask_number(
      "4. Nombre d'étages", default=12, min_val=1, max_val=76, is_int=True
  )
  gfa_parking = ask_number(
      "5. Surface parking (sq ft)",
      default=0.0,
      min_val=0.0,
      max_val=5_000_000.0,
  )

  gfa_building_default = max(gfa_total - gfa_parking, 0.0)
  gfa_building = ask_number(
      "6. Surface hors parking (sq ft)",
      default=gfa_building_default,
      min_val=0.0,
      max_val=10_000_000.0,
  )
  largest_gfa = ask_number(
      "7. Surface du plus grand usage (sq ft)",
      default=gfa_building,
      min_val=0.0,
      max_val=10_000_000.0,
  )

  # 2. Je récupère les sélections catégorielles
  property_types = [
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
  primary_type = ask_choice("8. Usage principal", property_types, default_idx=0)

  building_types = [
      "NonResidential",
      "Nonresidential COS",
      "SPS-District K-12",
      "Campus",
  ]
  building_type = ask_choice(
      "9. Type de structure", building_types, default_idx=0
  )

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
      "DELRIDGE",
  ]
  neighborhood = ask_choice("10. Quartier", neighborhoods, default_idx=0)

  # 3. Je récupère les énergies raccordées
  has_gas = ask_yes_no("11. Raccordement au gaz naturel ?", default=1)
  has_steam = ask_yes_no("12. Raccordement au réseau de vapeur ?", default=1)

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
      "HasSteam": has_steam,
  }

  print("\n" + "-" * 65)
  print("Transmission des données vérifiées à l'API...")
  print("-" * 65)

  try:
    response = requests.post(API_URL, json=payload, timeout=60)
    if response.status_code == 200:
      result = response.json()
      conso = result.get("predicted_energy_consumption_kBtu", 0)
      print("\nRÉSULTAT DE L'ESTIMATION (SiteEnergyUseWN) :")
      print(f"  Usage du bâtiment        : {result.get('building_type')}")
      print(
          f"  Surface totale           : {result.get('surface_sqft'):,.0f}"
          " sq ft"
      )
      print(f"  Consommation estimée     : {conso:,.2f} kBtu / an")
      print("=" * 65)
    else:
      print(f"\nErreur API ({response.status_code}) :")
      print(response.text)
  except requests.exceptions.RequestException as err:
    print(f"\nErreur de connexion au serveur : {err}")


if __name__ == "__main__":
  main()