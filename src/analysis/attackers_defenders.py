# attackers_defenders.py
"""
Sistema avanzato per trovare attaccanti e difensori di una casella.
Implementa la logica per identificare attaccanti diretti, transitivi (batterie)
e difensori di un pezzo.
"""

import chess
from typing import List, Set, Optional

def get_attacking_moves(board: chess.Board, target_square: chess.Square, 
                       attacking_color: chess.Color, transitive: bool = True) -> List[chess.Square]:
    """
    Trova tutti i pezzi che attaccano una data casa, inclusi gli attaccanti transitivi
    (pezzi che potrebbero attaccare dopo che altri pezzi si muovono, come nelle batterie).
    
    Args:
        board: Scacchiera corrente
        target_square: Casella da analizzare
        attacking_color: Colore degli attaccanti
        transitive: Se True, include anche gli attaccanti transitivi
        
    Returns:
        Lista delle caselle contenenti pezzi attaccanti
    """
    # Attaccanti diretti
    direct_attackers = list(board.attackers(attacking_color, target_square))
    
    if not transitive:
        return direct_attackers
    
    # Per gli attaccanti transitivi, dobbiamo simulare la rimozione di pezzi
    # e vedere se si rivelano nuovi attaccanti (batterie)
    all_attackers = direct_attackers.copy()
    frontier = direct_attackers.copy()
    
    while frontier:
        current_attacker = frontier.pop()
        attacker_piece = board.piece_at(current_attacker)
        
        # Il re non può essere alla testa di una batteria
        if not attacker_piece or attacker_piece.piece_type == chess.KING:
            continue
        
        # Crea una copia della scacchiera e rimuovi il pezzo attaccante
        temp_board = board.copy()
        temp_board.remove_piece_at(current_attacker)
        
        # Trova nuovi attaccanti rivelati
        new_attackers = list(temp_board.attackers(attacking_color, target_square))
        revealed_attackers = [sq for sq in new_attackers if sq not in all_attackers]
        
        # Aggiungi i nuovi attaccanti alla lista e alla frontiera per ulteriore ricorsione
        all_attackers.extend(revealed_attackers)
        frontier.extend(revealed_attackers)
    
    return all_attackers

def get_defending_moves(board: chess.Board, target_square: chess.Square, 
                       defending_color: chess.Color, transitive: bool = True) -> List[chess.Square]:
    """
    Trova tutti i pezzi che difendono una data casa.
    La logica è più complessa: simula la cattura del pezzo e trova chi può ricatturare.
    
    Args:
        board: Scacchiera corrente
        target_square: Casella da analizzare
        defending_color: Colore dei difensori
        transitive: Se True, include anche i difensori transitivi
        
    Returns:
        Lista delle caselle contenenti pezzi difensori
    """
    piece = board.piece_at(target_square)
    if not piece:
        return []
    
    # Ottieni gli attaccanti del pezzo
    attackers = get_attacking_moves(board, target_square, not defending_color, transitive=False)
    
    if not attackers:
        # Se non ci sono attaccanti, "capovolgi" il colore del pezzo e trova gli attaccanti
        # Questo simula chi potrebbe difendere se il pezzo fosse attaccato
        temp_board = board.copy()
        temp_board.remove_piece_at(target_square)
        temp_board.set_piece_at(target_square, chess.Piece(piece.piece_type, not piece.color))
        return list(temp_board.attackers(defending_color, target_square))
    
    # Trova il set più piccolo di ricatturatori simulando ogni possibile cattura
    smallest_recapture_set = None
    min_recapturers = float('inf')
    
    for attacker_square in attackers:
        attacker_piece = board.piece_at(attacker_square)
        if not attacker_piece:
            continue
        
        # Simula la cattura
        temp_board = board.copy()
        temp_board.remove_piece_at(target_square)
        temp_board.set_piece_at(target_square, attacker_piece)
        temp_board.remove_piece_at(attacker_square)
        
        # Trova chi può ricatturare
        recapturers = get_attacking_moves(temp_board, target_square, defending_color, transitive)
        
        if len(recapturers) < min_recapturers:
            min_recapturers = len(recapturers)
            smallest_recapture_set = recapturers
    
    return smallest_recapture_set if smallest_recapture_set is not None else []