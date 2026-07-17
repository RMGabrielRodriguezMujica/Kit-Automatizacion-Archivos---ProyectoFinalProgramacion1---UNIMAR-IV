"""
Paquete de pruebas unitarias del Kit Multifuncional de Automatizacion de
Archivos. Se ejecuta desde la raiz del proyecto con:

    python -m unittest discover tests

o, si tienes pytest instalado:

    python -m pytest tests
"""
import os
import sys

# Permite que los tests importen organizer, analyzer, auditor, undo, utils, reports
# sin necesidad de instalar el proyecto como paquete.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
