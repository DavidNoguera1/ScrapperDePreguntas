"""
Compatibilidad: Ahora es python -m cli.import_session
"""
import sys
import runpy

if __name__ == "__main__":
    runpy.run_module("cli.import_session", run_name="__main__")
