# stockfish_manager.py
"""
Modulo per la gestione centralizzata delle istanze di Stockfish.
Questo modulo implementa un pattern singleton per evitare la creazione
di multiple istanze di Stockfish e ottimizzare l'uso delle risorse.
"""

from stockfish import Stockfish
from src.config import STOCKFISH_PATH, MATE_VALUE_BASE, MATE_VALUE_DECREMENT
from typing import Optional, Dict, Any


class StockfishManager:
    """
    Gestisce le istanze di Stockfish in modo centralizzato.
    Implementa un pattern singleton per riutilizzare le istanze quando possibile.
    """
    
    _instances = {}
    
    @classmethod
    def get_instance(cls, depth: int = 15, threads: int = 1, key: str = "default") -> Optional[Stockfish]:
        """
        Ottiene un'istanza di Stockfish con i parametri specificati.
        
        Args:
            depth: Profondità di analisi
            threads: Numero di thread da utilizzare
            key: Chiave identificativa per l'istanza (default, analyzer, player, etc.)
            
        Returns:
            Un'istanza di Stockfish configurata, o None se non disponibile
        """
        instance_key = f"{key}_{depth}_{threads}"
        
        if instance_key not in cls._instances:
            try:
                instance = Stockfish(
                    path=STOCKFISH_PATH,
                    parameters={"Threads": threads}
                )
                instance.set_depth(depth)
                cls._instances[instance_key] = instance
            except (FileNotFoundError, PermissionError) as e:
                print(f"Errore nell'inizializzazione di Stockfish: {e}")
                return None
        
        return cls._instances[instance_key]
    
    @classmethod
    def create_new_instance(cls, depth: int = 15, threads: int = 1) -> Optional[Stockfish]:
        """
        Crea una nuova istanza di Stockfish senza cache.
        Utile per operazioni che richiedono un'istanza dedicata.
        
        Args:
            depth: Profondità di analisi
            threads: Numero di thread da utilizzare
            
        Returns:
            Una nuova istanza di Stockfish, o None se non disponibile
        """
        try:
            instance = Stockfish(
                path=STOCKFISH_PATH,
                parameters={"Threads": threads}
            )
            instance.set_depth(depth)
            return instance
        except (FileNotFoundError, PermissionError) as e:
            print(f"Errore nella creazione di una nuova istanza Stockfish: {e}")
            return None
    
    @classmethod
    def clear_cache(cls):
        """Pulisce la cache delle istanze di Stockfish."""
        cls._instances.clear()
    
    @classmethod
    def is_available(cls) -> bool:
        """
        Verifica se Stockfish è disponibile sul sistema.
        
        Returns:
            True se Stockfish è disponibile, False altrimenti
        """
        try:
            test_instance = Stockfish(path=STOCKFISH_PATH)
            return True
        except (FileNotFoundError, PermissionError):
            return False


def eval_to_centipawns(evaluation: Dict[str, Any]) -> int:
    """
    Converte una valutazione di Stockfish in centipawns.
    Funzione di utilità per standardizzare le conversioni.
    
    Args:
        evaluation: Dizionario con 'type' ('cp' o 'mate') e 'value'
        
    Returns:
        Valore in centipawns (int)
    """
    if not evaluation:
        return 0
    
    eval_type = evaluation.get('type')
    value = evaluation.get('value', 0)
    
    if eval_type == 'cp':
        return value if value is not None else 0
    elif eval_type == 'mate':
        if value == 0 or value is None:
            return 0
        # Mate positivo = vantaggio bianco, negativo = vantaggio nero
        return (MATE_VALUE_BASE - abs(value) * MATE_VALUE_DECREMENT) * (1 if value > 0 else -1)
    
    return 0


def convert_top_move_to_cp(eval_info: Dict[str, Any]) -> int:
    """
    Converte una valutazione da get_top_moves() in centipawns.
    Gestisce il formato specifico delle top moves di Stockfish.
    
    Args:
        eval_info: Dizionario con 'Centipawn' o 'Mate' e 'Move'
        
    Returns:
        Valore in centipawns (int)
    """
    if not eval_info:
        return 0
    
    # Gestisce il formato delle top moves di Stockfish
    if 'Centipawn' in eval_info:
        cp_val = eval_info['Centipawn']
        return cp_val if cp_val is not None else 0
    elif 'Mate' in eval_info:
        mate_val = eval_info['Mate']
        if mate_val == 0 or mate_val is None:
            return 0
        return (MATE_VALUE_BASE - abs(mate_val) * MATE_VALUE_DECREMENT) * (1 if mate_val > 0 else -1)
    
    # Fallback: prova il formato standard
    return eval_to_centipawns(eval_info)