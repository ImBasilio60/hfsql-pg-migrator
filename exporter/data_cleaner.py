"""
Nettoyage et transformation des valeurs brutes HFSQL.

Convertit chaque valeur en une chaîne propre et sûre pour le CSV.
"""

import re

from .blob_exporter import BlobExporter

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


class DataCleaner:
    """
    Nettoie les valeurs brutes HFSQL avant leur écriture dans le CSV.

    Normalise les GUID, convertit les contenus RTF en texte brut
    et décode les données binaires qui sont en réalité du texte.

    Les vraies données binaires (images, fichiers) sont déléguées
    au BlobExporter ; cette classe ne doit pas écrire de fichiers.
    """

    def __init__(self, blob_exporter=None):
        """Prépare le nettoyeur avec l'exporteur de binaires."""
        self.blob_exporter = blob_exporter or BlobExporter()

    def clean(self, value, table_name, key, column):
        """
        Transforme une valeur brute en chaîne prête pour le CSV.

        Les chaînes sont normalisées (GUID, RTF), les données binaires
        vides deviennent une chaîne vide, les binaires texte sont décodés
        et les autres binaires sont extraits vers un fichier.
        """
        if isinstance(value, str):
            return self._clean_text(value)

        if not isinstance(value, (bytes, bytearray)):
            return value

        data = bytes(value)

        if not data:
            return ""

        text = self._decode_text(data)

        if text is not None:
            return text

        return self.blob_exporter.export(
            data,
            table_name,
            key,
            column
        )

    def _clean_text(self, value):
        """Normalise une chaîne : GUID puis contenu RTF le cas échéant."""
        match = GUID_RE.match(value)

        if match:
            return match.group(1)

        if "\\rtf" in value[:200]:
            return self._rtf_to_text(value)

        return value

    @staticmethod
    def _decode_text(value):
        """Décode les octets en texte UTF-8 si le contenu est du texte pur."""
        try:
            text = value.decode("utf-8")
        except UnicodeDecodeError:
            return None

        if text and all(c.isprintable() or c in "\r\n\t" for c in text):
            return text

        return None

    @staticmethod
    def _rtf_to_text(value):
        """
        Convertit un contenu RTF en texte brut.

        Supprime les commandes, groupes de destination et métadonnées,
        et conserve uniquement le texte métier (accents compris).
        En cas d'erreur de parsing, la valeur d'origine est renvoyée.
        """
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