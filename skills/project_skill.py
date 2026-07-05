from __future__ import annotations

import ast as ast_module
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
ALLOWED_DIRS = [
    PROJECT_ROOT,
    PROJECT_ROOT / "training",
]
_TEMP_PERMITS: set[Path] = set()


def _resolve_path(path: str) -> Path | None:
    p = Path(path)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    p = p.resolve()
    for allowed in list(ALLOWED_DIRS) + list(_TEMP_PERMITS):
        try:
            p.relative_to(allowed)
            return p
        except ValueError:
            pass
    return None


def permit_path(path: str) -> str:
    p = Path(path).resolve()
    if not p.exists():
        return f"La ruta no existe: {p}"
    _TEMP_PERMITS.add(p)
    return f"Permiso concedido: {p}"


def deny_path(path: str) -> str:
    p = Path(path).resolve()
    _TEMP_PERMITS.discard(p)
    return f"Permiso revocado: {p}"


def list_permitted() -> str:
    if not _TEMP_PERMITS:
        return "No hay rutas externas autorizadas."
    lines = ["Rutas autorizadas:"]
    for p in sorted(_TEMP_PERMITS, key=str):
        lines.append(f"  - {p}")
    return "\n".join(lines)


def read_file(path: str) -> str:
    resolved = _resolve_path(path)
    if not resolved:
        return f"Acceso denegado: {path} no está en el proyecto"
    if not resolved.exists():
        return f"Archivo no encontrado: {resolved}"
    if not resolved.is_file():
        return f"No es un archivo: {resolved}"
    try:
        content = resolved.read_text(encoding="utf-8", errors="replace")
        return content
    except Exception as e:
        return f"Error leyendo {resolved}: {e}"


def write_file(path: str, content: str) -> str:
    resolved = _resolve_path(path)
    if not resolved:
        return f"Acceso denegado: {path} no está en el proyecto"
    try:
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        return f"Archivo escrito: {resolved}"
    except Exception as e:
        return f"Error escribiendo {resolved}: {e}"


def edit_file(path: str, old_string: str, new_string: str) -> str:
    resolved = _resolve_path(path)
    if not resolved:
        return f"Acceso denegado: {path} no está en el proyecto"
    if not resolved.exists():
        return f"Archivo no encontrado: {resolved}"
    try:
        content = resolved.read_text(encoding="utf-8", errors="replace")
        if old_string not in content:
            return f"Texto a reemplazar no encontrado en {resolved}"
        new_content = content.replace(old_string, new_string, 1)
        resolved.write_text(new_content, encoding="utf-8")
        return f"Editado: {resolved}"
    except Exception as e:
        return f"Error editando {resolved}: {e}"


def glob(pattern: str, base_path: str = "") -> str:
    resolved = _resolve_path(base_path) if base_path else PROJECT_ROOT
    if not resolved:
        resolved = PROJECT_ROOT
    try:
        matches = list(resolved.rglob(pattern))
        if not matches:
            return f"Sin resultados para: {pattern}"
        return "\n".join(str(m.relative_to(PROJECT_ROOT)) for m in matches[:50])
    except Exception as e:
        return f"Error en glob: {e}"


