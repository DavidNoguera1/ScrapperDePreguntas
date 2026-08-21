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
python main.py --instagram cuenta1 --months 1 --interest-only --output competencia_cuenta1.csv
```

Para análisis de competencia, ejecuta una cuenta por vez y espera a que
termine antes de iniciar la siguiente. Así cada cuenta conserva su propio CSV
y se evita usar la misma sesión de Instagram en paralelo.

### Opciones

| Argumento | Por defecto | Descripción |
|---|---|---|
| `--instagram` | — | Una o más cuentas separadas por espacio |
| `--months` | 2 | Meses hacia atrás |
| `--instagram-start-date` | — | Fecha inicial de publicaciones (`dd-mm-aaaa`) |
| `--instagram-end-date` | hoy | Fecha final de publicaciones (`dd-mm-aaaa`, inclusiva) |
| `--max-posts` | sin límite | Límite de posts/reels por cuenta (solo para pruebas) |
| `--interest-only` / `--no-interest-only` | activado | Filtra comentarios de interés legal |
| `--questions-only` / `--no-questions-only` | desactivado | Conserva solo preguntas |
| `--output` | `scraping_FECHA.csv` | Nombre del archivo CSV |

### Ejemplos

```powershell
# Recomendado para análisis de competencia: una cuenta y un CSV por ejecución
python main.py --instagram tramitex.es --instagram-start-date 14-08-2026 --instagram-end-date 21-08-2026 --questions-only --interest-only --output preguntas_tramitex_20260814_20260821.csv
python main.py --instagram abogadodeextranjeria --instagram-start-date 14-08-2026 --instagram-end-date 21-08-2026 --questions-only --interest-only --output preguntas_abogadodeextranjeria_20260814_20260821.csv
python main.py --instagram espanaabogados --instagram-start-date 14-08-2026 --instagram-end-date 21-08-2026 --questions-only --interest-only --output preguntas_espanaabogados_20260814_20260821.csv
python main.py --instagram parainmigrantes.info --instagram-start-date 14-08-2026 --instagram-end-date 21-08-2026 --questions-only --interest-only --output preguntas_parainmigrantes_20260814_20260821.csv

# Solo preguntas
python main.py --instagram abogadodeextranjeria --months 1 --questions-only --output preguntas.csv

# Rango exacto de fechas (formato dia-mes-año)
python main.py --instagram abogadodeextranjeria --instagram-start-date 01-06-2026 --instagram-end-date 30-06-2026 --questions-only --output preguntas_junio.csv

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
- **Fechas exactas**: escribe inicio y final en formato `dd-mm-aaaa`.
- **Meses hacia atrás**: `2`, si dejas vacía la fecha inicial.
- **Solo interés legal**: `Sí`
- **Solo preguntas**: según el reporte
- **Varias cuentas**: ejecuta un comando por cuenta para generar CSVs separados.
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
