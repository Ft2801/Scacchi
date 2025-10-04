# ui_components.py
"""
Componenti dell'interfaccia utente per l'applicazione di scacchi.

Questo modulo contiene i widget personalizzati per la visualizzazione della scacchiera,
la barra di valutazione, e tutti gli elementi grafici interattivi del gioco.
"""

import tkinter as tk
from tkinter import messagebox
from ttkbootstrap import ttk
import time
import chess
import os
import math
from PIL import Image, ImageTk

from src.config import (
    BOARD_SIZE, SQUARE_SIZE, PIECES_PATH, BOARD_COLORS, 
    CLASSIFICATIONS_PATH, CLASSIFICATION_IMAGES,
    EVAL_BAR_WIDTH, EVAL_BAR_ANIMATION_SPEED, EVAL_BAR_ANIMATION_FPS,
    EVAL_BAR_ANIMATION_DELAY, EVAL_BAR_CAP_VALUE, EVAL_BAR_THRESHOLD,
    EVAL_CENTIPAWN_DIVISOR, COLOR_EVAL_BAR_BG, COLOR_EVAL_BAR_TOP_BG,
    COLOR_EVAL_BAR_TOP_FG, COLOR_EVAL_BAR_BOTTOM_BG, COLOR_EVAL_BAR_BOTTOM_FG,
    COLOR_LEGAL_MOVE, COLOR_LAST_MOVE, COLOR_CHECK, COLOR_ARROW_DEFAULT,
    COLOR_HIGHLIGHT_DEFAULT, LEGAL_MOVE_RADIUS_EMPTY, LEGAL_MOVE_RADIUS_CAPTURE,
    LEGAL_MOVE_RING_WIDTH, ARROW_WIDTH_RATIO, ANIMATION_DURATION_MS,
    ANIMATION_DELAY_MS, TIME_TO_MILLISECONDS, CLASSIFICATION_ICON_SIZE_RATIO,
    PROMOTION_OVERLAY_COLOR, PROMOTION_OVERLAY_STIPPLE, COORDINATE_FONT_SIZE_DIVISOR,
    COORDINATE_PADDING, BOARD_RANKS, BOARD_FILES
)

