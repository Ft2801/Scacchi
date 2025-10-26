# main.py
"""
Applicazione principale di scacchi con interfaccia grafica.

Gestisce l'interfaccia utente, la logica di gioco, l'analisi delle mosse,
e l'integrazione con il motore Stockfish per l'IA e l'analisi.
"""

import tkinter as tk
from tkinter import messagebox, Toplevel, Text, CENTER
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import chess
import chess.pgn
import datetime
import pyperclip
import threading
import queue

from src.config import *
from src.core.game_logic import GameLogic
from src.ui.ui_components import ChessBoard, EvalBar
from src.analysis.advanced_move_classifier import AdvancedMoveClassifier
from src.core.stockfish_manager import StockfishManager, eval_to_centipawns
from src.analysis.accuracy_calculator import (
    move_accuracy_percent, 
    calculate_final_accuracy
)
from src.utils.utils import (
    is_ai_turn, 
    safe_widget_exists,
    get_ai_level_for_turn,
    create_pgn_headers,
    build_board_from_moves,
    calculate_player_accuracy
)

class ChessApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Chess")
        self.logic = GameLogic()
        self.game_mode = None
        self.selected_square = None
        self.is_board_flipped = False
        self.auto_flip_var = tk.BooleanVar()
        
        self.main_container = ttk.Frame(master, padding=MAIN_CONTAINER_PADDING)
        self.main_container.pack(fill=BOTH, expand=True)
        
        self.eval_bar_var = tk.BooleanVar(value=False)
        self.show_best_move_var = tk.BooleanVar(value=False)
                
        self.eval_thread = None
        self.eval_thread_running = False
        self.eval_queue = queue.Queue()
        self.new_eval_request = threading.Event()
        self.force_reanalyze = False
        self.review_queue = queue.Queue()
        self.review_data = []
        
        # Caricamento lazy di Stockfish - non caricato all'avvio del menu
        self.stockfish_analyzer = None
        self.stockfish_loading_thread = None
        self.stockfish_loaded = threading.Event()
        self.is_loading_stockfish = False

        self.is_paused = False
        self.player_color = None
        self.pvc_ai_level = DEFAULT_AI_LEVEL
        self.ai_white_level = DEFAULT_AI_LEVEL
        self.ai_black_level = DEFAULT_AI_LEVEL
        self.display_board = chess.Board()
        self.viewing_history = False
        self.game_over_state = False
        self.premove = None

        self.ai_move_job_id = None
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.create_main_menu()

    def on_closing(self):
        if self.ai_move_job_id:
            self.master.after_cancel(self.ai_move_job_id)
            self.ai_move_job_id = None
        self._stop_eval_thread()
        self.master.destroy()

    def create_main_menu(self):
        self._stop_eval_thread()
        for widget in self.main_container.winfo_children():
            widget.destroy()
        self.master.geometry(MENU_WINDOW_GEOMETRY)
        
        # Converte i livelli in una lista di stringhe per i Combobox
        ai_level_choices = [str(level) for level in AI_LEVELS.keys()]
        
        menu_frame = ttk.Frame(self.main_container)
        menu_frame.pack(expand=True, fill=X, padx=30, pady=20)
        
        title_label = ttk.Label(menu_frame, text="Chess", font=("Helvetica", 24, "bold"))
        title_label.pack(pady=(0, 20))
        
        pvp_frame = ttk.Labelframe(menu_frame, text="Giocatore vs Giocatore", padding=15)
        pvp_frame.pack(fill=X, pady=5)
        ttk.Button(pvp_frame, text="Avvia Partita", style="success.TButton", command=lambda: self.start_game('pvp')).pack(fill=X, ipady=8)

        ai_state = tk.NORMAL if self.logic.stockfish_player else tk.DISABLED

        pvc_frame = ttk.Labelframe(menu_frame, text="Giocatore vs Computer", padding=15)
        pvc_frame.pack(fill=X, pady=5)
        
        pvc_diff_frame = ttk.Frame(pvc_frame)
        pvc_diff_frame.pack(fill=X, pady=(0, 10))
        ttk.Label(pvc_diff_frame, text="Difficoltà AI:").pack(side=LEFT, padx=(0, 10))
        
        self.pvc_difficulty_selector = ttk.Combobox(pvc_diff_frame, values=ai_level_choices, state="readonly")
        self.pvc_difficulty_selector.set(str(DEFAULT_AI_LEVEL))
        self.pvc_difficulty_selector.pack(side=LEFT, expand=True, fill=X)
        
        pvc_color_frame = ttk.Frame(pvc_frame)
        pvc_color_frame.pack(fill=X, pady=(0, 15))
        ttk.Label(pvc_color_frame, text="Gioca come:").pack(side=LEFT, padx=(0, 10))
        self.pvc_player_color = tk.StringVar(value=DEFAULT_PLAYER_COLOR)
        ttk.Radiobutton(pvc_color_frame, text="Bianco", variable=self.pvc_player_color, value="white").pack(side=LEFT, padx=5)
        ttk.Radiobutton(pvc_color_frame, text="Nero", variable=self.pvc_player_color, value="black").pack(side=LEFT, padx=5)
        ttk.Button(pvc_frame, text="Avvia Partita", style="info.TButton", command=lambda: self.start_game('pvc'), state=ai_state).pack(fill=X, ipady=8)

        cvc_frame = ttk.Labelframe(menu_frame, text="Computer vs Computer", padding=15)
        cvc_frame.pack(fill=X, pady=5)
        
        cvc_white_frame = ttk.Frame(cvc_frame)
        cvc_white_frame.pack(fill=X, pady=2)
        ttk.Label(cvc_white_frame, text="Difficoltà Bianco:").pack(side=LEFT, padx=(0, 10))
        
        self.cvc_white_difficulty_selector = ttk.Combobox(cvc_white_frame, values=ai_level_choices, state="readonly")
        self.cvc_white_difficulty_selector.set(str(DEFAULT_AI_LEVEL))
        self.cvc_white_difficulty_selector.pack(side=LEFT, expand=True, fill=X)
        
        cvc_black_frame = ttk.Frame(cvc_frame)
        cvc_black_frame.pack(fill=X, pady=(5,15))
        ttk.Label(cvc_black_frame, text="Difficoltà Nero:").pack(side=LEFT, padx=(0, 10))
        
        self.cvc_black_difficulty_selector = ttk.Combobox(cvc_black_frame, values=ai_level_choices, state="readonly")
        self.cvc_black_difficulty_selector.set(str(DEFAULT_AI_LEVEL))
        self.cvc_black_difficulty_selector.pack(side=LEFT, expand=True, fill=X)
        ttk.Button(cvc_frame, text="Avvia Simulazione", style="warning.TButton", command=lambda: self.start_game('cvc'), state=ai_state).pack(fill=X, ipady=8)

        if not self.logic.stockfish_player:
            ttk.Label(menu_frame, text="Stockfish non trovato.\nFunzionalità AI disabilitate.", bootstyle="danger", justify=CENTER).pack(pady=20)

    def _load_stockfish_background(self):
        """Carica Stockfish in background"""
        try:
            self.stockfish_analyzer = StockfishManager.get_instance(
                depth=self.logic.analysis_depth,
                threads=STOCKFISH_ANALYZER_THREADS,
                key="analyzer"
            )
        except Exception as e:
            print(f"Errore nel caricamento di Stockfish: {e}")
            self.stockfish_analyzer = None
        finally:
            self.stockfish_loaded.set()
    
    def _wait_for_stockfish_loaded(self):
        """Attende il caricamento di Stockfish e poi avvia il thread di valutazione"""
        if self.stockfish_loaded.wait(timeout=30):  # Attende max 30 secondi
            if self.stockfish_analyzer:
                # Stockfish caricato, usa after() per aggiornare GUI nel thread principale
                def enable_stockfish_ui():
                    if safe_widget_exists(self, 'eval_bar_checkbutton'):
                        self.eval_bar_checkbutton.config(state=tk.NORMAL)
                    if safe_widget_exists(self, 'best_move_checkbutton'):
                        self.best_move_checkbutton.config(state=tk.NORMAL)
                    
                    self._start_eval_thread()
                    self._process_eval_queue()
                    self.new_eval_request.set()
                    self.is_loading_stockfish = False
                    self.update_display()
                
                self.master.after(0, enable_stockfish_ui)
        else:
            # Timeout - Stockfish non caricato
            def reset_loading():
                if safe_widget_exists(self, 'status_label'):
                    self.is_loading_stockfish = False
                    self.update_display()
            
            self.master.after(0, reset_loading)

    def start_game(self, mode):
        self.game_mode = mode
        self.is_paused = False
        self.game_over_state = False
        
        if self.game_mode == 'pvc':
            self.pvc_ai_level = int(self.pvc_difficulty_selector.get())
            self.player_color = chess.WHITE if self.pvc_player_color.get() == "white" else chess.BLACK
        elif self.game_mode == 'cvc':
            self.ai_white_level = int(self.cvc_white_difficulty_selector.get())
            self.ai_black_level = int(self.cvc_black_difficulty_selector.get())
        
        self.create_game_ui()
        
        # Carica Stockfish in background se non già in corso
        if not self.is_loading_stockfish and self.stockfish_analyzer is None:
            self.is_loading_stockfish = True
            self.stockfish_loaded.clear()
            self.stockfish_loading_thread = threading.Thread(
                target=self._load_stockfish_background,
                daemon=True
            )
            self.stockfish_loading_thread.start()
            
            # Avvia un thread per attendere il caricamento e poi inizializzare il motore di analisi
            stockfish_waiter_thread = threading.Thread(
                target=self._wait_for_stockfish_loaded,
                daemon=True
            )
            stockfish_waiter_thread.start()
        elif self.stockfish_analyzer:
            # Stockfish già caricato, avvia subito il thread di valutazione
            self._start_eval_thread()
            self._process_eval_queue()
            self.new_eval_request.set()
            
        if self.game_mode == 'cvc' or (self.game_mode == 'pvc' and self.player_color == chess.BLACK):
            self.trigger_ai_move()

    def create_game_ui(self):
        for widget in self.main_container.winfo_children():
            widget.destroy()
        self.master.geometry(GAME_WINDOW_GEOMETRY)
        
        game_frame = ttk.Frame(self.main_container)
        game_frame.pack(fill=BOTH, expand=True)
        
        board_container = ttk.Frame(game_frame)
        board_container.pack(side=LEFT, fill=Y, padx=10, pady=10)
        
        # MODIFICATO: Rimossa la chiamata .pack() da qui, perché è già dentro la classe ChessBoard
        self.board_widget = ChessBoard(board_container, self)
        
        self.eval_bar = EvalBar(board_container)
        
        side_panel = ttk.Frame(game_frame)
        side_panel.pack(side=LEFT, fill=BOTH, expand=True, padx=10, pady=10)
        
        side_panel.columnconfigure(0, weight=1)
        side_panel.rowconfigure(3, weight=1)
        side_panel.rowconfigure(4, weight=1)

        self.status_label = ttk.Label(side_panel, text="", font=("Helvetica", 14), justify=LEFT)
        self.status_label.grid(row=0, column=0, sticky="ew", pady=5)
        
        self.engine_info_label = ttk.Label(side_panel, text="", font=("Helvetica", 10, "italic"), justify=LEFT)
        
        self.analysis_frame = ttk.Labelframe(side_panel, text="Analisi Motore", padding=10)
        self.analysis_text = Text(self.analysis_frame, height=3, wrap=tk.WORD, font=("Courier", 10), state=tk.DISABLED)
        self.analysis_text.pack(fill=BOTH, expand=True)

        history_frame = ttk.Labelframe(side_panel, text="Cronologia Mosse", padding=10)
        history_frame.grid(row=3, column=0, sticky="nsew", pady=5)
        history_frame.columnconfigure(0, weight=1)
        history_frame.rowconfigure(0, weight=1)
        
        h_scroll = ttk.Scrollbar(history_frame)
        h_scroll.grid(row=0, column=1, sticky="ns")
        
        self.history_text = Text(history_frame, height=5, wrap=tk.WORD, yscrollcommand=h_scroll.set, font=("Courier", 11))
        self.history_text.grid(row=0, column=0, sticky="nsew")
        self.history_text.config(state=tk.DISABLED)
        h_scroll.config(command=self.history_text.yview)

        nav_frame = ttk.Frame(side_panel)
        nav_frame.grid(row=5, column=0, sticky="ew", pady=(0, 5))
        nav_frame.columnconfigure((0,1,2,3), weight=1)
        
        self.nav_start_btn = ttk.Button(nav_frame, text="\u00AB", command=self.nav_to_start)
        self.nav_start_btn.grid(row=0, column=0, sticky="ew")
        
        self.nav_prev_btn = ttk.Button(nav_frame, text="\u2039", command=self.nav_prev_move)
        self.nav_prev_btn.grid(row=0, column=1, sticky="ew")
        
        self.nav_next_btn = ttk.Button(nav_frame, text="\u203A", command=self.nav_next_move)
        self.nav_next_btn.grid(row=0, column=2, sticky="ew")
        
        self.nav_end_btn = ttk.Button(nav_frame, text="\u00BB", command=self.nav_to_end)
        self.nav_end_btn.grid(row=0, column=3, sticky="ew")
        
        self.options_frame = ttk.Frame(side_panel)
        self.options_frame.grid(row=6, column=0, sticky="ew", pady=5)
        eval_bar_state = tk.NORMAL if self.stockfish_analyzer else tk.DISABLED
        self.eval_bar_checkbutton = ttk.Checkbutton(self.options_frame, text="Mostra Eval Bar", variable=self.eval_bar_var, command=self._toggle_eval_bar, state=eval_bar_state)
        self.eval_bar_checkbutton.pack(anchor='w')
        self.best_move_checkbutton = ttk.Checkbutton(self.options_frame, text="Mostra Mossa Migliore", variable=self.show_best_move_var, command=self._on_toggle_best_move, state=eval_bar_state)
        self.best_move_checkbutton.pack(anchor='w')
        ttk.Checkbutton(self.options_frame, text="Ruota Scacchiera Automaticamente", variable=self.auto_flip_var, command=self.toggle_auto_flip).pack(anchor='w')
        
        btn_panel = ttk.Frame(side_panel)
        btn_panel.grid(row=7, column=0, sticky="ew", pady=(10,0))
        
        self.game_review_button = ttk.Button(btn_panel, text="Game Review", command=self.start_game_review, style="success.TButton")
        
        if self.game_mode == 'cvc':
            self.pause_button = ttk.Button(btn_panel, text="Pausa", command=self.toggle_pause, style="info.TButton")
            self.pause_button.pack(fill=X, pady=2)
            self.board_widget.is_enabled = False

        undo_redo_state = tk.DISABLED if self.game_mode == 'cvc' else tk.NORMAL
        
        self.undo_button = ttk.Button(btn_panel, text="Annulla Mossa (Ctrl+Z)", command=self.undo_last_move, state=undo_redo_state)
        self.undo_button.pack(fill=X, pady=2)
        
        self.redo_button = ttk.Button(btn_panel, text="Ripeti Mossa (Ctrl+Y)", command=self.redo_last_move, state=undo_redo_state)
        self.redo_button.pack(fill=X, pady=2)
        
        ttk.Button(btn_panel, text="Ruota Scacchiera (Ctrl+R)", command=self.toggle_flip_board).pack(fill=X, pady=2)
        ttk.Button(btn_panel, text="Copia PGN", command=self.copy_pgn).pack(fill=X, pady=2)
        ttk.Button(btn_panel, text="Torna al Menu", command=self.reset_game, style='danger.TButton').pack(fill=X, pady=(10, 2))
        
        self.setup_shortcuts()
        self.update_display()

    def _on_toggle_best_move(self):
        if self.show_best_move_var.get():
            self.engine_info_label.grid(row=1, column=0, sticky="ew", pady=(0, 10))
            self.analysis_frame.grid(row=2, column=0, sticky="nsew", pady=5)
            if self.stockfish_analyzer:
                self.force_reanalyze = True
                self.new_eval_request.set()
        else:
            self.engine_info_label.grid_remove()
            self.analysis_frame.grid_remove()
            self.board_widget.best_move_arrow = None
        self.update_display()

    def nav_to_start(self):
        """Naviga all'inizio della partita senza animazione"""
        if hasattr(self, 'board_widget') and self.board_widget:
            self.board_widget.cancel_animation()
        
        self.display_board.reset()
        self.viewing_history = True
        if self.stockfish_analyzer and self.eval_bar_var.get():
            self.new_eval_request.set()
        self.update_display()

    def nav_prev_move(self):
        """Naviga alla mossa precedente senza animazione"""
        if self.display_board.move_stack:
            if hasattr(self, 'board_widget') and self.board_widget:
                self.board_widget.cancel_animation()
            
            self.display_board.pop()
            self.viewing_history = True
            if self.stockfish_analyzer and self.eval_bar_var.get():
                self.new_eval_request.set()
            self.update_display()

    def nav_next_move(self):
        """Naviga alla mossa successiva senza animazione"""
        full_move_list = list(self.logic.board.move_stack)
        current_view_len = len(self.display_board.move_stack)
        if current_view_len < len(full_move_list):
            if hasattr(self, 'board_widget') and self.board_widget:
                self.board_widget.cancel_animation()
            
            next_move = full_move_list[current_view_len]
            self.display_board.push(next_move)
            self.viewing_history = (len(self.display_board.move_stack) < len(full_move_list))
            if self.stockfish_analyzer and self.eval_bar_var.get():
                self.new_eval_request.set()
            self.update_display()

    def nav_to_end(self):
        """Naviga alla fine della partita senza animazione"""
        if hasattr(self, 'board_widget') and self.board_widget:
            self.board_widget.cancel_animation()
        
        self.display_board = self.logic.board.copy()
        self.viewing_history = False
        if self.stockfish_analyzer and self.eval_bar_var.get():
            self.new_eval_request.set()
        self.update_display()

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        self.pause_button.config(text="Riprendi" if self.is_paused else "Pausa")
        if not self.is_paused and not self.logic.board.is_game_over():
            self.trigger_ai_move()

    def update_analysis_box(self, top_moves):
        """
        Aggiorna la casella di analisi con le migliori mosse suggerite.
        
        Args:
            top_moves: Lista di dizionari con le mosse e le loro valutazioni
        """
        if safe_widget_exists(self, 'analysis_text'):
            self.analysis_text.config(state=tk.NORMAL)
            self.analysis_text.delete('1.0', tk.END)
            temp_board = self.logic.board.copy()
            for move_info in top_moves:
                eval_str = ""
                if move_info['Centipawn'] is not None:
                    score = move_info['Centipawn'] / EVAL_CENTIPAWN_DIVISOR
                    eval_str = f"{score:+.2f}"
                elif move_info['Mate'] is not None:
                    eval_str = f"M{move_info['Mate']}"
                try:
                    san_move = temp_board.san(chess.Move.from_uci(move_info['Move']))
                    self.analysis_text.insert(tk.END, f"({eval_str}) {san_move}\n")
                except Exception:
                    self.analysis_text.insert(tk.END, f"({eval_str}) {move_info['Move']}\n")
            self.analysis_text.config(state=tk.DISABLED)

    def _eval_loop(self):
        last_analyzed_fen = None
        while self.eval_thread_running:
            # Aspetta il segnale con timeout per controllare periodicamente cambiamenti di posizione
            self.new_eval_request.wait(timeout=0.5)
            if not self.eval_thread_running:
                break
            
            # Se viene richiesta una re-analisi forzata, resetta last_analyzed_fen
            if self.force_reanalyze:
                last_analyzed_fen = None
                self.force_reanalyze = False
            
            try:
                # Usa display_board se stiamo visualizzando la cronologia, altrimenti usa logic.board
                board_to_analyze = self.display_board if self.viewing_history else self.logic.board
                fen = board_to_analyze.fen()
                
                # Analizza solo se la posizione è cambiata o se è stata esplicitamente richiesta
                if fen != last_analyzed_fen:
                    self.stockfish_analyzer.set_fen_position(fen)
                    top_moves = self.stockfish_analyzer.get_top_moves(TOP_MOVES_COUNT)
                    self.eval_queue.put((top_moves, self.logic.analysis_depth))
                    last_analyzed_fen = fen
            except Exception as e:
                if self.eval_thread_running:
                    print(f"Errore nel thread di valutazione: {e}")
                break
            
            self.new_eval_request.clear()

    def _process_eval_queue(self):
        try:
            while not self.eval_queue.empty():
                top_moves, depth = self.eval_queue.get_nowait()
                if safe_widget_exists(self, 'board_widget') and top_moves:
                    best_move_info = top_moves[0]
                    eval_dict = {
                        'type': 'cp' if best_move_info['Centipawn'] is not None else 'mate',
                        'value': best_move_info['Centipawn'] if best_move_info['Centipawn'] is not None else best_move_info['Mate']
                    }
                    
                    if safe_widget_exists(self, 'eval_bar'):
                        self.eval_bar.update_eval(eval_dict)
                        
                    if self.show_best_move_var.get():
                        if safe_widget_exists(self, 'engine_info_label'):
                            self.engine_info_label.config(text=f"Profondità Motore: {depth}")
                        self.board_widget.best_move_arrow = chess.Move.from_uci(best_move_info['Move'])
                        self.update_analysis_box(top_moves)
                    else:
                        self.board_widget.best_move_arrow = None
                    self.update_display()
        except queue.Empty:
            pass
        finally:
            if self.eval_thread_running:
                self.master.after(EVAL_QUEUE_PROCESS_DELAY, self._process_eval_queue)

    def finalize_move(self, move, skip_animation=False):
        self.board_widget.custom_arrows.clear()
        self.board_widget.custom_highlights.clear()
        
        # Callback da eseguire dopo l'animazione
        def after_animation():
            if self.logic.make_move(move):
                self.nav_to_end()
                self.update_board_orientation()
                
                if self.logic.board.is_game_over():
                    self.game_over_state = True
                    self.board_widget.is_enabled = True
                else:
                    if self.stockfish_analyzer:
                        self.new_eval_request.set()
                    
                    # Gestisce premove e turno AI
                    if self.premove and self.premove in self.logic.board.legal_moves:
                        self.execute_move(self.premove)
                        self.premove = None
                    elif is_ai_turn(self.game_mode, self.logic.board.turn, self.player_color):
                        self.trigger_ai_move()
                    else:
                        # È il turno del giocatore, abilita il board
                        self.board_widget.is_enabled = True
                self.update_display()
        
        # Avvia l'animazione o esegui direttamente
        if skip_animation:
            after_animation()
        else:
            self.board_widget.animate_move(move, after_animation)

    def update_move_history(self):
        if safe_widget_exists(self, 'history_text'):
            self.history_text.config(state=tk.NORMAL)
            self.history_text.delete('1.0', tk.END)
            game = chess.pgn.Game.from_board(self.logic.board)
            self.history_text.insert('1.0', str(game.mainline_moves()))
            self.history_text.see(tk.END)
            self.history_text.config(state=tk.DISABLED)
    
    def update_button_states(self):
        is_game_running = not self.game_over_state
        
        # Gestione pulsante Game Review
        if safe_widget_exists(self, 'game_review_button'):
            if is_game_running:
                self.game_review_button.pack_forget()
            else:
                self.game_review_button.pack(fill=X, pady=2, before=self.undo_button)

        # Gestione pulsante Pausa
        if safe_widget_exists(self, 'pause_button'):
            self.pause_button.config(state=tk.NORMAL if is_game_running else tk.DISABLED)
            
        # Gestione pulsanti Undo/Redo
        if safe_widget_exists(self, 'undo_button') and self.game_mode != 'cvc':
            can_undo = self.logic.board.move_stack and not self.viewing_history and is_game_running
            self.undo_button.config(state=tk.NORMAL if can_undo else tk.DISABLED)
            can_redo = self.logic.undone_moves and not self.viewing_history and is_game_running
            self.redo_button.config(state=tk.NORMAL if can_redo else tk.DISABLED)

        # Gestione pulsanti di navigazione
        if safe_widget_exists(self, 'nav_start_btn'):
            can_go_back = len(self.display_board.move_stack) > 0
            self.nav_start_btn.config(state=tk.NORMAL if can_go_back else tk.DISABLED)
            self.nav_prev_btn.config(state=tk.NORMAL if can_go_back else tk.DISABLED)
            can_go_forward = len(self.display_board.move_stack) < len(self.logic.board.move_stack)
            self.nav_next_btn.config(state=tk.NORMAL if can_go_forward else tk.DISABLED)
            self.nav_end_btn.config(state=tk.NORMAL if can_go_forward else tk.DISABLED)
            
    def reset_game(self):
        was_paused = self.is_paused
        if self.game_mode == 'cvc' and not was_paused:
            self.toggle_pause()
            
        if messagebox.askyesno("Conferma", "Tornare al menu principale? La partita corrente sarà persa."):
            if self.ai_move_job_id:
                self.master.after_cancel(self.ai_move_job_id)
                self.ai_move_job_id = None
            self.logic.reset()
            self.selected_square = None
            self.premove = None
            if hasattr(self, 'board_widget'):
                self.board_widget.hide_promotion_choices()
            self.is_board_flipped = False
            self.auto_flip_var.set(False)
            self.eval_bar_var.set(False)
            self.show_best_move_var.set(False)
            self.is_loading_stockfish = False  # Reset flag di caricamento
            self.create_main_menu()
        elif self.game_mode == 'cvc' and not was_paused:
            self.toggle_pause()

    def _toggle_eval_bar(self):
        if self.eval_bar_var.get():
            self.eval_bar.pack(side=LEFT, fill=Y, pady=10)
            self.new_eval_request.set()
        else:
            self.eval_bar.pack_forget()
            
    def _start_eval_thread(self):
        if not (self.eval_thread and self.eval_thread.is_alive()):
            self.eval_thread_running = True
            self.eval_thread = threading.Thread(target=self._eval_loop, daemon=True)
            self.eval_thread.start()
            
    def _stop_eval_thread(self):
        self.eval_thread_running = False
        if self.eval_thread:
            self.new_eval_request.set()
            self.eval_thread.join(timeout=0.2)
        self.eval_thread = None
        
    def setup_shortcuts(self):
        is_normal = lambda btn: btn.winfo_exists() and btn.cget('state') == 'normal'
        self.master.bind("<Control-z>", lambda e: is_normal(self.undo_button) and self.undo_last_move())
        self.master.bind("<Control-y>", lambda e: is_normal(self.redo_button) and self.redo_last_move())
        self.master.bind("<Control-r>", lambda e: self.toggle_flip_board())
        
    def toggle_auto_flip(self):
        self.update_board_orientation()
        self.deselect_and_update()
        
    def update_board_orientation(self):
        if self.auto_flip_var.get():
            if self.game_mode == 'pvc':
                self.is_board_flipped = (self.player_color == chess.BLACK)
            else:
                self.is_board_flipped = (self.logic.board.turn == chess.BLACK)
                
    def toggle_flip_board(self):
        self.auto_flip_var.set(False)
        self.is_board_flipped = not self.is_board_flipped
        self.deselect_and_update()
    def undo_last_move(self):
        """Annulla l'ultima mossa senza animazione"""
        self.game_over_state = False
        moves_to_undo = 2 if self.game_mode == 'pvc' and len(self.logic.board.move_stack) > 1 else 1
        
        if not self.logic.board.move_stack:
            return
        
        # Cancella eventuali animazioni in corso
        if hasattr(self, 'board_widget') and self.board_widget:
            self.board_widget.cancel_animation()
        
        # Annulla le mosse
        for _ in range(moves_to_undo): 
            self.logic.undo_move()
        
        self.nav_to_end()
        self.update_board_orientation()
        self.new_eval_request.set()
        
    def redo_last_move(self):
        """Ripristina l'ultima mossa annullata senza animazione"""
        moves_to_redo = 2 if self.game_mode == 'pvc' and len(self.logic.undone_moves) > 1 else 1
        
        if not self.logic.undone_moves:
            return
        
        # Cancella eventuali animazioni in corso
        if hasattr(self, 'board_widget') and self.board_widget:
            self.board_widget.cancel_animation()
        
        # Ripristina le mosse
        for _ in range(moves_to_redo): 
            self.logic.redo_move()
        
        self.nav_to_end()
        self.update_board_orientation()
        self.new_eval_request.set()
        
    def copy_pgn(self):
        game = chess.pgn.Game.from_board(self.logic.board)
        
        # Crea gli header usando la funzione helper
        headers = create_pgn_headers(
            self.game_mode,
            self.player_color,
            self.ai_white_level,
            self.ai_black_level,
            self.pvc_ai_level,
            self.logic.board.result()
        )
        
        # Applica gli header al gioco
        for key, value in headers.items():
            game.headers[key] = value
        
        try:
            pyperclip.copy(str(game))
            messagebox.showinfo("Successo", "PGN copiato negli appunti.")
        except pyperclip.PyperclipException:
            messagebox.showerror("Errore Clipboard", "Impossibile accedere agli appunti.")
    
    def cancel_premove(self):
        self.premove = None
    
    def handle_press(self, square):
        if self.game_over_state:
            return
        if self.viewing_history:
            self.nav_to_end()
        if self.selected_square is None:
            self.board_widget.custom_arrows.clear()
            self.board_widget.custom_highlights.clear()
            self.update_display()
        if self.selected_square is not None:
            self.attempt_move(self.selected_square, square)
        else:
            piece = self.logic.get_piece_at(square)
            if piece and piece.color == self.logic.board.turn:
                self.selected_square = square
                self.update_display()
    
    def deselect_and_update(self):
        self.selected_square = None
        self.update_display()
    
    def attempt_move(self, from_sq, to_sq, skip_animation=False):
        is_ai_turn = (self.game_mode == 'pvc' and self.logic.board.turn != self.player_color)
        if is_ai_turn:
            potential_premove = chess.Move(from_sq, to_sq)
            if self.logic.needs_promotion(potential_premove):
                potential_premove.promotion = chess.QUEEN
            self.premove = potential_premove
            print(f"Premove registrato: {self.premove.uci()}")
            self.deselect_and_update()
            return

        move = self.find_move(from_sq, to_sq)
        if move:
            self.execute_move(move, skip_animation)
            self.deselect_and_update()
        elif self.logic.get_piece_at(to_sq) and self.logic.get_piece_at(to_sq).color == self.logic.board.turn:
            self.selected_square = to_sq
            self.update_display()
        else:
            self.deselect_and_update()

    def find_move(self, from_sq, to_sq):
        move = chess.Move(from_sq, to_sq)
        if self.logic.needs_promotion(move):
            if chess.Move(from_sq, to_sq, promotion=chess.QUEEN) in self.logic.board.legal_moves:
                return move
        elif move in self.logic.board.legal_moves:
            return move
        return None

    def execute_move(self, move, skip_animation=False):
        if self.logic.needs_promotion(move) and move.promotion is None:
            self.board_widget.show_promotion_choices(move)
        else:
            self.finalize_move(move, skip_animation)

    def trigger_ai_move(self):
        if self.game_mode == 'cvc' and self.is_paused:
            return
        self.board_widget.is_enabled = False
        delay = AI_MOVE_DELAY_CVC if self.game_mode == 'cvc' else AI_MOVE_DELAY_NORMAL
        self.ai_move_job_id = self.master.after(delay, self.make_ai_move)

    def make_ai_move(self):
        self.ai_move_job_id = None
        if not self.master.winfo_exists():
            return
        
        # Determina quale livello usare in base alla modalità di gioco e al turno
        level_to_use = get_ai_level_for_turn(
            self.game_mode, 
            self.logic.board.turn, 
            self.pvc_ai_level, 
            self.ai_white_level, 
            self.ai_black_level
        )
        
        # Passa il livello direttamente alla funzione che calcola la mossa
        ai_move = self.logic.get_ai_move(level_to_use)
        
        if ai_move:
            self.execute_move(ai_move)
        
        # Riabilita il board se è il turno del giocatore o se la partita è terminata
        if self.game_mode == 'pvc' or self.game_over_state:
            self.board_widget.is_enabled = True

    def complete_promotion(self, move, piece_type):
        move.promotion = piece_type
        self.board_widget.hide_promotion_choices()
        self.finalize_move(move)
    
    def update_display(self):
        board_to_show = self.display_board if self.viewing_history else self.logic.board
        
        # Aggiorna la scacchiera
        if safe_widget_exists(self, 'board_widget'):
            self.board_widget.draw(board_to_show)
        
        # Aggiorna lo status label
        if safe_widget_exists(self, 'status_label'):
            # Mostra indicatore di caricamento di Stockfish se in corso
            if self.is_loading_stockfish and not self.stockfish_loaded.is_set():
                status_text = "⏳ Caricamento motore di analisi..."
            elif not self.viewing_history:
                status_text = self.logic.get_game_status()
            else:
                status_text = f"Mossa {board_to_show.fullmove_number}: Visualizzazione Storico"
            self.status_label.config(text=status_text)
        
        self.update_button_states()
        self.update_move_history()
    
    def start_game_review(self):
        review_window = Toplevel(self.master)
        review_window.title("Game Review")
        review_window.geometry("1350x800")
        review_window.resizable(False, False)
        
        main_frame = ttk.Frame(review_window, padding=10)
        main_frame.pack(fill=BOTH, expand=True)
        
        self.review_status_frame = ttk.Frame(main_frame)
        self.review_status_frame.pack(pady=10, fill=X)
        
        status_label = ttk.Label(self.review_status_frame, text="Avvio dell'analisi...", font=("Helvetica", 12))
        status_label.pack()
        
        progress_bar = ttk.Progressbar(self.review_status_frame, mode='determinate', length=400)
        progress_bar.pack(pady=10)
        
        self.review_content_frame = ttk.Frame(main_frame)
        threading.Thread(target=self._run_analysis_thread, daemon=True).start()
        self.master.after(100, self._process_review_queue, review_window, progress_bar, status_label)

    def _convert_eval_to_cp(self, evaluation):
        """
        Converte una valutazione in centipawns.
        Wrapper per la funzione centralizzata in stockfish_manager.
        
        Args:
            evaluation: Dizionario con 'type' e 'value'
            
        Returns:
            Valore in centipawns (int)
        """
        return eval_to_centipawns(evaluation)



    def _run_analysis_thread(self):
        try:
            analyzer = StockfishManager.get_instance(key="review_analyzer")
            analyzer.set_depth(14)
            # Crea un'istanza del nuovo classificatore avanzato
            classifier = AdvancedMoveClassifier(analyzer)
        except Exception as e:
            self.review_queue.put(('error', f"Impossibile avviare il motore di analisi: {e}"))
            return
            
        board = chess.Board()
        moves = list(self.logic.board.move_stack)
        results = []
        white_accuracies, black_accuracies = [], []
        win_chances = []  # Per il calcolo dell'accuratezza pesata per volatilità
        prev_eval_cp = 20

        # Aggiungi la probabilità di vittoria iniziale
        from src.analysis.accuracy_calculator import winning_chances_percent
        win_chances.append(winning_chances_percent(prev_eval_cp))

        for i, move in enumerate(moves):
            self.review_queue.put(('progress', i + 1, len(moves)))
            turn = board.turn
            
            # --- LOGICA DI ANALISI MIGLIORATA ---
            
            # 1. Ottieni le migliori mosse PRIMA di muovere
            analyzer.set_fen_position(board.fen())
            top_moves = analyzer.get_top_moves(3)  # Prendiamo 3 mosse per analisi più approfondita
            if not top_moves:
                board.push(move)
                continue

            # 2. Classifica la mossa usando il sistema avanzato
            classification_raw = classifier.classify_move(board, move, top_moves)
            # Converte la chiave dalla mappatura del classificatore
            classification_key = classifier.classification_map.get(classification_raw, classification_raw.lower())
            
            # 3. Calcola l'accuratezza usando le nuove funzioni
            win_chance_before_white = winning_chances_percent(prev_eval_cp)
            
            san_move = board.san(move)
            board.push(move)
            
            current_eval_info = {}
            current_eval_cp = 0
            if board.is_checkmate():
                current_eval_cp = WINNING_CHANCES_MATE_THRESHOLD if turn == chess.WHITE else -WINNING_CHANCES_MATE_THRESHOLD
                current_eval_info = {'type': 'mate', 'value': 1 if turn == chess.WHITE else -1}
            else:
                analyzer.set_fen_position(board.fen())
                current_eval_info = analyzer.get_evaluation()
                current_eval_cp = self._convert_eval_to_cp(current_eval_info)

            win_chance_after_white = winning_chances_percent(current_eval_cp)
            win_chances.append(win_chance_after_white)
            
            win_chance_before_player = win_chance_before_white if turn == chess.WHITE else 100 - win_chance_before_white
            win_chance_after_player = win_chance_after_white if turn == chess.WHITE else 100 - win_chance_after_white

            accuracy = move_accuracy_percent(win_chance_before_player, win_chance_after_player)
            (white_accuracies if turn == chess.WHITE else black_accuracies).append(accuracy)

            results.append({
                'move': move, 'san': san_move, 
                'classification': EVAL_CLASSIFICATIONS[classification_key],
                'classification_key': classification_key,  # Aggiungiamo la chiave per le immagini
                'color': EVAL_COLORS[classification_key],
                'evaluation': current_eval_info
            })
            prev_eval_cp = current_eval_cp
        
        # Calcola l'accuratezza finale usando il nuovo sistema avanzato
        white_final_accuracy = calculate_player_accuracy(white_accuracies, win_chances, True)
        black_final_accuracy = calculate_player_accuracy(black_accuracies, win_chances, False)
        
        self.review_queue.put(('done', results, white_final_accuracy, black_final_accuracy))

    def _process_review_queue(self, review_window, progress_bar, status_label):
        """
        Processa la coda dei risultati dell'analisi di game review.
        
        Args:
            review_window: Finestra del game review
            progress_bar: Barra di progresso
            status_label: Etichetta di stato
        """
        try:
            message = self.review_queue.get_nowait()
            msg_type, *data = message

            if msg_type == 'progress':
                progress_bar['value'] = (data[0] / data[1]) * 100
                status_label.config(text=f"Analizzando mossa {data[0]} di {data[1]}...")
                review_window.after(100, self._process_review_queue, review_window, progress_bar, status_label)

            elif msg_type == 'done':
                self.review_status_frame.pack_forget()
                self.review_content_frame.pack(fill=BOTH, expand=True)
                
                self.review_data, w_acc, b_acc = data
                
                # --- LAYOUT RIORGANIZZATO ---

                # Pannello SINISTRO: conterrà solo la scacchiera e la barra di valutazione
                left_panel = ttk.Frame(self.review_content_frame)
                left_panel.pack(side=LEFT, fill=Y, padx=(0, 10), pady=10)
                
                board_frame = ttk.Frame(left_panel)
                board_frame.pack(side=TOP)
                
                self.review_board_widget = ChessBoard(board_frame, self)
                self.review_eval_bar = EvalBar(board_frame)
                self.review_eval_bar.pack(side=LEFT, fill=Y, pady=10)
                self.review_board_widget.is_enabled = False

                # Pannello DESTRO: conterrà tutto il resto (precisione, lista mosse, navigazione)
                right_panel = ttk.Frame(self.review_content_frame)
                right_panel.pack(side=LEFT, fill=BOTH, expand=True, pady=10)

                # 1. Etichette di precisione in alto nel pannello destro
                acc_frame = ttk.Frame(right_panel)
                acc_frame.pack(fill=X, side=TOP, pady=5, anchor='n')
                ttk.Label(acc_frame, text=f"Precisione Bianco: {w_acc}%", font=("Helvetica", 11, "bold")).pack(side=LEFT, expand=True)
                ttk.Label(acc_frame, text=f"Precisione Nero: {b_acc}%", font=("Helvetica", 11, "bold")).pack(side=RIGHT, expand=True)
                
                # 2. Contenitore per i controlli di navigazione, in basso nel pannello destro
                nav_container = ttk.Frame(right_panel)
                nav_container.pack(fill=X, side=BOTTOM, pady=(10,0), anchor='s')

                self.review_move_slider = ttk.Scale(nav_container, from_=0, to=len(self.review_data) - 1, orient=HORIZONTAL, command=self._navigate_review_move)
                self.review_move_slider.pack(fill=X, ipady=5)

                btn_frame = ttk.Frame(nav_container)
                btn_frame.pack(fill=X, pady=(5,0))
                btn_frame.columnconfigure((0,1,2,3), weight=1)
                
                ttk.Button(btn_frame, text="\u00AB", command=lambda: self.review_move_slider.set(0)).grid(row=0, column=0, sticky="ew")
                ttk.Button(btn_frame, text="\u2039", command=lambda: self.review_move_slider.set(max(0, int(self.review_move_slider.get())-1))).grid(row=0, column=1, sticky="ew")
                ttk.Button(btn_frame, text="\u203A", command=lambda: self.review_move_slider.set(min(len(self.review_data)-1, int(self.review_move_slider.get())+1))).grid(row=0, column=2, sticky="ew")
                ttk.Button(btn_frame, text="\u00BB", command=lambda: self.review_move_slider.set(len(self.review_data)-1)).grid(row=0, column=3, sticky="ew")

                # 3. Elenco mosse al centro, si espande per riempire lo spazio rimanente
                tree_frame = ttk.Labelframe(right_panel, text="Mosse Partita")
                tree_frame.pack(fill=BOTH, expand=True, side=TOP, pady=5)
                
                tree = ttk.Treeview(tree_frame, columns=('num', 'w', 'b'), show='headings')
                tree.heading('num', text='#')
                tree.column('num', width=40, anchor='center')
                tree.heading('w', text='Bianco')
                tree.column('w', width=160)
                tree.heading('b', text='Nero')
                tree.column('b', width=160)

                for i in range(0, len(self.review_data), 2):
                    w_data = self.review_data[i]
                    b_data = self.review_data[i+1] if i + 1 < len(self.review_data) else None
                    tree.insert('', tk.END, values=(i//2+1, f"{w_data['san']} ({w_data['classification']})", f"{b_data['san']} ({b_data['classification']})" if b_data else ""))

                scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
                tree.configure(yscrollcommand=scroll.set)
                scroll.pack(side=RIGHT, fill=Y)
                tree.pack(side=LEFT, fill=BOTH, expand=True)
                
                # Inizializza la visualizzazione all'ultima mossa
                self.review_move_slider.set(len(self.review_data)-1)
                self._navigate_review_move(len(self.review_data)-1)

            elif msg_type == 'error':
                messagebox.showerror("Errore Analisi", data[0], parent=review_window)
                review_window.destroy()
        
        except queue.Empty:
            review_window.after(100, self._process_review_queue, review_window, progress_bar, status_label)
    
    def _navigate_review_move(self, value):
        if not hasattr(self, 'review_data') or not self.review_data:
            return
        move_index = int(float(value))
        
        # Ricostruisci la scacchiera fino alla posizione attuale
        moves = [data['move'] for data in self.review_data]
        board_after_move = build_board_from_moves(moves, move_index)
        current_move_data = self.review_data[move_index]
        
        # Disegna la scacchiera nello stato attuale
        self.review_board_widget.draw(board_after_move)
        
        # Aggiungi la freccia della mossa migliore
        best_move_uci = current_move_data.get('best_move_uci')
        if best_move_uci:
            best_move = chess.Move.from_uci(best_move_uci)
            self.review_board_widget.draw_best_move_arrow(best_move)
            
        # Aggiungi l'icona di classificazione sulla mossa
        self.review_board_widget.draw_evaluation_dot(
            current_move_data['move'].to_square,
            current_move_data['classification_key']
        )
        
        # Aggiorna la barra di valutazione
        self.review_eval_bar.update_eval(current_move_data['evaluation'])

if __name__ == "__main__":
    root = ttk.Window(themename=THEME_APP)
    app = ChessApp(root)
    root.mainloop()