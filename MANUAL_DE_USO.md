# Manual de uso del scraper de Entrámites

Este programa extrae comentarios públicos de cuentas de Instagram y, de forma
complementaria, de videos de TikTok y publicaciones de Facebook. Los resultados
se guardan como archivos CSV compatibles con Excel.

## 1. Preparación inicial

Abre PowerShell y entra en la carpeta del proyecto:

```powershell
cd "C:\Users\David\Desktop\Entretramites\Scrapper"
```

Instala las dependencias:

```powershell
python -m pip install -r requirements.txt
python -m playwright install chromium
```

Estos comandos solo necesitan repetirse después de reinstalar Python, cambiar
de computador o actualizar las dependencias.

## 2. Iniciar sesión en Instagram

Antes de la primera extracción ejecuta:

```powershell
python import_session.py
```

Se abrirá una ventana llamada **Chrome for Testing**. Es un navegador aislado
controlado por Playwright; no es otra sesión de tu Chrome personal.

1. Inicia sesión directamente en Instagram dentro de esa ventana.
2. Completa la verificación de Instagram si aparece.
3. Cuando veas que la sesión está iniciada, vuelve a PowerShell.
4. Presiona `Enter`.

El navegador se cerrará y la sesión quedará guardada en
`instagram_auth.json`. La contraseña no se guarda en ese archivo.

Para comprobar si existe una sesión local:

```powershell
python import_session.py --status
```

Para cerrar la sesión, revocarla en Instagram y eliminar el archivo local:

```powershell
python import_session.py --logout
```

El archivo `instagram_auth.json` es sensible porque permite reutilizar la
sesión. No debe enviarse por correo, chat ni subirse a GitHub.

## 3. Uso recomendado para Entrámites

El comando recomendado para analizar las cuentas de competencia durante los
último meses es:

```powershell
python main.py --instagram abogadodeextranjeria tramitex.es --months 1 --interest-only --output competencia.csv
```

El programa examinará posts y reels propios de cada cuenta. El resultado
quedará en:

```text
output\competencia.csv
```

No cierres la terminal mientras trabaja. El CSV se actualiza después de cada
comentario, pero si interrumpes el programa con `Ctrl+C`, el reporte quedará
parcial.

### Extraer únicamente preguntas

```powershell
python main.py --instagram abogadodeextranjeria tramitex.es --months 2 --questions-only --output preguntas_competencia.csv
```

### Extraer todos los comentarios

Este modo incluye felicitaciones, emojis y comentarios generales:

```powershell
python main.py --instagram abogadodeextranjeria tramitex.es --months 2 --no-interest-only --no-questions-only --output todos_los_comentarios.csv
```

### Hacer una prueba rápida

Para probar solo cinco publicaciones por cuenta:

```powershell
python main.py --instagram abogadodeextranjeria tramitex.es --months 2 --max-posts 5 --interest-only --output prueba.csv
```

`--max-posts` sirve para pruebas. No se recomienda usarlo en el reporte final,
porque puede dejar publicaciones sin revisar.

## 4. Diferencia entre los filtros

| Opción | Resultado |
|---|---|
| `--interest-only` | Preguntas y casos sustantivos relacionados con trámites, residencia, permisos, expedientes, trabajo y temas legales. Está activo por defecto. |
| `--questions-only` | Conserva únicamente comentarios detectados como preguntas. |
| `--no-interest-only --no-questions-only` | Conserva todos los comentarios válidos. |

El filtro de interés legal se aplica actualmente a Instagram. En TikTok y
Facebook está disponible el filtro de preguntas.

## 5. Uso mediante menú

También puedes iniciar el programa sin opciones:

```powershell
python main.py
```

El menú permite elegir:

1. Instagram por cuenta.
2. TikTok por URL de video.
3. Facebook por URL de publicación.
4. Unir reportes CSV.
5. Salir.

En Instagram se recomienda responder:

- Meses hacia atrás: `2`.
- Solo comentarios de interés legal: `Sí`.
- Dentro de esos, solo preguntas: depende del reporte requerido.
- Límite de posts: dejar vacío para el reporte completo.
- Segundo plano o *headless*: `Sí`.

## 6. TikTok

La extracción automática recibe una o varias URL de videos:

