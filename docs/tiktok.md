# TikTok Scraper

## Modo 1: Comentarios de un video

Extrae los comentarios de uno o más videos de TikTok.

### CLI

```powershell
python main.py --tiktok "URL_VIDEO_1" "URL_VIDEO_2" --output tiktok.csv
```

| Argumento | Por defecto | Descripción |
|---|---|---|
| `--tiktok` | — | Una o más URLs de videos separadas por espacio |
| `--questions-only` / `--no-questions-only` | desactivado | Conserva solo preguntas |
| `--output` | `scraping_FECHA.csv` | Nombre del archivo CSV |

```powershell
python main.py --tiktok "https://www.tiktok.com/@cuenta/video/123456789" --output tiktok.csv
```

### Menú

```powershell
python main.py
```

Opción **2** del menú. Ofrece dos modos:
1. **Automático (Playwright)** — abre el video y extrae comentarios con Playwright.
2. **Script para consola** — genera un script que pegas en F12 → Console del navegador.

---

## Modo 2: Perfil + métricas por rango de fechas (RECOMENDADO)

Extrae **todos los videos** de una cuenta con sus métricas (título, likes,
comentarios, guardados, compartidos, reproducciones) filtrados por rango de
fechas. El resultado se exporta a CSV con una fila por video.

> **Novedad:** El scraper ahora intercepta las llamadas XHR de TikTok
> (`/api/post/item_list/`) en lugar de depender del HTML estático, lo que
> permite obtener muchos más videos y datos fiables.

### CLI

```powershell
python main.py --tiktok-profile USUARIO --start-date YYYY-MM-DD --end-date YYYY-MM-DD --output archivo.csv
```

| Argumento | Por defecto | Descripción |
|---|---|---|
| `--tiktok-profile` | — | Usuario(s) o URL(s) de perfil (sin @ o con @) |
| `--start-date` | sin límite | Fecha inicio del filtro (YYYY-MM-DD) |
| `--end-date` | sin límite | Fecha fin del filtro (YYYY-MM-DD) |
| `--output` | `scraping_FECHA.csv` | Nombre del archivo CSV |

### Ejemplos

```powershell
:: @entretramites - videos del 1 abril al 27 julio 2026
python main.py --tiktok-profile entretramites --start-date 2026-04-01 --end-date 2026-07-27 --output entretramites.csv

:: Varias cuentas a la vez
python main.py --tiktok-profile entretramites tramitex.es abogadodeextranjeria --start-date 2026-01-01 --end-date 2026-07-27

:: Sin filtro de fechas (todos los videos disponibles)
python main.py --tiktok-profile entretramites --output todos.csv
```

### Menú interactivo

```powershell
python main.py
```

Opción **3** → `TikTok (perfil + metricas por fecha)`

Te pedirá:
1. **Usuario o URL** del perfil (ej: `entretramites` o `https://tiktok.com/@entretramites`)
2. **Fecha inicio** y **fecha fin** (formato `YYYY-MM-DD`, Enter = sin límite)
3. Si ejecutar en **segundo plano** (headless) o con navegador visible

### Columnas del CSV

| Columna | Contenido |
|---|---|
| `Dia` | Día de la extracción |
| `Cuenta` | Nombre de usuario |
| `Red Social` | TikTok |
| `Tipo de publicacion` | Video |
| `Enlace` | URL directa al video |
| `Comentario` | Título/descripción del video |
| `Tema principal` | (para uso futuro) |
| `Mes` | Mes de la extracción |
| `Titulo` | Título/descripción del video |
| `Likes` | Número de me gusta |
| `Comentarios` | Número de comentarios |
| `Guardados` | Número de veces guardado |
| `Compartidos` | Número de veces compartido |
| `Reproducciones` | Número de reproducciones |
| `Fecha publicacion` | Fecha de publicación del video |

### Qué datos extrae por video

- **Título** — descripción / caption del video
- **Likes** — `stats.diggCount`
- **Comentarios** — `stats.commentCount`
- **Guardados** — `stats.collectCount`
- **Compartidos** — `stats.shareCount`
- **Reproducciones** — `stats.playCount`
- **Fecha de publicación** — timestamp Unix convertido a `YYYY-MM-DD HH:MM:SS`
- **URL directa** — enlace al video en TikTok

### Notas técnicas

- Usa **Playwright** en modo headless con flags anti-detección
  (`--disable-blink-features=AutomationControlled`, etc.)
- Intercepta las respuestas XHR a `/api/post/item_list/` mientras hace scroll
  automático para cargar más videos
- El scroll se detiene cuando no se carga más contenido (3 intentos sin cambio
  de altura)
- Fallback: si no hay XHR, intenta extraer datos desde el DOM con JavaScript;
  si eso falla, parsea el HTML completo
- Si Playwright falla por completo, intenta un `requests` directo como último
  recurso (poco fiable, TikTok ya no sirve datos completos sin JS)

---

## Notas generales

- TikTok puede mostrar verificaciones o limitar contenido a navegadores
  automatizados. Si devuelve cero resultados, prueba desde el menú con
  navegador visible (responde `No` a "segundo plano").
- El modo perfil con XHR es **mucho más fiable** que el modo video-comentarios
  tradicional, porque obtiene los datos directamente de la API interna de TikTok.
