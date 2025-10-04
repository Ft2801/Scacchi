# critical_moves.py
"""
Modulo per l'identificazione di mosse critiche.
Una mossa critica è una mossa difficile da trovare che fa la differenza
tra mantenere un vantaggio e perderlo.
"""

import chess
from typing import Dict, Any, Optional
from src.config import CRITICAL_EVAL_THRESHOLD

def is_move_critical_candidate(previous_eval: Dict[str, Any], current_eval: Dict[str, Any], 
                              board_before: chess.Board) -> bool:
    """
    Determina se una mossa è candidata per essere critica.
    Le mosse facili da trovare o forzate non possono essere critiche.
    
    Args:
        previous_eval: Valutazione della posizione precedente
        current_eval: Valutazione della posizione corrente
        board_before: Scacchiera prima della mossa
        
    Returns:
        True se la mossa può essere critica, False altrimenti
    """
    # Ancora completamente vincente anche se questa mossa non fosse stata trovata
    if previous_eval.get('type') == 'cp':
        # Se la seconda migliore mossa era ancora >= +7.00, la mossa non è critica
        if previous_eval.get('value', 0) >= CRITICAL_EVAL_THRESHOLD:
            return False
    elif current_eval.get('type') == 'cp':
        if current_eval.get('value', 0) >= CRITICAL_EVAL_THRESHOLD:
            return False
    
    # Mosse in posizioni perdenti non possono essere critiche
    current_value = current_eval.get('value', 0)
    if current_eval.get('type') == 'cp' and current_value < 0:
        return False
    
    # Non permettere promozioni a donna come mosse critiche
    # (Questo dovrebbe essere controllato dal chiamante passando informazioni sulla mossa)
    
    # Non permettere mosse che devono essere giocate comunque per sfuggire allo scacco
    if board_before.is_check():
        return False
    
    return True