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
    def __init__(self):
        super().__init__()

        self.base_path = get_base_path()
        self.bin_path = get_bin_path()
        self.settings_file = os.path.join(self.base_path, "settings.json")
        self.config_file = os.path.join(self.base_path, "config.yaml")

        # Уничтожаем старые (зависшие) процессы mihomo.exe, чтобы они не ломали интернет
        self.kill_orphaned_mihomo()
        
        self.title("Smart Proxy Manager")
        self.geometry("450x450")
        self.resizable(False, False)

    def kill_orphaned_mihomo(self):
        try:
            # Убиваем все процессы mihomo.exe без вывода ошибок в консоль
            subprocess.call(
                ['taskkill', '/F', '/IM', 'mihomo.exe'], 
                startupinfo=subprocess.STARTUPINFO(), 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL
            )
        except:
            pass

        
        # Исправление работы буфера обмена (Ctrl+C / Ctrl+V) при запуске от имени Администратора
        self.bind("<Control-c>", self.copy_clipboard)
        self.bind("<Control-v>", self.paste_clipboard)
        self.bind("<Control-x>", self.cut_clipboard)

        # Заголовок
        self.title_label = ctk.CTkLabel(self, text="Управление HTTP Прокси", font=ctk.CTkFont(size=20, weight="bold"))
        self.title_label.pack(pady=20)

        # Поля для ввода IP и Порта
        self.ip_entry = ctk.CTkEntry(self, placeholder_text="IP адрес (напр. 192.168.1.10)", width=250)
        self.ip_entry.pack(pady=(10, 5))

        self.port_entry = ctk.CTkEntry(self, placeholder_text="Порт (напр. 8080)", width=250)
        self.port_entry.pack(pady=5)

        # Поля для авторизации (Логин и Пароль)
        self.user_entry = ctk.CTkEntry(self, placeholder_text="Логин (если есть)", width=250)
        self.user_entry.pack(pady=5)

        self.pass_entry = ctk.CTkEntry(self, placeholder_text="Пароль (если есть)", show="*", width=250)
        self.pass_entry.pack(pady=(5, 10))

        # Выбор режима
        self.mode_var = ctk.StringVar(value="global")
        
        self.radio_global = ctk.CTkRadioButton(self, text="Весь ПК (Глобально)", variable=self.mode_var, value="global", command=self.update_ui)
        self.radio_global.pack(pady=10)

        self.radio_app = ctk.CTkRadioButton(self, text="Только для конкретных программ", variable=self.mode_var, value="app", command=self.update_ui)
        self.radio_app.pack(pady=10)

        # Поле для ввода названий программ (будет скрыто в глобальном режиме)
        self.apps_entry = ctk.CTkEntry(self, placeholder_text="Программы: chrome.exe, game.exe", width=250)
        
        # --- Добавляем меню по правой кнопке к каждому полю ---
        self.add_context_menu(self.ip_entry)
        self.add_context_menu(self.port_entry)
        self.add_context_menu(self.user_entry)
        self.add_context_menu(self.pass_entry)
        self.add_context_menu(self.apps_entry)
        
        # Строка статуса/чекера
        self.status_label = ctk.CTkLabel(self, text="Статус: Ожидание...", text_color="gray")
        self.status_label.pack(pady=(10, 0))

        # Общий фрейм для кнопок
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(pady=10)

        # Кнопка проверки прокси
        self.check_btn = ctk.CTkButton(self.btn_frame, text="Проверить", fg_color="gray", hover_color="darkgray", width=100, command=self.check_proxy_thread)
        self.check_btn.grid(row=0, column=0, padx=10)

        # Кнопка включения/выключения
        self.is_running = False
        self.mihomo_process = None
        self.toggle_btn = ctk.CTkButton(self.btn_frame, text="Включить", fg_color="green", hover_color="darkgreen", width=100, command=self.toggle_proxy)
        self.toggle_btn.grid(row=0, column=1, padx=10)

        # Загрузка сохраненных настроек
        self.load_settings()

        # Начальное скрытие текстового поля программ
        self.update_ui()
        
        # Обработка закрытия окна
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

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
        except Exception:
            pass

    def save_settings(self):
        data = {
            "ip": self.ip_entry.get().strip(),
            "port": self.port_entry.get().strip(),
            "user": self.user_entry.get().strip(),
            "password": self.pass_entry.get().strip(),
            "mode": self.mode_var.get(),
            "apps": self.apps_entry.get().strip()
        }
        try:
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception:
            pass

    def update_ui(self):
        # Показываем или скрываем поле программ в зависимости от режима
        if self.mode_var.get() == "app":
            self.apps_entry.pack(pady=5, before=self.status_label)
        else:
            self.apps_entry.pack_forget()
            
    def generate_config(self, ip, port, username, password, mode, apps_str):
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
        
        # Добавляем авторизацию если она есть
        if username and password:
            config["proxies"][0]["username"] = username
            config["proxies"][0]["password"] = password

        # Настраиваем правила (роутинг)
        if mode == "global":
            # Весь трафик идет через прокси
            config["rules"].append("MATCH,MY_PROXY")
        else:
            # Трафик идет через прокси только для указанных процессов
            if apps_str.strip():
                # Разбиваем строку по запятым и пробелам
                apps_list = [app.strip() for app in apps_str.replace(',', ' ').split() if app.strip()]
                for app in apps_list:
                    # Добавляем .exe если юзер забыл
                    if not app.lower().endswith(".exe"):
                        app += ".exe"
                    
                    # ПРИЦЕЛЬНАЯ БЛОКИРОВКА UDP:
                    # HTTP-прокси не поддерживают UDP (включая QUIC и DNS-over-UDP). 
                    # Мы принудительно отбиваем UDP пакеты только от тех программ, которые пускаем через прокси.
                    # Из-за этого Chrome/Firefox за миллисекунду понимают, что QUIC не работает, 
                    # и переключаются на 100% стабильный TCP протокол, который отлично идет через HTTP прокси!
                    config["rules"].append(f"AND,((PROCESS-NAME,{app}),(NETWORK,UDP)),REJECT")
                    
                    # Сам TCP трафик от нужной программы кидаем в наш прокси
                    config["rules"].append(f"PROCESS-NAME,{app},MY_PROXY")
                    
            # Остальной трафик пускаем напрямую мимо прокси (это починит Дискорд, Телеграм и любые другие фоновые программы)
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
            self.status_label.configure(text="Введите IP и порт", text_color="red")
            return
            
        self.status_label.configure(text="Проверяем подключение...", text_color="yellow")
        
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
                
                info = f"✅ Успешно! {country}, {city} ({isp})"
                self.status_label.configure(text=info, text_color="green")
            else:
                self.status_label.configure(text="❌ Сервис не вернул данные", text_color="red")
                
        except requests.exceptions.ProxyError:
            self.status_label.configure(text="❌ Ошибка прокси (неверный IP/Порт/Авторизация)", text_color="red")
        except requests.exceptions.Timeout:
            self.status_label.configure(text="❌ Прокси не отвечает (Таймаут)", text_color="red")
        except Exception as e:
            self.status_label.configure(text="❌ Ошибка подключения", text_color="red")

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
                self.generate_config(ip, port, username, password, mode, apps)
                
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
                self.mihomo_process = subprocess.Popen(
                    [bin_executable, "-d", self.base_path, "-f", self.config_file],
                    startupinfo=startupinfo,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                    cwd=self.base_path
                )
                
                self.is_running = True
                self.toggle_btn.configure(text="Выключить прокси", fg_color="red", hover_color="darkred")
                
            except Exception as e:
                messagebox.showerror("Ошибка запуска", f"Не удалось запустить прокси:\n{str(e)}")
            
        else:
            # Останавливаем процесс
            if self.mihomo_process:
                # Просим закрыться мягко (CTRL_BREAK_EVENT), чтобы mihomo почистил маршруты Windows (TUN)
                try:
                    os.kill(self.mihomo_process.pid, signal.CTRL_BREAK_EVENT)
                    self.mihomo_process.wait(timeout=5)
                except Exception:
                    pass
                try:
                    # Если за 5 сек не закрылся сам - добиваем жестко
                    subprocess.call(['taskkill', '/F', '/T', '/PID', str(self.mihomo_process.pid)], startupinfo=subprocess.STARTUPINFO(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except:
                    pass
                self.mihomo_process = None
                
            self.is_running = False
            self.toggle_btn.configure(text="Включить прокси", fg_color="green", hover_color="darkgreen")

    def on_closing(self):
        self.save_settings()
        # При закрытии окна мягко завершаем прокси
        if self.is_running and self.mihomo_process:
            try:
                os.kill(self.mihomo_process.pid, signal.CTRL_BREAK_EVENT)
                self.mihomo_process.wait(timeout=5)
            except Exception:
                pass
            try:
                subprocess.call(['taskkill', '/F', '/T', '/PID', str(self.mihomo_process.pid)], startupinfo=subprocess.STARTUPINFO(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except:
                pass
        self.destroy()

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
