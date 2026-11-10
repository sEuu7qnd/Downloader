# -*- coding: utf-8 -*-
import argparse
import os
import sys
import threading
from pathlib import Path

from config import Config, APP_NAME
from core import cargar_motor, ejecutar, VIDEO_KEYS, AUDIO_KEYS, RESOLUCIONES, BITRATES
from logs import logger

def _adjuntar_consola_windows() -> None:
    if os.name != "nt": return
    try:
        import ctypes
        if ctypes.windll.kernel32.AttachConsole(-1):
            sys.stdout = sys.stderr = open("CONOUT$", "w", encoding="utf-8")
    except Exception: pass

def modo_cli(args: argparse.Namespace, cfg: Config) -> None:
    _adjuntar_consola_windows()

    if args.cookies:
        try:
            n = cfg.importar_cookies(args.cookies)
            cfg["use_cookies"] = True
            print(f"Cookies guardadas ({n}) en {cfg.cookies}")
        except Exception as e:
            sys.exit(f"Error al importar cookies: {e}")

    if args.formato:
        kind = "video" if args.formato in VIDEO_KEYS else "audio"
        fmt = args.formato
    else:
        kind = cfg["kind"]
        fmt = cfg[kind + "_fmt"]

    cfg["kind"] = kind
    cfg[kind + "_fmt"] = fmt
    cfg["dir"] = str(args.salida or cfg["dir"])
    cfg["resolution"] = args.resolucion or cfg["resolution"]
    cfg["bitrate"] = args.calidad or cfg["bitrate"]
    if args.subcarpeta: cfg["subfolder"] = (args.subcarpeta == "si")
    cfg.guardar()

    if not args.urls: return

    def emit(tipo: str, valor: str, tag: str = None) -> None:
        if tipo == "log": print(valor)
        elif tipo == "stats": print("\r  " + valor.ljust(60), end="", flush=True)

    print("Cargando motor de descarga yt-dlp...")
    cargar_motor()

    aj = {"kind": kind, "fmt": fmt, "res": cfg["resolution"], "bitrate": cfg["bitrate"], "dir": Path(cfg["dir"]).expanduser(), "cookies": cfg.cookies_en_uso(), "subfolder": cfg["subfolder"], "max_batch": cfg["max_batch"]}
    
    cancelar = threading.Event()
    try: resultado = ejecutar(args.urls, aj, emit, cancelar)
    except KeyboardInterrupt:
        cancelar.set()
        sys.exit("\nCancelado por el usuario.")
        
    print({"ok": "\n✓ Listo.", "errores": "\n✕ Terminó con errores.", "cancelado": "\n⚠ Cancelado."}.get(resultado, ""))

def modo_gui(cfg: Config) -> None:
    try: import tkinter as tk
    except ImportError: sys.exit("Falta tkinter. En Linux instala: sudo apt install python3-tk")

    if os.name == "nt":
        try:
            import ctypes; ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception: pass

    from gui.app import App
    App(cfg).mainloop()

def main() -> None:
    parser = argparse.ArgumentParser(description=f"{APP_NAME}: Descarga playlists y videos.")
    parser.add_argument("urls", nargs="*", help="URL(s) de la lista o video")
    parser.add_argument("-f", "--formato", choices=VIDEO_KEYS + AUDIO_KEYS, help="Formato de salida")
    parser.add_argument("-r", "--resolucion", choices=RESOLUCIONES, help="Resolución máxima (video)")
    parser.add_argument("-c", "--calidad", choices=BITRATES, help="Bitrate en kbps (audio)")
    parser.add_argument("-o", "--salida", help="Carpeta de destino")
    parser.add_argument("--subcarpeta", choices=("si", "no"), help="Crear subcarpeta para listas")
    parser.add_argument("--cookies", metavar="ARCHIVO", help="Importar cookies.txt")

    args = parser.parse_args()
    cfg = Config()

    if args.urls or args.cookies: modo_cli(args, cfg)
    else: modo_gui(cfg)

if __name__ == "__main__":
    main()