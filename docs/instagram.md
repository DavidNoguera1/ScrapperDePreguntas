# Instagram Scraper

## Iniciar sesión

Antes de la primera extracción guarda la sesión:

```powershell
python -m cli.import_session
```

Se abrirá una ventana **Chrome for Testing** (navegador aislado de Playwright).

1. Inicia sesión en Instagram dentro de esa ventana.
2. Completa la verificación si aparece.
3. Cuando la sesión esté activa, vuelve a PowerShell y presiona `Enter`.

La sesión se guarda en `instagram_auth.json` (no almacena contraseñas).

### Comandos útiles

| Acción | Comando |
|---|---|
| Verificar si hay sesión guardada | `python -m cli.import_session --status` |
| Cerrar sesión (remoto + local) | `python -m cli.import_session --logout` |

`instagram_auth.json` es sensible. No lo compartas por correo, chat ni lo
subas a repositorios.

## Uso por CLI

```powershell
python main.py --instagram cuenta1 cuenta2 --months 1 --interest-only --output competencia.csv
```

### Opciones

| Argumento | Por defecto | Descripción |
|---|---|---|
| `--instagram` | — | Una o más cuentas separadas por espacio |
| `--months` | 2 | Meses hacia atrás |
| `--max-posts` | sin límite | Límite de posts/reels por cuenta (solo para pruebas) |
| `--interest-only` / `--no-interest-only` | activado | Filtra comentarios de interés legal |
| `--questions-only` / `--no-questions-only` | desactivado | Conserva solo preguntas |
| `--output` | `scraping_FECHA.csv` | Nombre del archivo CSV |

### Ejemplos

```powershell
# Recomendado para análisis de competencia
python main.py --instagram tramitex.es --months 1 --interest-only --output competencia.csv
python main.py --instagram abogadodeextranjeria --months 1 --interest-only --output competenciaPau.csv

# Solo preguntas
python main.py --instagram abogadodeextranjeria --months 2 --questions-only --output preguntas.csv

# Todos los comentarios (sin filtros)
python main.py --instagram abogadodeextranjeria --months 2 --no-interest-only --no-questions-only --output todos.csv

# Prueba rápida (2 posts por cuenta)
python main.py --instagram tramitex.es --months 2 --max-posts 2 --interest-only --output validacion.csv
```

## Uso por menú

```powershell
python main.py
```

Opción **1** del menú. Te guiará paso a paso.

Recomendaciones para las preguntas:
- **Meses hacia atrás**: `2`
- **Solo interés legal**: `Sí`
- **Solo preguntas**: según el reporte
- **Límite de posts**: dejar vacío
- **Segundo plano (headless)**: `Sí`

## Diferencia entre los filtros

| Opción | Resultado |
|---|---|
| `--interest-only` (activo por defecto) | Preguntas y casos sustantivos sobre trámites, residencia, permisos, trabajo y temas legales |
| `--questions-only` | Solo comentarios detectados como preguntas |
| `--no-interest-only --no-questions-only` | Todos los comentarios válidos |

## Solución de problemas

### "La sesión de Instagram no está autenticada"

Renueva la sesión:

```powershell
python -m cli.import_session
```

### El reporte contiene `15h`, `1d` o `2w` como comentarios

Ejecuta las pruebas (`python -m unittest discover -s tests -v`) y confirma que
estás usando la versión actual de los archivos en `scrapers/instagram/`.

### Faltan publicaciones antiguas

- Aumenta `--months`.
- No uses `--max-posts` en la ejecución final.
- Deja que el proceso termine; el log debe mostrar `total_exportado`.

### Instagram muestra una verificación

Ejecuta nuevamente `python -m cli.import_session`, completa la verificación
en el navegador visible y presiona `Enter`.
