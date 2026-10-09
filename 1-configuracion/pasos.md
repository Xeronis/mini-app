# Etapa 1: Gestion de configuracion

**Que:** todo el proyecto bajo control de versiones, con linea base (tag), cambios por
Pull Request y secretos fuera del repositorio.
**Para que:** que todo cambio quede registrado, aprobado y sea reversible.

## Pasos

```bash
git init
git add .
git commit -m "Linea base inicial de la mini app"
git branch -M main
git tag -a v1.0 -m "Linea base aprobada v1.0"
# crea el repo vacio en GitHub y luego:
git remote add origin https://github.com/TU_USUARIO/mini-app.git
git push -u origin main --tags
```

## Proteger la rama main (en GitHub)
Settings > Branches > Add branch protection rule (o Rulesets) para `main`:
- Require a pull request before merging (con 1 aprobacion)
- Require status checks to pass: selecciona `seguridad` (el workflow de la etapa 4)

> Nota: en repositorios **privados** gratuitos GitHub puede limitar esta opcion.
> Si te pasa, hazlo publico para la demo o toma la captura de la regla configurada.

## Demo de control de cambios y rollback
```bash
git checkout -b cambio-malo
# edita app.py a proposito (por ejemplo cambia debug=False a debug=True)
git commit -am "Cambio inseguro: activa debug"
git checkout main && git merge cambio-malo      # (en la demo real iria por Pull Request)
git revert HEAD --no-edit                       # rollback: vuelve al estado seguro
git log --oneline --graph                       # CAPTURA: historial con el revert
```

## Secretos fuera del repo
- `.env` esta en `.gitignore`; solo se sube `.env.example` (sin valores reales).
- Opcional, para la captura: `gitleaks detect --source . -v` (https://github.com/gitleaks/gitleaks)
  debe reportar **no leaks found**.

## Capturas para el PPT
`git log --oneline --graph`, la regla de rama protegida, `git tag`, y `.gitignore` con `.env`.
