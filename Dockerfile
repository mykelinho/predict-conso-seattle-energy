FROM python:3.11-slim

WORKDIR /app

# J'installe les dépendances système légères
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# J'installe les packages Python nécessaires
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Je copie mes fichiers métier et le jeu de données de référence
COPY 2016_Building_Energy_Benchmarking.csv .
COPY export_model.py .
COPY schemas.py .
COPY service.py .

# J'entraîne et j'enregistre mon pipeline dans le magasin BentoML du conteneur
RUN python export_model.py

# J'expose le port BentoML
EXPOSE 3000

# Je lance le serveur BentoML en écoute sur toutes les interfaces
CMD ["bentoml", "serve", "service:SeattleEnergyService", "--host", "0.0.0.0", "--port", "3000"]