```powershell
python main.py --tiktok "https://www.tiktok.com/@cuenta/video/123456789" --output tiktok.csv
```

Para varios videos:

```powershell
python main.py --tiktok "URL_VIDEO_1" "URL_VIDEO_2" --output tiktok_competencia.csv
```

TikTok puede mostrar verificaciones o limitar el contenido visible a
navegadores automatizados. Si devuelve cero comentarios, prueba primero desde
el menú con navegador visible.

## 7. Facebook

Facebook normalmente requiere cookies de una sesión activa. La ruta del
archivo de cookies se configura en un archivo `.env`:

```text
FACEBOOK_COOKIES_FILE=C:\ruta\facebook_cookies.json
```

Después se ejecuta:

```powershell
python main.py --facebook "URL_PUBLICACION_1" "URL_PUBLICACION_2" --output facebook.csv
```

Las cookies deben estar en formato JSON compatible con Playwright. No compartas
ese archivo ni lo subas a repositorios.

## 8. Reportes y logs

Los CSV se guardan en:

```text
output\
```

Los logs detallados se guardan en:

```text
output\logs\
```

Cada fila del CSV contiene:

| Columna | Contenido |
|---|---|
| `Dia` | Fecha de la publicación. |
| `Cuenta` | Cuenta de competencia analizada. |
| `Red Social` | Instagram, TikTok o Facebook. |
| `Tipo de publicacion` | Post, Reel o Video. |
| `Enlace` | URL original. |
| `Comentario` | Texto extraído. |
| `Tema principal` | Campo reservado para clasificación posterior. |
| `Mes` | Mes de la publicación. |

Los CSV usan punto y coma (`;`) y codificación UTF-8 con BOM para facilitar su
apertura en Excel.

## 9. Unir varios CSV

Ejecuta:

```powershell
python main.py --merge
```

El programa mostrará los archivos de `output\`. Escribe los números que deseas
unir separados por comas, por ejemplo:

```text
1,2,4
```

El archivo resultante se guardará como `output\merged_FECHA_HORA.csv`.

## 10. Solución de problemas

### “La sesión de Instagram no está autenticada”

Renueva la sesión:

```powershell
python import_session.py
```

### El reporte contiene `15h`, `1d` o `2w` como comentarios

Eso indica una versión antigua del extractor. Ejecuta las pruebas indicadas en
la sección 11 y confirma que estás usando el archivo
`instagram_scraper.py` actual.

### Faltan publicaciones antiguas

- Aumenta `--months`.
- No uses `--max-posts` en la ejecución final.
- Deja que el proceso termine; el log debe mostrar `total_exportado`.

### El CSV tiene pocas filas

Revisa el log más reciente en `output\logs\`. Busca:

- `recursos_propios_encontrados`
- `comentarios_validos`
- `interes`
- `preguntas`
- `exportados`
- mensajes `ERROR` o `WARNING`

Un número pequeño puede ser correcto si se utilizó `--questions-only` o si las
publicaciones tienen pocos comentarios legales.

### Instagram muestra una verificación

Ejecuta nuevamente `python import_session.py`, completa la verificación en el
navegador visible y presiona `Enter`.

### El programa parece detenido

Algunas publicaciones tardan varios segundos en cargar y expandir comentarios.
Consulta el log para comprobar el avance. No ejecutes simultáneamente varias
copias con la misma sesión.

## 11. Comprobar que el scraper funciona

Ejecuta las pruebas automatizadas:

```powershell
python -m unittest discover -s tests -v
```

El resultado esperado termina en:

```text
OK
```

Después realiza una prueba pequeña:

```powershell
python main.py --instagram tramitex.es --months 2 --max-posts 2 --interest-only --output validacion.csv
```

Abre `output\validacion.csv` y comprueba que la columna `Comentario` contiene
texto real y no valores de tiempo.

## 12. Rutina recomendada

1. Comprueba la sesión con `python import_session.py --status`.
2. Inicia sesión si es necesario.
3. Ejecuta primero una prueba con `--max-posts 2`.
4. Ejecuta el reporte completo sin `--max-posts`.
5. Espera el mensaje `Reporte terminado`.
6. Revisa el CSV y el log.
7. Cierra la sesión con `python import_session.py --logout` si no volverás a
   usar el scraper pronto.

