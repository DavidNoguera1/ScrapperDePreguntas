# Scraper de comentarios de Entrámites

Extrae comentarios públicos de Instagram.
Los resultados se guardan como CSV compatible con Excel.

## Documentación

| Documento | Contenido |
|---|---|
| [docs/setup.md](docs/setup.md) | Instalación, formato CSV, merge, tests |
| [docs/instagram.md](docs/instagram.md) | Instagram: auth, CLI, filtros |

## Comando recomendado

```powershell
python main.py --instagram abogadodeextranjeria tramitex.es --months 2 --interest-only --output competencia.csv
```
