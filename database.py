import os
from dotenv import load_dotenv
import pypyodbc

load_dotenv()


def get_connection_pg():
    import psycopg
    try:
        conn = psycopg.connect(
            host=os.getenv("PG_HOST"),
            port=int(os.getenv("PG_PORT")),
            dbname=os.getenv("PG_DATABASE"),
            user=os.getenv("PG_USER"),
            password=os.getenv("PG_PASSWORD"),
        )

        print("Connexion PostgreSQL réussie")
        return conn
    except Exception as e:
        print("Erreur de connexion PSQL: ", e)
        return None


def get_connection_hf():
    try:
        conn_str = (
            f"DRIVER={os.getenv('HFSQL_DRIVER')};"
            f"Server Name={os.getenv('HFSQL_SERVER')};"
            f"Server Port={os.getenv('HFSQL_PORT')};"
            f"Database={os.getenv('HFSQL_DATABASE')};"
            f"UID={os.getenv('HFSQL_UID')};"
            f"PWD={os.getenv('HFSQL_PWD')}"
        )
        conn = pypyodbc.connect(conn_str)

        print("Connexion HFSQL réussie")
        return conn
    except Exception as e:
        print("Erreur de connexion HFSQL: ", e)
        return None

