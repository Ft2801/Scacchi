# danger_levels.py
"""
Sistema di valutazione dei livelli di pericolo.
Determina se una mossa crea o lascia minacce maggiori rispetto a quelle esistenti.
"""

import chess
from typing import List, Optional
from src.analysis.piece_safety import get_unsafe_pieces
from src.config import PIECE_VALUES

def move_creates_greater_threat(board: chess.Board, threatened_square: chess.Square, 
                               acting_move: chess.Move) -> bool:
    """
    Determina se una mossa crea una minaccia maggiore di quella già esistente
    sul pezzo minacciato.
    
    Args:
        board: Scacchiera corrente
        threatened_square: Casella del pezzo minacciato
        acting_move: Mossa da valutare
        
    Returns:
        True se la mossa crea una minaccia maggiore, False altrimenti
    """
    threatened_piece = board.piece_at(threatened_square)
    if not threatened_piece:
        return False

    # Simula la mossa per determinare il colore che agisce e lo stato successivo
    temp_board = board.copy()
    try:
        temp_board.push(acting_move)
    except ValueError:
        return False

    acting_color = not temp_board.turn  # Dopo push il turno è dell'avversario

    # Pezzi del colore che agisce, >= in valore al pezzo minacciato,
    # che sono già non sicuri prima della mossa
    previous_unsafe = get_unsafe_pieces(board, acting_color)
    previous_relative_threats = [
        sq for sq in previous_unsafe
        if (
            sq != threatened_square and
            board.piece_at(sq) and
            PIECE_VALUES[board.piece_at(sq).piece_type] >= PIECE_VALUES[threatened_piece.piece_type]
        )
    ]

    # Pezzi non sicuri dopo la mossa
    current_unsafe = get_unsafe_pieces(temp_board, acting_color, acting_move)
    current_relative_threats = [
        sq for sq in current_unsafe
        if (
            sq != threatened_square and
            temp_board.piece_at(sq) and  # Controlla che il pezzo esista ancora
            PIECE_VALUES[temp_board.piece_at(sq).piece_type] >= PIECE_VALUES[threatened_piece.piece_type]
        )
    ]

    # Nuove minacce create dalla mossa
    new_threats = [sq for sq in current_relative_threats if sq not in previous_relative_threats]

    if new_threats:
        return True
    
    # Sacrificio di pezzo di valore inferiore che porta a matto
    if (PIECE_VALUES[threatened_piece.piece_type] < PIECE_VALUES[chess.QUEEN] and
        any(temp_board.is_checkmate() for move in [temp_board.push(m) or temp_board.pop() or True 
                                                  for m in temp_board.legal_moves][:1])):
        return True
    
    return False

def move_leaves_greater_threat(board: chess.Board, threatened_square: chess.Square, 
                              acting_move: chess.Move) -> bool:
    """
    Determina se dopo una mossa rimangono minacce maggiori.
    
    Args:
        board: Scacchiera corrente
        threatened_square: Casella del pezzo minacciato
        acting_move: Mossa da valutare
        
    Returns:
        True se dopo la mossa rimangono minacce maggiori, False altrimenti
    """
    threatened_piece = board.piece_at(threatened_square)
    if not threatened_piece:
        return False
    
    # Simula la mossa
    temp_board = board.copy()
    try:
        temp_board.push(acting_move)
    except ValueError:
        return False

    acting_color = not temp_board.turn

    # Controlla le minacce relative dopo la mossa
    unsafe_pieces = get_unsafe_pieces(temp_board, acting_color)
    relative_threats = [
        sq for sq in unsafe_pieces
        if (
            sq != threatened_square and
            temp_board.piece_at(sq) and
            PIECE_VALUES[temp_board.piece_at(sq).piece_type] >= PIECE_VALUES[threatened_piece.piece_type]
        )
    ]

    if relative_threats:
        return True
    
    # Sacrificio che porta a matto
    if (PIECE_VALUES[threatened_piece.piece_type] < PIECE_VALUES[chess.QUEEN] and
        any(temp_board.is_checkmate() for move in [temp_board.push(m) or temp_board.pop() or True 
                                                  for m in temp_board.legal_moves][:1])):
        return True
    
    return False

def has_danger_levels(board: chess.Board, threatened_square: chess.Square, 
                     acting_moves: List[chess.Move], 
                     equality_strategy: str = "leaves") -> bool:
    """
    Determina se tutte le mosse di azione creano una minaccia maggiore
    di quella imposta sul pezzo minacciato.
    
    Args:
        board: Scacchiera corrente
        threatened_square: Casella del pezzo minacciato
        acting_moves: Lista di mosse da valutare
        equality_strategy: Strategia di valutazione ("creates" o "leaves")
        
    Returns:
        True se tutte le mosse creano/lasciano minacce maggiori, False altrimenti
    """
    if equality_strategy == "creates":
        return all(move_creates_greater_threat(board, threatened_square, move) 
                  for move in acting_moves)
    else:  # "leaves"
        return all(move_leaves_greater_threat(board, threatened_square, move) 
                  for move in acting_moves)