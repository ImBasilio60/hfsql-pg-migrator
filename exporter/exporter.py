"""
Orchestration de l'export HFSQL.

Pour chaque entreprise définie dans le .env (MEGAPRINT, SLIMMO, MEGAPOWER),
se connecte à SA base HFSQL, lit les tables et écrit les CSV dans :

    backend_rh/data/<ENTREPRISE>/

Les tables système de sauvegarde (_Backup_*) ne sont jamais exportées.
Les photos ne sont pas touchées : elles vivent déjà dans
backend_rh/data/<ENTREPRISE>/photos/ ; les données binaires rencontrées dans
les tables sont simplement laissées vides dans les CSV.
"""

import os

from dotenv import load_dotenv

from database import get_connection_hf

from .config import DATA_DIR, ENTREPRISES, PREFIXE_BACKUP
from .csv_writer import CsvFileWriter
from .data_cleaner import DataCleaner
from .hfsql_source import HfSqlSource

load_dotenv()


class HfSqlExporter:
    """
    Orchestre l'export des trois entreprises HFSQL vers backend_rh/data/.

    Pour chaque entreprise :
      1. lire la base HFSQL correspondante dans le .env ;
      2. se connecter à cette base ;
      3. exporter chaque table vers data/<ENTREPRISE>/<table>.csv.

    La logique de lecture reste dans HfSqlSource, celle de nettoyage dans
    DataCleaner et celle d'écriture dans CsvFileWriter : rien n'est changé
    sur ces mécanismes qui fonctionnent déjà.
    """

    def export_all(self):
        """
        Exporte les trois entreprises l'une après l'autre.

        Chaque export est indépendant : une erreur sur une entreprise n'a
        aucune influence sur les données des autres.
        """
        os.makedirs(DATA_DIR, exist_ok=True)

        for entreprise in ENTREPRISES:
            self.exporter_entreprise(entreprise)

        print("\nExport terminé.")

    def exporter_entreprise(self, entreprise):
        """Exporte UNE entreprise depuis SA base HFSQL vers SON dossier."""
        base_hfsql = os.getenv(entreprise)

        if not base_hfsql:
            print(
                f"\n{entreprise} : variable absente ou vide dans le .env, "
                "entreprise ignorée."
            )
            return

        dossier_entreprise = DATA_DIR / entreprise
        os.makedirs(dossier_entreprise, exist_ok=True)

        print(f"\n{'=' * 60}")
        print(f"Entreprise : {entreprise} (base HFSQL : {base_hfsql})")
        print(f"Destination : {dossier_entreprise}")

        conn = get_connection_hf(database=base_hfsql)

        if conn is None:
            print(
                f"{entreprise} : export interrompu (connexion impossible), "
                "les autres entreprises ne sont pas affectées."
            )
            return

        try:
            source = HfSqlSource(conn)
            writer = CsvFileWriter(str(dossier_entreprise))
            # ignorer_blobs=True : pas de création de media/, pas de photo
            # extraite — celles de data/<entreprise>/photos/ restent intactes.
            cleaner = DataCleaner(ignorer_blobs=True)

            tables = [
                table
                for table in source.get_table_names()
                if not table.startswith(PREFIXE_BACKUP)
            ]

            ignorees = len(source.get_table_names()) - len(tables)
            print(f"Tables à exporter : {len(tables)} (sauvegardes _Backup_ ignorées : {ignorees})")

            for table_name in tables:
                self._export_table(
                    source,
                    writer,
                    cleaner,
                    table_name,
                    dossier_entreprise,
                )

        finally:
            conn.close()

    def _export_table(
        self, source, writer, cleaner, table_name, dossier_entreprise
    ):
        """
        Exporte une table : lecture, nettoyage des valeurs et écriture CSV.

        Les erreurs sont capturées par table afin de ne pas interrompre
        l'export des tables suivantes. Le CSV est réécrit entièrement à
        chaque export (pas de SALAIRE_1.csv ni de fichiers fantômes).
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

            file_path = dossier_entreprise / f"{table_name}.csv"

            print(f" -> {file_path}")

        except Exception as e:
            print(f"Erreur lors de l'export de {table_name} : {e}")

        finally:
            if "rows" in locals() and rows is not None:
                rows.close()