class EvalBar(ttk.Frame):
    """
    Barra di valutazione verticale che mostra il vantaggio di Bianco/Nero.
    
    La barra è divisa in due sezioni (bianca e nera) con animazione fluida
    quando cambia la valutazione della posizione.
    """
    
    def __init__(self, parent):
        """
        Inizializza la barra di valutazione.
        
        Args:
            parent: Widget genitore Tkinter
        """
        super().__init__(parent, width=EVAL_BAR_WIDTH) 
        self.pack_propagate(False)
        self.top_label = ttk.Label(self, text="", font=("Helvetica", 9, "bold"), 
                                   background=COLOR_EVAL_BAR_TOP_BG, 
                                   foreground=COLOR_EVAL_BAR_TOP_FG, 
                                   padding=(0, 2), anchor="center")
        self.top_label.pack(side=tk.TOP, fill=tk.X)
        self.bar_canvas = tk.Canvas(self, bg=COLOR_EVAL_BAR_BG, highlightthickness=0)
        self.bar_canvas.pack(fill=tk.BOTH, expand=True)
        self.bottom_label = ttk.Label(self, text="", font=("Helvetica", 9, "bold"), 
                                      background=COLOR_EVAL_BAR_BOTTOM_BG, 
                                      foreground=COLOR_EVAL_BAR_BOTTOM_FG, 
                                      padding=(0, 2), anchor="center")
        self.bottom_label.pack(side=tk.BOTTOM, fill=tk.X)
        self.white_bar = self.bar_canvas.create_rectangle(0, 0, 0, 0, fill="white", outline="")
        self.black_bar = self.bar_canvas.create_rectangle(0, 0, 0, 0, fill="black", outline="")
        self.current_percentage = 0.5
        self.target_percentage = 0.5
        self.animation_job = None
    
    def update_eval(self, eval_dict):
        """
        Aggiorna la barra con una nuova valutazione.
        
        Args:
            eval_dict: Dizionario con 'type' ('cp' o 'mate') e 'value'
        """
        self.target_percentage = self._eval_to_percentage(eval_dict)
        self._update_labels(eval_dict)
        if self.animation_job:
            self.after_cancel(self.animation_job)
        self._animate_bar()
    
    def _animate_bar(self):
        """
        Anima la transizione della barra verso il valore target.
        Usa interpolazione lineare per un movimento fluido.
        """
        canvas_height = self.bar_canvas.winfo_height()
        canvas_width = self.bar_canvas.winfo_width()
        if canvas_height <= 1:
            self.animation_job = self.after(ANIMATION_DELAY_MS, self._animate_bar)
            return
        
        # Interpolazione lineare verso il target
        self.current_percentage += (self.target_percentage - self.current_percentage) * EVAL_BAR_ANIMATION_SPEED
        white_pixel_height = canvas_height * self.current_percentage
        self.bar_canvas.coords(self.white_bar, 0, canvas_height - white_pixel_height, canvas_width, canvas_height)
        self.bar_canvas.coords(self.black_bar, 0, 0, canvas_width, canvas_height - white_pixel_height)
        
        # Continua l'animazione se non abbiamo raggiunto il target
        if abs(self.target_percentage - self.current_percentage) > EVAL_BAR_THRESHOLD:
            self.animation_job = self.after(EVAL_BAR_ANIMATION_DELAY, self._animate_bar)
        else:
            self.animation_job = None
        
    def _update_labels(self, eval_dict):
        """
        Aggiorna le etichette di testo con la valutazione corrente.
        
        Args:
            eval_dict: Dizionario con la valutazione da visualizzare
        """
        text_to_display = self._format_eval_text(eval_dict)
        if self.target_percentage >= 0.5:
            self.bottom_label.config(text=text_to_display)
            self.top_label.config(text="")
        else:
            self.top_label.config(text=text_to_display)
            self.bottom_label.config(text="")
        
    def _format_eval_text(self, eval_dict):
        """
        Formatta la valutazione in testo leggibile.
        
        Args:
            eval_dict: Dizionario con 'type' e 'value'
            
        Returns:
            Stringa formattata (es. "+1.5", "M3", "-0.8")
        """
        if eval_dict is None:
            return "0.0"
        
        eval_type = eval_dict.get("type")
        value = eval_dict.get("value")
        
        if eval_type == "mate":
            return f"M{abs(value)}" if value != 0 else "0.0"
        
        if eval_type == "cp":
            pawn_value = value / EVAL_CENTIPAWN_DIVISOR
            if pawn_value < 0:
                return f"{-pawn_value:.1f}"
            return f"{pawn_value:+.1f}"
        
        return "0.0"
        
    def _eval_to_percentage(self, eval_data):
        """
        Converte una valutazione in percentuale per la barra (0.0 = Nero vince, 1.0 = Bianco vince).
        
        Usa una funzione tanh per normalizzare i valori di centipawn in un range 0-1.
        
        Args:
            eval_data: Dizionario con 'type' e 'value'
            
        Returns:
            Percentuale tra 0.0 e 1.0
        """
        if eval_data is None:
            return 0.5
        
        eval_type = eval_data.get("type")
        value = eval_data.get("value")
        
        if eval_type == "mate":
            return 1.0 if value > 0 else 0.0
        
        # Limita il valore al range [-cap, +cap]
        value = max(-EVAL_BAR_CAP_VALUE, min(EVAL_BAR_CAP_VALUE, value))
        normalized_value = value / (EVAL_BAR_CAP_VALUE / 4)
        tanh_val = math.tanh(normalized_value)
        return (tanh_val + 1) / 2

