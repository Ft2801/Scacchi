# advanced_move_classifier.py
"""
Classificatore di mosse avanzato che implementa la logica sofisticata
per identificare mosse brillanti, critiche, e calcolare accuratezza precisa.
"""

import chess
import math
from typing import Dict, Any, List, Optional, Tuple
from src.analysis.piece_safety import is_piece_safe, get_unsafe_pieces
from src.analysis.piece_trapped import is_piece_trapped
from src.analysis.critical_moves import is_move_critical_candidate
from src.analysis.accuracy_calculator import winning_chances_percent
from src.core.stockfish_manager import convert_top_move_to_cp
from src.config import (
    PIECE_VALUES, SACRIFICE_MIN_VALUE, BRILLIANT_MAX_LOSS,
    GREAT_MOVE_GAP, GREAT_MOVE_ADVANTAGE, GREAT_MOVE_TACTICAL_ADVANTAGE,
    GREAT_MOVE_LOSS_THRESHOLD, CRITICAL_THRESHOLD, ALTERNATIVE_BAD_THRESHOLD
)

class AdvancedMoveClassifier:
    """
    Classificatore di mosse avanzato che implementa la logica sofisticata
    per identificare mosse brillanti, critiche, e calcolare accuratezza precisa.
    """
    
    def __init__(self, analyzer):
        """
        Inizializza il classificatore con un'istanza di Stockfish.
        
        Args:
            analyzer: Istanza di Stockfish per l'analisi delle posizioni
        """
        self.analyzer = analyzer
        self.classification_map = {
            'BEST': 'best',
            'EXCELLENT': 'excellent', 
            'GOOD': 'good',
            'INACCURACY': 'inaccuracy',
            'MISTAKE': 'mistake', 
            'BLUNDER': 'blunder',
            'BRILLIANT': 'brilliant',
            'CRITICAL': 'great',
            'FORCED': 'forced',
            'THEORY': 'theory'
        }
    
    def _is_sacrifice_move(self, board: chess.Board, move: chess.Move) -> bool:
        """
        Determina se una mossa è un sacrificio significativo.
        
        Un sacrificio è quando:
        1. Si cattura un pezzo di valore inferiore o si muove su una casella vuota
        2. Il pezzo mosso viene messo in presa da un pezzo di valore inferiore
        3. Il materiale netto sacrificato è significativo (almeno un pedone)
        
        Args:
            board: Scacchiera corrente
            move: Mossa da valutare
            
        Returns:
            True se la mossa è un sacrificio, False altrimenti
        """
        moved_piece = board.piece_at(move.from_square)
        if not moved_piece or moved_piece.piece_type == chess.KING:
            return False
        
        captured_piece = board.piece_at(move.to_square)
        
        # Simula la mossa
        temp_board = board.copy()
        temp_board.push(move)
        
        # Verifica se il pezzo mosso è attaccato dall'avversario
        opponent_color = not board.turn
        opponent_attackers = temp_board.attackers(opponent_color, move.to_square)
        
        if not opponent_attackers:
            return False  # Non è in presa, non è un sacrificio
        
        # Calcola il valore del materiale sacrificato vs guadagnato
        moved_value = PIECE_VALUES[moved_piece.piece_type]
        captured_value = PIECE_VALUES[captured_piece.piece_type] if captured_piece else 0
        
        # Trova l'attaccante di valore più basso
        min_attacker_value = float('inf')
        for attacker_square in opponent_attackers:
            attacker_piece = temp_board.piece_at(attacker_square)
            if attacker_piece:
                attacker_value = PIECE_VALUES[attacker_piece.piece_type]
                min_attacker_value = min(min_attacker_value, attacker_value)
        
        # È un sacrificio se il pezzo mosso vale più dell'attaccante più debole
        # e il materiale netto sacrificato è significativo
        if min_attacker_value < moved_value:
            net_sacrifice = moved_value - captured_value - min_attacker_value
            return net_sacrifice >= SACRIFICE_MIN_VALUE
        
        return False
    
    def _consider_brilliant_classification(self, board_before: chess.Board, move: chess.Move,
                                         best_move_eval: Dict[str, Any], current_eval: Dict[str, Any]) -> bool:
        """
        Determina se una mossa dovrebbe essere classificata come brillante.
        
        Una mossa è brillante SOLO se:
        1. È un sacrificio significativo
        2. La perdita di valutazione non è eccessiva (<=150cp)
        3. Mantiene un vantaggio decente (>=0cp)
        
        Args:
            board_before: Scacchiera prima della mossa
            move: Mossa da valutare
            best_move_eval: Valutazione della mossa migliore
            current_eval: Valutazione della mossa giocata
            
        Returns:
            True se la mossa è brillante, False altrimenti
        """
        if not best_move_eval or not current_eval:
            return False

        # Una mossa è brillante SOLO se è un sacrificio
        if not self._is_sacrifice_move(board_before, move):
            return False

        turn = board_before.turn
        best_eval_cp = convert_top_move_to_cp(best_move_eval)
        current_eval_cp = convert_top_move_to_cp(current_eval)
        
        # Controllo di sicurezza per valori None
        if best_eval_cp is None or current_eval_cp is None:
            return False

        # Calcola la perdita di valutazione e il vantaggio soggettivo
        loss = (best_eval_cp - current_eval_cp) if turn == chess.WHITE else (current_eval_cp - best_eval_cp)
        subjective_advantage = current_eval_cp if turn == chess.WHITE else -current_eval_cp

        # Sacrificio brillante se soddisfa i criteri
        return loss <= BRILLIANT_MAX_LOSS and subjective_advantage >= 0
    
    def _consider_great_classification(self, board_before: chess.Board, move: chess.Move,
                                     best_move_eval: Dict[str, Any], current_eval: Dict[str, Any],
                                     second_best_eval: Optional[Dict[str, Any]]) -> bool:
        """
        Determina se una mossa dovrebbe essere classificata come "grande".
        
        Una mossa è "grande" se:
        1. È l'unica che mantiene un vantaggio significativo
        2. È molto superiore alle alternative
        3. È una mossa critica in una posizione importante
        
        Args:
            board_before: Scacchiera prima della mossa
            move: Mossa da valutare
            best_move_eval: Valutazione della mossa migliore
            current_eval: Valutazione della mossa giocata
            second_best_eval: Valutazione della seconda mossa migliore
            
        Returns:
            True se la mossa è "grande", False altrimenti
        """
        if not best_move_eval or not second_best_eval:
            return False

        turn = board_before.turn
        best_eval_cp = convert_top_move_to_cp(best_move_eval)
        current_eval_cp = convert_top_move_to_cp(current_eval)
        second_best_cp = convert_top_move_to_cp(second_best_eval)
        
        # Controllo di sicurezza per valori None
        if best_eval_cp is None or current_eval_cp is None or second_best_cp is None:
            return False

        # Calcola la perdita rispetto alla mossa migliore
        loss = (best_eval_cp - current_eval_cp) if turn == chess.WHITE else (current_eval_cp - best_eval_cp)
        subjective_advantage = current_eval_cp if turn == chess.WHITE else -current_eval_cp

        best_move_uci = best_move_eval.get('Move', '')
        
        # Caso 1: È la mossa migliore e molto superiore alle alternative
        if move.uci() == best_move_uci:
            alternative_gap = (best_eval_cp - second_best_cp) if turn == chess.WHITE else (second_best_cp - best_eval_cp)
            # Grande se il gap con la seconda migliore è significativo
            if alternative_gap >= GREAT_MOVE_GAP and subjective_advantage >= GREAT_MOVE_ADVANTAGE:
                return True
        
        # Caso 2: Non è la migliore ma è quasi altrettanto buona e tattica
        elif loss <= GREAT_MOVE_LOSS_THRESHOLD:
            # Controlla se è una mossa tattica importante
            if (board_before.piece_at(move.to_square) or  # Cattura
                board_before.gives_check(move) or         # Scacco
                self._is_sacrifice_move(board_before, move)):  # Sacrificio
                
                # È grande se mantiene un buon vantaggio
                return subjective_advantage >= GREAT_MOVE_TACTICAL_ADVANTAGE
        
        # Caso 3: Mossa che evita una perdita significativa
        if subjective_advantage >= 0 and subjective_advantage < 100:
            # Controlla se le alternative portano a svantaggio
            second_best_advantage = second_best_cp if turn == chess.WHITE else -second_best_cp
            if second_best_advantage < ALTERNATIVE_BAD_THRESHOLD:  # Le alternative sono cattive
                return True

        return False
    
    def _consider_critical_classification(self, prev_eval: Dict[str, Any], 
                                        second_best_eval: Optional[Dict[str, Any]],
                                        board_before: chess.Board) -> bool:
        """
        Determina se una mossa dovrebbe essere classificata come critica.
        
        Una mossa è critica se:
        1. È candidata per essere critica (non forzata, non in posizione perdente)
        2. La differenza con la seconda migliore è significativa (>100cp)
        
        Args:
            prev_eval: Valutazione della mossa migliore
            second_best_eval: Valutazione della seconda mossa migliore
            board_before: Scacchiera prima della mossa
            
        Returns:
            True se la mossa è critica, False altrimenti
        """
        if not second_best_eval:
            return False
        
        # Controlla se la mossa è candidata per essere critica
        if not is_move_critical_candidate(prev_eval, prev_eval, board_before):
            return False
        
        best_eval_cp = convert_top_move_to_cp(prev_eval)
        second_best_cp = convert_top_move_to_cp(second_best_eval)
        
        turn = board_before.turn
        advantage_loss = (best_eval_cp - second_best_cp) if turn == chess.WHITE else (second_best_cp - best_eval_cp)
        
        # Se la differenza tra la migliore e la seconda migliore mossa è significativa, è critica
        return advantage_loss > CRITICAL_THRESHOLD
    
    def _point_loss_classify(self, best_eval_cp: int, current_eval_cp: int, turn: chess.Color) -> str:
        """
        Classifica una mossa basata sulla perdita di probabilità di vittoria.
        """
        win_chance_after_best = winning_chances_percent(best_eval_cp)
        win_chance_after_played = winning_chances_percent(current_eval_cp)
        
        if turn == chess.WHITE:
            loss = win_chance_after_best - win_chance_after_played
        else:
            loss = win_chance_after_played - win_chance_after_best
        
        loss = max(0, loss)
        
        if loss <= 1:
            return 'BEST'
        elif loss <= 5:
            return 'EXCELLENT'
        elif loss <= 10:
            return 'GOOD'
        elif loss <= 20:
            return 'INACCURACY'
        elif loss <= 30:
            return 'MISTAKE'
        else:
            return 'BLUNDER'
    
    def classify_move(self, board_before: chess.Board, move: chess.Move, 
                     top_moves: List[Dict[str, Any]], 
                     opening_name: Optional[str] = None) -> str:
        """
        Classifica una mossa usando la logica avanzata.
        
        Args:
            board_before: Scacchiera prima della mossa
            move: Mossa da classificare
            top_moves: Lista delle migliori mosse con valutazioni
            opening_name: Nome dell'apertura (opzionale)
            
        Returns:
            Chiave della classificazione (es. 'best', 'brilliant', 'blunder')
        """
        turn = board_before.turn
        
        # Considera classificazione forzata
        if len(list(board_before.legal_moves)) <= 1:
            return self.classification_map['FORCED']
        
        # Considera classificazione teorica
        if opening_name:
            return self.classification_map['THEORY']
        
        # Simula la mossa
        board_after = board_before.copy()
        board_after.push(move)
        
        # Scacco matto è sempre la migliore
        if board_after.is_checkmate():
            return self.classification_map['BEST']
        
        # Ottieni le valutazioni
        best_move_eval = top_moves[0] if top_moves else {}
        second_best_eval = top_moves[1] if len(top_moves) > 1 else None
        
        # Valutazione della posizione dopo la mossa giocata
        self.analyzer.set_fen_position(board_after.fen())
        current_eval = self.analyzer.get_evaluation()
        
        best_eval_cp = convert_top_move_to_cp(best_move_eval)
        current_eval_cp = convert_top_move_to_cp(current_eval)
        
        # Controlla se è la mossa migliore
        best_move_uci = best_move_eval.get('Move', '')
        top_move_played = (move.uci() == best_move_uci)
        
        # Classificazione basata sulla perdita di punti
        classification = (self.classification_map['BEST'] if top_move_played 
                         else self._point_loss_classify(best_eval_cp, current_eval_cp, turn))
        
        # Sacrificio che mantiene il vantaggio -> brillante
        if self._consider_brilliant_classification(board_before, move, best_move_eval, current_eval):
            return self.classification_map['BRILLIANT']
        
        # Mossa migliore che mantiene il vantaggio in modo unico -> grande
        if self._consider_great_classification(board_before, move, best_move_eval, current_eval, second_best_eval):
            return self.classification_map['CRITICAL']  # "great"
        
        # Considera classificazione critica (solo per la mossa migliore in posizioni critiche)
        if (top_move_played and 
                self._consider_critical_classification(best_move_eval, second_best_eval, board_before)):
            return self.classification_map['CRITICAL']
        
        return classification