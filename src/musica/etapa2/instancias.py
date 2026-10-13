"""Orquestación de la transformación; no modifica los CSV originales."""

import json
from pathlib import Path

from musica.etapa2.entidades import Modelo
from musica.etapa2.entradas import Entradas
from musica.etapa2.escritura import Escritor, sha_archivo
from musica.etapa2.mediciones import acousticbrainz, generos, jmir
from musica.etapa2.relaciones import creditos, publicaciones, relaciones


def generar_instancias(carpeta, salida, progreso=print):
    carpeta, salida = Path(carpeta), Path(salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    temporal = salida.with_suffix(".ttl.tmp")
    try:
        with temporal.open("w", encoding="utf-8", newline="\n") as archivo:
            escritor = Escritor(archivo)
            entradas = Entradas(carpeta, escritor)
            modelo = Modelo(entradas)
            pasos = (
                ("Grabaciones locales", modelo.canciones),
                ("Correspondencias", modelo.correspondencias),
                ("Artistas, obras y publicaciones", modelo.entidades),
                ("Créditos", lambda: creditos(modelo)),
                ("Ediciones y sellos", lambda: publicaciones(modelo)),
                ("Relaciones musicales", lambda: relaciones(modelo)),
                ("Clasificaciones de género", lambda: generos(modelo)),
                ("Descriptores jMIR", lambda: jmir(modelo)),
                ("Análisis AcousticBrainz", lambda: acousticbrainz(modelo)),
            )
            for nombre, ejecutar in pasos:
                progreso(nombre, flush=True)
                ejecutar()
            resumen = escritor.cerrar_etiquetas()
        resumen.update(entradas.resumen())
        resumen.update(
            {
                "referencias_locales": len(modelo.locales),
                "referencias_reconciliadas": len(modelo.seleccion),
                "mbid_seleccionados_distintos": len(modelo.por_mbid),
                "conflictos_correspondencia": modelo.conflictos,
                "sha256_instances": sha_archivo(temporal),
            }
        )
        temporal.replace(salida)
        salida.with_suffix(".informe.json").write_text(
            json.dumps(resumen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return resumen
    finally:
        temporal.unlink(missing_ok=True)
