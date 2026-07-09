from database import get_connection_hf, get_connection_pg

def get_tables_hf():
    conn = get_connection_hf()
    
    if conn is None:
        return 
    
    try:
        cursor = conn.cursor()

        tables =  cursor.tables(tableType="TABLE")

        print("\nListe des Tables HFSQL :")
        print("-" * 40)

        for table in tables:
            print(table[1])
        
        cursor.close()
        conn.close()

    except Exception as e:
        print("Erreur récupération tables HFSQL :", e)

def get_tables_pg():
    conn = get_connection_pg()

    if conn is None:
        return
    
    try:
        cursor = conn.cursor()
        print("\nListe des Tables PostgreSQL :")
        print("-" * 40)
        
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)

        tables = cursor.fetchall()

        for table in tables:
            print(table[0])
        
        cursor.close()
        conn.close()
    except Exception as e:
        print("Erreur récupération tables PostgreSQL :", e)


if __name__ == "__main__":
    print("===== TEST HFSQL =====")
    get_tables_hf()

    print("\n===== TEST POSTGRESQL =====")
    get_tables_pg()