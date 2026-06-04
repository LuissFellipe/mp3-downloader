import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import threading
import os
import json
import re
from datetime import datetime
import webbrowser
import urllib.request
import io
from PIL import Image

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "download_history.json")

COLOR_BG        = "#0e0e16"
COLOR_PANEL     = "#14141f"
COLOR_CARD      = "#1a1a2e"
COLOR_BORDER    = "#252540"
COLOR_ACCENT    = "#4a7cf7"
COLOR_ACCENT2   = "#6c3fc5"
COLOR_SUCCESS   = "#3dba7a"
COLOR_WARNING   = "#e0a030"
COLOR_ERROR     = "#e05050"
COLOR_TEXT      = "#d0d4f0"
COLOR_MUTED     = "#5a5e80"
COLOR_LOG_BG    = "#0a0a12"


def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_history(history):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


class QualitySelector(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.format_var = tk.StringVar(value="mp3")
        self.quality_var = tk.StringVar(value="320k")

        ctk.CTkLabel(self, text="Formato", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLOR_MUTED).grid(row=0, column=0, sticky="w", padx=(0, 6))
        ctk.CTkLabel(self, text="Qualidade", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLOR_MUTED).grid(row=0, column=1, sticky="w", padx=(10, 6))
        ctk.CTkLabel(self, text="Tipo", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLOR_MUTED).grid(row=0, column=2, sticky="w", padx=(10, 0))

        self.fmt_menu = ctk.CTkOptionMenu(
            self, values=["mp3", "flac", "wav", "ogg", "m4a"],
            variable=self.format_var,
            font=ctk.CTkFont(size=12),
            fg_color=COLOR_CARD, button_color=COLOR_ACCENT,
            button_hover_color=COLOR_ACCENT2,
            dropdown_fg_color=COLOR_PANEL,
            width=90, height=30,
            command=self._on_format_change,
        )
        self.fmt_menu.grid(row=1, column=0, sticky="w", padx=(0, 6), pady=(4, 0))

        self.qual_menu = ctk.CTkOptionMenu(
            self, values=["320k", "256k", "192k", "128k", "96k"],
            variable=self.quality_var,
            font=ctk.CTkFont(size=12),
            fg_color=COLOR_CARD, button_color=COLOR_ACCENT,
            button_hover_color=COLOR_ACCENT2,
            dropdown_fg_color=COLOR_PANEL,
            width=90, height=30,
        )
        self.qual_menu.grid(row=1, column=1, sticky="w", padx=(10, 6), pady=(4, 0))

        self.type_var = tk.StringVar(value="audio")
        self.type_menu = ctk.CTkOptionMenu(
            self, values=["audio", "video (mp4)", "video (webm)"],
            variable=self.type_var,
            font=ctk.CTkFont(size=12),
            fg_color=COLOR_CARD, button_color=COLOR_ACCENT,
            button_hover_color=COLOR_ACCENT2,
            dropdown_fg_color=COLOR_PANEL,
            width=130, height=30,
            command=self._on_type_change,
        )
        self.type_menu.grid(row=1, column=2, sticky="w", padx=(10, 0), pady=(4, 0))

    def _on_type_change(self, value):
        if "video" in value:
            self.fmt_menu.configure(state="disabled")
            self.qual_menu.configure(state="disabled")
        else:
            self.fmt_menu.configure(state="normal")
            self.qual_menu.configure(state="normal")
            self._on_format_change(self.format_var.get())

    def _on_format_change(self, value):
        if value in ("flac", "wav"):
            self.qual_menu.configure(state="disabled")
        else:
            self.qual_menu.configure(state="normal")

    def get_options(self):
        t = self.type_var.get()
        fmt = self.format_var.get()
        qual = self.quality_var.get()
        bitrate = qual.replace("k", "")
        return t, fmt, bitrate


class DownloadItem(ctk.CTkFrame):
    def __init__(self, master, url, index, total, **kwargs):
        super().__init__(master, fg_color=COLOR_CARD, corner_radius=8, **kwargs)
        self.url = url
        self.configure(border_width=1, border_color=COLOR_BORDER)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(8, 2))

        badge = ctk.CTkLabel(top, text=f" {index}/{total} ",
                             font=ctk.CTkFont(size=10, weight="bold"),
                             fg_color=COLOR_ACCENT2, corner_radius=4,
                             text_color="white", width=40)
        badge.pack(side="left", padx=(0, 8))

        short = url if len(url) <= 60 else url[:57] + "..."
        ctk.CTkLabel(top, text=short, font=ctk.CTkFont(family="Consolas", size=11),
                     text_color=COLOR_MUTED, anchor="w").pack(side="left", fill="x", expand=True)

        self.status_label = ctk.CTkLabel(top, text="⏳ Aguardando",
                                          font=ctk.CTkFont(size=11),
                                          text_color=COLOR_MUTED)
        self.status_label.pack(side="right")

        self.bar = ctk.CTkProgressBar(self, mode="indeterminate",
                                       fg_color=COLOR_BORDER,
                                       progress_color=COLOR_ACCENT,
                                       height=4, corner_radius=2)
        self.bar.pack(fill="x", padx=10, pady=(2, 8))
        self.bar.set(0)

        self.title_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=11),
                                         text_color=COLOR_TEXT, anchor="w")

    def set_downloading(self):
        self.bar.start()
        self.status_label.configure(text="⬇ Baixando...", text_color=COLOR_ACCENT)

    def set_done(self, title=""):
        self.bar.stop()
        self.bar.set(1)
        self.bar.configure(progress_color=COLOR_SUCCESS)
        self.status_label.configure(text="✔ Concluído", text_color=COLOR_SUCCESS)
        if title:
            self.title_label.configure(text=f"  {title}")
            self.title_label.pack(fill="x", padx=10, pady=(0, 6))

    def set_failed(self, reason=""):
        self.bar.stop()
        self.bar.configure(mode="determinate", progress_color=COLOR_ERROR)
        self.bar.set(1)
        self.status_label.configure(text="✖ Falhou", text_color=COLOR_ERROR)
        if reason:
            short = reason[:80] + "..." if len(reason) > 80 else reason
            self.title_label.configure(text=f"  {short}", text_color=COLOR_ERROR)
            self.title_label.pack(fill="x", padx=10, pady=(0, 6))


