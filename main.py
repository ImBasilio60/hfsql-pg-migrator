import sys
import unicodedata

from database import get_connection_hf, get_connection_pg


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


def get_tables_pg():
    conn = get_connection_pg()

    if conn is None:
        return []

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        table_names = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return table_names
    except Exception as e:
        print("Erreur récupération tables PostgreSQL :", e)
        return []


def safe_print(text):
    print(text.encode(sys.stdout.encoding, errors="replace").decode(sys.stdout.encoding))


def names_match(a, b):
    """Compare two table names: U+FFFD (corruption) matches any single character."""
    a = a.lower()
    b = b.lower()
    if len(a) != len(b):
        return False
    for ca, cb in zip(a, b):
        if ca == '\ufffd' or cb == '\ufffd':
            continue
        if ca != cb:
            return False
    return True


def has_corruption(name):
    return '\ufffd' in name


def compare_tables():
    hf_tables = get_tables_hf()
    pg_tables = get_tables_pg()

    if not hf_tables and not pg_tables:
        print("Aucune table récupérée.")
        return

    print("\n===== LISTE DES TABLES HFSQL =====")
    print("-" * 40)
    for t in hf_tables:
        safe_print(t)

    print("\n===== LISTE DES TABLES POSTGRESQL =====")
    print("-" * 40)
    for t in pg_tables:
        safe_print(t)

    hf_set = {t.lower() for t in hf_tables}
    missing = []
    corruption_pairs = []

    for pg_t in pg_tables:
        if pg_t.lower() in hf_set:
            continue

        matched = False
        for hf_t in hf_tables:
            if names_match(pg_t, hf_t):
                corruption_pairs.append((pg_t, hf_t))
                matched = True
                break

        if not matched:
            missing.append(pg_t)

    if corruption_pairs:
        print("\n===== TABLES AVEC CORRUPTION D'ENCODAGE (U+FFFD) =====")
        print("-" * 40)
        for pg_t, hf_t in corruption_pairs:
            print(f"  PostgreSQL: ", end="")
            safe_print(pg_t)
            print(f"  HFSQL:      ", end="")
            safe_print(hf_t)
            print(f"  -> Correspondance établie (caractère corrompu ignoré)")
            print()

    if missing:
        print("\n===== TABLES POSTGRESQL RÉELLEMENT ABSENTES DANS HFSQL =====")
        print("-" * 40)
        for t in missing:
            safe_print(t)
    else:
        print("\nToutes les tables PostgreSQL ont une correspondance dans HFSQL.")


if __name__ == "__main__":
    compare_tables()