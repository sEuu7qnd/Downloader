# -*- coding: utf-8 -*-
from __future__ import annotations
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from logs import logger

APP_NAME = "Downloader"

DEFECTOS: Dict[str, Any] = {
    "kind": "video",
    "video_fmt": "mp4",
    "audio_fmt": "mp3",
    "resolution": "1080",
    "bitrate": "192",
    "dir": str(Path.home() / "Downloads" / APP_NAME),
    "use_cookies": True,
    "subfolder": True,
    "max_batch": 50,  # 0 = sin límite
}

def carpeta_config() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config"))
    return base / APP_NAME

def contar_cookies(texto: str) -> int:
    n = 0
    for linea in texto.splitlines():
        s = linea.strip()
        if not s or (s.startswith("#") and not s.startswith("#HttpOnly_")):
            continue
        if len(s.split("\t")) >= 7:
            n += 1
    return n

class Config:
    def __init__(self) -> None:
        self.carpeta = carpeta_config()
        self.archivo = self.carpeta / "config.json"
        self.cookies = self.carpeta / "cookies.txt"
        self.d = dict(DEFECTOS)
        self._ultimo = ""
        self.cargar()

    def cargar(self) -> None:
        try:
            if self.archivo.exists():
                leido = json.loads(self.archivo.read_text(encoding="utf-8"))
                if isinstance(leido, dict):
                    for k, v in leido.items():
                        if k in DEFECTOS and isinstance(v, type(DEFECTOS[k])):
                            self.d[k] = v
        except (OSError, ValueError) as err:
            logger.warning("Error leyendo configuración, usando defaults: %s", err)

    def __getitem__(self, k: str) -> Any:
        return self.d[k]

    def __setitem__(self, k: str, v: Any) -> None:
        self.d[k] = v

    def guardar(self) -> None:
        try:
            texto = json.dumps(self.d, ensure_ascii=False, indent=2)
            if texto == self._ultimo:
                return
            self.carpeta.mkdir(parents=True, exist_ok=True)
            tmp = self.archivo.with_suffix(".tmp")
            tmp.write_text(texto, encoding="utf-8")
            os.replace(tmp, self.archivo)
            self._ultimo = texto
        except OSError as err:
            logger.error("Error al guardar la configuración: %s", err)

    def importar_cookies(self, origen: str) -> int:
        texto = Path(origen).read_text(encoding="utf-8-sig", errors="replace")
        n = contar_cookies(texto)
        if not n:
            raise ValueError("No se encontró ninguna cookie válida en el archivo Netscape.")
        if "HTTP Cookie File" not in texto.splitlines()[0]:
            texto = "# Netscape HTTP Cookie File\n" + texto
        self.carpeta.mkdir(parents=True, exist_ok=True)
        tmp = self.cookies.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(texto.replace("\r\n", "\n"))
        os.replace(tmp, self.cookies)
        try:
            os.chmod(self.cookies, 0o600)
        except OSError:
            pass
        return n

    def quitar_cookies(self) -> None:
        try:
            self.cookies.unlink()
        except FileNotFoundError:
            pass

    def info_cookies(self) -> Optional[Tuple[int, str]]:
        try:
            texto = self.cookies.read_text(encoding="utf-8", errors="replace")
            fecha = datetime.fromtimestamp(self.cookies.stat().st_mtime).strftime("%d/%m/%Y %H:%M")
            return contar_cookies(texto), fecha
        except OSError:
            return None

    def cookies_en_uso(self) -> Optional[str]:
        if self.d["use_cookies"] and self.cookies.is_file():
            return str(self.cookies)
        return None