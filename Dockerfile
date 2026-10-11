FROM python:3.11-slim

WORKDIR /app

# Dépendances système légères
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Installation des packages Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie des fichiers métier et des données
COPY 2016_Building_Energy_Benchmarking.csv .
COPY export_model.py .
COPY schemas.py .
COPY service.py .

# Entraînement et enregistrement du pipeline dans le magasin BentoML du conteneur
RUN python export_model.py

# Port BentoML
EXPOSE 3000

# Lancement du serveur BentoML en écoute sur toutes les interfaces
CMD ["bentoml", "serve", "service:SeattleEnergyService", "--host", "0.0.0.0", "--port", "3000"]