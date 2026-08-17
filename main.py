import sys
import unicodedata

from database import get_connection_hf

def get_tables_hf():
    conn = get_connection_hf()

    if conn is None:
        return []

    try:
        cursor = conn.cursor()
        tables = cursor.tables(tableType="TABLE")
        table_names = [table[1] for table in tables]
        cursor.close()
        conn.close()
        return table_names
    except Exception as e:
        print("Erreur récupération tables HFSQL :", e)
        return []

if __name__ == "__main__":
    get_tables_hf()