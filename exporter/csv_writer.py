"""
Écriture des fichiers CSV d'export.

Gère l'ouverture des fichiers, l'en-tête et l'écriture des lignes.
"""

import csv
import os
from contextlib import contextmanager

from .config import EXPORT_DIR


class CsvFileWriter:
    """
    Écrit les données d'une table dans un fichier CSV encodé en UTF-8.

    Gère le séparateur, le quote des champs et l'encodage avec BOM
    pour une ouverture facile dans Excel.

    Ne connaît ni la source des données, ni les transformations
    appliquées aux valeurs : elle reçoit des lignes prêtes à écrire.
    """

    def __init__(self, export_dir=EXPORT_DIR):
        """Prépare l'écrivain avec le dossier de destination."""
        self.export_dir = export_dir

    @contextmanager
    def table_file(self, table_name):
        """
        Ouvre le fichier CSV d'une table et renvoie son écrivain csv.

        Le fichier est fermé automatiquement à la fin du bloc.
        """
        file_path = os.path.join(
            self.export_dir,
            f"{table_name}.csv"
        )

        with open(
            file_path,
            "w",
            newline="",
            encoding="utf-8-sig"
        ) as csv_file:
            writer = csv.writer(
                csv_file,
                delimiter=";",
                quoting=csv.QUOTE_MINIMAL
            )

            yield writer