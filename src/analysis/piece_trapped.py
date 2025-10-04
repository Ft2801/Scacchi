# piece_trapped.py
"""
Modulo per il rilevamento di pezzi intrappolati.
Un pezzo è intrappolato se non è sicuro e non ha mosse sicure disponibili.
"""

import chess
from typing import Optional
from src.analysis.piece_safety import is_piece_safe
from src.analysis.danger_levels import move_creates_greater_threat

def is_piece_trapped(board: chess.Board, square: chess.Square, 
                    danger_levels: bool = True) -> bool:
    """
    Determina se un pezzo è intrappolato.
    
    Un pezzo è intrappolato se:
    1. Non è sicuro nella sua posizione attuale
    2. Non ha mosse sicure disponibili
    3. (Opzionale) Muoverlo permetterebbe all'avversario una controminaccia maggiore
    
    Args:
        board: Scacchiera corrente
        square: Casella del pezzo da analizzare
        danger_levels: Se True, considera anche i livelli di pericolo
        
    Returns:
        True se il pezzo è intrappolato, False altrimenti
    """
    piece = board.piece_at(square)
    if not piece:
        return False
    
    # Se il pezzo è sicuro dove si trova, non è intrappolato
    if is_piece_safe(board, square):
        return False
    
    # Crea una copia della scacchiera con il turno corretto
    temp_board = board.copy()
    temp_board.turn = piece.color
    
    # Controlla tutte le mosse legali per quel pezzo
    piece_moves = [move for move in temp_board.legal_moves if move.from_square == square]
    
    for move in piece_moves:
        # Non considerare le catture del re (illegali)
        if temp_board.piece_at(move.to_square) and temp_board.piece_at(move.to_square).piece_type == chess.KING:
            continue
        
        # Se i danger levels sono abilitati, controlla se la mossa crea una minaccia maggiore
        if danger_levels and move_creates_greater_threat(board, square, move):
            continue
        
        # Simula la mossa e controlla se il pezzo è sicuro nella nuova posizione
        temp_board.push(move)
        is_safe_after_move = is_piece_safe(temp_board, move.to_square, move)
        temp_board.pop()
        
        if is_safe_after_move:
            return False  # Ha trovato una mossa sicura, non è intrappolato
    
    return True  # Nessuna mossa sicura trovata, il pezzo è intrappolato