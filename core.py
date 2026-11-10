# -*- coding: utf-8 -*-
from __future__ import annotations
import os
import re
import shutil
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from urllib.parse import parse_qs, urlparse

from logs import logger
VIDEO = [("mp4", "MP4"), ("webm", "WebM"), ("mkv", "MKV"), ("avi", "AVI"), ("mov", "MOV")]
AUDIO = [("mp3", "MP3"), ("opus", "Opus"), ("m4a", "M4A"), ("aac", "AAC"), ("flac", "FLAC"), ("wav", "WAV"), ("ogg", "OGG")]
VIDEO_KEYS = [k for k, _ in VIDEO]
AUDIO_KEYS = [k for k, _ in AUDIO]
RESOLUCIONES = ["360", "480", "720", "1080", "1440", "2160"]
BITRATES = ["128", "192", "256", "320"]
_yt: Any = None
_motor_listo = threading.Event()
_motor_error: Optional[str] = None
_ffmpeg: Tuple[Optional[str], bool] = (None, False)
_hay_js: bool = False

CODEC_AUDIO = {
    "mp3": "mp3", "opus": "opus", "m4a": "m4a", "aac": "aac",
    "flac": "flac", "wav": "wav", "ogg": "vorbis"
}
CON_BITRATE = {"mp3", "aac", "ogg"}

PLANTILLA_LISTA = "%(playlist_title)s/%(playlist_index)03d - %(title)s.%(ext)s"
PLANTILLA_PLANA = "%(playlist_index)03d - %(title)s.%(ext)s"
PLANTILLA_VIDEO = "%(title)s.%(ext)s"
_PREFIJO_NUM = re.compile(r"^\d+[\s\-_]+(.+)$")
_ANSI = re.compile(r"\x1b\[[0-9;]*m")

def hay_runtime_js() -> bool:
    return any(shutil.which(x) for x in ("deno", "node", "bun", "qjs"))

def ubicar_ffmpeg() -> Tuple[Optional[str], bool]:
    global _ffmpeg
    if shutil.which("ffmpeg"):
        _ffmpeg = (None, True)
        return _ffmpeg
    try:
        import imageio_ffmpeg
        ruta = imageio_ffmpeg.get_ffmpeg_exe()
        if ruta and os.path.isfile(ruta):
            _ffmpeg = (ruta, True)
    except Exception as e:
        logger.debug("No se pudo localizar imageio-ffmpeg: %s", e)
    return _ffmpeg

def cargar_motor(avisar: Optional[Callable[[str], None]] = None) -> None:
    global _yt, _motor_error, _hay_js
    try:
        import yt_dlp
        _yt = yt_dlp
        ubicar_ffmpeg()
        _hay_js = hay_runtime_js()
    except Exception as e:
        _motor_error = f"{type(e).__name__}: {e}"
        logger.error("Error al cargar motor de descarga: %s", _motor_error)
    finally:
        _motor_listo.set()
        if avisar:
            if _motor_error:
                avisar("error")
            elif not _ffmpeg[1]:
                avisar("sin_ffmpeg")
            elif not _hay_js:
                avisar("sin_js")
            else:
                avisar("listo")

def es_lista(url: str) -> bool:
    try:
        p = urlparse(url if "://" in url else "https://" + url)
        return "list" in parse_qs(p.query) or p.path.rstrip("/").endswith("/playlist")
    except ValueError:
        return False

