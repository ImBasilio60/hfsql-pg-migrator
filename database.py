import os
from datetime import date, datetime, time
from dotenv import load_dotenv
import pypyodbc

load_dotenv()

def _decode(value):
    if isinstance(value, bytes):
        value = value.decode("ascii", "replace")
    return (value or "").strip().rstrip("\x00")

def _convert_date(value):
    value = _decode(value)
    if not value:
        return None
    if len(value) == 8:
        return date(int(value[0:4]), int(value[4:6]), int(value[6:8]))
    return date.fromisoformat(value)

def _convert_time(value):
    value = _decode(value)
    if not value:
        return None
    if len(value) == 6:
        return time(int(value[0:2]), int(value[2:4]), int(value[4:6]))
    return time.fromisoformat(value)

def _convert_timestamp(value):
    value = _decode(value)
    if not value:
        return None
    if len(value) >= 14 and value[4] not in "-/":
        return datetime(
            int(value[0:4]), int(value[4:6]), int(value[6:8]),
            int(value[8:10]), int(value[10:12]), int(value[12:14])
        )
    return datetime.fromisoformat(value)

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

        conn.add_output_converter(pypyodbc.SQL_TYPE_DATE, _convert_date)
        conn.add_output_converter(pypyodbc.SQL_TYPE_TIME, _convert_time)
        conn.add_output_converter(pypyodbc.SQL_TYPE_TIMESTAMP, _convert_timestamp)

        print("Connexion HFSQL réussie")

        return conn
    
    except Exception as e:
        print("Erreur de connexion HFSQL: ", e)
        return None

