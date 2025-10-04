# config.py
"""
File di configurazione per l'applicazione Chess.
Contiene tutte le costanti, i percorsi, i colori e le impostazioni dell'AI.
"""

# --- COSTANTI DI CONFIGURAZIONE INTERFACCIA ---
BOARD_SIZE = 720  # Dimensione della scacchiera in pixel
SQUARE_SIZE = BOARD_SIZE // 8  # Dimensione di ogni casella
ASSET_PATH = "assets"  # Percorso base per le risorse
PIECES_PATH = "assets/pieces"  # Percorso per le immagini dei pezzi
CLASSIFICATIONS_PATH = "assets/classifications"  # Percorso per le immagini di classificazione
THEME_APP = "litera"  # Tema dell'interfaccia grafica
BOARD_COLORS = ("#EADAB9", "#B58863")  # Colori delle caselle (chiaro, scuro)
STOCKFISH_PATH = "engine/stockfish.exe"  # Percorso dell'eseguibile Stockfish

# --- COSTANTI PER L'INTERFACCIA UTENTE ---
# Dimensioni finestre
MENU_WINDOW_GEOMETRY = "500x650"
GAME_WINDOW_GEOMETRY = "1150x800"

# Ritardi e timing (in millisecondi)
EVAL_QUEUE_PROCESS_DELAY = 100
AI_MOVE_DELAY_CVC = 1000
AI_MOVE_DELAY_NORMAL = 500
REVIEW_QUEUE_PROCESS_DELAY = 100
ANIMATION_DURATION_MS = 300
ANIMATION_DELAY_MS = 10

# Valori di default
DEFAULT_AI_LEVEL = 5
DEFAULT_PLAYER_COLOR = "white"
STOCKFISH_ANALYZER_THREADS = 1
MAIN_CONTAINER_PADDING = 10
TOP_MOVES_COUNT = 3
ANALYSIS_DEPTH = 15

# --- COSTANTI PER LA BARRA DI VALUTAZIONE ---
EVAL_BAR_WIDTH = 40
EVAL_BAR_ANIMATION_SPEED = 0.1
EVAL_BAR_ANIMATION_FPS = 60
EVAL_BAR_ANIMATION_DELAY = 16
EVAL_BAR_CAP_VALUE = 800
EVAL_BAR_THRESHOLD = 0.001
EVAL_CENTIPAWN_DIVISOR = 100.0

# --- COSTANTI PER I COLORI DELL'INTERFACCIA ---
COLOR_EVAL_BAR_BG = "#333"
COLOR_EVAL_BAR_TOP_BG = "#111"
COLOR_EVAL_BAR_TOP_FG = "white"
COLOR_EVAL_BAR_BOTTOM_BG = "#FFF"
COLOR_EVAL_BAR_BOTTOM_FG = "black"
COLOR_LEGAL_MOVE = "#64A455"
COLOR_LAST_MOVE = "#f0e68c"
COLOR_CHECK = "#FF6347"
COLOR_ARROW_DEFAULT = "#18844D"
COLOR_HIGHLIGHT_DEFAULT = "#F6F669"
PROMOTION_OVERLAY_COLOR = "#000000"
PROMOTION_OVERLAY_STIPPLE = "gray50"

# --- COSTANTI PER LA SCACCHIERA ---
LEGAL_MOVE_RADIUS_EMPTY = 6
LEGAL_MOVE_RADIUS_CAPTURE = 2
LEGAL_MOVE_RING_WIDTH = 8
ARROW_WIDTH_RATIO = 0.15
TIME_TO_MILLISECONDS = 1000
CLASSIFICATION_ICON_SIZE_RATIO = 0.25
COORDINATE_FONT_SIZE_DIVISOR = 5.5
COORDINATE_PADDING = 5
BOARD_RANKS = "87654321"
BOARD_FILES = "abcdefgh"

# --- LIVELLI DI DIFFICOLTÀ DELL'AI ---
# Ogni livello definisce: skill level (-20 a 20), profondità di ricerca, tempo di calcolo (ms)
AI_LEVELS = {
    1: {"skill": -9, "depth": 2, "movetime": 50},    # Principiante
    2: {"skill": -5, "depth": 3, "movetime": 100},   # Facile
    3: {"skill": -1, "depth": 4, "movetime": 150},   # Medio-Facile
    4: {"skill":  3, "depth": 5, "movetime": 200},   # Medio
    5: {"skill":  7, "depth": 5, "movetime": 300},   # Medio-Difficile
    6: {"skill": 11, "depth": 8, "movetime": 400},   # Difficile
    7: {"skill": 16, "depth": 13, "movetime": 500},  # Molto Difficile
    8: {"skill": 20, "depth": 22, "movetime": 1000}  # Esperto
}

