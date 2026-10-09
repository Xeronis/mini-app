"""Ejecuta pip-audit y guarda la evidencia.

Uso:  python 3-parcheo/auditar.py antes
      python 3-parcheo/auditar.py despues [archivo_requirements]
"""
import subprocess  # nosec
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
momento = sys.argv[1] if len(sys.argv) > 1 else "antes"
req = sys.argv[2] if len(sys.argv) > 2 else "requirements.txt"
r = subprocess.run(  # nosec
    [sys.executable, "-m", "pip_audit", "-r", req, "--no-deps", "--disable-pip"],
    cwd=BASE, capture_output=True, text=True,
)
salida = (r.stdout + r.stderr).strip()
print(salida)
destino = BASE / "evidencia" / f"auditoria_{momento}.txt"
destino.write_text(f"Archivo auditado: {req}\nCodigo de salida: {r.returncode}\n\n{salida}\n", encoding="utf-8")
print(f"\n[evidencia guardada en {destino.relative_to(BASE)}]")
