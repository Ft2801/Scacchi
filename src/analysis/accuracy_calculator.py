# accuracy_calculator.py
"""
Modulo per il calcolo avanzato dell'accuratezza delle mosse.
Implementa formule standard per convertire valutazioni in probabilità di vittoria
e calcolare l'accuratezza delle mosse basata sulla perdita di probabilità.
"""

import math
from typing import List, Tuple
from src.config import (
    WINNING_CHANCES_MATE_THRESHOLD, WINNING_CHANCES_MULTIPLIER,
    ACCURACY_FORMULA_A, ACCURACY_FORMULA_B, ACCURACY_FORMULA_C,
    VOLATILITY_MAX_WEIGHT, VOLATILITY_MIN_WEIGHT, VOLATILITY_WINDOW_SIZE
)

def winning_chances_percent(cp_eval: int) -> float:
    """
    Converte una valutazione in centipawn in probabilità di vittoria (0-100%).
    Usa la formula standard degli scacchi basata su una funzione sigmoidale.
    
    Args:
        cp_eval: Valutazione in centipawns
        
    Returns:
        Probabilità di vittoria in percentuale (0-100)
    """
    if cp_eval >= WINNING_CHANCES_MATE_THRESHOLD:
        return 100.0
    if cp_eval <= -WINNING_CHANCES_MATE_THRESHOLD:
        return 0.0
    
    chances = 2 / (1 + math.exp(WINNING_CHANCES_MULTIPLIER * cp_eval)) - 1
    return 50 + 50 * max(min(chances, 1), -1)

def move_accuracy_percent(win_before: float, win_after: float) -> float:
    """
    Calcola l'accuratezza di una singola mossa basata sulla perdita di probabilità di vittoria.
    
    Args:
        win_before: Probabilità di vittoria prima della mossa (0-100)
        win_after: Probabilità di vittoria dopo la mossa (0-100)
        
    Returns:
        Accuratezza della mossa in percentuale (0-100)
    """
    if win_after >= win_before:
        return 100.0
    
    win_diff = win_before - win_after
    raw = ACCURACY_FORMULA_A * math.exp(ACCURACY_FORMULA_B * win_diff) + ACCURACY_FORMULA_C
    return max(min(raw + 1, 100), 0)

def harmonic_mean(values: List[float]) -> float:
    """
    Calcola la media armonica di una lista di valori.
    La media armonica penalizza maggiormente i valori bassi rispetto alla media aritmetica.
    
    Args:
        values: Lista di valori numerici
        
    Returns:
        Media armonica dei valori
    """
    if not values:
        return 0
    
    # Filtra i valori zero per evitare divisione per zero
    non_zero_values = [v for v in values if v > 0]
    if not non_zero_values:
        return 0
    
    reciprocal_sum = sum(1 / x for x in non_zero_values)
    return len(non_zero_values) / reciprocal_sum if reciprocal_sum else 0

def std_dev(sequence: List[float]) -> float:
    """
    Calcola la deviazione standard di una sequenza.
    
    Args:
        sequence: Lista di valori numerici
        
    Returns:
        Deviazione standard della sequenza
    """
    if not sequence:
        return VOLATILITY_MIN_WEIGHT  # Peso minimo se la sotto-sequenza è vuota
    
    mean = sum(sequence) / len(sequence)
    variance = sum((x - mean) ** 2 for x in sequence) / len(sequence)
    return math.sqrt(variance)

def volatility_weighted_mean(accuracies: List[float], win_chances: List[float], is_white: bool) -> float:
    """
    Calcola una media pesata per volatilità delle accuratezze.
    Le posizioni più volatili (con maggiore deviazione standard nelle probabilità di vittoria)
    ricevono un peso maggiore nel calcolo dell'accuratezza finale.
    
    Args:
        accuracies: Lista delle accuratezze delle mosse
        win_chances: Lista delle probabilità di vittoria per ogni posizione
        is_white: True se si calcola per il bianco, False per il nero
        
    Returns:
        Media pesata per volatilità delle accuratezze
    """
    if not accuracies:
        return 0
    
    weights = []
    for i in range(len(accuracies)):
        # Calcola l'indice base per il giocatore
        base_index = i * 2 + 1 if is_white else i * 2 + 2
        
        # Definisce una finestra intorno alla mossa corrente
        start_idx = max(base_index - VOLATILITY_WINDOW_SIZE, 0)
        end_idx = min(base_index + VOLATILITY_WINDOW_SIZE, len(win_chances) - 1)
        
        # Estrae la sotto-sequenza delle probabilità di vittoria
        sub_seq = win_chances[start_idx:end_idx + 1]
        
        # Calcola il peso basato sulla deviazione standard (volatilità)
        weight = max(min(std_dev(sub_seq), VOLATILITY_MAX_WEIGHT), VOLATILITY_MIN_WEIGHT)
        weights.append(weight)
    
    # Calcola la media pesata
    weighted_sum = sum(accuracies[i] * weights[i] for i in range(len(accuracies)))
    total_weight = sum(weights)
    
    return weighted_sum / total_weight if total_weight else 0

def calculate_final_accuracy(accuracies: List[float], win_chances: List[float], is_white: bool) -> Tuple[float, float, float]:
    """
    Calcola l'accuratezza finale usando sia la media armonica che quella pesata per volatilità.
    
    Args:
        accuracies: Lista delle accuratezze delle mosse
        win_chances: Lista delle probabilità di vittoria per ogni posizione
        is_white: True se si calcola per il bianco, False per il nero
        
    Returns:
        Tupla con (media_armonica, media_pesata, accuratezza_finale)
    """
    if not accuracies:
        return 0.0, 0.0, 0.0
    
    harmonic_mean_acc = harmonic_mean(accuracies)
    weighted_mean_acc = volatility_weighted_mean(accuracies, win_chances, is_white)
    
    # L'accuratezza finale è la media delle due medie
    final_accuracy = (harmonic_mean_acc + weighted_mean_acc) / 2
    
    return harmonic_mean_acc, weighted_mean_acc, final_accuracy