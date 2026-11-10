# -*- coding: utf-8 -*-
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import Any, List

from config import Config, APP_NAME
from core import BITRATES, RESOLUCIONES, AUDIO, VIDEO, cargar_motor, ejecutar, _motor_listo, _motor_error
from gui import widgets
from gui.widgets import Boton, Interruptor, Nav, Segmentado, Tarjeta, Barra, P, F

class App(tk.Tk):
    def __init__(self, cfg: Config) -> None:
        super().__init__()
        try: widgets.ESC = max(1.0, self.winfo_fpixels("1i") / 96.0)
        except Exception: widgets.ESC = 1.0

        self.cfg = cfg
        self.title(APP_NAME)
        self.configure(bg="#A9AFBE")
        
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = min(P(980), sw - P(40)), min(P(760), sh - P(90))
        self.geometry(f"{w}x{h}+{max(0, (sw - w) // 2)}+{max(0, (sh - h) // 2 - P(20))}")
        self.minsize(min(P(900), w), min(P(680), h))

        self.cola: queue.Queue = queue.Queue()
        self.cancelar = threading.Event()
        self.hilo: Any = None
        self.trabajando = False
        self.dir_var = tk.StringVar(value=cfg["dir"])

        self._construir()
        self._aplicar_tipo()
        self._refrescar_cookies()
        
        self.protocol("WM_DELETE_WINDOW", self._cerrar)
        self.after(50, self._poll)
        self.after(150, self._lanzar_motor)

    def _construir(self) -> None:
        cfg = self.cfg
        g, gap = P(18), P(12)
        self.columnconfigure(0, weight=5, minsize=P(520))
        self.columnconfigure(1, weight=3, minsize=P(300))
        self.rowconfigure(5, weight=1)
        
        # --- Barra de navegación superior ---
        self.nav = Nav(self, self._elegir_tipo)
        self.nav.grid(row=0, column=0, columnspan=2, sticky="ew", padx=g, pady=(g, gap))

        t1 = Tarjeta(self, "Enlaces")
        t1.grid(row=1, column=0, sticky="nsew", padx=(g, gap // 2), pady=(0, gap))
        marco_txt = tk.Frame(t1.cuerpo, bg="#C6CAD6", padx=1, pady=1)
        marco_txt.pack(fill="x")
        self.txt = tk.Text(marco_txt, height=4, wrap="char", relief="flat", bd=0, bg="#F1F2F6", fg="#14161C", font=F(10), padx=P(10), pady=P(8), undo=True)
        self.txt.pack(fill="x")
        tk.Label(t1.cuerpo, text="Pega enlaces de listas o videos, uno por línea.", bg="#FFFFFF", fg="#5B6275", font=F(9), anchor="w").pack(fill="x", pady=(P(8), 0))

        t2 = Tarjeta(self, "Carpeta de destino")
        t2.grid(row=1, column=1, sticky="nsew", padx=(gap // 2, g), pady=(0, gap))
        marco_ent = tk.Frame(t2.cuerpo, bg="#C6CAD6", padx=1, pady=1)
        marco_ent.pack(fill="x")
        self.ent = tk.Entry(marco_ent, textvariable=self.dir_var, relief="flat", bd=0, bg="#F1F2F6", fg="#14161C", font=F(10))
        self.ent.pack(fill="x", ipady=P(8))
        self.ent.bind("<FocusOut>", lambda e: self._guardar_dir())
        self.ent.bind("<Return>", lambda e: self._guardar_dir())
        
        fila_btns = tk.Frame(t2.cuerpo, bg="#FFFFFF")
        fila_btns.pack(fill="x", pady=(P(10), 0))
        Boton(fila_btns, "Examinar…", self._elegir_dir, bg="#8590AB", ancho=112, alto=36, radio=10, tam=9).pack(side="left")
        Boton(fila_btns, "Abrir", self._abrir_dir, bg="#0A0A0E", ancho=124, alto=36, radio=10, tam=9).pack(side="left", padx=(P(8), 0))
        
        fila_sw = tk.Frame(t2.cuerpo, bg="#FFFFFF")
        fila_sw.pack(fill="x", pady=(P(12), 0))
        self.sw_sub = Interruptor(fila_sw, cfg["subfolder"], self._toggle_sub)
        self.sw_sub.pack(side="left")
        tk.Label(fila_sw, text="Subcarpeta para listas", bg="#FFFFFF", fg="#14161C", font=F(9)).pack(side="left", padx=(P(10), 0))

        self.card_fmt = Tarjeta(self, "Formato")
        self.card_fmt.grid(row=2, column=0, sticky="nsew", padx=(g, gap // 2), pady=(0, gap))
        b_fmt = self.card_fmt.cuerpo
        self.seg_v = Segmentado(b_fmt, VIDEO, cfg["video_fmt"], self._cambia_fmt, ancho=76)
        self.seg_a = Segmentado(b_fmt, AUDIO, cfg["audio_fmt"], self._cambia_fmt, ancho=64)
        self.lbl_q = tk.Label(b_fmt, text="", bg="#FFFFFF", fg="#14161C", font=F(9, True), anchor="w")
        self.seg_r = Segmentado(b_fmt, [(r, r + "p") for r in RESOLUCIONES], cfg["resolution"], self._cambia_res, ancho=66)
        self.seg_b = Segmentado(b_fmt, [(x, x) for x in BITRATES], cfg["bitrate"], self._cambia_bit, ancho=66)
        self.lbl_q.grid(row=1, column=0, sticky="w", pady=(P(12), P(4)))

        fila_lote = tk.Frame(b_fmt, bg="#FFFFFF")
        fila_lote.grid(row=3, column=0, sticky="w", pady=(P(12), 0))
        tk.Label(fila_lote, text="Límite por lote:", bg="#FFFFFF", fg="#14161C", font=F(9, True)).pack(side="left")
        self.seg_lote = Segmentado(fila_lote, [("25", "25"), ("50", "50"), ("100", "100"), ("0", "Todo")], str(cfg["max_batch"]), self._cambia_lote, ancho=50, alto=30)
        self.seg_lote.pack(side="left", padx=(P(10), 0))

        t3 = Tarjeta(self, "Cookies")
        t3.grid(row=2, column=1, sticky="nsew", padx=(gap // 2, g), pady=(0, gap))
        b_ck = t3.cuerpo
        self.lbl_ck = tk.Label(b_ck, text="", bg="#FFFFFF", fg="#14161C", font=F(9), anchor="w", justify="left", wraplength=P(260))
        self.lbl_ck.pack(fill="x")
        
        fila_ck = tk.Frame(b_ck, bg="#FFFFFF")
        fila_ck.pack(fill="x", pady=(P(10), 0))
        Boton(fila_ck, "Importar…", self._importar_cookies, bg="#8590AB", ancho=108, alto=36, radio=10, tam=9).pack(side="left")
        self.btn_quitar = Boton(fila_ck, "Quitar", self._quitar_cookies, bg="#ED1C24", ancho=84, alto=36, radio=10, tam=9)
        self.btn_quitar.pack(side="left", padx=(P(8), 0))
        
        fila_swck = tk.Frame(b_ck, bg="#FFFFFF")
        fila_swck.pack(fill="x", pady=(P(12), 0))
        self.sw = Interruptor(fila_swck, cfg["use_cookies"], self._toggle_cookies)
        self.sw.pack(side="left")
        tk.Label(fila_swck, text="Usar cookies", bg="#FFFFFF", fg="#14161C", font=F(9)).pack(side="left", padx=(P(10), 0))

        fila_ctrl = tk.Frame(self, bg="#A9AFBE")
        fila_ctrl.grid(row=3, column=0, columnspan=2, sticky="ew", padx=g, pady=(0, P(4)))
        self.btn_desc = Boton(fila_ctrl, "↓   Descargar", self._iniciar, bg="#0A0A0E", ancho=190, alto=46, radio=14, tam=12)
        self.btn_desc.pack(side="left")
        self.btn_canc = Boton(fila_ctrl, "✕   Cancelar", self._cancelar, bg="#ED1C24", ancho=140, alto=46, radio=14, tam=11)
        self.btn_canc.pack(side="left", padx=(P(10), 0))
        self.btn_canc.activar(False)
        
        self.lbl_stats = tk.Label(fila_ctrl, text="", bg="#A9AFBE", fg="#14161C", font=F(10), anchor="e")
        self.lbl_stats.pack(side="right")
        self.lbl_estado = tk.Label(fila_ctrl, text="Listo.", bg="#A9AFBE", fg="#14161C", font=F(10, True), anchor="w")
        self.lbl_estado.pack(side="left", padx=(P(16), 0), fill="x", expand=True)

        self.barra = Barra(self)
        self.barra.grid(row=4, column=0, columnspan=2, sticky="ew", padx=g, pady=(P(2), gap))

        t4 = Tarjeta(self, "Registro", cuerpo_bg="#434F69", expandir=True)
        t4.grid(row=5, column=0, columnspan=2, sticky="nsew", padx=g, pady=(0, g))
        self.log = tk.Text(t4.cuerpo, height=5, wrap="word", relief="flat", bd=0, bg="#434F69", fg="#E8ECF5", font=("Consolas", 9), state="disabled", padx=0, pady=0)
        self.log.pack(fill="both", expand=True)
        self.log.tag_configure("error", foreground="#FF9B9B")
        self.log.tag_configure("ok", foreground="#B6E36B")
        self.log.tag_configure("aviso", foreground="#FFD479")
        self.log.tag_configure("titulo", foreground="#FFFFFF", font=("Consolas", 9, "bold"))

    def _lanzar_motor(self) -> None:
        def avisar(estado: str) -> None: self.cola.put(("motor", estado, None))
        threading.Thread(target=cargar_motor, args=(avisar,), daemon=True).start()
        
    def _elegir_tipo(self, tipo: str) -> None:
        self.cfg["kind"] = tipo
        self._aplicar_tipo()
        self.cfg.guardar()

    def _aplicar_tipo(self) -> None:
        tipo = self.cfg["kind"]
        self.nav.poner_tipo(tipo)
        if tipo == "video":
            self.seg_a.grid_remove(); self.seg_b.grid_remove()
            self.seg_v.grid(row=0, column=0, sticky="w"); self.seg_r.grid(row=2, column=0, sticky="w")
            self.card_fmt.titulo("Formato de video"); self.lbl_q.configure(text="Resolución máxima")
        else:
            self.seg_v.grid_remove(); self.seg_r.grid_remove()
            self.seg_a.grid(row=0, column=0, sticky="w"); self.seg_b.grid(row=2, column=0, sticky="w")
            self.card_fmt.titulo("Formato de audio"); self.lbl_q.configure(text="Calidad de audio (kbps)")

    def _estado_motor(self, estado: str) -> None:
        if estado == "listo":
            self.nav.poner_estado("Listo", "#8DC63F")
        elif estado == "sin_js":
            self.nav.poner_estado("Falta Deno", "#F5B731")
            self._log("⚠ YouTube podría ocultar calidades altas sin Deno/Node.js.", "aviso")
        elif estado == "sin_ffmpeg":
            self.nav.poner_estado("Falta ffmpeg", "#ED1C24")
            self._log("✕ No se encontró ffmpeg.", "error")
        else:
            self.nav.poner_estado("Error", "#ED1C24")
            self._log("✕ Error del motor de descarga.", "error")

    def _cambia_fmt(self, clave: str) -> None: self.cfg[self.cfg["kind"] + "_fmt"] = clave; self.cfg.guardar()
    def _cambia_res(self, v: str) -> None: self.cfg["resolution"] = v; self.cfg.guardar()
    def _cambia_bit(self, v: str) -> None: self.cfg["bitrate"] = v; self.cfg.guardar()
    def _cambia_lote(self, v: str) -> None: self.cfg["max_batch"] = int(v); self.cfg.guardar()

    def _guardar_dir(self) -> None:
        d = self.dir_var.get().strip()
        if d: self.cfg["dir"] = d; self.cfg.guardar()

    def _elegir_dir(self) -> None:
        if d := filedialog.askdirectory(initialdir=self.dir_var.get() or str(Path.home()), title="Carpeta destino"):
            self.dir_var.set(os.path.normpath(d)); self._guardar_dir()

    def _abrir_dir(self) -> None:
        p = Path(self.dir_var.get().strip() or self.cfg["dir"]).expanduser()
        try:
            p.mkdir(parents=True, exist_ok=True)
            if os.name == "nt": os.startfile(str(p))
            elif sys.platform == "darwin": subprocess.Popen(["open", str(p)])
            else: subprocess.Popen(["xdg-open", str(p)])
        except Exception as e: self._log(f"✕ No se pudo abrir la carpeta: {e}", "error")

    def _toggle_sub(self, v: bool) -> None: self.cfg["subfolder"] = v; self.cfg.guardar()
    def _toggle_cookies(self, v: bool) -> None: self.cfg["use_cookies"] = v; self.cfg.guardar()

    def _refrescar_cookies(self) -> None:
        info = self.cfg.info_cookies()
        if info: self.lbl_ck.configure(text=f"✓ Guardadas: {info[0]} cookies\nActualizado: {info[1]}")
        else: self.lbl_ck.configure(text="Sin cookies guardadas.")
        self.btn_quitar.activar(bool(info)); self.sw.activar(bool(info)); self.sw.poner(bool(info) and self.cfg["use_cookies"])

    def _importar_cookies(self) -> None:
        ruta = filedialog.askopenfilename(title="Selecciona cookies.txt", filetypes=[("TXT", "*.txt"), ("Todos", "*.*")])
        if not ruta: return
        try:
            n = self.cfg.importar_cookies(ruta)
            self.cfg["use_cookies"] = True; self.cfg.guardar(); self._refrescar_cookies()
            self._log(f"✓ Cookies guardadas ({n}).", "ok")
        except Exception as e: messagebox.showerror(APP_NAME, f"Error:\n{e}")

    def _quitar_cookies(self) -> None: self.cfg.quitar_cookies(); self._refrescar_cookies(); self._log("Cookies eliminadas.", "aviso")

    def _log(self, texto: str, tag: str = "") -> None:
        self.log.configure(state="normal")
        self.log.insert("end", texto + "\n", tag); self.log.see("end"); self.log.configure(state="disabled")

    def _poll(self) -> None:
        try:
            for _ in range(50):
                tipo, valor, tag = self.cola.get_nowait()
                if tipo == "log": self._log(valor, tag)
                elif tipo == "estado": self.lbl_estado.configure(text=valor[:90])
                elif tipo == "stats": self.lbl_stats.configure(text=valor)
                elif tipo == "pct": self.barra.poner(valor)
                elif tipo == "motor": self._estado_motor(valor)
                elif tipo == "fin": self._fin(valor, tag)
        except queue.Empty: pass
        self.after(100, self._poll)

    def _leer_urls(self) -> List[str]: return [u for u in self.txt.get("1.0", "end").split() if u]

    def _iniciar(self) -> None:
        if self.trabajando: return
        urls = self._leer_urls()
        if not urls:
            self._log("Pega al menos un enlace.", "aviso")
            return
        self._guardar_dir()
        
        tipo = self.cfg["kind"]
        aj = {"kind": tipo, "fmt": self.cfg[tipo + "_fmt"], "res": self.cfg["resolution"], "bitrate": self.cfg["bitrate"], "dir": Path(self.cfg["dir"]).expanduser(), "cookies": self.cfg.cookies_en_uso(), "subfolder": self.cfg["subfolder"], "max_batch": self.cfg["max_batch"]}
        
        self.cancelar.clear(); self.trabajando = True; self.barra.poner(0)
        self.lbl_estado.configure(text="Conectando…"); self.btn_desc.activar(False); self.btn_canc.activar(True)
        self.hilo = threading.Thread(target=self._trabajo, args=(urls, aj), daemon=True)
        self.hilo.start()

    def _trabajo(self, urls: List[str], aj: dict) -> None:
        def emit(tipo: str, valor: Any, tag: str = None) -> None: self.cola.put((tipo, valor, tag))
        try: resultado = ejecutar(urls, aj, emit, self.cancelar)
        except Exception as e: emit("log", f"✕ Error crítico: {e}", "error"); resultado = "errores"
        emit("fin", "", resultado)

    def _fin(self, _texto: str, resultado: str) -> None:
        self.trabajando = False; self.btn_desc.activar(True); self.btn_canc.activar(False)
        if resultado == "ok":
            self.barra.poner(1); self.lbl_estado.configure(text="✓ Descarga finalizada"); self._log("✓ Descarga finalizada.", "ok")
        elif resultado == "cancelado": self.lbl_estado.configure(text="Cancelado")
        else: self.lbl_estado.configure(text="Terminó con errores")

    def _cancelar(self) -> None:
        if self.trabajando: self.cancelar.set(); self.lbl_estado.configure(text="Cancelando…")

    def _cerrar(self) -> None:
        if self.trabajando:
            if not messagebox.askyesno(APP_NAME, "Hay una descarga en curso.\n¿Cancelar y salir?"): return
            self.cancelar.set()
        self._guardar_dir(); self.destroy(); os._exit(0)