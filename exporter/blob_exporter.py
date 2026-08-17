"""
Export des données binaires vers des fichiers sur disque.

Détecte le format des données binaires, écrit les fichiers
et renvoie un chemin relatif au dossier d'export.
"""

import os
import re

from .config import EXPORT_DIR, MEDIA_DIR

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


class BlobExporter:
    """
    Extraction des données binaires (images, fichiers) vers des fichiers.

    Détecte le format grâce aux octets magiques, génère un nom de fichier
    déterministe à partir de la table, de la clé et de la colonne,
    et renvoie un chemin relatif au dossier d'export.

    Ne s'occupe pas de savoir si une valeur est binaire ou texte :
    elle reçoit uniquement des données binaires à écrire.
    """

    def __init__(self, export_dir=EXPORT_DIR, media_dir=None):
        """
        Prépare l'exporteur avec les chemins du dossier d'export.

        Le sous-dossier média se trouve par défaut sous le dossier d'export.
        """
        self.export_dir = export_dir
        self.media_dir = media_dir or os.path.join(export_dir, MEDIA_DIR)

    def export(self, data, table_name, key, column):
        """
        Écrit les données binaires dans un fichier et renvoie son chemin relatif.

        Si un fichier identique existe déjà, le chemin existant est réutilisé
        (déduplication) ; sinon un suffixe numéroté évite les collisions.
        """
        ext = self._detect_ext(data)
        base = f"{self._sanitize_name(table_name)}_{key}_{column}"
        path = os.path.join(self.media_dir, f"{base}.{ext}")

        n = 2
        while os.path.exists(path):
            with open(path, "rb") as f:
                if f.read() == data:
                    return os.path.relpath(path, self.export_dir).replace("\\", "/")
            path = os.path.join(self.media_dir, f"{base}_{n}.{ext}")
            n += 1

        with open(path, "wb") as f:
            f.write(data)

        return os.path.relpath(path, self.export_dir).replace("\\", "/")

    @staticmethod
    def _detect_ext(data):
        """Renvoie l'extension de fichier détectée via les octets magiques."""
        for magic, ext in MAGIC_EXT:
            if data.startswith(magic):
                return ext

        return "bin"

    @staticmethod
    def _sanitize_name(name):
        """Remplace les caractères invalides pour un nom de fichier."""
        return re.sub(r'[\\/:*?"<>|]', "_", name)