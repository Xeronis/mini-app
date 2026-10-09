# Mini app: ciclo de vida seguro del software

Una mini app Flask (login + pedidos) que recorre las 6 etapas del tema
Mantenimiento, DevOps y Retiro Seguro del Software**. Todo en Python: funciona igual en
Windows, Mac y Linux.

| Carpeta | Etapa | Que muestra |
|---|---|---|
| `1-configuracion/` | Gestion de configuracion | Git, linea base (tag), PR, rollback, secretos fuera del repo |
| `2-entorno/` | Verificacion del entorno | `verificar.py` compara el entorno contra `baseline.txt` |
| `3-parcheo/` | Parcheo y vulnerabilidades | `pip-audit` antes y despues de actualizar |
| `.github/workflows/` | DevSecOps | Pipeline con Bandit (SAST) + pip-audit que bloquea |
| `5-monitoreo/` | Monitoreo e incidentes | `detectar.py` alerta y bloquea; MTTD y MTTR |
| `6-retiro/` | Retiro seguro | `retirar.py`: respaldo cifrado, sanitizacion y acta de baja |

## Preparacion (10 min)

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate        Mac/Linux:  source .venv/bin/activate
pip install -r requirements.txt -r requirements-herramientas.txt
cp .env.example .env        # Windows: copy .env.example .env   (y cambia los valores)
python app.py               # http://127.0.0.1:5000/login
```

## Guion de la noche (con capturas en `evidencia/`)

**Etapa 1.** Sigue `1-configuracion/pasos.md`.

**Etapa 2.**
```bash
python 2-entorno/verificar.py        # con el tag v1.0 creado: todo OK
# Provoca una desviacion:
#   Mac/Linux:  chmod 777 .env
#   Windows:    cambia debug=False por debug=True en app.py
python 2-entorno/verificar.py        # CAPTURA: marca DESVIACION
```

**Etapa 3.** (`requirements.txt` ya trae versiones viejas con CVE a proposito)
```bash
python 3-parcheo/auditar.py antes                 # CAPTURA: lista de vulnerabilidades
pip install -r 3-parcheo/requirements-parcheado.txt
cp 3-parcheo/requirements-parcheado.txt requirements.txt   # Windows: copy /Y
python 3-parcheo/auditar.py despues               # CAPTURA: "No known vulnerabilities found"
python app.py                                     # comprueba que la app sigue funcionando
```
Prioriza con CVSS: busca 1 o 2 de los IDs del reporte en https://nvd.nist.gov o en la
pestana Advisories de GitHub, anota su puntaje y explica por que atiendes primero el mas alto.
Sin parche disponible: mitigacion (deshabilitar la funcion afectada, regla de filtrado, aislar
el servicio) mientras sale la correccion.

**Etapa 4.** Antes de parchear, haz *push* con el `requirements.txt` viejo: el workflow
`seguridad` queda en **rojo** (CAPTURA de la pestana Actions). Luego sube el parche: queda en
**verde** (CAPTURA).

**Etapa 5.** En tres terminales (con la app corriendo):
```bash
python 5-monitoreo/detectar.py --vigilar --responder
python 5-monitoreo/simular_ataque.py
```
CAPTURA: alertas `FUERZA_BRUTA` e `INYECCION_SQL`, con MTTD y MTTR, y la IP bloqueada.
Para desbloquearte: vacia `5-monitoreo/bloqueadas.txt`.
Leccion aprendida: sin limite de intentos ni bloqueo automatico, el ataque habria seguido.

**Etapa 6.** Hazla **al final** (borra datos de la app).
```bash
python 6-retiro/retirar.py --responsable "Tu Nombre"             # simulacion
python 6-retiro/retirar.py --responsable "Tu Nombre" --ejecutar  # real (escribe RETIRAR)
```
CAPTURA: salida del script y `6-retiro/acta_de_baja.md`. Para volver a tener los datos de
ejemplo: `git checkout -- data`.

## Explicacion corta por etapa ("Hicimos X, con Y, para Z")
1. Pusimos todo bajo Git con linea base y PR, para que cada cambio sea trazable y reversible.
2. Comparamos el entorno real contra una linea base con un script, para detectar desviaciones.
3. Auditamos dependencias, priorizamos por CVSS y actualizamos, para cerrar vulnerabilidades conocidas.
4. Automatizamos Bandit y pip-audit en GitHub Actions, para que la seguridad se revise sola en cada cambio.
5. Analizamos logs para detectar fuerza bruta e inyeccion y bloquear, midiendo MTTD y MTTR.
6. Respaldamos cifrado, sobrescribimos y eliminamos datos y documentamos en un acta, para cerrar el ciclo sin dejar riesgo.
