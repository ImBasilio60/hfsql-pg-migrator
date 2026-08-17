import csv
import os
import re
import sys

from database import get_connection_hf

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

EXPORT_DIR = "export_hfsql"
MEDIA_DIR = os.path.join(EXPORT_DIR, "media")

MAGIC_EXT = [
    (b"\xff\xd8\xff", "jpg"),
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"GIF87a", "gif"),
    (b"GIF89a", "gif"),
    (b"BM", "bmp"),
    (b"%PDF", "pdf"),
    (b"II*\x00", "tif"),
    (b"MM\x00*", "tif"),
    (b"\x00\x00\x01\x00", "ico"),
    (b"PK\x03\x04", "zip"),
]

GUID_RE = re.compile(
    r"^b'([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{12})'$"
)

RTF_SKIP_GROUPS = {
    "fonttbl", "colortbl", "stylesheet", "info", "pict",
    "header", "headerl", "headerr", "headerf",
    "footer", "footerl", "footerr", "footerf",
    "object", "themedata", "colorschememapping",
    "latentstyles", "listtable", "listoverridetable",
    "revtbl", "rsidtbl", "generator",
}

RTF_CHAR_MAP = {
    "\\": "\\",
    "{": "{",
    "}": "}",
    "~": " ",
    "_": "_",
    "-": "-",
}

def _rtf_to_text(value):
    codepage = 1252
    output = []
    depth = 0
    skipping = False
    skip_next = False
    skip_depth = 0
    uc_fallback = 1
    i = 0
    n = len(value)

    try:
        while i < n:
            char = value[i]

            if char == "{":
                if skip_next:
                    skipping = True
                    skip_depth = depth + 1
                    skip_next = False
                depth += 1
                i += 1
                continue

            if char == "}":
                depth -= 1
                if skipping and depth < skip_depth:
                    skipping = False
                    skip_depth = 0
                i += 1
                continue

            if char in "\r\n":
                i += 1
                continue

            if char == "\\":
                i += 1

                if i >= n:
                    break

                marker = value[i]

                if marker.isalpha():
                    j = i
                    while j < n and value[j].isalpha():
                        j += 1

                    word = value[i:j]

                    sign = 1
                    param = None

                    if j < n and value[j] == "-":
                        sign = -1
                        j += 1

                    if j < n and value[j].isdigit():
                        start = j
                        while j < n and value[j].isdigit():
                            j += 1
                        param = sign * int(value[start:j])

                    if j < n and value[j] == " ":
                        j += 1

                    i = j

                    if word in ("par", "line"):
                        if not skipping:
                            output.append("\n")
                    elif word == "tab":
                        if not skipping:
                            output.append("\t")
                    elif word == "u":
                        if not skipping and param is not None:
                            output.append(chr(param & 0xFFFF))
                            k = i
                            consumed = 0
                            while k < n and consumed < max(uc_fallback, 1):
                                ck = value[k]
                                if ck in "{}":
                                    break
                                if ck == "\\":
                                    if k + 1 < n and value[k + 1] in ("{", "}", "\\"):
                                        k += 2
                                    else:
                                        break
                                else:
                                    k += 1
                                consumed += 1
                            i = k
                    elif word == "uc":
                        if param is not None:
                            uc_fallback = max(param, 0)
                    elif word == "ansicpg":
                        if param is not None:
                            codepage = param
                    elif word == "*":
                        skip_next = True
                    elif word in RTF_SKIP_GROUPS:
                        skipping = True
                        skip_depth = depth + 1
                    continue

                if marker == "'":
                    if i + 2 < n:
                        try:
                            byte_val = int(value[i + 1:i + 3], 16)
                            if not skipping:
                                output.append(bytes([byte_val]).decode(f"cp{codepage}"))
                        except Exception:
                            pass
                        i += 3
                    else:
                        i += 1
                    continue

                if marker in RTF_CHAR_MAP:
                    if not skipping:
                        output.append(RTF_CHAR_MAP[marker])
                    i += 1
                    continue

                i += 1
                continue

            if not skipping:
                output.append(char)

            i += 1
    except Exception:
        return value

    text = "".join(output)

    lines = [
        re.sub(r"[ \t]+", " ", line).strip()
        for line in text.split("\n")
    ]

    text = "\n".join(line for line in lines if line)

    return text

