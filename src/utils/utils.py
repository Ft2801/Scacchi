# utils.py
"""
Modulo di utilità con funzioni helper per ridurre la duplicazione del codice.
Contiene funzioni comuni utilizzate in più parti dell'applicazione.
"""

import chess
from typing import Dict, Any, Optional


def get_turn_color_name(turn: chess.Color) -> str:
    """
    Converte il turno in nome del colore in italiano.
    
    Args:
        turn: Colore del turno (chess.WHITE o chess.BLACK)
        
    Returns:
        Nome del colore ("Bianco" o "Nero")
    """
    return "Bianco" if turn == chess.WHITE else "Nero"


def format_eval_display(eval_dict: Optional[Dict[str, Any]]) -> str:
    """
    Formatta una valutazione per la visualizzazione.
    
    Args:
        eval_dict: Dizionario con 'type' ('cp' o 'mate') e 'value'
        
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
        pawn_value = value / 100.0
        if pawn_value < 0:
            return f"{-pawn_value:.1f}"
        return f"{pawn_value:+.1f}"
    
    return "0.0"


def is_ai_turn(game_mode: str, current_turn: chess.Color, player_color: Optional[chess.Color]) -> bool:
    """
    Determina se è il turno dell'AI.
    
    Args:
        game_mode: Modalità di gioco ('pvp', 'pvc', 'cvc')
        current_turn: Turno corrente
        player_color: Colore del giocatore (None in modalità pvp/cvc)
        
    Returns:
        True se è il turno dell'AI, False altrimenti
    """
    if game_mode == 'cvc':
        return True
    if game_mode == 'pvc' and player_color is not None:
        return current_turn != player_color
    return False


def safe_widget_exists(obj, attr_name: str) -> bool:
    """
    Verifica se un attributo widget esiste ed è valido su un oggetto.
    
    Args:
        obj: Oggetto che contiene il widget
        attr_name: Nome dell'attributo widget da verificare
        
    Returns:
        True se l'attributo esiste ed è un widget valido, False altrimenti
    """
    try:
        if not hasattr(obj, attr_name):
            return False
        widget = getattr(obj, attr_name)
        return hasattr(widget, 'winfo_exists') and widget.winfo_exists()
    except:
        return False


def clamp(value: float, min_value: float, max_value: float) -> float:
    """
    Limita un valore tra un minimo e un massimo.
    
    Args:
        value: Valore da limitare
        min_value: Valore minimo
        max_value: Valore massimo
        
    Returns:
        Valore limitato tra min_value e max_value
    """
    return max(min_value, min(max_value, value))


def get_piece_symbol(piece: chess.Piece) -> str:
    """
    Ottiene il simbolo Unicode di un pezzo.
    
    Args:
        piece: Pezzo di scacchi
        
    Returns:
        Simbolo Unicode del pezzo
    """
    symbols = {
        (chess.PAWN, chess.WHITE): '♙',
        (chess.KNIGHT, chess.WHITE): '♘',
        (chess.BISHOP, chess.WHITE): '♗',
        (chess.ROOK, chess.WHITE): '♖',
        (chess.QUEEN, chess.WHITE): '♕',
        (chess.KING, chess.WHITE): '♔',
        (chess.PAWN, chess.BLACK): '♟',
        (chess.KNIGHT, chess.BLACK): '♞',
        (chess.BISHOP, chess.BLACK): '♝',
        (chess.ROOK, chess.BLACK): '♜',
        (chess.QUEEN, chess.BLACK): '♛',
        (chess.KING, chess.BLACK): '♚',
    }
    return symbols.get((piece.piece_type, piece.color), '')


def square_to_coords(square: chess.Square) -> tuple:
    """
    Converte un indice di casella in coordinate (riga, colonna).
    
    Args:
        square: Indice della casella (0-63)
        
    Returns:
        Tupla (riga, colonna) dove 0,0 è a1
    """
    return divmod(square, 8)


def coords_to_square(row: int, col: int) -> chess.Square:
    """
    Converte coordinate (riga, colonna) in indice di casella.
    
    Args:
        row: Riga (0-7)
        col: Colonna (0-7)
        
    Returns:
        Indice della casella (0-63)
    """
    return row * 8 + col


def get_ai_level_for_turn(game_mode, board_turn, pvc_ai_level, ai_white_level, ai_black_level):
    """
    Determina il livello AI da usare in base alla modalità di gioco e al turno.
    
    Args:
        game_mode: Modalità di gioco ('pvc', 'cvc', 'pvp')
        board_turn: Turno corrente (chess.WHITE o chess.BLACK)
        pvc_ai_level: Livello AI per modalità PvC
        ai_white_level: Livello AI per il bianco in modalità CvC
        ai_black_level: Livello AI per il nero in modalità CvC
        
    Returns:
        Livello AI da utilizzare
    """
    if game_mode == 'pvc':
        return pvc_ai_level
    elif game_mode == 'cvc':
        return ai_white_level if board_turn == chess.WHITE else ai_black_level
    return 1  # Default


def create_pgn_headers(game_mode, player_color, ai_white_level, ai_black_level, pvc_ai_level, board_result):
    """
    Crea gli header PGN per la partita.
    
    Args:
        game_mode: Modalità di gioco ('pvc', 'cvc', 'pvp')
        player_color: Colore del giocatore (chess.WHITE o chess.BLACK)
        ai_white_level: Livello AI bianco
        ai_black_level: Livello AI nero
        pvc_ai_level: Livello AI per PvC
        board_result: Risultato della partita
        
    Returns:
        Dizionario con gli header PGN
    """
    import datetime
    
    headers = {
        "Event": "Partita Locale",
        "Site": "Scacchi Moderni App",
        "Date": datetime.date.today().strftime("%Y.%m.%d"),
        "Result": board_result
    }
    
    if game_mode == 'cvc':
        headers["White"] = f"Stockfish Livello {ai_white_level}"
        headers["Black"] = f"Stockfish Livello {ai_black_level}"
    elif game_mode == 'pvc':
        headers["White"] = "Giocatore" if player_color == chess.WHITE else f"Stockfish Livello {pvc_ai_level}"
        headers["Black"] = "Giocatore" if player_color == chess.BLACK else f"Stockfish Livello {pvc_ai_level}"
    else:
        headers["White"] = "Giocatore Bianco"
        headers["Black"] = "Giocatore Nero"
    
    return headers


def build_board_from_moves(moves, move_index):
    """
    Ricostruisce una scacchiera fino a un determinato indice di mossa.
    
    Args:
        moves: Lista di mosse
        move_index: Indice fino al quale ricostruire (incluso)
        
    Returns:
        Oggetto chess.Board con la posizione dopo la mossa specificata
    """
    board = chess.Board()
    for i in range(move_index + 1):
        board.push(moves[i])
    return board


def calculate_player_accuracy(accuracies, win_chances, is_white):
    """
    Calcola l'accuratezza finale per un giocatore.
    
    Args:
        accuracies: Lista delle accuratezze delle mosse del giocatore
        win_chances: Lista delle probabilità di vittoria per ogni posizione
        is_white: True se si calcola per il bianco, False per il nero
        
    Returns:
        Accuratezza finale arrotondata a 1 decimale, o 0 se non ci sono mosse
    """
    from src.analysis.accuracy_calculator import calculate_final_accuracy
    
    if not accuracies:
        return 0.0
    
    _, _, final_accuracy = calculate_final_accuracy(accuracies, win_chances, is_white)
    return round(final_accuracy, 1)


def load_and_resize_image(filepath, size, convert_mode="RGBA"):
    """
    Carica e ridimensiona un'immagine.
    
    Args:
        filepath: Percorso del file immagine
        size: Tupla (larghezza, altezza) o singolo valore per dimensioni quadrate
        convert_mode: Modalità di conversione dell'immagine (default: "RGBA")
        
    Returns:
        Oggetto Image ridimensionato, o None se il file non esiste
        
    Raises:
        FileNotFoundError: Se il file non esiste
    """
    from PIL import Image
    
    img = Image.open(filepath).convert(convert_mode)
    
    # Se size è un singolo valore, crea dimensioni quadrate
    if isinstance(size, int):
        size = (size, size)
    
    return img.resize(size, Image.LANCZOS)