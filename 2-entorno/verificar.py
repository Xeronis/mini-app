"""Verificacion del entorno: compara el estado REAL contra la linea base.

Uso:  python 2-entorno/verificar.py
Sale con codigo 1 si encuentra desviaciones (sirve tambien en un pipeline).
"""
import os
import re
import socket
import subprocess  # nosec - solo se usa para consultar git
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
BASELINE = Path(__file__).resolve().parent / "baseline.txt"
PUERTOS_A_REVISAR = [21, 22, 23, 80, 443, 3306, 5432, 5000, 8000, 8080, 8888]
ES_WINDOWS = os.name == "nt"
desviaciones = 0


def leer(ruta):
    datos = {}
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if linea and not linea.startswith("#") and "=" in linea:
            k, v = linea.split("=", 1)
            datos[k.strip()] = v.strip()
    return datos


def resultado(nombre, ok, detalle=""):
    global desviaciones
    if ok is None:
        estado = "OMITIDO "
    elif ok:
        estado = "OK      "
    else:
        estado = "DESVIACION"
        desviaciones += 1
    print(f"[{estado}] {nombre}" + (f" -> {detalle}" if detalle else ""))


def git(*args):
    try:
        r = subprocess.run(["git", *args], cwd=BASE, capture_output=True, text=True)  # nosec
        return r.returncode, r.stdout.strip()
    except FileNotFoundError:
        return None, ""


def main():
    base = leer(BASELINE)
    env = leer(BASE / ".env") if (BASE / ".env").exists() else {}
    print(f"== Verificacion del entorno contra linea base {base['LINEA_BASE_TAG']} ==\n")

    # 1. Version de Python
    minimo = tuple(int(x) for x in base["PYTHON_MINIMO"].split("."))
    actual = sys.version_info[:2]
    resultado("Version de Python", actual >= minimo, f"actual {actual[0]}.{actual[1]}, minimo {base['PYTHON_MINIMO']}")

    # 2. Existe .env (config fuera del codigo)
    resultado("Archivo .env presente", (BASE / ".env").exists(), "copia .env.example a .env si falta")

    # 3. Permisos del .env
    if ES_WINDOWS or not (BASE / ".env").exists():
        resultado("Permisos de .env", None, "no aplica en Windows o no existe")
    else:
        permisos = oct(os.stat(BASE / ".env").st_mode & 0o777)[-3:]
        resultado("Permisos de .env", permisos == base["PERMISOS_ENV"], f"actual {permisos}, esperado {base['PERMISOS_ENV']}")

    # 4. .env no esta en Git
    codigo, _ = git("ls-files", "--error-unmatch", ".env")
    if codigo is None or codigo not in (0, 1):
        resultado(".env fuera del repositorio Git", None, "git no disponible o no es un repo")
    else:
        resultado(".env fuera del repositorio Git", codigo == 1, "esta rastreado por Git" if codigo == 0 else "")

    # 5. Existe la linea base (tag) en Git
    codigo, salida = git("tag", "--list", base["LINEA_BASE_TAG"])
    if codigo != 0:
        resultado(f"Tag de linea base {base['LINEA_BASE_TAG']}", None, "git no disponible o no es un repo")
    else:
        resultado(f"Tag de linea base {base['LINEA_BASE_TAG']}", salida == base["LINEA_BASE_TAG"], "no existe el tag" if not salida else "")

    # 6. Modo debug apagado
    codigo_app = (BASE / "app.py").read_text(encoding="utf-8")
    resultado("Modo debug desactivado", not re.search(r"debug\s*=\s*True", codigo_app))

    # 7. Host de escucha esperado
    host = env.get("APP_HOST", "127.0.0.1")
    resultado("Host de escucha", host == base["HOST_ESPERADO"], f"actual {host}, esperado {base['HOST_ESPERADO']}")

    # 8. Dependencias fijadas (reproducibilidad)
    sin_fijar = [
        l for l in (BASE / "requirements.txt").read_text(encoding="utf-8").splitlines()
        if l.strip() and not l.startswith("#") and "==" not in l
    ]
    resultado("Dependencias con version fija", not sin_fijar, ", ".join(sin_fijar))

    # 9. Puertos abiertos no permitidos
    permitidos = {int(p) for p in base["PUERTOS_PERMITIDOS"].split(",")}
    abiertos = []
    for puerto in PUERTOS_A_REVISAR:
        with socket.socket() as s:
            s.settimeout(0.3)
            if s.connect_ex(("127.0.0.1", puerto)) == 0:
                abiertos.append(puerto)
    inesperados = [p for p in abiertos if p not in permitidos]
    resultado("Puertos abiertos inesperados", not inesperados, f"abiertos: {abiertos}, inesperados: {inesperados}")

    # 10. Archivos con escritura para todos
    if ES_WINDOWS:
        resultado("Archivos escribibles por todos", None, "no aplica en Windows")
    else:
        malos = []
        for raiz, dirs, archivos in os.walk(BASE):
            dirs[:] = [d for d in dirs if d not in (".git", ".venv", "__pycache__")]
            for a in archivos:
                if os.stat(Path(raiz) / a).st_mode & 0o002:
                    malos.append(str((Path(raiz) / a).relative_to(BASE)))
        resultado("Archivos escribibles por todos", not malos, ", ".join(malos))

    print()
    if desviaciones:
        print(f"RESULTADO: {desviaciones} desviacion(es) respecto a la linea base.")
        sys.exit(1)
    print("RESULTADO: el entorno coincide con la linea base.")


if __name__ == "__main__":
    main()
