# -*- coding: utf-8 -*-
import os
import sys
import tkinter as tk
from typing import Any, Callable, List, Optional, Tuple

ESC = 1.0
FAMILIA = "Segoe UI" if os.name == "nt" else ("Helvetica Neue" if sys.platform == "darwin" else "DejaVu Sans")

def P(n: float) -> int: return max(1, int(round(n * ESC)))
def F(tam: int = 10, negrita: bool = False) -> Tuple: return (FAMILIA, tam, "bold") if negrita else (FAMILIA, tam)

def mezclar(a: str, b: str, t: float) -> str:
    ca, cb = [int(a[i:i + 2], 16) for i in (1, 3, 5)], [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(ca, cb))

def rrect(cv: tk.Canvas, x1: float, y1: float, x2: float, y2: float, r: float, **kw: Any) -> int:
    r = max(0.0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    pts = [x1+r, y1, x2-r, y1, x2, y1, x2, y1+r, x2, y2-r, x2, y2, x2-r, y2, x1+r, y2, x1, y2, x1, y2-r, x1, y1+r, x1, y1]
    return cv.create_polygon(pts, smooth=True, **kw)

class Boton(tk.Canvas):
    def __init__(self, master: Any, texto: str, comando: Optional[Callable[[], None]], bg: str = "#0A0A0E", fg: str = "#FFFFFF", ancho: int = 140, alto: int = 40, radio: int = 12, tam: int = 10) -> None:
        self._ancho, self._alto = P(ancho), P(alto)
        super().__init__(master, width=self._ancho, height=self._alto, bg=master.cget("bg"), highlightthickness=0, bd=0, cursor="hand2", takefocus=True)
        self._texto, self._cmd, self._color, self._fg, self._radio, self._tam = texto, comando, bg, fg, P(radio), tam
        self._activo, self._sobre, self._foco = True, False, False
        self.bind("<Enter>", lambda e: self._hover(True))
        self.bind("<Leave>", lambda e: self._hover(False))
        self.bind("<Button-1>", self._click)
        self.bind("<FocusIn>", lambda e: self._set_foco(True))
        self.bind("<FocusOut>", lambda e: self._set_foco(False))
        self.bind("<Return>", self._click)
        self.bind("<space>", self._click)
        self._dibujar()

    def _hover(self, v: bool) -> None: self._sobre = v; self._dibujar()
    def _set_foco(self, v: bool) -> None: self._foco = v; self._dibujar()
    def _click(self, _e: Any = None) -> None: 
        if self._activo and self._cmd: self._cmd()
    def activar(self, v: bool) -> None: 
        self._activo = bool(v); self.configure(cursor="hand2" if v else "arrow", takefocus=v); self._dibujar()

    def _dibujar(self) -> None:
        self.delete("all")
        fondo = (mezclar(self._color, "#FFFFFF", 0.16) if self._sobre else self._color) if self._activo else mezclar(self._color, "#A9AFBE", 0.55)
        fg = self._fg if self._activo else mezclar(self._fg, "#A9AFBE", 0.45)
        rrect(self, 1, 1, self._ancho - 1, self._alto - 1, self._radio, fill=fondo, outline="#007ACC" if self._foco else "", width=2 if self._foco else 0)
        self.create_text(self._ancho / 2, self._alto / 2, text=self._texto, fill=fg, font=F(self._tam, True))

class Segmentado(tk.Canvas):
    def __init__(self, master: Any, opciones: List[Tuple[str, str]], valor: str, comando: Callable[[str], None], ancho: int = 70, alto: int = 38) -> None:
        self._ops, self._seg, self._pad = list(opciones), P(ancho), P(3)
        self._ancho, self._alto = self._seg * len(self._ops) + 2 * self._pad, P(alto)
        super().__init__(master, width=self._ancho, height=self._alto, bg=master.cget("bg"), highlightthickness=0, bd=0)
        self._valor, self._cmd, self._activo, self._sobre = valor, comando, True, -1
        self.bind("<Button-1>", self._click)
        self.bind("<Motion>", self._mover)
        self.bind("<Leave>", lambda e: self._set_sobre(-1))
        self._dibujar()

    def _indice(self, x: float) -> int: i = int((x - self._pad) // self._seg); return i if 0 <= i < len(self._ops) else -1
    def _set_sobre(self, i: int) -> None:
        if i != self._sobre: self._sobre = i; self._dibujar()
    def _mover(self, e: Any) -> None: self._set_sobre(self._indice(e.x) if self._activo else -1); self.configure(cursor="hand2" if self._activo and self._sobre >= 0 else "arrow")
    def _click(self, e: Any) -> None:
        i = self._indice(e.x)
        if self._activo and i >= 0: self.poner(self._ops[i][0], notificar=True)
    def poner(self, valor: str, notificar: bool = False) -> None:
        if valor != self._valor:
            self._valor = valor; self._dibujar()
            if notificar and self._cmd: self._cmd(valor)
    def activar(self, v: bool) -> None: self._activo = bool(v); self._sobre = -1; self._dibujar()

    def _dibujar(self) -> None:
        self.delete("all")
        rrect(self, 1, 1, self._ancho - 1, self._alto - 1, P(12), fill="#F1F2F6", outline="#C6CAD6")
        for i, (clave, etiqueta) in enumerate(self._ops):
            x1, x2 = self._pad + i * self._seg, self._pad + i * self._seg + self._seg
            sel = (clave == self._valor)
            if sel: rrect(self, x1 + 1, self._pad, x2 - 1, self._alto - self._pad, P(9), fill="#8590AB" if self._activo else mezclar("#8590AB", "#FFFFFF", 0.5), outline="")
            elif i == self._sobre and self._activo: rrect(self, x1 + 1, self._pad, x2 - 1, self._alto - self._pad, P(9), fill="#DDE2F0", outline="")
            self.create_text((x1 + x2) / 2, self._alto / 2, text=etiqueta, fill="#FFFFFF" if sel else ("#14161C" if self._activo else "#A3A9B8"), font=F(10, sel))

class Interruptor(tk.Canvas):
    def __init__(self, master: Any, valor: bool, comando: Callable[[bool], None]) -> None:
        self._ancho, self._alto = P(78), P(32)
        super().__init__(master, width=self._ancho, height=self._alto, bg=master.cget("bg"), highlightthickness=0, bd=0, cursor="hand2", takefocus=True)
        self._valor, self._cmd, self._activo, self._foco = bool(valor), comando, True, False
        self.bind("<Button-1>", self._click); self.bind("<FocusIn>", lambda e: self._set_foco(True))
        self.bind("<FocusOut>", lambda e: self._set_foco(False)); self.bind("<Return>", self._click); self.bind("<space>", self._click)
        self._dibujar()

    def _set_foco(self, v: bool) -> None: self._foco = v; self._dibujar()
    def _click(self, _e: Any = None) -> None:
        if self._activo: self.poner(not self._valor, notificar=True)
    def poner(self, v: bool, notificar: bool = False) -> None:
        v = bool(v)
        if v != self._valor:
            self._valor = v; self._dibujar()
            if notificar and self._cmd: self._cmd(v)
    def activar(self, v: bool) -> None: self._activo = bool(v); self.configure(cursor="hand2" if v else "arrow", takefocus=v); self._dibujar()

    def _dibujar(self) -> None:
        self.delete("all")
        w, h, m = self._ancho, self._alto, P(4)
        on = self._valor and self._activo
        rrect(self, 1, 1, w - 1, h - 1, h / 2, fill="#0A0A0E" if on else "#D8DBE5", outline="#007ACC" if self._foco else ("" if on else "#C6CAD6"), width=2 if self._foco else 1)
        d = h - 2 * m
        if on:
            self.create_text(w * 0.32, h / 2, text="ON", fill="#FFFFFF", font=F(9, True))
            self.create_oval(w - m - d, m, w - m, m + d, fill="#FFFFFF", outline="")
        else:
            self.create_text(w * 0.66, h / 2, text="OFF", fill="#7A8196", font=F(9, True))
            self.create_oval(m, m, m + d, m + d, fill="#8590AB" if self._activo else "#B9BECC", outline="")

class Barra(tk.Canvas):
    def __init__(self, master: Any) -> None:
        super().__init__(master, height=P(22), bg=master.cget("bg"), highlightthickness=0, bd=0)
        self._f = 0.0
        self.bind("<Configure>", lambda e: self._dibujar())

    def poner(self, f: float) -> None:
        f = min(max(float(f), 0.0), 1.0)
        if abs(f - self._f) > 0.001: self._f = f; self._dibujar()

    def _dibujar(self) -> None:
        w, h = self.winfo_width(), self.winfo_height()
        if w < 30: return
        self.delete("all")
        m, cy, g, r = P(10), h / 2, P(4), P(8)
        rrect(self, m, cy - g, w - m, cy + g, g, fill="#434F69", outline="")
        x = m + (w - 2 * m) * self._f
        if self._f > 0: rrect(self, m, cy - g, max(x, m + 2 * g), cy + g, g, fill="#DDE2F0", outline="")
        self.create_oval(x - r, cy - r, x + r, cy + r, fill="#FFFFFF", outline="#0A0A0E", width=2)

class Tarjeta(tk.Canvas):
    CAB, PAD = 36, 16
    def __init__(self, master: Any, titulo: str, cuerpo_bg: str = "#FFFFFF", expandir: bool = False) -> None:
        super().__init__(master, height=P(100), bg=master.cget("bg"), highlightthickness=0, bd=0)
        self._titulo, self._cb, self._expandir = titulo, cuerpo_bg, expandir
        self.cuerpo = tk.Frame(self, bg=cuerpo_bg)
        self._ventana = self.create_window(P(self.PAD), P(self.CAB + self.PAD), window=self.cuerpo, anchor="nw")
        self.bind("<Configure>", self._al_cambiar)
        self.cuerpo.bind("<Configure>", self._al_cambiar_cuerpo)

    def titulo(self, texto: str) -> None: self._titulo = texto; self._dibujar(self.winfo_width())
    def _al_cambiar_cuerpo(self, _e: Any) -> None:
        h = self.cuerpo.winfo_reqheight() + P(self.CAB + 2 * self.PAD)
        if int(float(self.cget("height"))) != h: self.configure(height=h)
    def _al_cambiar(self, e: Any) -> None:
        self.itemconfigure(self._ventana, width=max(10, e.width - 2 * P(self.PAD)))
        if self._expandir: self.itemconfigure(self._ventana, height=max(P(30), e.height - P(self.CAB + 2 * self.PAD)))
        self._dibujar(e.width)
    def _dibujar(self, w: float) -> None:
        h = self.winfo_height()
        if w < 20 or h < 20: return
        self.delete("fondo")
        r = P(14)
        rrect(self, 0, 0, w, h, r, fill=self._cb, outline="", tags="fondo")
        rrect(self, 0, 0, w, P(self.CAB) + r, r, fill="#0A0A0E", outline="", tags="fondo")
        self.create_rectangle(0, P(self.CAB), w, P(self.CAB) + r + 1, fill=self._cb, outline="", tags="fondo")
        self.create_text(P(18), P(self.CAB) / 2, text=self._titulo, anchor="w", fill="#FFFFFF", font=F(10, True), tags="fondo")

class Nav(tk.Canvas):
    PESTANAS = (("video", "▶  Video"), ("audio", "♪  Audio"))
    def __init__(self, master: Any, al_elegir: Callable[[str], None]) -> None:
        self._alto = P(60)
        super().__init__(master, height=self._alto, bg=master.cget("bg"), highlightthickness=0, bd=0)
        self._cmd, self._tipo, self._tabs = al_elegir, "video", {}
        self._chip = ("Cargando motor…", "#F5B731")
        self.bind("<Configure>", lambda e: self._dibujar())
        self.bind("<Button-1>", self._click)
        self.bind("<Motion>", self._mover)

    def poner_tipo(self, tipo: str) -> None: self._tipo = tipo; self._dibujar()
    def poner_estado(self, texto: str, color: str) -> None: self._chip = (texto, color); self._dibujar()
    
    def _en_pestana(self, x: float, y: float) -> Optional[str]:
        for clave, (x1, x2) in self._tabs.items():
            if x1 <= x <= x2 and 0 <= y <= self._alto: return clave
        return None
        
    def _mover(self, e: Any) -> None: self.configure(cursor="hand2" if self._en_pestana(e.x, e.y) else "arrow")
    def _click(self, e: Any) -> None:
        if clave := self._en_pestana(e.x, e.y):
            if clave != self._tipo: self._cmd(clave)

    def _dibujar(self) -> None:
        w, h = self.winfo_width(), self._alto
        if w < 50: return
        self.delete("all")
        rrect(self, 0, 0, w, h, h / 2, fill="#0A0A0E", outline="")
        self.create_text(P(30), h / 2, text="Downloader", anchor="w", fill="#FFFFFF", font=F(15, True))
        x = P(250)
        self._tabs = {}
        for clave, texto in self.PESTANAS:
            x1, x2 = x, x + P(130)
            if clave == self._tipo:
                self.create_rectangle(x1, 0, x2, h, fill="#8590AB", outline="")
                self.create_rectangle(x1, h - P(4), x2, h, fill="#FFFFFF", outline="")
            self.create_text((x1 + x2) / 2, h / 2 - P(1), text=texto, fill="#FFFFFF", font=F(11, True))
            self._tabs[clave] = (x1, x2)
            x = x2
            
        texto, color = self._chip
        t = self.create_text(w - P(30), h / 2, text=texto, anchor="e", fill="#FFFFFF", font=F(9))
        x0 = self.bbox(t)[0] - P(14)
        r = P(5)
        self.create_oval(x0 - r, h / 2 - r, x0 + r, h / 2 + r, fill=color, outline="")