def _sanitize_name(name):
    return re.sub(r'[\\/:*?"<>|]', "_", name)

def _detect_ext(data):
    for magic, ext in MAGIC_EXT:
        if data.startswith(magic):
            return ext
    return "bin"

def _decode_text(value):
    try:
        text = value.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if text and all(c.isprintable() or c in "\r\n\t" for c in text):
        return text
    return None

def _extract_media(data, table_name, key, column):
    ext = _detect_ext(data)
    base = f"{_sanitize_name(table_name)}_{key}_{column}"
    path = os.path.join(MEDIA_DIR, f"{base}.{ext}")

    n = 2
    while os.path.exists(path):
        with open(path, "rb") as f:
            if f.read() == data:
                return os.path.relpath(path, EXPORT_DIR).replace("\\", "/")
        path = os.path.join(MEDIA_DIR, f"{base}_{n}.{ext}")
        n += 1

    with open(path, "wb") as f:
        f.write(data)

    return os.path.relpath(path, EXPORT_DIR).replace("\\", "/")

def _csv_value(value, table_name, key, column):
    if isinstance(value, str):
        match = GUID_RE.match(value)

        if match:
            return match.group(1)

        if "\\rtf" in value[:200]:
            return _rtf_to_text(value)

        return value

    if not isinstance(value, (bytes, bytearray)):
        return value

    data = bytes(value)

    if not data:
        return ""

    text = _decode_text(data)

    if text is not None:
        return text

    return _extract_media(
        data,
        table_name,
        key,
        column
    )

def get_tables_hf(conn):
    cursor = conn.cursor()

    try:
        tables = cursor.tables(tableType="TABLE")

        table_names = []

        for table in tables:
            table_name = table[1]

            if table_name:
                table_names.append(table_name)

        return table_names
    
    except Exception as e:
        print("Une erreur est survenue", e)
        return None
    
    finally:
        cursor.close()

def export_table_to_csv(conn, table_name):
    cursor = conn.cursor()

    try:
        print(f"Export de la table : {table_name}")

        query = f"SELECT * FROM [{table_name}]"

        cursor.execute(query)

        columns = [column[0] for column in cursor.description]

        key_index = None

        for i, col in enumerate(columns):
            if col.lower() in ("matricule", "id", "code"):
                key_index = i
                break

        file_path = os.path.join(
            EXPORT_DIR,
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

            writer.writerow(columns)

            row_index = 0

            for row in cursor:
                row_index += 1

                key = (
                    row[key_index]
                    if key_index is not None
                    else row_index
                )

                writer.writerow([
                    _csv_value(
                        value,
                        table_name,
                        key,
                        columns[i]
                    )
                    for i, value in enumerate(row)
                ])

        print(f" -> {file_path}")

    except Exception as e:
        print(f"Erreur lors de l'export de {table_name} : {e}")

    finally:
        cursor.close()

def export_all_tables():
    conn = get_connection_hf()

    if conn is None:
        return

    os.makedirs(
        EXPORT_DIR,
        exist_ok=True
    )

    os.makedirs(
        MEDIA_DIR,
        exist_ok=True
    )

    try:
        tables = get_tables_hf(conn)

        print(f"\n Nombre de tables trouvées : {len(tables)}")

        for table_name in tables:
            export_table_to_csv(
                conn,
                table_name
            )

        print("\nExport terminé.")

    finally:
        conn.close()

if __name__ == "__main__":
    export_all_tables()