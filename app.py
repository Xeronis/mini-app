"""Mini app demostrativa (login + lista de pedidos).

Es el "sujeto de estudio" del ciclo de vida seguro: configuracion, verificacion
del entorno, parcheo, DevSecOps, monitoreo y retiro.
"""
import hmac
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, redirect, render_template_string, request, session, url_for

BASE = Path(__file__).resolve().parent
LOG = BASE / "logs" / "app.log"
BLOQUEADAS = BASE / "5-monitoreo" / "bloqueadas.txt"
PEDIDOS = BASE / "data" / "pedidos.json"


def cargar_env(ruta=BASE / ".env"):
    """Carga variables desde .env: los secretos NO viven en el codigo ni en Git."""
    if ruta.exists():
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                clave, valor = linea.split("=", 1)
                os.environ.setdefault(clave.strip(), valor.strip())


cargar_env()
for requerida in ("SECRET_KEY", "APP_USER", "APP_PASSWORD"):
    if not os.environ.get(requerida):
        raise SystemExit(f"Falta {requerida}. Copia .env.example a .env y completalo.")

app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]
LOG.parent.mkdir(exist_ok=True)

LOGIN_HTML = """
<h2>Mini app - Login</h2>
<form method="post">
  Usuario: <input name="usuario"><br>
  Clave: <input name="clave" type="password"><br>
  <button type="submit">Entrar</button>
</form>
<p style="color:red">{{ mensaje }}</p>
"""

PEDIDOS_HTML = """
<h2>Pedidos</h2>
<ul>{% for p in pedidos %}<li>#{{ p.id }} - {{ p.plato }} (x{{ p.cantidad }})</li>{% endfor %}</ul>
<a href="{{ url_for('logout') }}">Salir</a>
"""


def registrar(usuario, resultado):
    """Una linea por intento de login: es la fuente de datos del monitoreo."""
    ip = request.remote_addr or "?"
    usuario = usuario.replace("\n", " ").replace("\r", " ").replace("|", "/")[:80]
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"{ts} | {ip} | {usuario} | {resultado}\n")


def ip_bloqueada(ip):
    return BLOQUEADAS.exists() and ip in BLOQUEADAS.read_text(encoding="utf-8").split()


@app.route("/login", methods=["GET", "POST"])
def login():
    mensaje = ""
    if request.method == "POST":
        usuario = request.form.get("usuario", "")
        clave = request.form.get("clave", "")
        if ip_bloqueada(request.remote_addr or ""):
            registrar(usuario, "BLOQUEADO")
            return "Acceso bloqueado por el equipo de seguridad", 403
        ok_u = hmac.compare_digest(usuario.encode(), os.environ["APP_USER"].encode())
        ok_c = hmac.compare_digest(clave.encode(), os.environ["APP_PASSWORD"].encode())
        if ok_u and ok_c:
            session["usuario"] = usuario
            registrar(usuario, "OK")
            return redirect(url_for("pedidos"))
        registrar(usuario, "FALLO")
        mensaje = "Credenciales invalidas"
    return render_template_string(LOGIN_HTML, mensaje=mensaje)


@app.route("/")
@app.route("/pedidos")
def pedidos():
    if "usuario" not in session:
        return redirect(url_for("login"))
    datos = json.loads(PEDIDOS.read_text(encoding="utf-8"))
    return render_template_string(PEDIDOS_HTML, pedidos=datos)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(
        host=os.environ.get("APP_HOST", "127.0.0.1"),
        port=int(os.environ.get("APP_PORT", "5000")),
        debug=False,
    )
