"""
Constantes de configuration de l'export HFSQL.
"""

from pathlib import Path

# Dossier de destination des CSV : backend_rh/data/, situé à côté de
# migration_hfsql/. Créé automatiquement s'il n'existe pas (voir exporter.py).
BASE_PROJET = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_PROJET / "backend_rh" / "data"

# Entreprises à exporter, dans l'ordre. Chaque nom correspond à une variable
# du .env qui contient le nom de la base HFSQL de cette entreprise
# (ex : MEGAPRINT=MEGAPAIE2021).
ENTREPRISES = ("MEGAPRINT", "SLIMMO", "MEGAPOWER")

# Les tables HFSQL dont le nom commence par ce préfixe sont des sauvegardes
# système (_Backup_SALAIRE, _Backup_...Integrity, ...) : jamais exportées.
PREFIXE_BACKUP = "_Backup_"

# --- Legacy : plus utilisés par le flux entreprise -> data/, conservés pour
# les valeurs par défaut de BlobExporter / CsvFileWriter. ---
EXPORT_DIR = "exported_data"
MEDIA_DIR = "media"
