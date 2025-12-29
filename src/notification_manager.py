import tkinter as tk
from tkinter import ttk
import threading
import time

class NotificationManager:
    """Gestisce le notifiche toast a comparsa."""
    
    def __init__(self, root):
        self.root = root
        self.notifications = []
        self.unread_count = 0
        self.bell_label = None
        
    def setup_bell_icon(self, parent_frame):
        """Aggiunge l'icona della campanella alla dashboard."""
        container = ttk.Frame(parent_frame, style='Card.TFrame')
        container.pack(side='right', padx=20)
        
        self.bell_label = tk.Label(container, text="🔔 0", font=('Segoe UI Emoji', 12), 
                                  bg='#FFFFFF', fg='#6C757D', cursor="hand2")
        self.bell_label.pack()
        self.bell_label.bind("<Button-1>", self.show_history)
        
    def notify(self, title, message, level="INFO"):
        """Crea una nuova notifica toast."""
        self.unread_count += 1
        self._update_bell()
        
        # Colori base
        bg_color = "#333333"
        fg_color = "#FFFFFF"
        if level == "SUCCESS": bg_color = "#198754"
        elif level == "WARNING": bg_color = "#FFC107"; fg_color="#000000"
        elif level == "ERROR": bg_color = "#DC3545"
        
        # Calcolo posizione (stacking dal basso a destra)
        # Offset base
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        window_width = 300
        window_height = 80
        margin = 20
        
        # Trova slot libero
        active_toasts = [n for n in self.notifications if n['window'].winfo_exists()]
        offset_y = margin + (len(active_toasts) * (window_height + 10))
        
        x = screen_width - window_width - margin
        y = screen_height - window_height - offset_y - 50 # 50px per taskbar approx
        
        # Window
        toast = tk.Toplevel(self.root)
        toast.overrideredirect(True)
        toast.geometry(f"{window_width}x{window_height}+{x}+{y}")
        toast.configure(bg=bg_color)
        toast.attributes("-topmost", True)
        toast.attributes("-alpha", 0.0) # Fade in start
        
        # Content
        tk.Label(toast, text=title, font=('Segoe UI', 10, 'bold'), bg=bg_color, fg=fg_color).pack(anchor='w', padx=10, pady=(10, 0))
        tk.Label(toast, text=message, font=('Segoe UI', 9), bg=bg_color, fg=fg_color, wraplength=280, justify='left').pack(anchor='w', padx=10, pady=(0, 10))
        
        # Close button (X)
        close_btn = tk.Label(toast, text="✕", bg=bg_color, fg=fg_color, cursor="hand2")
        close_btn.place(relx=1.0, rely=0.0, x=-10, y=5, anchor="ne")
        close_btn.bind("<Button-1>", lambda e: self._close_toast(toast))
        
        # Tracking
        self.notifications.append({'window': toast, 'title': title, 'msg': message, 'time': time.time()})
        
        # Animation Fade In
        self._fade_in(toast)
        
        # Auto close
        self.root.after(5000, lambda: self._close_toast(toast))
        
    def _fade_in(self, window, alpha=0):
        if alpha < 0.9:
            alpha += 0.1
            if window.winfo_exists():
                window.attributes("-alpha", alpha)
                self.root.after(20, self._fade_in, window, alpha)

    def _close_toast(self, window):
        if window.winfo_exists():
            window.destroy()
            
    def _update_bell(self):
        if self.bell_label:
            self.bell_label.config(text=f"🔔 {self.unread_count}", fg='#DC3545' if self.unread_count > 0 else '#6C757D')

    def show_history(self, event):
        # Reset counter
        self.unread_count = 0
        self._update_bell()
        # TODO: Mostrare finestra storico se richiesto (per ora resetta solo)

