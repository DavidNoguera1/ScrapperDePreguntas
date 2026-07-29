# TikTok Scraper

## Modo 1: Comentarios de un video

Extrae los comentarios de uno o mas videos de TikTok.

### CLI

```powershell
python main.py --tiktok "URL_VIDEO_1" "URL_VIDEO_2" --output tiktok.csv
```

| Argumento | Por defecto | Descripcion |
|---|---|---|
| `--tiktok` | - | Una o mas URLs de videos separadas por espacio |
| `--questions-only` / `--no-questions-only` | desactivado | Conserva solo preguntas |
| `--output` | `scraping_FECHA.csv` | Nombre del archivo CSV |

```powershell
python main.py --tiktok "https://www.tiktok.com/@cuenta/video/123456789" --output tiktok.csv
```

### Menu

```powershell
python main.py
```

Opcion **2** del menu. Ofrece dos modos:
1. **Automatico (Playwright)** - abre el video y extrae comentarios con Playwright.
2. **Script para consola** - genera un script que pegas en F12 -> Console del navegador.

---

## Modo 2: Perfil + metricas por rango de fechas (RECOMENDADO)

Extrae todos los contenidos de una cuenta con sus metricas (titulo, likes,
comentarios, guardados, compartidos, reproducciones y duracion) filtrados por
rango de fechas. El resultado se exporta a CSV con una fila por contenido.

El scraper intercepta las llamadas XHR de TikTok (`/api/post/item_list/`) en
lugar de depender del HTML estatico, lo que permite obtener muchos mas
contenidos y datos fiables.

### CLI

```powershell
python main.py --tiktok-profile USUARIO --start-date YYYY-MM-DD --end-date YYYY-MM-DD --output archivo.csv
```

| Argumento | Por defecto | Descripcion |
|---|---|---|
| `--tiktok-profile` | - | Usuario(s) o URL(s) de perfil (sin @ o con @) |
| `--start-date` | sin limite | Fecha inicio del filtro (YYYY-MM-DD) |
| `--end-date` | sin limite | Fecha fin del filtro (YYYY-MM-DD), inclusiva durante todo el dia |
| `--output` | `scraping_FECHA.csv` | Nombre del archivo CSV |
| `--visible` | desactivado | Abre el navegador visible; util si TikTok bloquea el modo headless |

### Ejemplos

```powershell
# @entretramites - contenidos del 1 abril al 27 julio 2026
python main.py --tiktok-profile entretramites --start-date 2026-04-01 --end-date 2026-07-27 --output entretramites.csv

# Si TikTok devuelve cero resultados en headless
python main.py --tiktok-profile entretramites --start-date 2026-04-01 --end-date 2026-07-27 --visible --output entretramites.csv

# Varias cuentas a la vez
python main.py --tiktok-profile entretramites tramitex.es abogadodeextranjeria --start-date 2026-01-01 --end-date 2026-07-27

# Sin filtro de fechas (todos los contenidos disponibles)
python main.py --tiktok-profile entretramites --output todos.csv
```

### Menu interactivo

```powershell
python main.py
```

Opcion **3** -> `TikTok (perfil + metricas por fecha)`

Te pedira:
1. **Usuario o URL** del perfil (ej: `entretramites` o `https://tiktok.com/@entretramites`)
2. **Fecha inicio** y **fecha fin** (formato `YYYY-MM-DD`, Enter = sin limite)
3. Si ejecutar en **segundo plano** (headless) o con navegador visible

### Columnas del CSV

| Columna | Contenido |
|---|---|
| `Dia` | Dia de publicacion del contenido |
| `Cuenta` | Nombre de usuario |
| `Red Social` | TikTok |
| `Tipo de publicacion` | `Video` o `Carrusel` cuando `duracion` es 0 |
| `Enlace` | URL directa al contenido |
| `Comentario` | Titulo/descripcion del contenido |
| `Tema principal` | (para uso futuro) |
| `Mes` | Mes de publicacion del contenido |
| `duracion` | Duracion reportada por TikTok. Si es `0`, el contenido es un carrusel |
| `Titulo` | Titulo/descripcion del contenido |
| `Likes` | Numero de me gusta |
| `Comentarios` | Numero de comentarios |
| `Guardados` | Numero de veces guardado |
| `Compartidos` | Numero de veces compartido |
| `Reproducciones` | Numero de reproducciones |
| `Fecha publicacion` | Fecha de publicacion del contenido |

### Que datos extrae por contenido

- **Titulo** - descripcion / caption del contenido
- **Likes** - `stats.diggCount`
- **Comentarios** - `stats.commentCount`
- **Guardados** - `stats.collectCount`
- **Compartidos** - `stats.shareCount`
- **Reproducciones** - `stats.playCount`
- **Duracion** - `video.duration`
- **Fecha de publicacion** - timestamp Unix convertido a `YYYY-MM-DD HH:MM:SS`
- **URL directa** - enlace al contenido en TikTok

### Notas tecnicas

- Usa **Playwright** en modo headless con flags anti-deteccion
  (`--disable-blink-features=AutomationControlled`, etc.)
- Intercepta las respuestas XHR a `/api/post/item_list/` mientras hace scroll
  automatico para cargar mas contenidos.
- El scroll se detiene cuando no se carga mas contenido.
- Fallback: si no hay XHR, intenta extraer datos desde el DOM con JavaScript;
  si eso falla, parsea el HTML completo.
- Si Playwright falla por completo, intenta un `requests` directo como ultimo
  recurso, aunque TikTok no siempre sirve datos completos sin JS.

---

## Notas generales

- TikTok puede mostrar verificaciones o limitar contenido a navegadores
  automatizados. Si devuelve cero resultados, prueba desde el menu con navegador
  visible (responde `No` a "segundo plano").
- El modo perfil con XHR es mas fiable que el modo video-comentarios
  tradicional, porque obtiene los datos directamente de la API interna de TikTok.
