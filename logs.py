# -*- coding: utf-8 -*-
import logging
from pathlib import Path

def obtener_logger(nombre: str = "Downloader") -> logging.Logger:
    logger = logging.getLogger(nombre)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formato = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

        # Salida por consola
        ch = logging.StreamHandler()
        ch.setFormatter(formato)
        logger.addHandler(ch)

        # Archivo de registro en la carpeta del usuario
        log_file = Path.home() / ".downloader_debug.log"
        try:
            fh = logging.FileHandler(log_file, encoding="utf-8")
            fh.setFormatter(formato)
            logger.addHandler(fh)
        except OSError:
            pass

    return logger

logger = obtener_logger()