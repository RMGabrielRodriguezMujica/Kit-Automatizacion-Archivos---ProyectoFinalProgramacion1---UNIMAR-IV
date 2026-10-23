"""
auditor.py
----------
Auditor de Cambios.
Genera snapshots (fotografias) del estado de una carpeta, los compara
para detectar archivos nuevos, modificados o eliminados, y registra el
historial de auditorias en audit.log.
"""

import os
import json
from datetime import datetime

# Importamos las funciones auxiliares reutilizadas por el auditor.
from utils import registrar_actividad, listar_archivos, obtener_metadata, escribir_log, calcular_hash_archivo

# Carpeta donde se almacenarán los snapshots en formato JSON.
CARPETA_SNAPSHOTS = "snapshots"


@registrar_actividad
def crear_snapshot(carpeta, nombre_snapshot=None):
    """
    Crea un snapshot del estado actual de 'carpeta': nombre, tamano,
    fecha de modificacion y hash de cada archivo. Se guarda como JSON
    dentro de la carpeta 'snapshots/'. Retorna la ruta del snapshot creado.
    """
    # Primero aseguramos que exista la carpeta de snapshots.
    try:
        os.makedirs(CARPETA_SNAPSHOTS, exist_ok=True)
    except PermissionError as e:
        raise IOError(
            f"No se pudo crear la carpeta '{CARPETA_SNAPSHOTS}/': permiso denegado. "
            f"Mueve el proyecto fuera de Descargas/Documentos o quita el atributo "
            f"'Solo lectura' de la carpeta. Detalle: {e}"
        )

    # Diccionario principal que almacenará el estado actual de la carpeta.
    estado = {}

    # Recorremos todos los archivos detectados y guardamos una versión resumida
    # con tamaño, fecha de modificación y un hash del contenido.
    for ruta in listar_archivos(carpeta):
        meta = obtener_metadata(ruta)
        estado[meta["nombre"]] = {
            "tamano": meta["tamano"],
            "modificado": meta["modificado"],
            "hash": calcular_hash_archivo(ruta),
        }

    # Si no se pasó un nombre, se genera uno automático con la fecha y hora actual.
    if nombre_snapshot is None:
        nombre_snapshot = f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    # Ruta completa donde se guardará el archivo JSON del snapshot.
    ruta_snapshot = os.path.join(CARPETA_SNAPSHOTS, nombre_snapshot)

    # Guardamos el estado en disco como JSON legible.
    try:
        with open(ruta_snapshot, "w", encoding="utf-8") as f:
            json.dump(estado, f, indent=4, ensure_ascii=False)
    except OSError as e:
        raise IOError(f"No se pudo guardar el snapshot: {e}")

    return ruta_snapshot


def _ultimo_snapshot(excluir=None):
    """Retorna la ruta del snapshot mas reciente disponible, o None si no existe ninguno."""
    # Si la carpeta no existe, no hay snapshots previos para comparar.
    if not os.path.isdir(CARPETA_SNAPSHOTS):
        return None

    # Listamos solo los archivos JSON válidos y descartamos el snapshot opcionalmente excluido.
    snapshots = [
        f for f in os.listdir(CARPETA_SNAPSHOTS)
        if f.endswith(".json") and f != excluir
    ]

    # Si no hay snapshots, devolvemos None.
    if not snapshots:
        return None

    # Ordenamos alfabéticamente para tomar el más reciente por nombre.
    snapshots.sort()
    return os.path.join(CARPETA_SNAPSHOTS, snapshots[-1])


def _cargar_snapshot(ruta_snapshot):
    """Carga un snapshot JSON desde disco y lo retorna como diccionario."""
    # Leemos el archivo guardado en disco y lo convertimos a un diccionario Python.
    try:
        with open(ruta_snapshot, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise IOError(f"No se pudo leer el snapshot '{ruta_snapshot}': {e}")


@registrar_actividad
def comparar_snapshots(snapshot_anterior, snapshot_actual):
    """
    Compara dos snapshots (diccionarios) y detecta archivos nuevos,
    modificados (mismo nombre, distinto hash) y eliminados.
    """
    # Convertimos las claves de cada snapshot a conjuntos para comparar fácilmente.
    archivos_anteriores = set(snapshot_anterior.keys())
    archivos_actuales = set(snapshot_actual.keys())

    # Archivos presentes ahora pero no antes: son nuevos.
    nuevos = archivos_actuales - archivos_anteriores

    # Archivos presentes antes pero no ahora: fueron eliminados.
    eliminados = archivos_anteriores - archivos_actuales

    # Archivos que siguen existiendo en ambos snapshots, pero cuyo contenido cambió.
    modificados = {
        nombre for nombre in archivos_actuales & archivos_anteriores
        if snapshot_actual[nombre]["hash"] != snapshot_anterior[nombre]["hash"]
    }

    # Devolvemos una estructura limpia con los tres tipos de cambios.
    return {
        "nuevos": sorted(nuevos),
        "modificados": sorted(modificados),
        "eliminados": sorted(eliminados),
    }


@registrar_actividad
def auditar_carpeta(carpeta):
    """
    Flujo completo de auditoria: carga el ultimo snapshot guardado (si
    existe), genera uno nuevo, compara ambos y registra el resultado en
    audit.log. Retorna el diccionario de diferencias detectadas.
    """
    # 1) Buscamos el snapshot más reciente que ya exista, si es que hay uno.
    ruta_snapshot_previo = _ultimo_snapshot()
    snapshot_previo = _cargar_snapshot(ruta_snapshot_previo) if ruta_snapshot_previo else {}

    # 2) Generamos un nuevo snapshot con el estado actual de la carpeta.
    ruta_snapshot_nuevo = crear_snapshot(carpeta)
    snapshot_nuevo = _cargar_snapshot(ruta_snapshot_nuevo)

    # 3) Comparamos el snapshot anterior con el nuevo para detectar cambios.
    diferencias = comparar_snapshots(snapshot_previo, snapshot_nuevo)

    # 4) Registramos en el log cuántos archivos nuevos, modificados y eliminados hubo.
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    escribir_log(
        f"{timestamp} | AUDITORIA | nuevos={len(diferencias['nuevos'])} "
        f"modificados={len(diferencias['modificados'])} "
        f"eliminados={len(diferencias['eliminados'])}"
    )

    # 5) Devolvemos el resumen de diferencias para uso posterior.
    return diferencias

    