def plan_formato(kind: str, fmt: str, res: str, bitrate: str) -> Dict[str, Any]:
    meta = {"key": "FFmpegMetadata"}
    if kind == "audio":
        sel = {"m4a": "bestaudio[ext=m4a]/bestaudio/best",
               "opus": "bestaudio[acodec=opus]/bestaudio/best"}.get(fmt, "bestaudio/best")
        pp = {"key": "FFmpegExtractAudio", "preferredcodec": CODEC_AUDIO[fmt]}
        if fmt in CON_BITRATE:
            pp["preferredquality"] = bitrate
        pps = [pp] if fmt in ("wav", "aac") else [pp, meta]
        return {"format": sel, "postprocessors": pps}

    h = int(res)
    cap = f"[height<={h}]"
    h264 = "[vcodec^=avc1]" if h <= 1080 else ""
    compat = f"bv*{cap}{h264}+ba[ext=m4a]/bv*{cap}[ext=mp4]+ba[ext=m4a]/bv*{cap}+ba/b{cap}/b"

    if fmt == "webm":
        return {"format": f"bv*{cap}[ext=webm]+ba[ext=webm]/bv*{cap}+ba/b{cap}/b",
                "merge_output_format": "webm", "postprocessors": [meta]}
    if fmt == "mkv":
        return {"format": f"bv*{cap}+ba/b{cap}/b",
                "merge_output_format": "mkv", "postprocessors": [meta]}
    if fmt == "mov":
        clave = "FFmpegVideoRemuxer" if h <= 1080 else "FFmpegVideoConvertor"
        return {"format": compat, "merge_output_format": "mp4",
                "postprocessors": [meta, {"key": clave, "preferedformat": "mov"}]}
    if fmt == "avi":
        return {"format": compat, "merge_output_format": "mp4",
                "postprocessors": [meta, {"key": "FFmpegVideoConvertor", "preferedformat": "avi"}],
                "postprocessor_args": {"videoconvertor": ["-c:v", "mpeg4", "-q:v", "3"]}}
    return {"format": compat, "merge_output_format": "mp4", "postprocessors": [meta]}

class RegistroYtDlp:
    def __init__(self, emit: Callable[[str, str, Optional[str]], None]) -> None:
        self._emit = emit
        self.bots = 0
        self._aviso_bot = False

    @staticmethod
    def _limpio(m: Any) -> str:
        m = _ANSI.sub("", str(m)).strip()
        return re.sub(r"^(ERROR|WARNING):\s*", "", m)

    def debug(self, msg: Any) -> None:
        m = self._limpio(msg)
        if "has already been recorded" in m or "has already been downloaded" in m:
            self._emit("log", "↷ Omitido: registrado como descargado.", "aviso")

    info = debug

    def warning(self, msg: Any) -> None:
        m = self._limpio(msg)
        if "No title found in player responses" not in m:
            self._emit("log", "⚠ " + m, "aviso")

    def error(self, msg: Any) -> None:
        m = self._limpio(msg)
        if "not a bot" in m:
            self.bots += 1
            pref = re.match(r"^(\[[^\]]+\]\s*[^:]+:)", m)
            self._emit("log", f"✕ {pref.group(1) + ' ' if pref else ''}YouTube solicitó verificación anti-bot.", "error")
            if not self._aviso_bot:
                self._aviso_bot = True
                self._emit("log", "⚠ YouTube está limitando peticiones. Espera 1 a 2 horas o renueva tus cookies.", "aviso")
            return
        self._emit("log", "✕ " + m, "error")

def normalizar_nombre_archivo(nombre_archivo: str) -> str:
    base = Path(nombre_archivo).stem
    m = _PREFIJO_NUM.match(base)
    if m:
        base = m.group(1)
    return re.sub(r"[\W_]+", "", base).lower()

def _nombres_en(carpeta: Path) -> Set[str]:
    out = set()
    try:
        for f in os.listdir(carpeta):
            norm = normalizar_nombre_archivo(f)
            if norm:
                out.add(norm)
    except OSError:
        pass
    return out

