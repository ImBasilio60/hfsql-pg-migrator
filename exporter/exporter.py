"""
Orchestration de l'export HFSQL.

Coordonne la connexion, la lecture des données, le nettoyage
et l'écriture des fichiers CSV.
"""

import os

from database import get_connection_hf

from .blob_exporter import BlobExporter
from .config import EXPORT_DIR, MEDIA_DIR
from .csv_writer import CsvFileWriter
from .data_cleaner import DataCleaner
from .hfsql_source import HfSqlSource


class HfSqlExporter:
    """
    Orchestre l'export complet de la base HFSQL vers des fichiers CSV.

    Crée la connexion, récupère la liste des tables, puis coordonne
    pour chaque table la lecture, le nettoyage des valeurs et l'écriture
    du fichier CSV.

    Ne contient pas la logique métier de nettoyage ni d'écriture :
    elle délègue ces tâches à DataCleaner, BlobExporter et CsvFileWriter.
    """

    def __init__(
        self,
        export_dir=EXPORT_DIR,
        connection_factory=get_connection_hf
    ):
        """
        Prépare l'exporteur avec le dossier de destination.

        La fabrique de connexion est injectable pour faciliter les tests.
        """
        self.export_dir = export_dir
        self.connection_factory = connection_factory
        self.media_dir = os.path.join(export_dir, MEDIA_DIR)

    def export_all(self):
        """
        Exporte toutes les tables HFSQL vers des fichiers CSV.

        Crée les dossiers nécessaires, itère sur les tables
        et ferme la connexion en fin de processus.
        """
        conn = self.connection_factory()

        if conn is None:
            return

        os.makedirs(
            self.export_dir,
            exist_ok=True
        )

        os.makedirs(
            self.media_dir,
            exist_ok=True
        )

        try:
            source = HfSqlSource(conn)
            writer = CsvFileWriter(self.export_dir)
            cleaner = DataCleaner(
                BlobExporter(self.export_dir)
            )

            tables = source.get_table_names()

            print(f"\n Nombre de tables trouvées : {len(tables)}")

            for table_name in tables:
                self._export_table(
                    source,
                    writer,
                    cleaner,
                    table_name
                )

            print("\nExport terminé.")

        finally:
            conn.close()

    def _export_table(self, source, writer, cleaner, table_name):
        """
        Exporte une table : lecture, nettoyage des valeurs et écriture CSV.

        Les erreurs sont capturées par table afin de ne pas interrompre
        l'export des tables suivantes.
        """
        try:
            print(f"Export de la table : {table_name}")

            columns, rows = source.query_table(table_name)

            key_index = source.get_key_index(columns)

            with writer.table_file(table_name) as csv_writer:
                csv_writer.writerow(columns)

                row_index = 0

                for row in rows:
                    row_index += 1

                    key = (
                        row[key_index]
                        if key_index is not None
                        else row_index
                    )

                    csv_writer.writerow([
                        cleaner.clean(
                            value,
                            table_name,
                            key,
                            columns[i]
                        )
                        for i, value in enumerate(row)
                    ])

            file_path = os.path.join(
                self.export_dir,
                f"{table_name}.csv"
            )

            print(f" -> {file_path}")

        except Exception as e:
            print(f"Erreur lors de l'export de {table_name} : {e}")

        finally:
            if "rows" in locals() and rows is not None:
                rows.close()