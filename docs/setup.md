# Setup general

## Instalación

```powershell
python -m pip install -r requirements.txt
python -m playwright install chromium
```

Estos comandos solo necesitan repetirse después de reinstalar Python, cambiar
de computador o actualizar las dependencias.

## Variables de entorno

Copia `.env.example` a `.env` y completa los valores:

| Variable | Obligatoria | Descripción |
|---|---|---|
| `FACEBOOK_COOKIES_FILE` | Solo para Facebook | Ruta al archivo JSON con cookies de Facebook |

## Formato de salida (CSV)

Los archivos se guardan en `output/`. Los logs van en `output/logs/`.

| Columna | Contenido |
|---|---|
| `Dia` | Fecha de la publicación. |
| `Cuenta` | Cuenta analizada. |
| `Red Social` | Instagram, TikTok o Facebook. |
| `Tipo de publicacion` | Post, Reel o Video. |
| `Enlace` | URL original. |
| `Comentario` | Texto extraído. |
| `Tema principal` | Campo reservado para clasificación posterior. |
| `Mes` | Mes de la publicación. |

Los CSV usan punto y coma (`;`) y codificación UTF-8 con BOM para abrirse
directamente en Excel.

## Unir varios CSV

```powershell
python main.py --merge
```

Selecciona los números de los archivos separados por coma (ej: `1,2,4`).

## Tests automatizados

```powershell
python -m unittest discover -s tests -v
```

El resultado esperado:
```text
OK
```

## Solución de problemas general

### El CSV tiene pocas filas

Revisa el log más reciente en `output/logs/`. Busca las métricas
(`recursos_propios_encontrados`, `comentarios_validos`, `exportados`, etc.)
y mensajes `ERROR` o `WARNING`.

Un número pequeño puede ser correcto si usaste `--questions-only` o si las
publicaciones tienen pocos comentarios legales.

### El programa parece detenido

Algunas publicaciones tardan en cargar y expandir comentarios. Consulta el
log de `output/logs/` para comprobar el avance. No ejecutes simultáneamente
varias copias con la misma sesión de Instagram.