def indexar_existentes(yt: Any, aj: Dict[str, Any], url: str, registro: Any) -> Tuple[Set[str], int, str, str, Optional[List[int]]]:
    destino = Path(aj["dir"])
    quiere_sub = bool(aj.get("subfolder", True))
    defecto = PLANTILLA_LISTA if quiere_sub else PLANTILLA_PLANA
    opts = {"quiet": True, "no_warnings": True, "ignoreerrors": True,
            "extract_flat": "in_playlist", "windowsfilenames": True, "logger": registro,
            "paths": {"home": str(destino)}, "outtmpl": {"default": PLANTILLA_LISTA}}
    if aj.get("cookies"):
        opts["cookiefile"] = aj["cookies"]
    try:
        with yt.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False) or {}
            entradas = [e for e in (info.get("entries") or []) if e and e.get("id")]
            if not entradas:
                return set(), 0, defecto, "", None
            titulo = info.get("title") or "NA"
            base = {"playlist_title": titulo, "playlist": titulo, "playlist_index": 0, "ext": aj["fmt"]}

            def ruta_de(e: Dict[str, Any]) -> Path:
                return Path(ydl.prepare_filename({**e, **base}))

            carpeta_sub = ruta_de(entradas[0]).parent
            en_raiz = _nombres_en(destino)
            en_sub = _nombres_en(carpeta_sub)
            ids_raiz, ids_sub = set(), set()
            for e in entradas:
                nombre = ruta_de(e).name
                norm = normalizar_nombre_archivo(nombre)
                if norm in en_raiz:
                    ids_raiz.add(e["id"])
                if norm in en_sub:
                    ids_sub.add(e["id"])

            usar_sub, nota = quiere_sub, ""
            if usar_sub and carpeta_sub.name.lower() == destino.name.lower():
                usar_sub = False
                nota = "Se usa la carpeta elegida tal cual."
            elif usar_sub and ids_raiz and not ids_sub:
                usar_sub = False
                nota = "Se usa la carpeta elegida (contiene elementos de esta lista)."
            plantilla = PLANTILLA_LISTA if usar_sub else PLANTILLA_PLANA
            ya = ids_raiz | ids_sub
            pendientes = [i for i, e in enumerate(entradas, 1) if e["id"] not in ya]
            return ya, len(entradas), plantilla, nota, pendientes
    except Exception as err:
        logger.error("Error al indexar elementos existentes: %s", err)
        return set(), 0, defecto, "", None

def rangos(indices: List[int]) -> str:
    partes, ini, prev = [], None, None
    for i in sorted(indices):
        if ini is None:
            ini = prev = i
        elif i == prev + 1:
            prev = i
        else:
            partes.append(f"{ini}-{prev}" if prev > ini else str(ini))
            ini = prev = i
    if ini is not None:
        partes.append(f"{ini}-{prev}" if prev > ini else str(ini))
    return ",".join(partes)

def construir_opciones(aj: Dict[str, Any], plantilla: str, hook: Any, filtro: Any, registro: Any, items: Optional[str] = None) -> Dict[str, Any]:
    destino = Path(aj["dir"])
    opts: Dict[str, Any] = {
        "paths": {"home": str(destino)},
        "outtmpl": {"default": plantilla},
        "download_archive": str(destino / f"descargados_{aj['fmt']}.txt"),
        "ignoreerrors": True,
        "retries": 10,
        "fragment_retries": 10,
        "extractor_retries": 3,
        "concurrent_fragment_downloads": 4,
        "http_chunk_size": 10 * 1024 * 1024,
        "windowsfilenames": True,
        "noprogress": True,
        "quiet": True,
        "no_color": True,
        "logger": registro,
        "progress_hooks": [hook],
        "match_filter": filtro,
        "sleep_interval_requests": 1,
        "sleep_interval": 2,
        "max_sleep_interval": 5,
        "js_runtimes": {"deno": {}, "node": {}, "bun": {}, "quickjs": {}},
    }
    if items:
        opts["playlist_items"] = items

    ruta_ff, _ = _ffmpeg
    if ruta_ff:
        opts["ffmpeg_location"] = ruta_ff
    if aj.get("cookies"):
        opts["cookiefile"] = aj["cookies"]
    opts.update(plan_formato(aj["kind"], aj["fmt"], aj["res"], aj["bitrate"]))
    return opts

