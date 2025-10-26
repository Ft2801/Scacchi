"""
Entry point per l'applicazione Chess.
Questo file importa e avvia l'applicazione dalla cartella src.
"""

import sys
import os
import ctypes
import tkinter as tk

# Aggiungi la directory root al path per permettere gli import da src
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.main import ChessApp
from src.config import THEME_APP
import ttkbootstrap as ttk

if __name__ == "__main__":
    root = ttk.Window(themename=THEME_APP)
    
    # Nascondi la finestra finché non è completamente pronta
    root.withdraw()
    
    # Imposta l'icona della finestra (Regina nera)
    try:
        icon_path = os.path.join(os.path.dirname(__file__), "assets/pieces/bQ.png")
        if os.path.exists(icon_path):
            root.iconphoto(False, tk.PhotoImage(file=icon_path))
    except Exception as e:
        print(f"Avviso: Non è stato possibile impostare l'icona della finestra: {e}")
    
    app = ChessApp(root)
    
    # Imposta la titlebar a tema scuro su Windows 11 (dopo la creazione della GUI)
    root.update()  # Aggiorna per ottenere hwnd valido
    if sys.platform == "win32":
        try:
            hwnd = root.winfo_id()
            # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 
                20, 
                ctypes.byref(ctypes.c_int(1)), 
                ctypes.sizeof(ctypes.c_int)
            )
        except Exception as e:
            print(f"Avviso: Non è stato possibile impostare il tema scuro della titlebar: {e}")
    
    # Rendi visibile la finestra
    root.deiconify()
    root.mainloop()