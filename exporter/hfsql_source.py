"""
Source de données HFSQL.

Fournit l'accès en lecture à la base HFSQL : liste des tables,
colonnes et lignes de chaque table.
"""

class HfSqlSource:
    """
    Lecture des données depuis la base HFSQL.

    Récupère la liste des tables, exécute les requêtes SQL
    et expose les colonnes et lignes de chaque table.

    Ne gère ni le nettoyage des valeurs, ni l'écriture des fichiers :
    elle est uniquement responsable de la lecture des données.
    """

    KEY_COLUMNS = ("matricule", "id", "code")

    def __init__(self, connection):
        """
        Prépare la source avec la connexion HFSQL.

        La connexion est créée et fermée par l'orchestrateur.
        """
        self.connection = connection

    def get_table_names(self):
        """
        Renvoie la liste des noms de tables de la base.

        Le pilote HFSQL renvoie les tables sous forme de tuples
        dont le nom se trouve à l'index 1.
        """
        cursor = self.connection.cursor()

        try:
            tables = cursor.tables(tableType="TABLE")

            table_names = []

            for table in tables:
                table_name = table[1]

                if table_name:
                    table_names.append(table_name)

            return table_names

        finally:
            cursor.close()

    def query_table(self, table_name):
        """
        Exécute SELECT * sur la table et renvoie (colonnes, lignes).

        Les lignes sont renvoyées sous forme d'itérateur à consommer
        immédiatement, avant la fermeture du curseur.
        """
        cursor = self.connection.cursor()

        try:
            cursor.execute(f"SELECT * FROM [{table_name}]")

            columns = [column[0] for column in cursor.description]

            return columns, cursor

        except Exception:
            cursor.close()
            raise

    @staticmethod
    def get_key_index(columns):
        """
        Renvoie l'index de la colonne clé (matricule, id, code)
        ou None si aucune colonne clé n'est présente.

        La clé sert à nommer les fichiers binaires extraits.
        """
        for i, col in enumerate(columns):
            if col.lower() in HfSqlSource.KEY_COLUMNS:
                return i

        return None