def ejecutar(urls: List[str], aj: Dict[str, Any], emit: Callable[[str, Any, Optional[str]], None], cancelar: threading.Event) -> str:
    _motor_listo.wait()
    if _motor_error:
        emit("log", f"✕ No se pudo cargar yt-dlp: {_motor_error}", "error")
        return "errores"
    if not _ffmpeg[1]:
        emit("log", "✕ No se encontró ffmpeg.", "error")
        return "errores"

    yt = _yt
    Cancelado = getattr(yt.utils, "DownloadCancelled", yt.utils.DownloadError)
    destino = Path(aj["dir"])
    try:
        destino.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        emit("log", f"✕ Carpeta de destino inválida: {e}", "error")
        return "errores"

    registro = RegistroYtDlp(emit)
    estado: Dict[str, Any] = {"item": None, "t": 0.0, "ya": set(), "pos": {}}

    def hook(d: Dict[str, Any]) -> None:
        if cancelar.is_set():
            raise Cancelado("Cancelado por el usuario")
        info = d.get("info_dict") or {}
        idx, n = info.get("playlist_index"), info.get("n_entries")
        pos_map = estado["pos"]
        if pos_map and idx in pos_map:
            pos, n_sel = pos_map[idx], len(pos_map)
        elif idx and n:
            pos, n_sel = idx, n
        else:
            pos = n_sel = None
        ident = info.get("id")
        if ident != estado["item"]:
            estado["item"] = ident
            pref = f"[{pos}/{n_sel}] " if pos else ""
            titulo = f"{pref}{info.get('title') or ident or ''}"
            emit("log", titulo, None)
            emit("estado", titulo, None)
        if d.get("status") == "downloading":
            ahora = time.monotonic()
            if ahora - estado["t"] < 0.12:
                return
            estado["t"] = me = ahora
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            frac = (d.get("downloaded_bytes") or 0) / total if total else 0.0
            frac = min(max(frac, 0.0), 1.0)
            emit("pct", ((pos - 1) + frac) / n_sel if pos else frac, None)
            emit("stats", f"{frac * 100:5.1f}%  ·  {d.get('_speed_str', '')}  ·  ETA {d.get('_eta_str', '')}", None)
        elif d.get("status") == "finished":
            emit("stats", "Procesando…", None)

    def filtro(info: Dict[str, Any], *, incomplete: bool = False) -> Optional[str]:
        if cancelar.is_set():
            return "Cancelado"
        if registro.bots >= 3:
            return "Detenido por verificación anti-bot"
        if info.get("id") in estado["ya"]:
            return "Ya existe en la carpeta"
        return None

    hubo_errores = False
    max_batch = int(aj.get("max_batch", 0))

    try:
        for i, url in enumerate(urls, 1):
            if cancelar.is_set():
                return "cancelado"
            lista = es_lista(url)
            emit("log", f"\n▶ ({i}/{len(urls)}) {url}" + ("   [lista]" if lista else ""), "titulo")
            estado["ya"], estado["pos"], registro.bots = set(), {}, 0
            plantilla, items, pend = PLANTILLA_VIDEO, None, None
            if lista:
                emit("estado", "Comprobando archivos existentes…", None)
                ya, total, plantilla, nota, pend = indexar_existentes(yt, aj, url, registro)
                estado["ya"] = ya
                if nota:
                    emit("log", "↳ " + nota, "aviso")
                if ya:
                    emit("log", f"↷ {len(ya)} de {total} ya existen y se omitirán.", "aviso")
                if pend is not None:
                    if not pend:
                        emit("log", "✓ Todo ya estaba descargado.", "ok")
                        continue
                    
                    # CORRECCIÓN DE PAGINACIÓN: Límite por lote aplicado sobre PENDIENTES
                    if max_batch > 0 and len(pend) > max_batch:
                        emit("log", f"ℹ Limitando este lote a las primeras {max_batch} canciones pendientes.", "aviso")
                        pend = pend[:max_batch]

                    estado["pos"] = {idx: k for k, idx in enumerate(pend, 1)}
                    items = rangos(pend)

            opts = construir_opciones(aj, plantilla, hook, filtro, registro, items)
            with yt.YoutubeDL(opts) as ydl:
                if ydl.download([url]) != 0:
                    hubo_errores = True
            if registro.bots >= 3:
                emit("log", "⛔ Proceso detenido por seguridad anti-bot.", "error")
                hubo_errores = True
    except Cancelado:
        return "cancelado"
    if cancelar.is_set():
        return "cancelado"
    emit("log", f"\nArchivos guardados en: {destino.resolve()}", None)
    return "errores" if hubo_errores else "ok"