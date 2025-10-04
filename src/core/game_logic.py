# game_logic.py
"""
Modulo per la logica di gioco degli scacchi.
Gestisce la scacchiera, le mosse, l'AI e lo stato della partita.
"""

import chess
from src.config import AI_LEVELS, ANALYSIS_DEPTH
from src.core.stockfish_manager import StockfishManager

class GameLogic:
    """
    Classe che gestisce la logica di gioco degli scacchi.
    Mantiene lo stato della scacchiera e fornisce metodi per interagire con essa.
    """
    
    def __init__(self):
        """Inizializza la logica di gioco con una nuova scacchiera."""
        self.board = chess.Board()
        self.undone_moves = []
        self.analysis_depth = ANALYSIS_DEPTH
        
        # Usa StockfishManager per ottenere un'istanza cached
        self.stockfish_player = StockfishManager.get_instance(
            depth=self.analysis_depth,
            threads=1,
            key="game_player"
        )
        
        if not self.stockfish_player:
            print("AVVISO: Stockfish non trovato per il gioco.")
            
    def get_piece_at(self, square):
        """
        Restituisce il pezzo presente in una casella.
        
        Args:
            square: Casella da controllare
            
        Returns:
            Pezzo presente nella casella o None
        """
        return self.board.piece_at(square)
    
    def get_legal_moves(self, square):
        """
        Restituisce tutte le mosse legali da una casella.
        
        Args:
            square: Casella di partenza
            
        Returns:
            Lista di mosse legali
        """
        return [m for m in self.board.legal_moves if m.from_square == square]

    def make_move(self, move):
        """
        Esegue una mossa sulla scacchiera.
        
        Args:
            move: Mossa da eseguire
            
        Returns:
            True se la mossa è stata eseguita, False altrimenti
        """
        try:
            self.board.push(move)
            self.undone_moves.clear()
            return True
        except (ValueError, AssertionError):
            return False

    def get_ai_move(self, level: int):
        """
        Calcola la mossa migliore per l'AI in base a un livello di difficoltà predefinito.
        
        Args:
            level: Livello di difficoltà (1-8)
            
        Returns:
            Mossa calcolata dall'AI o None se non disponibile
        """
        if not self.stockfish_player:
            return None

        # 1. Ottieni i parametri per il livello selezionato
        params = AI_LEVELS.get(level)
        if not params:
            print(f"AVVISO: Livello AI {level} non trovato. Uso i default.")
            # Imposta dei valori di default sicuri in caso di errore
            self.stockfish_player.set_skill_level(20)
            self.stockfish_player.set_depth(15)
            movetime = 1000
        else:
            # 2. Imposta i parametri in Stockfish
            self.stockfish_player.set_skill_level(params["skill"])
            self.stockfish_player.set_depth(params["depth"])
            movetime = params["movetime"]

        # 3. Imposta la posizione e calcola la mossa entro il tempo limite
        self.stockfish_player.set_fen_position(self.board.fen())
        best_move_uci = self.stockfish_player.get_best_move_time(movetime)
        
        if best_move_uci:
            return chess.Move.from_uci(best_move_uci)
        return None

    def undo_move(self):
        """
        Annulla l'ultima mossa eseguita.
        
        Returns:
            True se la mossa è stata annullata, False altrimenti
        """
        if self.board.move_stack:
            self.undone_moves.append(self.board.pop())
            return True
        return False

    def redo_move(self):
        """
        Ripristina l'ultima mossa annullata.
        
        Returns:
            True se la mossa è stata ripristinata, False altrimenti
        """
        if self.undone_moves:
            self.board.push(self.undone_moves.pop())
            return True
        return False

    def needs_promotion(self, move):
        """
        Verifica se una mossa richiede la promozione di un pedone.
        
        Args:
            move: Mossa da verificare
            
        Returns:
            True se la mossa richiede promozione, False altrimenti
        """
        piece = self.board.piece_at(move.from_square)
        if not piece or piece.piece_type != chess.PAWN:
            return False
        to_rank = chess.square_rank(move.to_square)
        return (piece.color == chess.WHITE and to_rank == 7) or \
               (piece.color == chess.BLACK and to_rank == 0)

    def get_game_status(self):
        """
        Restituisce lo stato corrente della partita.
        
        Returns:
            Stringa descrittiva dello stato della partita
        """
        from utils import get_turn_color_name
        
        if self.board.is_checkmate():
            winner = get_turn_color_name(not self.board.turn)
            return f"Scacco Matto! Vince il {winner}."
        if self.board.is_stalemate():
            return "Partita Patta per Stallo."
        if self.board.is_insufficient_material():
            return "Partita Patta per Materiale Insufficiente."
        if self.board.can_claim_draw():
            return "Partita Patta per Regole Speciali."
        if self.board.is_check():
            turn_color = get_turn_color_name(self.board.turn)
            return f"Scacco! Turno del {turn_color}."
        turn_color = get_turn_color_name(self.board.turn)
        return f"Turno del {turn_color}."

    def reset(self):
        """Resetta la scacchiera allo stato iniziale."""
        self.board.reset()
        self.undone_moves.clear()