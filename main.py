import customtkinter as ctk
import tkinter.messagebox as messagebox
import yaml
import subprocess
import os
import signal
import requests
import threading
import sys
import ctypes
import pyperclip
import tkinter as tk
import json

# Настройки внешнего вида
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

def get_base_path():
    """Возвращает путь к папке, где лежит EXE (для конфигов)"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def get_bin_path():
    """Возвращает путь к mihomo.exe (встроенному в EXE или локальному)"""
    if getattr(sys, 'frozen', False):
        # Если запущено из EXE, исходники (включая bin) распаковываются во временную папку _MEIPASS
        bundle_dir = sys._MEIPASS
        return os.path.join(bundle_dir, "bin")
    # Если запуск из .py
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin")

class ProxyApp(ctk.CTk):

    # ─── Цветовая палитра ───
    COLOR_BG          = "#1a1a2e"
    COLOR_CARD        = "#16213e"
    COLOR_CARD_HOVER  = "#1a2744"
    COLOR_ACCENT      = "#7c3aed"
    COLOR_ACCENT_HOVER= "#6d28d9"
    COLOR_GREEN       = "#10b981"
    COLOR_GREEN_HOVER = "#059669"
    COLOR_RED         = "#ef4444"
    COLOR_RED_HOVER   = "#dc2626"
    COLOR_GRAY        = "#64748b"
    COLOR_GRAY_HOVER  = "#475569"
    COLOR_TEXT         = "#e2e8f0"
    COLOR_TEXT_DIM     = "#94a3b8"
    COLOR_ENTRY_BG    = "#0f172a"
    COLOR_ENTRY_BORDER= "#334155"
    APP_VERSION       = "v1.1.0"

    def __init__(self):
        super().__init__()

        self.base_path = get_base_path()
        self.bin_path = get_bin_path()
        self.settings_file = os.path.join(self.base_path, "settings.json")
        self.config_file = os.path.join(self.base_path, "config.yaml")

        # Уничтожаем старые (зависшие) процессы mihomo.exe
        self.kill_orphaned_mihomo()

        # ─── Окно ───
        self.title("Smart Proxy Manager")
        self.geometry("540x700")
        self.resizable(False, False)
        self.configure(fg_color=self.COLOR_BG)

        # Исправление буфера обмена при запуске от имени Администратора
        self.bind("<Control-c>", self.copy_clipboard)
        self.bind("<Control-v>", self.paste_clipboard)
        self.bind("<Control-x>", self.cut_clipboard)

        # ══════════════════════════════════════════
        # ─── ЗАГОЛОВОК ───
        # ══════════════════════════════════════════
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=25, pady=(14, 2))

        self.title_label = ctk.CTkLabel(
            header_frame,
            text="⚡  Smart Proxy Manager",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=self.COLOR_TEXT
        )
        self.title_label.pack(side="left")

        # Индикатор статуса (точка) справа от заголовка
        self.status_dot = ctk.CTkLabel(
            header_frame,
            text="●",
            font=ctk.CTkFont(size=14),
            text_color=self.COLOR_GRAY
        )
        self.status_dot.pack(side="right", padx=(0, 4))

        subtitle = ctk.CTkLabel(
            self,
            text="Управление HTTP-прокси через Mihomo",
            font=ctk.CTkFont(size=12),
            text_color=self.COLOR_TEXT_DIM
        )
        subtitle.pack(anchor="w", padx=28, pady=(0, 8))

        # ══════════════════════════════════════════
        # ─── СЕКЦИЯ 1: Прокси-сервер ───
        # ══════════════════════════════════════════
        proxy_card = ctk.CTkFrame(self, fg_color=self.COLOR_CARD, corner_radius=14)
        proxy_card.pack(fill="x", padx=20, pady=(0, 6))

        ctk.CTkLabel(
            proxy_card,
            text="🌐  Прокси-сервер",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.COLOR_TEXT
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(10, 6))

        # IP
        ctk.CTkLabel(proxy_card, text="IP", font=ctk.CTkFont(size=11), text_color=self.COLOR_TEXT_DIM).grid(
            row=1, column=0, sticky="w", padx=(16, 4), pady=(0, 2)
        )
        self.ip_entry = ctk.CTkEntry(
            proxy_card, placeholder_text="192.168.1.10",
            fg_color=self.COLOR_ENTRY_BG, border_color=self.COLOR_ENTRY_BORDER,
            text_color=self.COLOR_TEXT, width=300, height=34
        )
        self.ip_entry.grid(row=2, column=0, padx=(16, 6), pady=(0, 10), sticky="ew")

        # Port
        ctk.CTkLabel(proxy_card, text="Порт", font=ctk.CTkFont(size=11), text_color=self.COLOR_TEXT_DIM).grid(
            row=1, column=1, sticky="w", padx=(6, 16), pady=(0, 2)
        )
        self.port_entry = ctk.CTkEntry(
            proxy_card, placeholder_text="8080",
            fg_color=self.COLOR_ENTRY_BG, border_color=self.COLOR_ENTRY_BORDER,
            text_color=self.COLOR_TEXT, width=140, height=34
        )
        self.port_entry.grid(row=2, column=1, padx=(6, 16), pady=(0, 10), sticky="ew")

        proxy_card.grid_columnconfigure(0, weight=3)
        proxy_card.grid_columnconfigure(1, weight=1)

        # ══════════════════════════════════════════
        # ─── СЕКЦИЯ 2: Авторизация ───
        # ══════════════════════════════════════════
        auth_card = ctk.CTkFrame(self, fg_color=self.COLOR_CARD, corner_radius=14)
        auth_card.pack(fill="x", padx=20, pady=(0, 6))

        ctk.CTkLabel(
            auth_card,
            text="🔐  Авторизация",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.COLOR_TEXT
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(10, 6))

        # Login
        ctk.CTkLabel(auth_card, text="Логин", font=ctk.CTkFont(size=11), text_color=self.COLOR_TEXT_DIM).grid(
            row=1, column=0, sticky="w", padx=(16, 4), pady=(0, 2)
        )
        self.user_entry = ctk.CTkEntry(
            auth_card, placeholder_text="необязательно",
            fg_color=self.COLOR_ENTRY_BG, border_color=self.COLOR_ENTRY_BORDER,
            text_color=self.COLOR_TEXT, height=34
        )
        self.user_entry.grid(row=2, column=0, padx=(16, 6), pady=(0, 10), sticky="ew")

        # Password
        ctk.CTkLabel(auth_card, text="Пароль", font=ctk.CTkFont(size=11), text_color=self.COLOR_TEXT_DIM).grid(
            row=1, column=1, sticky="w", padx=(6, 16), pady=(0, 2)
        )
        self.pass_entry = ctk.CTkEntry(
            auth_card, placeholder_text="необязательно", show="•",
            fg_color=self.COLOR_ENTRY_BG, border_color=self.COLOR_ENTRY_BORDER,
            text_color=self.COLOR_TEXT, height=34
        )
        self.pass_entry.grid(row=2, column=1, padx=(6, 16), pady=(0, 10), sticky="ew")

        auth_card.grid_columnconfigure(0, weight=1)
        auth_card.grid_columnconfigure(1, weight=1)

        # ══════════════════════════════════════════
        # ─── СЕКЦИЯ 3: Режим работы ───
        # ══════════════════════════════════════════
        mode_card = ctk.CTkFrame(self, fg_color=self.COLOR_CARD, corner_radius=14)
        mode_card.pack(fill="x", padx=20, pady=(0, 6))

        ctk.CTkLabel(
            mode_card,
            text="⚙️  Режим работы",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.COLOR_TEXT
        ).pack(anchor="w", padx=16, pady=(10, 6))

        self.mode_var = ctk.StringVar(value="global")

        radio_frame = ctk.CTkFrame(mode_card, fg_color="transparent")
        radio_frame.pack(fill="x", padx=16, pady=(0, 4))

        self.radio_global = ctk.CTkRadioButton(
            radio_frame, text="🖥  Весь ПК (Глобально)",
            variable=self.mode_var, value="global", command=self.update_ui,
            fg_color=self.COLOR_ACCENT, hover_color=self.COLOR_ACCENT_HOVER,
            text_color=self.COLOR_TEXT, font=ctk.CTkFont(size=13)
        )
        self.radio_global.pack(side="left", padx=(0, 20))

        self.radio_app = ctk.CTkRadioButton(
            radio_frame, text="📋  Только программы",
            variable=self.mode_var, value="app", command=self.update_ui,
            fg_color=self.COLOR_ACCENT, hover_color=self.COLOR_ACCENT_HOVER,
            text_color=self.COLOR_TEXT, font=ctk.CTkFont(size=13)
        )
        self.radio_app.pack(side="left")

        # Поле для ввода программ (скрыто по умолчанию)
        self.apps_frame = ctk.CTkFrame(mode_card, fg_color="transparent")
        self.apps_entry = ctk.CTkEntry(
            self.apps_frame, placeholder_text="chrome.exe, discord.exe, telegram.exe",
            fg_color=self.COLOR_ENTRY_BG, border_color=self.COLOR_ENTRY_BORDER,
            text_color=self.COLOR_TEXT, height=34
        )
        self.apps_entry.pack(fill="x", padx=0, pady=(6, 0))

        # Разделитель в карточке (нижний padding)
        self.mode_card_bottom_spacer = ctk.CTkFrame(mode_card, fg_color="transparent", height=8)
        self.mode_card_bottom_spacer.pack()

        # ══════════════════════════════════════════
        # ─── СЕКЦИЯ 3.5: Домены-исключения ───
        # ══════════════════════════════════════════
        exclude_card = ctk.CTkFrame(self, fg_color=self.COLOR_CARD, corner_radius=14)
        exclude_card.pack(fill="x", padx=20, pady=(0, 6))

        ctk.CTkLabel(
            exclude_card,
            text="🚫  Исключения (домены → напрямую)",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.COLOR_TEXT
        ).pack(anchor="w", padx=16, pady=(10, 6))

        self.exclude_entry = ctk.CTkEntry(
            exclude_card, placeholder_text="google.com, youtube.com, github.com",
            fg_color=self.COLOR_ENTRY_BG, border_color=self.COLOR_ENTRY_BORDER,
            text_color=self.COLOR_TEXT, height=34
        )
        self.exclude_entry.pack(fill="x", padx=16, pady=(0, 10))

        # ─── Контекстные меню ───
        self.add_context_menu(self.ip_entry)
        self.add_context_menu(self.port_entry)
        self.add_context_menu(self.user_entry)
        self.add_context_menu(self.pass_entry)
        self.add_context_menu(self.apps_entry)
        self.add_context_menu(self.exclude_entry)

        # ══════════════════════════════════════════
        # ─── СЕКЦИЯ 4: Статус ───
        # ══════════════════════════════════════════
        status_card = ctk.CTkFrame(self, fg_color=self.COLOR_CARD, corner_radius=14)
        status_card.pack(fill="x", padx=20, pady=(0, 6))

        self.status_label = ctk.CTkLabel(
            status_card,
            text="⏳  Ожидание...",
            font=ctk.CTkFont(size=13),
            text_color=self.COLOR_TEXT_DIM
        )
        self.status_label.pack(padx=16, pady=(8, 3), anchor="w")

        self.progress_bar = ctk.CTkProgressBar(
            status_card,
            progress_color=self.COLOR_ACCENT,
            fg_color=self.COLOR_ENTRY_BG,
            height=6
        )
        self.progress_bar.pack(fill="x", padx=16, pady=(0, 8))
        self.progress_bar.set(0)

        # ══════════════════════════════════════════
        # ─── КНОПКИ ───
        # ══════════════════════════════════════════
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(fill="x", padx=20, pady=(4, 4))

        self.is_running = False
        self.mihomo_process = None

        self.check_btn = ctk.CTkButton(
            self.btn_frame, text="🔍 Проверить",
            fg_color=self.COLOR_GRAY, hover_color=self.COLOR_GRAY_HOVER,
            text_color="white", height=38, corner_radius=10,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.check_proxy_thread
        )
        self.check_btn.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        self.toggle_btn = ctk.CTkButton(
            self.btn_frame, text="▶  Включить",
            fg_color=self.COLOR_GREEN, hover_color=self.COLOR_GREEN_HOVER,
            text_color="white", height=38, corner_radius=10,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.toggle_proxy
        )
        self.toggle_btn.grid(row=0, column=1, padx=6, sticky="ew")

        self.update_core_btn = ctk.CTkButton(
            self.btn_frame, text="⬇  Ядро",
            fg_color=self.COLOR_ACCENT, hover_color=self.COLOR_ACCENT_HOVER,
            text_color="white", height=38, corner_radius=10,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.download_core_thread
        )
        self.update_core_btn.grid(row=0, column=2, padx=(6, 0), sticky="ew")

        self.btn_frame.grid_columnconfigure(0, weight=1)
        self.btn_frame.grid_columnconfigure(1, weight=1)
        self.btn_frame.grid_columnconfigure(2, weight=1)

        # ─── Футер ───
        footer = ctk.CTkLabel(
            self,
            text=f"Smart Proxy Manager {self.APP_VERSION}  •  Mihomo Engine",
            font=ctk.CTkFont(size=10),
            text_color="#475569"
        )
        footer.pack(side="bottom", pady=(0, 8))

        # ─── Загрузка настроек и финализация ───
        self.load_settings()
        self.update_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def kill_orphaned_mihomo(self):
        """Убивает все зависшие процессы mihomo.exe"""
        try:
            subprocess.call(
                ['taskkill', '/F', '/IM', 'mihomo.exe'],
                startupinfo=subprocess.STARTUPINFO(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except:
            pass

    def load_settings(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.ip_entry.insert(0, data.get("ip", ""))
                    self.port_entry.insert(0, data.get("port", ""))
                    self.user_entry.insert(0, data.get("user", ""))
                    self.pass_entry.insert(0, data.get("password", ""))
                    self.mode_var.set(data.get("mode", "global"))
                    self.apps_entry.insert(0, data.get("apps", ""))
                    self.exclude_entry.insert(0, data.get("exclude_domains", ""))
        except Exception:
            pass

    def save_settings(self):
        data = {
            "ip": self.ip_entry.get().strip(),
            "port": self.port_entry.get().strip(),
            "user": self.user_entry.get().strip(),
            "password": self.pass_entry.get().strip(),
            "mode": self.mode_var.get(),
            "apps": self.apps_entry.get().strip(),
            "exclude_domains": self.exclude_entry.get().strip()
        }
        try:
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception:
            pass

    def update_ui(self):
        if self.mode_var.get() == "app":
            self.apps_frame.pack(fill="x", padx=16, pady=(0, 0), before=self.mode_card_bottom_spacer)
        else:
            self.apps_frame.pack_forget()
            
    def generate_config(self, ip, port, username, password, mode, apps_str, exclude_str=""):
        # Парсим домены-исключения
        excluded_domains = []
        if exclude_str and exclude_str.strip():
            for d in exclude_str.replace(',', ' ').split():
                d = d.strip().lower()
                d = d.replace("http://", "").replace("https://", "").strip("/")
                # Убираем www. — DOMAIN-SUFFIX без www. матчит и www.domain, и domain
                if d.startswith("www."):
                    d = d[4:]
                if d:
                    excluded_domains.append(d)

        # Базовая структура конфига
        config = {
            "mode": "rule",
            "log-level": "info",
            "allow-lan": False,
            "udp": True,
            "tcp-concurrent": True,
            "tun": {
                "enable": True,
                "stack": "mixed",
                "auto-route": True,
                "auto-detect-interface": True,
                "endpoint-independent-nat": True,
            },
            "dns": {
                "enable": True,
                "listen": "0.0.0.0:53",
                "ipv6": False,
                "enhanced-mode": "fake-ip",
                "fake-ip-range": "198.18.0.1/16",
                "nameserver": ["8.8.8.8", "1.1.1.1"]
            },
            "sniffer": {
                "enable": True,
                "override-destination": True,
                "sniff": {
                    "TLS": {
                        "ports": [443, 8443]
                    },
                    "HTTP": {
                        "ports": [80, 8080]
                    }
                }
            },
            "proxies": [
                {
                    "name": "MY_PROXY",
                    "type": "http",
                    "server": ip,
                    "port": int(port),
                }
            ],
            "rules": []
        }

        # Добавляем force-domain в sniffer для исключённых доменов
        # Это гарантирует что mihomo будет сниффить эти домены из SNI/Host
        if excluded_domains:
            config["sniffer"]["force-domain"] = excluded_domains

        # Добавляем авторизацию если она есть
        if username and password:
            config["proxies"][0]["username"] = username
            config["proxies"][0]["password"] = password

        # Настраиваем правила (роутинг)
        if mode == "global":
            # Исключения → DIRECT, остальное → PROXY
            for domain in excluded_domains:
                config["rules"].append(f"DOMAIN-SUFFIX,{domain},DIRECT")
            config["rules"].append("MATCH,MY_PROXY")
        else:
            # Режим "для конкретных программ"
            if apps_str.strip():
                apps_list = [app.strip() for app in apps_str.replace(',', ' ').split() if app.strip()]
                for app in apps_list:
                    if not app.lower().endswith(".exe"):
                        app += ".exe"

                    # Для каждого исключённого домена: трафик от этого процесса к этому домену → DIRECT
                    # Ставим ДО правил прокси, чтобы перехватить первыми
                    for domain in excluded_domains:
                        config["rules"].append(f"AND,((PROCESS-NAME,{app}),(DOMAIN-SUFFIX,{domain})),DIRECT")

                    # Блокировка UDP для этого процесса (HTTP-прокси не поддерживает UDP/QUIC)
                    config["rules"].append(f"AND,((PROCESS-NAME,{app}),(NETWORK,UDP)),REJECT")

                    # TCP трафик от нужного процесса → через прокси
                    config["rules"].append(f"PROCESS-NAME,{app},MY_PROXY")

            # Остальной трафик → напрямую
            config["rules"].append("MATCH,DIRECT")

        # Сохраняем в файл config.yaml
        with open(self.config_file, "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

    def check_proxy_thread(self):
        # Запускаем проверку в отдельном потоке, чтобы не вешать интерфейс
        threading.Thread(target=self.do_check_proxy, daemon=True).start()

    def do_check_proxy(self):
        ip = self.ip_entry.get().strip()
        port = self.port_entry.get().strip()
        user = self.user_entry.get().strip()
        pwd = self.pass_entry.get().strip()
        
        if not ip or not port:
            self.status_label.configure(text="⚠️  Введите IP и порт", text_color=self.COLOR_RED)
            return
            
        self.status_label.configure(text="🔄  Проверяем подключение...", text_color="#fbbf24")
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.start()
        
        # Формируем строку прокси для библиотеки requests
        proxy_url = f"http://{user}:{pwd}@{ip}:{port}" if user and pwd else f"http://{ip}:{port}"
        proxies = {"http": proxy_url, "https": proxy_url}
        
        try:
            # Делаем запрос к сервису, чтобы узнать инфу по IP (таймаут 5 сек)
            response = requests.get("http://ip-api.com/json/", proxies=proxies, timeout=5)
            data = response.json()
            
            if data.get("status") == "success":
                country = data.get("country", "Неизвестно")
                city = data.get("city", "Неизвестно")
                real_ip = data.get("query", "Неизвестно")
                isp = data.get("isp", "Неизвестно")
                
                info = f"✅  {country}, {city} — {isp}"
                self.status_label.configure(text=info, text_color=self.COLOR_GREEN)
                self.progress_bar.stop()
                self.progress_bar.configure(mode="determinate")
                self.progress_bar.set(1)
            else:
                self.status_label.configure(text="❌  Сервис не вернул данные", text_color=self.COLOR_RED)
                self.progress_bar.stop()
                self.progress_bar.configure(mode="determinate")
                self.progress_bar.set(0)
                
        except requests.exceptions.ProxyError:
            self.status_label.configure(text="❌  Ошибка прокси (IP/Порт/Авториз.)", text_color=self.COLOR_RED)
            self.progress_bar.stop()
            self.progress_bar.configure(mode="determinate")
            self.progress_bar.set(0)
        except requests.exceptions.Timeout:
            self.status_label.configure(text="❌  Прокси не отвечает (Таймаут)", text_color=self.COLOR_RED)
            self.progress_bar.stop()
            self.progress_bar.configure(mode="determinate")
            self.progress_bar.set(0)
        except Exception as e:
            self.status_label.configure(text="❌  Ошибка подключения", text_color=self.COLOR_RED)
            self.progress_bar.stop()
            self.progress_bar.configure(mode="determinate")
            self.progress_bar.set(0)

    def download_core_thread(self):
        # Если прокси запущен, предупреждаем
        if self.is_running:
            messagebox.showwarning("Внимание", "Сначала выключите прокси перед обновлением ядра!")
            return
        threading.Thread(target=self.do_download_core, daemon=True).start()

    def do_download_core(self):
        import zipfile
        import io
        
        self.status_label.configure(text="🔍  Поиск актуального ядра...", text_color="#fbbf24")
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.start()
        self.update_core_btn.configure(state="disabled")
        try:
            # Получаем инфо о последнем релизе
            resp = requests.get("https://api.github.com/repos/MetaCubeX/mihomo/releases/latest", timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            # Ищем нужный архив для Windows AMD64
            target_asset = None
            for asset in data.get("assets", []):
                # Берём windows amd64 compatible (самый универсальный для 64-бит)
                if "windows-amd64-compatible" in asset["name"] and asset["name"].endswith(".zip"):
                    target_asset = asset
                    break
                    
            if not target_asset:
                for asset in data.get("assets", []):
                    if "windows-amd64" in asset["name"] and asset["name"].endswith(".zip"):
                        target_asset = asset
                        break
            
            if not target_asset:
                self.status_label.configure(text="❌  Ядро для Windows не найдено", text_color=self.COLOR_RED)
                self.progress_bar.stop()
                self.progress_bar.configure(mode="determinate")
                self.progress_bar.set(0)
                self.update_core_btn.configure(state="normal")
                return
                
            download_url = target_asset["browser_download_url"]
            file_name = target_asset["name"]
            
            self.status_label.configure(text=f"⬇  Скачивание {file_name}...", text_color="#fbbf24")
            
            # Скачиваем архив в память
            zip_resp = requests.get(download_url, timeout=60)
            zip_resp.raise_for_status()
            
            self.status_label.configure(text="📦  Распаковка...", text_color="#fbbf24")
            
            # Если папки bin нет, создадим её
            if not os.path.exists(self.bin_path):
                os.makedirs(self.bin_path)
                
            # Распаковываем exe
            with zipfile.ZipFile(io.BytesIO(zip_resp.content)) as z:
                # Ищем .exe внутри
                exe_filename = None
                for name in z.namelist():
                    if name.lower().endswith(".exe"):
                        exe_filename = name
                        break
                
                if exe_filename:
                    exe_data = z.read(exe_filename)
                    # Останавливаем любые зависшие старые процессы перед перезаписью
                    self.kill_orphaned_mihomo()
                    
                    target_path = os.path.join(self.bin_path, "mihomo.exe")
                    with open(target_path, "wb") as f:
                        f.write(exe_data)
                    
                    tag = data.get('tag_name', '')
                    self.status_label.configure(text=f"✅  Ядро обновлено ({tag})", text_color=self.COLOR_GREEN)
                    self.progress_bar.stop()
                    self.progress_bar.configure(mode="determinate")
                    self.progress_bar.set(1)
                else:
                    self.status_label.configure(text="❌  В архиве нет .exe", text_color=self.COLOR_RED)
                    self.progress_bar.stop()
                    self.progress_bar.configure(mode="determinate")
                    self.progress_bar.set(0)
                    
        except Exception as e:
            self.status_label.configure(text="❌  Ошибка скачивания", text_color=self.COLOR_RED)
            self.progress_bar.stop()
            self.progress_bar.configure(mode="determinate")
            self.progress_bar.set(0)
            messagebox.showerror("Ошибка", f"Не удалось скачать ядро:\n{e}")
        finally:
            self.update_core_btn.configure(state="normal")

    def toggle_proxy(self):
        ip = self.ip_entry.get().strip()
        port = self.port_entry.get().strip()
        username = self.user_entry.get().strip()
        password = self.pass_entry.get().strip()
        mode = self.mode_var.get()
        apps = self.apps_entry.get().strip()

        if not ip or not port:
            messagebox.showwarning("Ошибка", "Введите IP и Порт прокси!")
            return
            
        if mode == "app" and not apps:
            messagebox.showwarning("Ошибка", "Укажите хотя бы одну программу (например, chrome.exe)")
            return

        self.save_settings()

        if not self.is_running:
            try:
                # Генерируем конфигурацию
                self.generate_config(ip, port, username, password, mode, apps, self.exclude_entry.get().strip())
                
                # Запускаем Mihomo
                bin_executable = os.path.join(self.bin_path, "mihomo.exe")
                if not os.path.exists(bin_executable):
                    messagebox.showerror("Ошибка", f"Не найден движок: {bin_executable}\nУбедитесь, что положили mihomo.exe в папку bin!")
                    return
                    
                # Запускаем без черного окна консоли (startupinfo)
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                # Запускаем как дочерний процесс
                # Изменяем process_group, чтобы работало мягкое закрытие (CTRL_BREAK_EVENT)
                # Обязательно DEVNULL, иначе буфер переполняется и процесс зависает
                self.mihomo_process = subprocess.Popen(
                    [bin_executable, "-d", self.base_path, "-f", self.config_file],
                    startupinfo=startupinfo,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                    cwd=self.base_path,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                
                self.is_running = True
                self.toggle_btn.configure(text="⏹  Выключить", fg_color=self.COLOR_RED, hover_color=self.COLOR_RED_HOVER)
                self.status_dot.configure(text_color=self.COLOR_GREEN)
                self.status_label.configure(text="🟢  Прокси активен", text_color=self.COLOR_GREEN)
                self.progress_bar.set(1)
                
            except Exception as e:
                messagebox.showerror("Ошибка запуска", f"Не удалось запустить прокси:\n{str(e)}")
            
        else:
            # Останавливаем процесс
            if self.mihomo_process:
                # Просим закрыться мягко (CTRL_BREAK_EVENT), чтобы mihomo почистил маршруты Windows (TUN)
                try:
                    os.kill(self.mihomo_process.pid, signal.CTRL_BREAK_EVENT)
                    self.mihomo_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    # Если за 10 сек не закрылся сам - добиваем жестко
                    try:
                        subprocess.call(['taskkill', '/F', '/T', '/PID', str(self.mihomo_process.pid)], startupinfo=subprocess.STARTUPINFO(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except:
                        pass
                except Exception:
                    pass
                self.mihomo_process = None
                
            self.is_running = False
            self.toggle_btn.configure(text="▶  Включить", fg_color=self.COLOR_GREEN, hover_color=self.COLOR_GREEN_HOVER)
            self.status_dot.configure(text_color=self.COLOR_GRAY)
            self.status_label.configure(text="⏳  Ожидание...", text_color=self.COLOR_TEXT_DIM)
            self.progress_bar.set(0)

    def on_closing(self):
        self.save_settings()
        # При закрытии окна мягко завершаем прокси
        if self.is_running and self.mihomo_process:
            try:
                os.kill(self.mihomo_process.pid, signal.CTRL_BREAK_EVENT)
                self.mihomo_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                try:
                    subprocess.call(['taskkill', '/F', '/T', '/PID', str(self.mihomo_process.pid)], startupinfo=subprocess.STARTUPINFO(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except:
                    pass
            except Exception:
                pass
            
        self.quit()
        self.destroy()
        os._exit(0)

    # --- Обработчики буфера обмена (через pyperclip) ---
    def add_context_menu(self, widget):
        # Создаем стандартное меню Tkinter
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Копировать (Ctrl+C)", command=lambda: self.copy_clipboard(widget))
        menu.add_command(label="Вставить (Ctrl+V)", command=lambda: self.paste_clipboard(widget))
        menu.add_command(label="Вырезать (Ctrl+X)", command=lambda: self.cut_clipboard(widget))
        
        # Привязываем правый клик мыши к показу меню
        widget.bind("<Button-3>", lambda event: menu.tk_popup(event.x_root, event.y_root))

    def copy_clipboard(self, widget=None, event=None):
        widget = widget or self.focus_get()
        if isinstance(widget, ctk.CTkEntry):
            if widget.select_present():
                pyperclip.copy(widget.selection_get())
        return "break"

    def paste_clipboard(self, widget=None, event=None):
        widget = widget or self.focus_get()
        if isinstance(widget, ctk.CTkEntry):
            text = pyperclip.paste()
            if text:
                if widget.select_present():
                    widget.delete(ctk.SEL_FIRST, ctk.SEL_LAST)
                widget.insert(ctk.INSERT, text)
        return "break"

    def cut_clipboard(self, widget=None, event=None):
        widget = widget or self.focus_get()
        if isinstance(widget, ctk.CTkEntry):
            if widget.select_present():
                pyperclip.copy(widget.selection_get())
                widget.delete(ctk.SEL_FIRST, ctk.SEL_LAST)
        return "break"

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if __name__ == "__main__":
    if is_admin():
        # Если мы администратор, запускаем приложение
        app = ProxyApp()
        app.mainloop()
    else:
        # Если нет, пытаемся перезапустить с правами администратора
        print("Запрос прав администратора...")
        if getattr(sys, 'frozen', False):
            # Если это скомпилированный EXE файл
            exe_path = sys.executable
            work_dir = os.path.dirname(exe_path)
            # В sys.argv для EXE первый элемент - это сам EXE, его убираем из параметров
            params = " ".join(sys.argv[1:])
            ctypes.windll.shell32.ShellExecuteW(None, "runas", exe_path, params, work_dir, 1)
        else:
            # Если это обычный питон скрипт
            script = os.path.abspath(sys.argv[0])
            params = " ".join([script] + sys.argv[1:])
            work_dir = os.path.dirname(script)
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, work_dir, 1)
        # Оригинальный процесс без прав просто закрывается
        sys.exit()
