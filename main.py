"""
Entry point per l'applicazione Chess.
Questo file importa e avvia l'applicazione dalla cartella src.
"""

import sys
import os

# Aggiungi la directory root al path per permettere gli import da src
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.main import ChessApp
from src.config import THEME_APP
import ttkbootstrap as ttk

if __name__ == "__main__":
    root = ttk.Window(themename=THEME_APP)
    app = ChessApp(root)
    root.mainloop()