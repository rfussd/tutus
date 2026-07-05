from __future__ import annotations

import shutil
from pathlib import Path

FORBIDDEN_PATHS = [
    Path("C:/Windows"),
    Path("C:/Program Files"),
    Path("C:/Program Files (x86)"),
    Path.home() / "AppData",
]

FOLDER_MAP = {
    "downloads": Path.home() / "Downloads",
    "descargas": Path.home() / "Downloads",
    "desktop": Path.home() / "Desktop",
    "escritorio": Path.home() / "Desktop",
    "documents": Path.home() / "Documents",
    "documentos": Path.home() / "Documents",
    "music": Path.home() / "Music",
    "música": Path.home() / "Music",
    "pictures": Path.home() / "Pictures",
    "imágenes": Path.home() / "Pictures",
    "videos": Path.home() / "Videos",
}

CATEGORIES = {
    "Imágenes": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico"],
    "Videos": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"],
    "Música": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"],
    "Documentos": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".csv"],
    "Comprimidos": [".zip", ".rar", ".7z", ".tar", ".gz"],
    "Programas": [".exe", ".msi", ".dmg", ".deb", ".apk"],
    "Código": [".py", ".js", ".html", ".css", ".json", ".xml", ".java", ".cpp"],
}


def is_safe_path(path: Path) -> bool:
    path = path.resolve()
    for forbidden in FORBIDDEN_PATHS:
        if str(path).startswith(str(forbidden)):
            return False
    return True


def organize_downloads() -> str:
    downloads = Path.home() / "Downloads"
    moved = 0
    errors = []

    for file in downloads.iterdir():
        if not file.is_file():
            continue
        ext = file.suffix.lower()
        destino = downloads / "Otros"

        for categoria, extensiones in CATEGORIES.items():
            if ext in extensiones:
                destino = downloads / categoria
                break

        try:
            destino.mkdir(exist_ok=True)
            shutil.move(str(file), str(destino / file.name))
            moved += 1
        except Exception as e:
            errors.append(str(e))

    return f"Organicé {moved} archivos en Descargas." + (f" Errores: {len(errors)}" if errors else "")


def list_files(folder: str = "descargas") -> str:
    path = FOLDER_MAP.get(folder.lower())
    if not path:
        return f"Carpeta '{folder}' no reconocida."
    if not path.exists():
        return f"La carpeta {folder} no existe."

    files = [f.name for f in path.iterdir() if f.is_file()]
    if not files:
        return f"La carpeta {folder} está vacía."

    return f"Archivos en {folder} ({len(files)}):\n" + "\n".join(files[:20])


def move_file(filename: str, destination: str) -> str:
    dest_path = FOLDER_MAP.get(destination.lower())
    if not dest_path:
        return f"Destino '{destination}' no permitido."

    search_paths = [Path.home() / "Downloads", Path.home() / "Desktop"]
    source = None
    for sp in search_paths:
        candidate = sp / filename
        if candidate.exists():
            source = candidate
            break

    if not source:
        return f"No encontré '{filename}'."

    if not is_safe_path(dest_path):
        return "Ruta de destino no permitida."

    try:
        shutil.move(str(source), str(dest_path / filename))
        return f"Moví '{filename}' a {destination}."
    except Exception as e:
        return f"Error al mover: {str(e)}"
