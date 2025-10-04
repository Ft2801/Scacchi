# piece_safety.py
"""
Sistema avanzato per valutare la sicurezza dei pezzi.
Determina se un pezzo è sicuro nella sua posizione considerando
attaccanti, difensori e valori relativi dei pezzi.
"""

import chess
from typing import List, Optional, Set
from src.analysis.attackers_defenders import get_attacking_moves, get_defending_moves
from src.config import PIECE_VALUES

def is_piece_safe(board: chess.Board, square: chess.Square, played_move: Optional[chess.Move] = None) -> bool:
    """
    Determina se un pezzo in una data casa è sicuro.
    Implementa la logica avanzata considerando attaccanti diretti e transitivi,
    difensori e valori relativi dei pezzi.
    
    Args:
        board: Scacchiera corrente
        square: Casella da analizzare
        played_move: Mossa giocata (opzionale, per considerare sacrifici favorevoli)
        
    Returns:
        True se il pezzo è sicuro, False altrimenti
    """
    piece = board.piece_at(square)
    if not piece:
        return True
    
    # Ottieni attaccanti diretti e transitivi
    direct_attackers = get_attacking_moves(board, square, not piece.color, transitive=False)
    all_attackers = get_attacking_moves(board, square, not piece.color, transitive=True)
    defenders = get_defending_moves(board, square, piece.color)
    
    # Sacrifici favorevoli (torre per 2 pezzi minori) sono considerati sicuri
    if played_move:
        captured_piece = board.piece_at(played_move.to_square)
        if (captured_piece and 
            piece.piece_type == chess.ROOK and
            PIECE_VALUES.get(captured_piece.piece_type, 0) == PIECE_VALUES[chess.KNIGHT] and
            len(all_attackers) == 1 and len(defenders) > 0 and
            len([a for a in all_attackers if board.piece_at(a) and 
                 PIECE_VALUES[board.piece_at(a).piece_type] == PIECE_VALUES[chess.KNIGHT]]) > 0):
            return True
    
    # Un pezzo con un attaccante diretto di valore inferiore non è sicuro
    for attacker_square in direct_attackers:
        attacker_piece = board.piece_at(attacker_square)
        if attacker_piece and PIECE_VALUES[attacker_piece.piece_type] < PIECE_VALUES[piece.piece_type]:
            return False
    
    # Un pezzo che non ha più attaccanti che difensori è sicuro
    if len(all_attackers) <= len(defenders):
        return True
    
    # Un pezzo di valore inferiore a qualsiasi attaccante diretto,
    # e con qualsiasi difensore di valore inferiore a tutti gli attaccanti diretti, è sicuro
    if direct_attackers:
        lowest_attacker_value = min(
            PIECE_VALUES[board.piece_at(sq).piece_type] 
            for sq in direct_attackers 
            if board.piece_at(sq)
        )
        
        if (PIECE_VALUES[piece.piece_type] < lowest_attacker_value and
            any(board.piece_at(def_sq) and 
                PIECE_VALUES[board.piece_at(def_sq).piece_type] < lowest_attacker_value
                for def_sq in defenders)):
            return True
    
    # Un pezzo difeso da un pedone è generalmente sicuro
    if any(board.piece_at(def_sq) and board.piece_at(def_sq).piece_type == chess.PAWN 
           for def_sq in defenders):
        return True
    
    return False

def get_unsafe_pieces(board: chess.Board, color: chess.Color, played_move: Optional[chess.Move] = None) -> List[chess.Square]:
    """
    Restituisce una lista di case contenenti pezzi non sicuri del colore specificato.
    
    Args:
        board: Scacchiera corrente
        color: Colore dei pezzi da analizzare
        played_move: Mossa giocata (opzionale)
        
    Returns:
        Lista delle caselle contenenti pezzi non sicuri
    """
    captured_piece_value = 0
    if played_move:
        # Determina se la mossa è una cattura controllando la casella di destinazione
        captured_piece = board.piece_at(played_move.to_square)
        if captured_piece:
            captured_piece_value = PIECE_VALUES.get(captured_piece.piece_type, 0)
    
    unsafe_pieces = []
    
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if (piece and piece.color == color and 
            piece.piece_type not in [chess.PAWN, chess.KING] and
            PIECE_VALUES[piece.piece_type] > captured_piece_value and
            not is_piece_safe(board, square, played_move)):
            unsafe_pieces.append(square)
    
    return unsafe_pieces