"""
Point d'entrée de l'export HFSQL.

Pour chaque entreprise du .env (MEGAPRINT, SLIMMO, MEGAPOWER), exporte SA
base HFSQL vers backend_rh/data/<ENTREPRISE>/ en fichiers CSV.
Toute la logique se trouve dans le package exporter/.

Cette commande ne fait QUE : HFSQL -> CSV.
La suite (CSV -> PostgreSQL) est lancée séparément avec :
    docker exec -it backend_rh bash
    python manage.py data_migrations
"""

import sys

from exporter import HfSqlExporter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    HfSqlExporter().export_all()


if __name__ == "__main__":
    main()
