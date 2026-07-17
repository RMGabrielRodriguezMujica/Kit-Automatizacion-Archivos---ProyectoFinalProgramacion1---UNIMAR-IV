"""Pruebas unitarias para organizer.py (Gestor de Organizacion de Archivos)."""
import os
import time
import tempfile
import unittest

import organizer


class TestOrganizer(unittest.TestCase):
    def setUp(self):
        # Cada prueba corre en su propia carpeta temporal, y con el
        # directorio de trabajo apuntando ahi, para no ensuciar el
        # proyecto real con audit.log / historial_operaciones.json de prueba.
        self._cwd_original = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)

        self.carpeta = os.path.join(self._tmp.name, "datos")
        os.makedirs(self.carpeta)
        self._crear_archivo("foto.jpg", b"x" * 10)
        self._crear_archivo("documento.txt", b"contenido de prueba")
        self._crear_archivo("hoja.csv", b"a,b,c")

    def tearDown(self):
        os.chdir(self._cwd_original)
        self._tmp.cleanup()

    def _crear_archivo(self, nombre, contenido=b"x"):
        ruta = os.path.join(self.carpeta, nombre)
        with open(ruta, "wb") as f:
            f.write(contenido)
        return ruta

    def test_clasificar_por_extension_dry_run_no_mueve_archivos(self):
        resultado = organizer.clasificar_por_extension(self.carpeta, dry_run=True)
        # En dry-run, el resultado ya agrupa los archivos...
        self.assertEqual(sorted(resultado.keys()), ["CSV", "JPG", "TXT"])
        # ...pero ningun archivo debe haberse movido de la carpeta original.
        self.assertTrue(os.path.exists(os.path.join(self.carpeta, "foto.jpg")))
        self.assertFalse(os.path.isdir(os.path.join(self.carpeta, "JPG")))

    def test_clasificar_por_extension_real_mueve_archivos(self):
        organizer.clasificar_por_extension(self.carpeta, dry_run=False)
        self.assertTrue(os.path.exists(os.path.join(self.carpeta, "JPG", "foto.jpg")))
        self.assertTrue(os.path.exists(os.path.join(self.carpeta, "TXT", "documento.txt")))
        self.assertFalse(os.path.exists(os.path.join(self.carpeta, "foto.jpg")))

    def test_clasificar_por_tamano_categoriza_correctamente(self):
        self._crear_archivo("grande.bin", b"x" * (6 * 1024 * 1024))  # > 5MB
        resultado = organizer.clasificar_por_tamano(self.carpeta, dry_run=True)
        self.assertIn("grande.bin", resultado["Grandes"])
        self.assertIn("foto.jpg", resultado["Pequenos"])

    def test_renombrar_con_patron_aplica_regex(self):
        cambios = organizer.renombrar_con_patron(self.carpeta, r"^documento", "DOC_", dry_run=False)
        self.assertEqual(cambios, [("documento.txt", "DOC_.txt")])
        self.assertTrue(os.path.exists(os.path.join(self.carpeta, "DOC_.txt")))

    def test_renombrar_con_patron_invalido_lanza_valueerror(self):
        with self.assertRaises(ValueError):
            organizer.renombrar_con_patron(self.carpeta, "(regex sin cerrar", "x", dry_run=True)

    def test_clasificar_carpeta_vacia_no_falla(self):
        vacia = os.path.join(self._tmp.name, "vacia")
        os.makedirs(vacia)
        resultado = organizer.clasificar_por_extension(vacia, dry_run=True)
        self.assertEqual(resultado, {})


if __name__ == "__main__":
    unittest.main()
