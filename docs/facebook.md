# Facebook Scraper

## Preparación

Facebook requiere cookies de una sesión activa. Configura la ruta del archivo
JSON en `.env`:

```text
FACEBOOK_COOKIES_FILE=C:\ruta\facebook_cookies.json
```

El archivo debe contener cookies en formato compatible con Playwright. Para
obtenerlas puedes usar una extensión como *Get cookies.txt* (exportar como
JSON) o extraerlas desde las herramientas de desarrollador del navegador.

Las cookies son sensibles. No las compartas ni las subas a repositorios.

## Uso por CLI

```powershell
python main.py --facebook "URL_POST_1" "URL_POST_2" --output facebook.csv
```

### Opciones

| Argumento | Por defecto | Descripción |
|---|---|---|
| `--facebook` | — | Una o más URLs de posts separadas por espacio |
| `--questions-only` / `--no-questions-only` | desactivado | Conserva solo preguntas |
| `--output` | `scraping_FECHA.csv` | Nombre del archivo CSV |

## Uso por menú

```powershell
python main.py
```

Opción **3** del menú. Si no hay archivo de cookies configurado, el scraper
abrirá el navegador visible para que inicies sesión manualmente.

## Sin archivo de cookies

Si no tienes el archivo, el scraper abrirá el navegador en modo visible.
Deberás iniciar sesión en la ventana que se abre. Una vez dentro, la
extracción continuará automáticamente.
