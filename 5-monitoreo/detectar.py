"""Deteccion de ataques leyendo logs/app.log.

Uso:
  python 5-monitoreo/detectar.py               # analiza el log una vez
  python 5-monitoreo/detectar.py --vigilar     # queda leyendo en vivo
  python 5-monitoreo/detectar.py --vigilar --responder   # y bloquea la IP atacante

Reglas:  1) fuerza bruta: 5 fallos de la misma IP en 60 s
         2) inyeccion SQL: patrones tipicos en el campo usuario
"""
import re
import sys
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent
LOG = AQUI.parent / "logs" / "app.log"
ALERTAS = AQUI / "alertas.log"
BLOQUEADAS = AQUI / "bloqueadas.txt"
UMBRAL, VENTANA = 5, 60
SQLI = re.compile(r"('|\")\s*(or|and)\s|--|;\s*drop|union\s+select|/\*", re.I)


def ahora():
    return datetime.now(timezone.utc)


class Detector:
    def __init__(self, responder=False):
        self.fallos = defaultdict(deque)   # ip -> instantes de fallos
        self.alertadas = set()             # (tipo, ip) ya avisadas
        self.responder = responder

    def procesar(self, linea):
        partes = [p.strip() for p in linea.split(" | ")]
        if len(partes) != 4:
            return
        ts, ip, usuario, res = partes
        t = datetime.fromisoformat(ts)
        if res == "FALLO":
            cola = self.fallos[ip]
            cola.append(t)
            while (t - cola[0]).total_seconds() > VENTANA:
                cola.popleft()
            if len(cola) >= UMBRAL and ("FUERZA_BRUTA", ip) not in self.alertadas:
                self.alertar("FUERZA_BRUTA", ip, cola[0], f"{len(cola)} fallos en {VENTANA}s")
        if SQLI.search(usuario) and ("INYECCION_SQL", ip) not in self.alertadas:
            self.alertar("INYECCION_SQL", ip, t, f"usuario sospechoso: {usuario}")

    def alertar(self, tipo, ip, inicio, detalle):
        self.alertadas.add((tipo, ip))
        t_alerta = ahora()
        mttd = (t_alerta - inicio).total_seconds()
        msg = (f"ALERTA {tipo} | ip={ip} | {detalle} | inicio={inicio.isoformat(timespec='seconds')} "
               f"| alerta={t_alerta.isoformat(timespec='seconds')} | MTTD={mttd:.1f}s")
        print(msg)
        with ALERTAS.open("a", encoding="utf-8") as f:
            f.write(msg + "\n")
        if self.responder:
            ya = BLOQUEADAS.read_text(encoding="utf-8").split() if BLOQUEADAS.exists() else []
            if ip not in ya:
                with BLOQUEADAS.open("a", encoding="utf-8") as f:
                    f.write(ip + "\n")
            mttr = (ahora() - inicio).total_seconds()
            print(f"  -> RESPUESTA: IP {ip} bloqueada | MTTR={mttr:.1f}s (inicio del ataque -> contencion)")


def main():
    vigilar = "--vigilar" in sys.argv
    det = Detector(responder="--responder" in sys.argv)
    if not LOG.exists():
        if not vigilar:
            print(f"No existe {LOG}. Inicia la app y genera trafico primero.")
            return
        print("Esperando a que la app genere logs/app.log ...")
        while not LOG.exists():
            time.sleep(0.5)
    with LOG.open(encoding="utf-8") as f:
        for linea in f:
            det.procesar(linea)
        if not vigilar:
            if not det.alertadas:
                print("Sin alertas: no se detecto actividad sospechosa.")
            return
        print("Vigilando logs/app.log ... (Ctrl+C para salir)")
        try:
            while True:
                linea = f.readline()
                if linea:
                    det.procesar(linea)
                else:
                    time.sleep(0.3)
        except KeyboardInterrupt:
            print("\nVigilancia detenida.")


if __name__ == "__main__":
    main()
