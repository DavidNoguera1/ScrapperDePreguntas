# TikTok Scraper

## Uso por CLI

```powershell
python main.py --tiktok "URL_VIDEO_1" "URL_VIDEO_2" --output tiktok.csv
```

### Opciones

| Argumento | Por defecto | Descripción |
|---|---|---|
| `--tiktok` | — | Una o más URLs de videos separadas por espacio |
| `--questions-only` / `--no-questions-only` | desactivado | Conserva solo preguntas |
| `--output` | `scraping_FECHA.csv` | Nombre del archivo CSV |

### Ejemplos

```powershell
python main.py --tiktok "https://www.tiktok.com/@cuenta/video/123456789" --output tiktok.csv
```

## Uso por menú

```powershell
python main.py
```

Opción **2** del menú. Ofrece dos modos:

1. **Automático (Playwright)** — abre el video y extrae comentarios mediante
   Playwright.
2. **Script para consola** — genera un script que pegas en F12 → Console del
   navegador para descargar un CSV manualmente.

## Notas

- TikTok puede mostrar verificaciones o limitar el contenido a navegadores
  automatizados. Si devuelve cero comentarios, prueba desde el menú con
  navegador visible (responde `No` a "segundo plano").