# --- COSTANTI PER L'ANALISI DELLE MOSSE ---

# Soglie di valutazione per la classificazione delle mosse (in centipawns)
EVAL_THRESHOLDS = {
    'brilliant': -200,   # Mossa geniale (sacrificio brillante)
    'great': -100,       # Grande mossa (critica)
    'best': 5,           # Mossa migliore
    'excellent': 20,     # Mossa eccellente
    'good': 50,          # Mossa buona
    'inaccuracy': 100,   # Imprecisione
    'mistake': 200,      # Errore
}

# Etichette descrittive per ogni classificazione
EVAL_CLASSIFICATIONS = {
    'brilliant': "Geniale (!!)",
    'great': "Grande Mossa (!)",
    'best': "Migliore (=)",
    'excellent': "Eccellente",
    'good': "Buona",
    'inaccuracy': "Imprecisione (?!)",
    'mistake': "Errore (?)",
    'blunder': "Svarione (??)",
    'forced': "Forzata",
    'theory': "Teorica"
}

# Colori associati a ogni classificazione
EVAL_COLORS = {
    'brilliant': "#00BFFF",   # Azzurro brillante
    'great': "#1E90FF",       # Blu dodger
    'best': "#90EE90",        # Verde chiaro
    'excellent': "#32CD32",   # Verde lime
    'good': "#006400",        # Verde scuro
    'inaccuracy': "#FFFF00",  # Giallo
    'mistake': "#FFA500",     # Arancione
    'blunder': "#FF0000",     # Rosso
    'forced': "#800080",      # Viola
    'theory': "#4B0082"       # Indaco
}

# Mappatura tra classificazioni e nomi file delle immagini
CLASSIFICATION_IMAGES = {
    'brilliant': 'brilliant.png',
    'great': 'critical.png',      # "great" usa l'immagine "critical"
    'best': 'best.png',
    'excellent': 'excellent.png',
    'good': 'okay.png',           # "good" usa l'immagine "okay"
    'inaccuracy': 'inaccuracy.png',
    'mistake': 'mistake.png',
    'blunder': 'blunder.png',
    'forced': 'forced.png',
    'theory': 'best.png'          # "theory" usa l'immagine "best" come fallback
}

# --- COSTANTI PER LA CLASSIFICAZIONE AVANZATA DELLE MOSSE ---
SACRIFICE_MIN_VALUE = 100  # Valore minimo per considerare un sacrificio (centipawns)
BRILLIANT_MAX_LOSS = 150  # Perdita massima per una mossa brillante (centipawns)
GREAT_MOVE_GAP = 50  # Gap minimo con la seconda migliore per essere "grande"
GREAT_MOVE_ADVANTAGE = 100  # Vantaggio minimo per una mossa grande
GREAT_MOVE_TACTICAL_ADVANTAGE = 150  # Vantaggio minimo per una mossa tattica grande
GREAT_MOVE_LOSS_THRESHOLD = 30  # Perdita massima per considerare una mossa quasi ottimale
CRITICAL_THRESHOLD = 100  # Soglia per mosse critiche (centipawns)
ALTERNATIVE_BAD_THRESHOLD = -100  # Soglia per alternative cattive (centipawns)

# --- COSTANTI PER LA CONVERSIONE DELLE VALUTAZIONI ---
MATE_VALUE_BASE = 30000
MATE_VALUE_DECREMENT = 100

# --- VALORI DEI PEZZI (in centipawn) ---
# Importato da chess per evitare dipendenze circolari
# Questi valori sono usati in piece_safety.py e altri moduli di analisi
import chess
PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000
}

# --- COSTANTI PER L'ANALISI DELLE MOSSE CRITICHE ---
CRITICAL_EVAL_THRESHOLD = 700  # Soglia per posizioni completamente vincenti (centipawns)

# --- COSTANTI PER IL CALCOLO DELL'ACCURATEZZA ---
WINNING_CHANCES_MATE_THRESHOLD = 32000  # Soglia per considerare una posizione come matto
WINNING_CHANCES_MULTIPLIER = -0.00368208  # Moltiplicatore per la funzione sigmoidale
ACCURACY_FORMULA_A = 103.1668100711649  # Coefficiente A nella formula di accuratezza
ACCURACY_FORMULA_B = -0.04354415386753951  # Coefficiente B nella formula di accuratezza
ACCURACY_FORMULA_C = -3.166924740191411  # Coefficiente C nella formula di accuratezza
VOLATILITY_MAX_WEIGHT = 12  # Peso massimo per la volatilità
VOLATILITY_MIN_WEIGHT = 0.5  # Peso minimo per la volatilità
VOLATILITY_WINDOW_SIZE = 2  # Dimensione della finestra per il calcolo della volatilità