class ChessBoard(tk.Canvas):
    """
    Widget Canvas personalizzato per la visualizzazione e interazione con la scacchiera.
    
    Gestisce il rendering dei pezzi, le evidenziazioni, le frecce, le animazioni,
    e tutti gli eventi di input dell'utente (click, drag, promozione).
    """
    
    def __init__(self, parent, controller):
        """
        Inizializza la scacchiera.
        
        Args:
            parent: Widget genitore Tkinter
            controller: Istanza di ChessApp per la comunicazione con la logica
        """
        super().__init__(parent, width=BOARD_SIZE, height=BOARD_SIZE)
        self.controller = controller
        self.pack(side=tk.LEFT)
        self.bind("<ButtonPress-1>", self.on_left_press)
        self.bind("<B1-Motion>", self.on_drag_motion)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<ButtonPress-3>", self.on_right_press)
        self.bind("<B3-Motion>", self.on_right_drag)
        self.bind("<ButtonRelease-3>", self.on_right_release)
        
        self.colors = BOARD_COLORS
        self.highlight_colors = {
            "legal": COLOR_LEGAL_MOVE, 
            "last_move": COLOR_LAST_MOVE, 
            "check": COLOR_CHECK
        }
        self.piece_images = {}
        self.classification_images = {}
        self.drag_data = {"start_square": None, "item_id": None, "is_dragging": False}
        self.is_enabled = True
        self.promotion_data = {"active": False, "move": None, "choices_bounds": {}}
        self.best_move_arrow = None
        self.custom_arrows = []
        self.custom_highlights = []
        self.right_drag_data = {'start_square': None, 'temp_arrow_id': None}
        self.animation_data = {
            "active": False, 
            "piece": None, 
            "from_square": None, 
            "to_square": None, 
            "start_time": 0, 
            "duration": ANIMATION_DURATION_MS, 
            "item_id": None, 
            "callback": None, 
            "was_enabled": True
        }
        self._load_piece_images()
        self._load_classification_images()

    def draw_custom_highlight(self, square, color):
        """
        Disegna un'evidenziazione personalizzata su una casella.
        
        Args:
            square: Indice della casella (0-63)
            color: Colore dell'evidenziazione (formato hex)
        """
        is_flipped = self.controller.is_board_flipped
        r, c = self._get_coords(square, is_flipped)
        y1, x1 = r * SQUARE_SIZE, c * SQUARE_SIZE
        self.create_rectangle(x1, y1, x1 + SQUARE_SIZE, y1 + SQUARE_SIZE, fill=color, outline="", stipple='gray25')
    
    def draw_legal_move_indicator(self, square, has_piece=False):
        """
        Disegna un indicatore per una mossa legale.
        
        Se la casella è vuota, disegna un pallino verde.
        Se la casella contiene un pezzo (cattura), disegna un anello verde.
        
        Args:
            square: Indice della casella (0-63)
            has_piece: True se la casella contiene un pezzo da catturare
        """
        is_flipped = self.controller.is_board_flipped
        r, c = self._get_coords(square, is_flipped)
        center_x = c * SQUARE_SIZE + SQUARE_SIZE // 2
        center_y = r * SQUARE_SIZE + SQUARE_SIZE // 2
        
        if has_piece:
            # Cattura: disegna un anello verde
            radius = SQUARE_SIZE // LEGAL_MOVE_RADIUS_CAPTURE - LEGAL_MOVE_RADIUS_CAPTURE
            self.create_oval(center_x - radius, center_y - radius, 
                           center_x + radius, center_y + radius, 
                           outline=COLOR_LEGAL_MOVE, width=LEGAL_MOVE_RING_WIDTH, fill="")
        else:
            # Casella vuota: disegna un pallino verde
            radius = SQUARE_SIZE // LEGAL_MOVE_RADIUS_EMPTY
            self.create_oval(center_x - radius, center_y - radius, 
                           center_x + radius, center_y + radius, 
                           fill=COLOR_LEGAL_MOVE, outline="")

    def draw(self, board_to_draw, square_to_hide=None):
        """
        Disegna l'intera scacchiera con pezzi, evidenziazioni e frecce.
        
        Args:
            board_to_draw: Istanza di chess.Board da visualizzare
            square_to_hide: Casella da nascondere (usato durante le animazioni)
        """
        self.delete("all")
        is_flipped = self.controller.is_board_flipped
        
        # Disegna le caselle della scacchiera
        for i in range(64):
            r, c = divmod(i, 8)
            color = self.colors[(r + c) % 2]
            y1, x1 = r * SQUARE_SIZE, c * SQUARE_SIZE
            self.create_rectangle(x1, y1, x1 + SQUARE_SIZE, y1 + SQUARE_SIZE, fill=color, outline="")

        # Evidenziazioni personalizzate (create con click destro)
        for h_square, h_color in self.custom_highlights:
            self.draw_custom_highlight(h_square, h_color)
        
        # Evidenzia l'ultima mossa giocata
        if board_to_draw.move_stack:
            last_move_on_display = board_to_draw.peek()
            r_from, c_from = self._get_coords(last_move_on_display.from_square, is_flipped)
            r_to, c_to = self._get_coords(last_move_on_display.to_square, is_flipped)
            self._highlight_square(r_from, c_from, self.highlight_colors["last_move"])
            self._highlight_square(r_to, c_to, self.highlight_colors["last_move"])
        
        # Evidenzia il re sotto scacco
        if board_to_draw.is_check():
            r_king, c_king = self._get_coords(board_to_draw.king(board_to_draw.turn), is_flipped)
            self._highlight_square(r_king, c_king, self.highlight_colors["check"])
        
        # Mostra le mosse legali per il pezzo selezionato
        if self.controller.selected_square is not None and not self.controller.viewing_history:
            legal_moves = [m for m in self.controller.logic.board.legal_moves 
                          if m.from_square == self.controller.selected_square]
            for move in legal_moves:
                has_piece = board_to_draw.piece_at(move.to_square) is not None
                self.draw_legal_move_indicator(move.to_square, has_piece)

        # Disegna frecce personalizzate e freccia della mossa migliore
        for from_sq, to_sq, color in self.custom_arrows:
            self.draw_custom_arrow(from_sq, to_sq, color)

        if self.best_move_arrow:
            self.draw_best_move_arrow(self.best_move_arrow)
        
        # --- DISEGNO DEI PEZZI ---
        for i in range(64):
            if i == square_to_hide: continue
            piece = board_to_draw.piece_at(i)
            if piece:
                r, c = self._get_coords(i, is_flipped)
                self.create_image(c * SQUARE_SIZE, r * SQUARE_SIZE, image=self.piece_images[piece], anchor="nw")
        
        # Disegna le coordinate della scacchiera
        font_size = int(SQUARE_SIZE / COORDINATE_FONT_SIZE_DIVISOR)
        font_style = ("Helvetica", font_size)

        # Disegna i numeri (ranks) sulla colonna di sinistra
        for r in range(8):
            square_color_index = r % 2
            text_color = self.colors[1 - square_color_index]
            number = BOARD_RANKS[r] if not is_flipped else BOARD_RANKS[::-1][r]
            x = COORDINATE_PADDING
            y = r * SQUARE_SIZE + COORDINATE_PADDING
            self.create_text(x, y, text=number, anchor="nw", font=font_style, fill=text_color)

        # Disegna le lettere (files) sulla riga in basso
        for c in range(8):
            square_color_index = (7 + c) % 2
            text_color = self.colors[1 - square_color_index]
            letter = BOARD_FILES[c] if not is_flipped else BOARD_FILES[::-1][c]
            x = c * SQUARE_SIZE + SQUARE_SIZE - COORDINATE_PADDING
            y = 7 * SQUARE_SIZE + SQUARE_SIZE - COORDINATE_PADDING
            self.create_text(x, y, text=letter, anchor="se", font=font_style, fill=text_color)
        
        if self.promotion_data["active"]:
            self._draw_promotion_overlay()

    def _load_piece_images(self):
        piece_chars = {
            chess.KING: 'K', chess.QUEEN: 'Q', chess.BISHOP: 'B',
            chess.KNIGHT: 'N', chess.ROOK: 'R', chess.PAWN: 'P'
        }
        color_chars = { chess.WHITE: 'w', chess.BLACK: 'b' }
        missing_files = []
        for color in [chess.WHITE, chess.BLACK]:
            for piece_type in [chess.KING, chess.QUEEN, chess.BISHOP, chess.KNIGHT, chess.ROOK, chess.PAWN]:
                filename = f"{color_chars[color]}{piece_chars[piece_type]}.png"
                filepath = os.path.join(PIECES_PATH, filename)
                try:
                    img = Image.open(filepath).convert("RGBA")
                    img = img.resize((SQUARE_SIZE, SQUARE_SIZE), Image.LANCZOS)
                    self.piece_images[chess.Piece(piece_type, color)] = ImageTk.PhotoImage(img)
                except FileNotFoundError:
                    missing_files.append(filename)
        if missing_files:
            messagebox.showerror("Errore", f"File dei pezzi mancanti:\n{', '.join(missing_files)}")
            self.controller.master.destroy()

    def _load_classification_images(self):
        """Carica le immagini delle classificazioni delle mosse."""
        missing_files = []
        icon_size = int(SQUARE_SIZE * CLASSIFICATION_ICON_SIZE_RATIO)
        
        for classification_key, image_filename in CLASSIFICATION_IMAGES.items():
            filepath = os.path.join(CLASSIFICATIONS_PATH, image_filename)
            try:
                img = Image.open(filepath).convert("RGBA")
                img = img.resize((icon_size, icon_size), Image.LANCZOS)
                self.classification_images[classification_key] = ImageTk.PhotoImage(img)
            except FileNotFoundError:
                missing_files.append(image_filename)
        
        if missing_files:
            messagebox.showwarning("Avviso", f"File di classificazione mancanti:\n{', '.join(missing_files)}\nVerranno usati cerchi colorati come fallback.")

    def _draw_promotion_overlay(self):
        move = self.promotion_data["move"]; to_square = move.to_square
        is_flipped = self.controller.is_board_flipped
        r, c = self._get_coords(to_square, is_flipped)
        color = self.controller.logic.board.piece_at(move.from_square).color
        pieces_to_show = [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]
        overlay_height = SQUARE_SIZE * len(pieces_to_show)
        x_start = c * SQUARE_SIZE
        if (color == chess.WHITE and not is_flipped) or (color == chess.BLACK and is_flipped): y_start = r * SQUARE_SIZE
        else: y_start = (r + 1) * SQUARE_SIZE - overlay_height; pieces_to_show.reverse()
        self.create_rectangle(x_start, y_start, x_start + SQUARE_SIZE, y_start + overlay_height, fill=PROMOTION_OVERLAY_COLOR, stipple=PROMOTION_OVERLAY_STIPPLE, outline="")
        self.promotion_data["choices_bounds"].clear()
        for i, piece_type in enumerate(pieces_to_show):
            y = y_start + (i * SQUARE_SIZE); piece = chess.Piece(piece_type, color)
            self.create_image(x_start, y, image=self.piece_images[piece], anchor="nw")
            self.promotion_data["choices_bounds"][piece_type] = (x_start, y, x_start + SQUARE_SIZE, y + SQUARE_SIZE)
            
    def _get_coords(self, square, is_flipped):
        row, col = divmod(square, 8); return (row, 7 - col) if is_flipped else (7 - row, col)
        
    def _highlight_square(self, row, col, color, stipple="gray50"):
        y1, x1 = row * SQUARE_SIZE, col * SQUARE_SIZE
        self.create_rectangle(x1, y1, x1 + SQUARE_SIZE, y1 + SQUARE_SIZE, fill=color, outline="", stipple=stipple)
    
    def cancel_animation(self):
        """
        Interrompe l'animazione in corso senza eseguire il callback.
        Ripristina lo stato della scacchiera.
        """
        if self.animation_data["active"]:
            self.animation_data["active"] = False
            self.is_enabled = self.animation_data.get("was_enabled", True)
            self.animation_data["callback"] = None
    
    def animate_move(self, move, callback=None):
        """
        Anima una mossa dalla casella di partenza a quella di arrivo.
        
        Args:
            move: Istanza di chess.Move da animare
            callback: Funzione da chiamare al termine dell'animazione
        """
        # Ottieni il pezzo dalla scacchiera corretta
        board_to_use = (self.controller.display_board if self.controller.viewing_history 
                       else self.controller.logic.board)
        piece = board_to_use.piece_at(move.from_square)
        
        if not piece:
            # Se non c'è un pezzo, esegui il callback senza animazione
            if callback:
                callback()
            return
        
        self.animation_data["active"] = True
        self.animation_data["piece"] = piece
        self.animation_data["from_square"] = move.from_square
        self.animation_data["to_square"] = move.to_square
        self.animation_data["start_time"] = time.time() * TIME_TO_MILLISECONDS
        self.animation_data["callback"] = callback
        self.animation_data["was_enabled"] = self.is_enabled
        
        # Disabilita l'input durante l'animazione
        self.is_enabled = False
        
        # Avvia l'animazione
        self._animate_step()
    
    def _animate_step(self):
        """Esegue un passo dell'animazione"""
        if not self.animation_data["active"]:
            return
        
        current_time = time.time() * 1000
        elapsed = current_time - self.animation_data["start_time"]
        progress = min(elapsed / self.animation_data["duration"], 1.0)
        
        # Easing function (ease-out cubic per un movimento più naturale)
        eased_progress = 1 - pow(1 - progress, 3)
        
        # Calcola la posizione corrente
        from_square = self.animation_data["from_square"]
        to_square = self.animation_data["to_square"]
        is_flipped = self.controller.is_board_flipped
        
        r_from, c_from = self._get_coords(from_square, is_flipped)
        r_to, c_to = self._get_coords(to_square, is_flipped)
        
        x_from = c_from * SQUARE_SIZE + SQUARE_SIZE // 2
        y_from = r_from * SQUARE_SIZE + SQUARE_SIZE // 2
        x_to = c_to * SQUARE_SIZE + SQUARE_SIZE // 2
        y_to = r_to * SQUARE_SIZE + SQUARE_SIZE // 2
        
        current_x = x_from + (x_to - x_from) * eased_progress
        current_y = y_from + (y_to - y_from) * eased_progress
        
        # Ridisegna la scacchiera corretta senza il pezzo animato
        board_to_draw = self.controller.display_board.copy() if self.controller.viewing_history else self.controller.logic.board.copy()
        self.draw(board_to_draw, square_to_hide=from_square)
        
        # Disegna il pezzo nella posizione animata
        piece = self.animation_data["piece"]
        self.create_image(current_x, current_y, image=self.piece_images[piece], anchor="center")
        
        if progress < 1.0:
            # Continua l'animazione
            self.after(16, self._animate_step)  # ~60 FPS
        else:
            # Animazione completata
            self.animation_data["active"] = False
            # Ripristina lo stato precedente di is_enabled
            self.is_enabled = self.animation_data.get("was_enabled", True)
            
            # Esegui il callback se presente
            if self.animation_data["callback"]:
                self.animation_data["callback"]()
        
    def on_left_press(self, event):
        if self.promotion_data["active"]: self._handle_promotion_click(event); return
        if not self.is_enabled: return
        square = self.get_square_from_event(event)
        if square is None: return
        self.drag_data["start_square"] = square; self.controller.handle_press(square)
        
    def _handle_promotion_click(self, event):
        for piece_type, bounds in self.promotion_data["choices_bounds"].items():
            x1, y1, x2, y2 = bounds
            if x1 <= event.x <= x2 and y1 <= event.y <= y2: self.controller.complete_promotion(self.promotion_data["move"], piece_type); return
        self.hide_promotion_choices(); self.controller.deselect_and_update()
        
    def on_drag_motion(self, event):
        if self.promotion_data["active"]: return
        if not self.is_enabled or self.drag_data["start_square"] is None: return
        if not self.drag_data["is_dragging"]:
            self.drag_data["is_dragging"] = True; from_sq = self.drag_data["start_square"]
            piece = self.controller.logic.get_piece_at(from_sq)
            if piece and self.controller.selected_square is not None:
                board_to_draw = self.controller.display_board if self.controller.viewing_history else self.controller.logic.board
                self.draw(board_to_draw, square_to_hide=from_sq)
                self.drag_data["item_id"] = self.create_image(event.x, event.y, image=self.piece_images[piece], anchor="center")
        if self.drag_data["item_id"]: self.coords(self.drag_data["item_id"], event.x, event.y)
            
    def on_release(self, event):
        if self.promotion_data["active"]: return
        if not self.is_enabled: return
        if self.drag_data["item_id"]: self.delete(self.drag_data["item_id"])
        if self.drag_data["is_dragging"]:
            to_sq = self.get_square_from_event(event); from_sq = self.drag_data["start_square"]
            if from_sq is not None and to_sq is not None and from_sq != to_sq: 
                self.controller.attempt_move(from_sq, to_sq, skip_animation=True)
            else: self.controller.deselect_and_update()
        self.drag_data = {"start_square": None, "item_id": None, "is_dragging": False}
        
    def on_right_press(self, event):
        """
        Gestisce il click destro per iniziare a disegnare frecce o evidenziazioni.
        
        Args:
            event: Evento Tkinter del mouse
        """
        self.controller.cancel_premove()
        self.right_drag_data['start_square'] = self.get_square_from_event(event)
        
    def on_right_drag(self, event):
        """
        Gestisce il trascinamento con il tasto destro per visualizzare una freccia temporanea.
        
        Args:
            event: Evento Tkinter del mouse
        """
        start_sq = self.right_drag_data['start_square']
        if start_sq is None:
            return
        
        # Rimuovi la freccia temporanea precedente
        if self.right_drag_data['temp_arrow_id']:
            self.delete(self.right_drag_data['temp_arrow_id'])
        
        # Disegna una nuova freccia temporanea
        is_flipped = self.controller.is_board_flipped
        from_r, from_c = self._get_coords(start_sq, is_flipped)
        x1 = from_c * SQUARE_SIZE + SQUARE_SIZE // 2
        y1 = from_r * SQUARE_SIZE + SQUARE_SIZE // 2
        x2, y2 = event.x, event.y
        arrow_width = int(SQUARE_SIZE * ARROW_WIDTH_RATIO)
        self.right_drag_data['temp_arrow_id'] = self.create_line(
            x1, y1, x2, y2, arrow=tk.LAST, fill=COLOR_ARROW_DEFAULT, width=arrow_width
        )

    def on_right_release(self, event):
        """
        Gestisce il rilascio del tasto destro per creare frecce o evidenziazioni permanenti.
        
        Args:
            event: Evento Tkinter del mouse
        """
        # Rimuovi la freccia temporanea
        if self.right_drag_data['temp_arrow_id']:
            self.delete(self.right_drag_data['temp_arrow_id'])
        
        start_sq = self.right_drag_data['start_square']
        end_sq = self.get_square_from_event(event)
        
        if start_sq is not None and end_sq is not None:
            if start_sq == end_sq:
                # Click sulla stessa casella: crea evidenziazione
                self.custom_highlights.append((start_sq, COLOR_HIGHLIGHT_DEFAULT))
            else:
                # Trascinamento: crea freccia
                self.custom_arrows.append((start_sq, end_sq, COLOR_ARROW_DEFAULT))
        
        self.right_drag_data = {'start_square': None, 'temp_arrow_id': None}
        self.controller.update_display()
        
    def get_square_from_event(self, event):
        """
        Converte le coordinate del mouse in un indice di casella della scacchiera.
        
        Args:
            event: Evento Tkinter del mouse
            
        Returns:
            Indice della casella (0-63) o None se fuori dalla scacchiera
        """
        is_flipped = self.controller.is_board_flipped
        col, row = event.x // SQUARE_SIZE, 7 - (event.y // SQUARE_SIZE)
        if is_flipped:
            col, row = 7 - col, 7 - row
        return chess.square(col, row) if 0 <= col <= 7 and 0 <= row <= 7 else None
        
    def show_promotion_choices(self, move):
        self.promotion_data["active"] = True; self.promotion_data["move"] = move
        board_to_draw = self.controller.display_board if self.controller.viewing_history else self.controller.logic.board
        self.draw(board_to_draw)
        
    def hide_promotion_choices(self):
        self.promotion_data["active"] = False; self.promotion_data["move"] = None; self.promotion_data["choices_bounds"].clear()
    
    def draw_evaluation_dot(self, square, classification_key):
        """
        Disegna l'icona di classificazione della mossa sulla casella specificata.
        
        Args:
            square: La casella su cui disegnare l'icona
            classification_key: La chiave della classificazione (es. 'brilliant', 'best', 'blunder', etc.)
        """
        is_flipped = self.controller.is_board_flipped
        r, c = self._get_coords(square, is_flipped)
        
        # Posizione nell'angolo in alto a destra della casella
        x_center = (c + 1) * SQUARE_SIZE - (SQUARE_SIZE * 0.15)
        y_center = r * SQUARE_SIZE + (SQUARE_SIZE * 0.15)
        
        # Prova a usare l'immagine se disponibile
        if classification_key in self.classification_images:
            self.create_image(x_center, y_center, image=self.classification_images[classification_key], anchor="center")
        else:
            # Fallback: usa un cerchio colorato se l'immagine non è disponibile
            from config import EVAL_COLORS
            color = EVAL_COLORS.get(classification_key, "#808080")  # Grigio come default
            radius = SQUARE_SIZE * 0.1
            self.create_oval(x_center - radius, y_center - radius, x_center + radius, y_center + radius, 
                           fill=color, outline="black", width=1.5)

    def draw_custom_arrow(self, from_sq, to_sq, color):
        is_flipped = self.controller.is_board_flipped
        from_r, from_c = self._get_coords(from_sq, is_flipped); to_r, to_c = self._get_coords(to_sq, is_flipped)
        x1 = from_c * SQUARE_SIZE + SQUARE_SIZE / 2; y1 = from_r * SQUARE_SIZE + SQUARE_SIZE / 2
        x2 = to_c * SQUARE_SIZE + SQUARE_SIZE / 2; y2 = to_r * SQUARE_SIZE + SQUARE_SIZE / 2
        arrow_width = int(SQUARE_SIZE * 0.15); arrow_shape = (int(SQUARE_SIZE * 0.3), int(SQUARE_SIZE * 0.4), int(SQUARE_SIZE * 0.2))
        return self.create_line(x1, y1, x2, y2, arrow=tk.LAST, fill=color, width=arrow_width, arrowshape=arrow_shape, stipple='gray50')

    def draw_best_move_arrow(self, move):
        is_flipped = self.controller.is_board_flipped
        from_r, from_c = self._get_coords(move.from_square, is_flipped)
        to_r, to_c = self._get_coords(move.to_square, is_flipped)
        x1 = from_c * SQUARE_SIZE + SQUARE_SIZE // 2; y1 = from_r * SQUARE_SIZE + SQUARE_SIZE // 2
        x2 = to_c * SQUARE_SIZE + SQUARE_SIZE // 2; y2 = to_r * SQUARE_SIZE + SQUARE_SIZE // 2
        arrow_color = "#3498db"; arrow_width = int(SQUARE_SIZE * 0.2)
        arrow_shape_config = (int(SQUARE_SIZE * 0.4), int(SQUARE_SIZE * 0.5), int(SQUARE_SIZE * 0.25))
        self.create_line(x1, y1, x2, y2, arrow=tk.LAST, fill=arrow_color, width=arrow_width, arrowshape=arrow_shape_config, stipple='gray50')