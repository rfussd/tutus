from __future__ import annotations

import ast
import subprocess
import sys
import textwrap


def _check_code_safety(code: str) -> tuple[bool, str]:
    dangerous_modules = {
        "ctypes",
        "socket",
        "http.server",
        "os",
        "shutil",
        "subprocess",
        "sys",
        "builtins",
        "pathlib",
        "pickle",
        "shlex",
        "base64",
        "inspect",
        "importlib",
        "compile",
        "eval",
        "exec",
    }
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in dangerous_modules:
                        return False, f"Módulo no permitido: {alias.name}"
            if isinstance(node, ast.ImportFrom):
                if node.module in dangerous_modules:
                    return False, f"Módulo no permitido: {node.module}"
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    name = f"{ast.unparse(node.func.value)}.{node.func.attr}"
                    # block attribute access on dangerous objects too
                    base = (
                        ast.unparse(node.func.value)
                        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
                        else ""
                    )
                    if base in ("os", "shutil", "subprocess", "pickle", "builtins"):
                        return False, f"Operación no permitida: {name}"
                elif isinstance(node.func, ast.Name):
                    name = node.func.id
                    if name in ("eval", "exec", "__import__", "compile", "open"):
                        return False, f"Operación no permitida: {name}"
                else:
                    continue
                if name in (
                    "os.system",
                    "os.popen",
                    "os.execl",
                    "os.execle",
                    "os.execlp",
                    "os.execle",
                    "os.execv",
                    "os.execve",
                    "os.execvp",
                    "os.execvpe",
                    "os.spawnl",
                    "os.spawnle",
                    "os.spawnlp",
                    "os.spawnlpe",
                    "os.spawnv",
                    "os.spawnve",
                    "os.spawnvp",
                    "os.spawnvpe",
                    "os.startfile",
                    "subprocess.call",
                    "subprocess.Popen",
                    "subprocess.run",
                    "subprocess.check_call",
                    "subprocess.check_output",
                    "shutil.rmtree",
                    "shutil.move",
                    "shutil.copy",
                    "shutil.copytree",
                    "builtins.exec",
                    "builtins.eval",
                    "builtins.__import__",
                    "pickle.load",
                    "pickle.loads",
                    "pickle.Unpickler",
                ):
                    return False, f"Operación no permitida: {name}"
    except SyntaxError as e:
        return False, f"Error de sintaxis: {e}"

    return True, ""


def execute_python(code: str) -> str:
    safe, msg = _check_code_safety(code)
    if not safe:
        return msg

    wrapped = textwrap.dedent(f"""
import sys
try:
    exec(\"\"\"
{code}
\"\"\")
except Exception as e:
    print(f"Error: {{e}}", file=sys.stderr)
""")

    try:
        result = subprocess.run(
            [sys.executable, "-c", wrapped],
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout.strip() if result.stdout.strip() else ""
        if result.stderr.strip():
            output += f"\n{result.stderr.strip()}" if output else result.stderr.strip()
        return output or "Código ejecutado (sin salida)."
    except subprocess.TimeoutExpired:
        return "El código tardó demasiado (>30s) y fue cancelado."
    except Exception as e:
        return f"Error de ejecución: {e}"