def grep(pattern: str, path: str = "", include: str = "*.py") -> str:
    import shutil

    resolved = _resolve_path(path) if path else PROJECT_ROOT
    if not resolved:
        resolved = PROJECT_ROOT
    try:
        if shutil.which("rg"):
            cmd = [
                "rg",
                "-n",
                pattern,
                "--glob",
                include,
                "--max-count",
                "5",
                "-l",
            ]
            result = subprocess.run(
                cmd + [str(resolved)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            files = [line.strip() for line in result.stdout.split("\n") if line.strip()]
            if files:
                output = []
                for f in files[:10]:
                    fpath = Path(f)
                    try:
                        rel = fpath.relative_to(PROJECT_ROOT)
                    except ValueError:
                        rel = fpath
                    output.append(str(rel))
                return "\n".join(output)

        matched = [
            f for f in resolved.rglob(include) if f.is_file() and pattern.lower() in f.read_text(encoding="utf-8", errors="replace").lower()
        ]
        if not matched:
            return f"Sin resultados para: {pattern}"
        return "\n".join(str(m.relative_to(PROJECT_ROOT)) for m in matched[:10])
    except Exception as e:
        return f"Error en grep: {e}"


def run_file(executable: str, *args: str) -> str:
    """Ejecuta un archivo o comando directamente (sin shell)."""
    try:
        cmd = [executable] + list(args)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(PROJECT_ROOT),
        )
        output = result.stdout.strip() if result.stdout.strip() else ""
        if result.stderr.strip():
            stderr = result.stderr.strip()
            if output:
                output += f"\n[stderr]\n{stderr}"
            else:
                output = f"[stderr]\n{stderr}"
        return output or "Comando ejecutado (sin salida)."
    except subprocess.TimeoutExpired:
        return "El comando tardó demasiado (>120s) y fue cancelado."
    except Exception as e:
        return f"Error ejecutando comando: {e}"


def run_shell(command: str) -> str:
    """Ejecuta un comando shell con validación estricta."""
    blacklist = [
        "rm -rf",
        "rmdir",
        "rd ",
        "del ",
        "erase ",
        "format ",
        "format:",
        "shutdown",
        "reboot",
        "restart-computer",
        "cacls",
        "icacls",
        "takeown",
        "attrib ",
        "diskpart",
        "wmic ",
        "powershell",
        "pwsh ",
        "reg ",
        "regedit",
        "sc ",
        "schtasks",
        "net user",
        "net localgroup",
        "net stop",
        "net start",
        "wevtutil",
        "bcdedit",
        "bootrec",
        "fsutil",
        "vssadmin",
        "wbadmin",
        "|",
        ">",
        "<",
        "&",
        ";",
        "`",
        "$(",
        "@(",
    ]
    cmd_lower = command.lower()
    for b in blacklist:
        if b in cmd_lower:
            return f"Comando bloqueado por seguridad: {b}"

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(PROJECT_ROOT),
        )
        output = result.stdout.strip() if result.stdout.strip() else ""
        if result.stderr.strip():
            stderr = result.stderr.strip()
            if output:
                output += f"\n[stderr]\n{stderr}"
            else:
                output = f"[stderr]\n{stderr}"
        return output or "Comando ejecutado (sin salida)."
    except subprocess.TimeoutExpired:
        return "El comando tardó demasiado (>120s) y fue cancelado."
    except Exception as e:
        return f"Error ejecutando comando: {e}"


def get_file_tree(path: str = "", max_depth: int = 3) -> str:
    resolved = _resolve_path(path) if path else PROJECT_ROOT
    if not resolved:
        resolved = PROJECT_ROOT

    lines = []
    root_name = resolved.name or str(resolved)

    def walk(p: Path, depth: int) -> None:
        if depth > max_depth:
            return
        try:
            entries = sorted(p.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
        except PermissionError:
            return
        for entry in entries:
            if entry.name.startswith(".") or entry.name.startswith("__pycache__"):
                continue
            indent = "  " * depth
            if entry.is_dir():
                lines.append(f"{indent}{entry.name}/")
                walk(entry, depth + 1)
            else:
                lines.append(f"{indent}{entry.name}")

    walk(resolved, 0)
    return f"{root_name}/\n" + "\n".join(lines)


def check_syntax(path: str) -> str:
    resolved = _resolve_path(path)
    if not resolved:
        return f"Acceso denegado: {path}"
    if not resolved.exists():
        return f"Archivo no encontrado: {resolved}"
    try:
        content = resolved.read_text(encoding="utf-8", errors="replace")
        ast_module.parse(content)
        return f"Syntax OK: {resolved.name}"
    except SyntaxError as e:
        return f"Syntax Error en {resolved.name}: {e}"
    except Exception as e:
        return f"Error: {e}"
