import tkinter as tk
import time
import psutil
import win32gui
import win32process
from pynput import mouse, keyboard
import threading

class TimeTracker:
    def __init__(self):
        self.running = False
        self.start_time = None
        self.elapsed = 0
        self.last_input_time = time.time()
        self.force_run = False
        self.lock = threading.Lock()

        self.app_usage = {} 
        self.current_app = None
        self.app_start_time = None

        self.listener_mouse = mouse.Listener(on_move=self.on_input, on_click=self.on_input, on_scroll=self.on_input)
        self.listener_keyboard = keyboard.Listener(on_press=self.on_input)
        self.listener_mouse.start()
        self.listener_keyboard.start()

    def on_input(self, *args):
        self.last_input_time = time.time()

    def is_foreground_process(self, process_name):
        foreground_app = self.get_active_process_name()
        if foreground_app is None:
            return False
        return foreground_app == process_name.lower()

    def toggle(self):
        with self.lock:
            if not self.running:
                self.running = True
                self.start_time = time.time()
                self.app_start_time = time.time()
                self.current_app = self.get_active_process_name()
                if self.current_app is None:
                    self.current_app = "알 수 없음"
            else:
                self._update_app_usage()
                self.elapsed += time.time() - self.start_time
                self.running = False
                self.start_time = None
                self.app_start_time = None
                self.current_app = None

    def reset(self):
        with self.lock:
            self.elapsed = 0
            self.start_time = None
            self.running = False
            self.app_usage.clear()
            self.current_app = None
            self.app_start_time = None

    def get_elapsed(self):
        with self.lock:
            total = self.elapsed
            if self.running:
                total += time.time() - self.start_time
            return total

    def get_active_process_name(self):
        hwnd = win32gui.GetForegroundWindow()
        if hwnd == 0:
            return None
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc = psutil.Process(pid)
            if win32gui.IsIconic(hwnd):
                return None
            return proc.name().lower()
        except Exception:
            return None

    def _update_app_usage(self):
        if not self.running or self.current_app is None or self.app_start_time is None:
            return
        now = time.time()
        duration = now - self.app_start_time
        if duration < 0:
            duration = 0
        self.app_usage[self.current_app] = self.app_usage.get(self.current_app, 0) + duration
        self.app_start_time = now

    def update(self):
        vscode_running = any("Code.exe" in p.name() for p in psutil.process_iter(['name']))
        inactive = time.time() - self.last_input_time > 5

        if not vscode_running:
            self.force_run = True
        elif inactive:
            self.force_run = False
        else:
            self.force_run = False

        if self.force_run and not self.running:
            self.running = True
            self.start_time = time.time()
            self.app_start_time = time.time()
            self.current_app = self.get_active_process_name()
            if self.current_app is None:
                self.current_app = "알 수 없음"
        elif not self.force_run and self.running and inactive:
            self._update_app_usage()
            self.elapsed += time.time() - self.start_time
            self.running = False
            self.start_time = None
            self.app_start_time = None
            self.current_app = None
        else:
            if self.running:
                active_app = self.get_active_process_name()
                if active_app is None:
                    self._update_app_usage()
                else:
                    if active_app != self.current_app:
                        self._update_app_usage()
                        self.current_app = active_app
                        self.app_start_time = time.time()
                    else:
                        self._update_app_usage()

class TimeApp:
    def __init__(self, root):
        self.root = root
        self.tracker = TimeTracker()

        self.root.title("시간기록 프로그램")
        self.label = tk.Label(root, text="00:00:00", font=("Arial", 24))
        self.label.pack(pady=10)

        self.text = tk.Text(root, height=15, width=50)
        self.text.pack(pady=10)

        frame = tk.Frame(root)
        frame.pack(pady=10)

        self.start_btn = tk.Button(frame, text="시작", width=10, command=self.toggle)
        self.start_btn.pack(side="left", padx=5)

        self.stop_btn = tk.Button(frame, text="멈춤", width=10, command=self.toggle)
        self.stop_btn.pack(side="left", padx=5)

        self.reset_btn = tk.Button(frame, text="초기화", width=10, command=self.reset)
        self.reset_btn.pack(side="left", padx=5)

        self.update_clock()

    def toggle(self):
        self.tracker.toggle()

    def reset(self):
        self.tracker.reset()
        self.text.delete("1.0", tk.END)

    def update_clock(self):
        self.tracker.update()
        elapsed = int(self.tracker.get_elapsed())
        h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
        self.label.config(text=f"{h:02}:{m:02}:{s:02}")

        self.text.delete("1.0", tk.END)
        for app, seconds in sorted(self.tracker.app_usage.items(), key=lambda x: x[1], reverse=True):
            ah = int(seconds // 3600)
            am = int((seconds % 3600) // 60)
            a_s = int(seconds % 60)
            self.text.insert(tk.END, f"{app}: {ah}시간 {am}분 {a_s}초\n")

        self.root.after(1000, self.update_clock)

if __name__ == "__main__":
    root = tk.Tk()
    app = TimeApp(root)
    root.mainloop()