class HistoryWindow(ctk.CTkToplevel):
    def __init__(self, master, history, on_reuse):
        super().__init__(master)
        self.title("Histórico de Downloads")
        self.geometry("700x460")
        self.configure(fg_color=COLOR_BG)
        self.on_reuse = on_reuse

        ctk.CTkLabel(self, text="📋  Histórico de Downloads",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=COLOR_ACCENT).pack(pady=(20, 4))
        ctk.CTkLabel(self, text=f"{len(history)} downloads registrados",
                     font=ctk.CTkFont(size=12), text_color=COLOR_MUTED).pack(pady=(0, 12))

        scroll = ctk.CTkScrollableFrame(self, fg_color=COLOR_PANEL, corner_radius=10)
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        if not history:
            ctk.CTkLabel(scroll, text="Nenhum download registrado ainda.",
                         text_color=COLOR_MUTED).pack(pady=40)
        else:
            for entry in reversed(history):
                row = ctk.CTkFrame(scroll, fg_color=COLOR_CARD, corner_radius=8,
                                   border_width=1, border_color=COLOR_BORDER)
                row.pack(fill="x", pady=3, padx=4)

                info = ctk.CTkFrame(row, fg_color="transparent")
                info.pack(side="left", fill="x", expand=True, padx=10, pady=8)

                status_color = COLOR_SUCCESS if entry.get("status") == "ok" else COLOR_ERROR
                status_icon = "✔" if entry.get("status") == "ok" else "✖"

                ctk.CTkLabel(info, text=f"{status_icon}  {entry.get('title', entry.get('url', '')[:50])}",
                             font=ctk.CTkFont(size=12, weight="bold"),
                             text_color=status_color, anchor="w").pack(anchor="w")
                ctk.CTkLabel(info,
                             text=f"{entry.get('date', '')}  ·  {entry.get('fmt', '').upper()}  ·  {entry.get('url', '')[:50]}",
                             font=ctk.CTkFont(family="Consolas", size=10),
                             text_color=COLOR_MUTED, anchor="w").pack(anchor="w")

                ctk.CTkButton(row, text="↺ Reusar URL",
                              width=100, height=28,
                              font=ctk.CTkFont(size=11),
                              fg_color=COLOR_ACCENT2, hover_color="#8855dd",
                              corner_radius=6,
                              command=lambda u=entry.get("url", ""): self._reuse(u)
                              ).pack(side="right", padx=10)

        ctk.CTkButton(self, text="Fechar", command=self.destroy,
                      fg_color=COLOR_CARD, hover_color=COLOR_BORDER,
                      height=34, corner_radius=8).pack(pady=(0, 16))

    def _reuse(self, url):
        self.on_reuse(url)
        self.destroy()


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("yt-dlp Downloader")
        self.geometry("760x860")
        self.resizable(True, True)
        self.minsize(700, 720)
        self.configure(fg_color=COLOR_BG)

        self.destination_path = tk.StringVar(value="")
        self.is_downloading = False
        self.history = load_history()
        self._drag_data = None
        
        self.github_icon = self._fetch_github_icon()

        self._build_ui()
        self._setup_drag_drop()

    def _fetch_github_icon(self):
        # Baixa a logo oficial branca do GitHub para usar na interface
        try:
            url = "https://github.githubassets.com/images/modules/logos_page/GitHub-Mark-Light.png"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            raw_data = urllib.request.urlopen(req, timeout=5).read()
            im = Image.open(io.BytesIO(raw_data))
            return ctk.CTkImage(light_image=im, dark_image=im, size=(18, 18))
        except Exception:
            return None  # Retorna None se estiver sem internet no momento de abrir

    def _build_ui(self):
        topbar = ctk.CTkFrame(self, fg_color=COLOR_PANEL, height=48, corner_radius=0)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)

        ctk.CTkLabel(topbar, text="🎵  yt-dlp Downloader",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=COLOR_ACCENT).pack(side="left", padx=(20, 10))

        # 1. BOTÃO COM ÍCONE DO GITHUB NO TOPO
        top_github = ctk.CTkButton(topbar, text="LuissFellipe", 
                                   image=self.github_icon,
                                   font=ctk.CTkFont(size=12, weight="bold"),
                                   fg_color="transparent", hover_color=COLOR_CARD,
                                   text_color=COLOR_MUTED, cursor="hand2", width=10,
                                   command=lambda: webbrowser.open_new("https://github.com/LuissFellipe"))
        top_github.pack(side="left")

        ctk.CTkButton(topbar, text="📋 Histórico",
                      command=self._show_history,
                      font=ctk.CTkFont(size=12),
                      fg_color="transparent", hover_color=COLOR_CARD,
                      border_width=1, border_color=COLOR_BORDER,
                      height=30, width=110, corner_radius=6).pack(side="right", padx=10, pady=9)

        body = ctk.CTkFrame(self, fg_color=COLOR_BG)
        body.pack(fill="both", expand=True, padx=0, pady=0)

        url_card = ctk.CTkFrame(body, fg_color=COLOR_CARD, corner_radius=12,
                                border_width=1, border_color=COLOR_BORDER)
        url_card.pack(fill="x", padx=20, pady=(16, 0))

        url_header = ctk.CTkFrame(url_card, fg_color="transparent")
        url_header.pack(fill="x", padx=14, pady=(10, 4))

        ctk.CTkLabel(url_header, text="URLs para Download",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=COLOR_TEXT).pack(side="left")

        ctk.CTkButton(url_header, text="🗑 Limpar",
                      command=self._clear_urls,
                      font=ctk.CTkFont(size=11),
                      fg_color="transparent", hover_color=COLOR_BORDER,
                      border_width=1, border_color=COLOR_BORDER,
                      height=26, width=80, corner_radius=6).pack(side="right")

        ctk.CTkLabel(url_card, text="Cole os links abaixo, um por linha. Suporta arrastar e soltar.",
                     font=ctk.CTkFont(size=11), text_color=COLOR_MUTED).pack(anchor="w", padx=14, pady=(0, 4))

        self.url_textbox = ctk.CTkTextbox(
            url_card, height=120,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color="#0d0d20", text_color=COLOR_TEXT,
            border_color=COLOR_BORDER, border_width=1,
            corner_radius=8, scrollbar_button_color=COLOR_BORDER,
        )
        self.url_textbox.pack(padx=14, pady=(0, 14), fill="x")

        options_card = ctk.CTkFrame(body, fg_color=COLOR_CARD, corner_radius=12,
                                    border_width=1, border_color=COLOR_BORDER)
        options_card.pack(fill="x", padx=20, pady=(10, 0))

        ctk.CTkLabel(options_card, text="Opções de Download",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=COLOR_TEXT).pack(anchor="w", padx=14, pady=(10, 6))

        self.quality_selector = QualitySelector(options_card)
        self.quality_selector.pack(anchor="w", padx=14, pady=(0, 14))

        dest_card = ctk.CTkFrame(body, fg_color=COLOR_CARD, corner_radius=12,
                                  border_width=1, border_color=COLOR_BORDER)
        dest_card.pack(fill="x", padx=20, pady=(10, 0))

        ctk.CTkLabel(dest_card, text="Pasta de Destino",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=COLOR_TEXT).pack(anchor="w", padx=14, pady=(10, 6))

        dest_row = ctk.CTkFrame(dest_card, fg_color="transparent")
        dest_row.pack(fill="x", padx=14, pady=(0, 14))

        self.dest_label = ctk.CTkLabel(
            dest_row,
            text="Nenhuma pasta selecionada",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=COLOR_MUTED, anchor="w", wraplength=480,
        )
        self.dest_label.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ctk.CTkButton(dest_row, text="📁  Selecionar Pasta",
                      command=self._select_folder,
                      font=ctk.CTkFont(size=12, weight="bold"),
                      fg_color=COLOR_ACCENT, hover_color="#2a5fcc",
                      corner_radius=8, width=160, height=34).pack(side="right")

        status_card = ctk.CTkFrame(body, fg_color=COLOR_CARD, corner_radius=12,
                                    border_width=1, border_color=COLOR_BORDER)
        status_card.pack(fill="x", padx=20, pady=(10, 0))

        status_top = ctk.CTkFrame(status_card, fg_color="transparent")
        status_top.pack(fill="x", padx=14, pady=(10, 4))

        self.status_label = ctk.CTkLabel(status_top, text="Aguardando...",
                                          font=ctk.CTkFont(size=12),
                                          text_color=COLOR_MUTED)
        self.status_label.pack(side="left")

        self.count_label = ctk.CTkLabel(status_top, text="",
                                         font=ctk.CTkFont(size=11),
                                         text_color=COLOR_MUTED)
        self.count_label.pack(side="right")

        self.global_bar = ctk.CTkProgressBar(status_card, mode="determinate",
                                              fg_color=COLOR_BORDER,
                                              progress_color=COLOR_ACCENT,
                                              height=6, corner_radius=3)
        self.global_bar.pack(fill="x", padx=14, pady=(0, 10))
        self.global_bar.set(0)

        self.items_frame = ctk.CTkFrame(body, fg_color="transparent")
        self.items_frame.pack(fill="x", padx=20, pady=(8, 0))

        btn_col = ctk.CTkFrame(body, fg_color="transparent")
        btn_col.pack(pady=(16, 4))

        btn_row = ctk.CTkFrame(btn_col, fg_color="transparent")
        btn_row.pack()

        self.download_btn = ctk.CTkButton(
            btn_row, text="⬇  Baixar e Converter",
            command=self._start_download,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=COLOR_ACCENT, hover_color="#2a5fcc",
            corner_radius=10, height=48, width=240,
        )
        self.download_btn.pack(side="left", padx=8)

        ctk.CTkButton(btn_row, text="🗑  Limpar Log",
                      command=self._clear_items,
                      font=ctk.CTkFont(size=13),
                      fg_color=COLOR_CARD, hover_color=COLOR_BORDER,
                      border_width=1, border_color=COLOR_BORDER,
                      corner_radius=10, height=48, width=130).pack(side="left", padx=8)

        ctk.CTkLabel(btn_col,
                     text="✦  O download e a conversão para o formato escolhido acontecem automaticamente em um único passo.",
                     font=ctk.CTkFont(size=11),
                     text_color=COLOR_MUTED).pack(pady=(8, 16))

        log_card = ctk.CTkFrame(body, fg_color=COLOR_LOG_BG, corner_radius=12,
                                 border_width=1, border_color=COLOR_BORDER)
        log_card.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkLabel(log_card, text="Log",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLOR_MUTED).pack(anchor="w", padx=12, pady=(8, 0))

        self.log_box = ctk.CTkTextbox(
            log_card, height=80,
            font=ctk.CTkFont(family="Consolas", size=10),
            fg_color=COLOR_LOG_BG, text_color="#5a9fd8",
            border_width=0, corner_radius=8,
            scrollbar_button_color=COLOR_BORDER,
            state="disabled",
        )
        self.log_box.pack(padx=12, pady=(2, 10), fill="x")

        # 2. BOTÃO COM ÍCONE DO GITHUB NO RODAPÉ
        bottom_github = ctk.CTkButton(body, text="Desenvolvido por LuissFellipe", 
                                      image=self.github_icon,
                                      font=ctk.CTkFont(size=12, weight="bold"),
                                      fg_color="transparent", hover_color=COLOR_LOG_BG,
                                      text_color=COLOR_MUTED, cursor="hand2",
                                      command=lambda: webbrowser.open_new("https://github.com/LuissFellipe"))
        bottom_github.pack(pady=(5, 15))

    def _setup_drag_drop(self):
        self.url_textbox.drop_target_register = lambda *a: None
        try:
            self.url_textbox.bind("<Drop>", self._on_drop)
        except Exception:
            pass

    def _on_drop(self, event):
        data = event.data if hasattr(event, "data") else ""
        if data:
            self.url_textbox.insert("end", "\n" + data.strip())

    def _clear_urls(self):
        self.url_textbox.delete("1.0", "end")

    def _clear_items(self):
        for w in self.items_frame.winfo_children():
            w.destroy()
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")
        self.global_bar.set(0)
        self.status_label.configure(text="Aguardando...", text_color=COLOR_MUTED)
        self.count_label.configure(text="")

    def _select_folder(self):
        folder = filedialog.askdirectory(title="Selecione a pasta de destino")
        if folder:
            self.destination_path.set(folder)
            self.dest_label.configure(text=folder, text_color=COLOR_ACCENT)

    def _log(self, msg):
        self.log_box.configure(state="normal")
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.insert("end", f"[{ts}] {msg}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _add_url_from_history(self, url):
        current = self.url_textbox.get("1.0", "end").strip()
        sep = "\n" if current else ""
        self.url_textbox.insert("end", sep + url)

    def _show_history(self):
        win = HistoryWindow(self, self.history, self._add_url_from_history)
        win.focus()

    def _start_download(self):
        if self.is_downloading:
            return

        raw = self.url_textbox.get("1.0", "end").strip()
        urls = [u.strip() for u in raw.splitlines() if u.strip()]

        if not urls:
            self.status_label.configure(text="⚠  Cole pelo menos uma URL.", text_color=COLOR_WARNING)
            return

        dest = self.destination_path.get()
        if not dest:
            self.status_label.configure(text="⚠  Selecione uma pasta de destino.", text_color=COLOR_WARNING)
            return

        for w in self.items_frame.winfo_children():
            w.destroy()

        self.download_items = []
        for i, url in enumerate(urls, 1):
            item = DownloadItem(self.items_frame, url, i, len(urls))
            item.pack(fill="x", pady=3)
            self.download_items.append(item)

        self.is_downloading = True
        self.download_btn.configure(state="disabled", text="⏳  Convertendo...")
        self.global_bar.set(0)

        t = self.quality_selector.get_options()
        thread = threading.Thread(
            target=self._download_all,
            args=(urls, dest, t),
            daemon=True,
        )
        thread.start()

    def _download_all(self, urls, dest, options):
        dl_type, fmt, bitrate = options
        total = len(urls)
        success = 0
        failed = 0

        for i, url in enumerate(urls):
            item = self.download_items[i]
            self.after(0, self.status_label.configure,
                       {"text": f"⬇  Baixando {i+1} de {total}...", "text_color": COLOR_ACCENT})
            self.after(0, self.count_label.configure, {"text": f"{i+1}/{total}"})
            self.after(0, item.set_downloading)
            self.after(0, self._log, f"Iniciando [{i+1}/{total}]: {url}")

            title_found = ""

            try:
                if "video" in dl_type:
                    vfmt = "mp4" if "mp4" in dl_type else "webm"
                    cmd = [
                        "yt-dlp",
                        "--format", f"bestvideo[ext={vfmt}]+bestaudio/best[ext={vfmt}]/best",
                        "--merge-output-format", vfmt,
                        "--output", os.path.join(dest, "%(title)s.%(ext)s"),
                        "--no-playlist",
                        "--print", "after_move:%(filepath)s",
                        url,
                    ]
                else:
                    cmd = [
                        "yt-dlp",
                        "--extract-audio",
                        "--audio-format", fmt,
                        "--audio-quality", bitrate if fmt not in ("flac", "wav") else "0",
                        "--output", os.path.join(dest, "%(title)s.%(ext)s"),
                        "--no-playlist",
                        "--print", "after_move:%(filepath)s",
                        url,
                    ]

                result = subprocess.run(
                    cmd, capture_output=True, text=True,
                    encoding="utf-8", errors="replace",
                )

                if result.returncode == 0:
                    lines = [l.strip() for l in result.stdout.strip().splitlines() if l.strip()]
                    filepath = lines[-1] if lines else ""
                    title_found = os.path.splitext(os.path.basename(filepath))[0] if filepath else ""
                    success += 1
                    self.after(0, item.set_done, title_found)
                    self.after(0, self._log, f"  ✔ {title_found or 'Concluído'}")
                    self.history.append({
                        "url": url,
                        "title": title_found,
                        "fmt": fmt if "audio" in dl_type else dl_type,
                        "status": "ok",
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    })
                else:
                    failed += 1
                    err = result.stderr.strip().splitlines()
                    err_msg = err[-1] if err else "Erro desconhecido"
                    self.after(0, item.set_failed, err_msg)
                    self.after(0, self._log, f"  ✖ Erro: {err_msg}")
                    self.history.append({
                        "url": url, "title": "", "fmt": fmt,
                        "status": "error",
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    })

            except FileNotFoundError:
                failed += 1
                msg = "yt-dlp não encontrado. Instale com: pip install yt-dlp"
                self.after(0, item.set_failed, msg)
                self.after(0, self._log, f"  ✖ {msg}")
                break
            except Exception as e:
                failed += 1
                self.after(0, item.set_failed, str(e))
                self.after(0, self._log, f"  ✖ Exceção: {e}")

            self.after(0, self.global_bar.set, (i + 1) / total)

        save_history(self.history)
        self.after(0, self._finish, success, failed, total)

    def _finish(self, success, failed, total):
        self.is_downloading = False
        self.download_btn.configure(state="normal", text="⬇  Baixar e Converter")
        self.count_label.configure(text=f"{success} ✔  {failed} ✖")

        if failed == 0:
            self.status_label.configure(
                text=f"✅  Concluído! {success} de {total} arquivo(s) baixado(s).",
                text_color=COLOR_SUCCESS,
            )
            self._log(f"✅ Todos os {total} download(s) concluídos com sucesso!")
        else:
            self.status_label.configure(
                text=f"⚠  {success} concluídos, {failed} com erro.",
                text_color=COLOR_WARNING,
            )
            self._log(f"⚠ Finalizou: {success} ok, {failed} com erro.")


if __name__ == "__main__":
    app = App()
    app.mainloop()

