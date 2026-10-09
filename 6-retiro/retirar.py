"""Retiro y eliminacion segura de la mini app.

Uso:
  python 6-retiro/retirar.py --responsable "Tu Nombre"             # SIMULACION (no borra nada)
  python 6-retiro/retirar.py --responsable "Tu Nombre" --ejecutar  # retiro REAL (pide confirmacion)

Pasos: 1) respaldo cifrado  2) revocar credenciales  3) sanitizar  4) verificar  5) acta de baja
"""
import argparse
import hashlib
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from cryptography.fernet import Fernet

AQUI = Path(__file__).resolve().parent
BASE = AQUI.parent
A_RESPALDAR = ["data", "logs"]
A_DESTRUIR = ["data", "logs", ".env", "5-monitoreo/alertas.log", "5-monitoreo/bloqueadas.txt"]
CHECKLIST_MANUAL = [
    "Revocar tokens personales de GitHub usados con este repositorio",
    "Eliminar secretos de GitHub Actions (Settings > Secrets)",
    "Eliminar usuarios/llaves SSH o cuentas de servicio asociadas",
    "Archivar (no borrar) el repositorio en GitHub para conservar la trazabilidad",
    "Notificar a los usuarios la fecha de fin de soporte",
]


def sha256(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(65536), b""):
            h.update(bloque)
    return h.hexdigest()


def archivos_de(rutas):
    for r in rutas:
        p = BASE / r
        if p.is_file():
            yield p
        elif p.is_dir():
            for sub in sorted(p.rglob("*")):
                if sub.is_file():
                    yield sub


def sobrescribir_y_borrar(p):
    """Sobrescribe con datos aleatorios y elimina. (En SSD/journaling no es garantia total.)"""
    tam = p.stat().st_size
    with open(p, "r+b") as f:
        f.write(os.urandom(tam))
        f.flush()
        os.fsync(f.fileno())
    p.unlink()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--responsable", required=True)
    ap.add_argument("--ejecutar", action="store_true", help="hacer el retiro real")
    ap.add_argument("--si", action="store_true", help="no pedir confirmacion")
    a = ap.parse_args()
    real = a.ejecutar
    modo = "EJECUCION REAL" if real else "SIMULACION (no se borra nada)"
    print(f"== Retiro seguro: {modo} ==\n")

    objetivos = list(archivos_de(A_DESTRUIR))
    respaldables = list(archivos_de(A_RESPALDAR))
    print("Archivos que se respaldarian (cifrados):")
    for p in respaldables:
        print("  -", p.relative_to(BASE))
    print("Archivos que se eliminarian de forma segura:")
    for p in objetivos:
        print("  -", p.relative_to(BASE), f"({p.stat().st_size} bytes)")
    if not real:
        print("\nSimulacion terminada. Agrega --ejecutar para el retiro real.")
        return
    if not a.si and input("\nEscribe RETIRAR para continuar: ").strip() != "RETIRAR":
        print("Cancelado.")
        sys.exit(1)

    inicio = datetime.now(timezone.utc)
    # 1. Respaldo final cifrado
    with tempfile.TemporaryDirectory() as tmp:
        for r in A_RESPALDAR:
            if (BASE / r).exists():
                shutil.copytree(BASE / r, Path(tmp) / "contenido" / r)
        zip_tmp = shutil.make_archive(str(Path(tmp) / "respaldo"), "zip", Path(tmp) / "contenido")
        llave = Fernet.generate_key()
        cifrado = Fernet(llave).encrypt(Path(zip_tmp).read_bytes())
    respaldo = AQUI / "respaldo_final.enc"
    respaldo.write_bytes(cifrado)
    (AQUI / "llave_respaldo.key").write_bytes(llave)
    hash_respaldo = sha256(respaldo)
    print(f"[1/5] Respaldo cifrado creado: {respaldo.name} (SHA-256 {hash_respaldo[:16]}...)")

    # 2. Revocar credenciales (la fuente local son los secretos del .env)
    print("[2/5] Credenciales locales (.env) se destruyen en el paso 3. Pendientes manuales: ver acta.")

    # 3. Sanitizacion
    eliminados = []
    for p in objetivos:
        eliminados.append((str(p.relative_to(BASE)), p.stat().st_size))
        sobrescribir_y_borrar(p)
    for carpeta in ("data", "logs"):
        d = BASE / carpeta
        if d.exists():
            shutil.rmtree(d)
    print(f"[3/5] {len(eliminados)} archivo(s) sobrescrito(s) y eliminado(s).")

    # 4. Verificacion
    quedan = [r for r in A_DESTRUIR if (BASE / r).exists()]
    print("[4/5] Verificacion:", "OK, no queda ningun dato" if not quedan else f"QUEDAN: {quedan}")

    # 5. Acta de baja
    fin = datetime.now(timezone.utc)
    filas = "\n".join(f"| `{n}` | {t} bytes | Sobrescrito + eliminado |" for n, t in eliminados)
    manual = "\n".join(f"- [ ] {c}" for c in CHECKLIST_MANUAL)
    acta = f"""# Acta de baja y retiro seguro del software

| Campo | Valor |
|---|---|
| Sistema | Mini app demostrativa (Flask) |
| Responsable | {a.responsable} |
| Inicio | {inicio.isoformat(timespec='seconds')} |
| Fin | {fin.isoformat(timespec='seconds')} |
| Motivo | Fin de ciclo de vida (proyecto demostrativo) |

## 1. Respaldo final
- Archivo: `6-retiro/respaldo_final.enc` (cifrado con Fernet / AES)
- SHA-256: `{hash_respaldo}`
- La llave (`llave_respaldo.key`) debe guardarse **aparte**, en custodia, y nunca junto al respaldo.

## 2. Datos eliminados
| Archivo | Tamano | Metodo |
|---|---|---|
{filas}

Verificacion posterior: {"no queda ningun dato en las rutas eliminadas" if not quedan else "QUEDAN: " + ", ".join(quedan)}.

## 3. Revocacion de accesos (manual)
{manual}

## 4. Nota sobre la sanitizacion
Sobrescribir archivos es efectivo en discos magneticos, pero en SSD y sistemas de archivos con
journaling no garantiza el borrado fisico. En produccion se usa **borrado criptografico** (cifrar
y destruir la llave) o la destruccion certificada del medio (NIST SP 800-88).

## 5. Cumplimiento
Retencion del respaldo: segun la politica de la organizacion y la normativa de proteccion de datos aplicable.

Firma del responsable: ______________________
"""
    (AQUI / "acta_de_baja.md").write_text(acta, encoding="utf-8")
    print("[5/5] Acta generada: 6-retiro/acta_de_baja.md")


if __name__ == "__main__":
    main()
