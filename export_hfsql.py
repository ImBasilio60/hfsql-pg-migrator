"""
Point d'entrée de l'export HFSQL.

Lance l'export complet de la base HFSQL vers des fichiers CSV.
Toute la logique se trouve dans le package exporter/.
"""

import sys

from exporter import HfSqlExporter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    HfSqlExporter().export_all()


if __name__ == "__main__":
    main()