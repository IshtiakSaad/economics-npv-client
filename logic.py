import math
import numpy as np
import pandas as pd
from typing import List, Dict, Any

def calculate_lcm(numbers: List[int]) -> int:
    """
    Calculates the Least Common Multiple (LCM) for a list of integers.
    Returns 0 if list is empty.
    """
    if not numbers:
        return 0
    # Ensure all numbers are integers
    integers = [int(n) for n in numbers if n > 0]
    if not integers:
        return 0
    return math.lcm(*integers)

def generate_cash_flows(
    investment: float,
    revenue: float,
    cost: float,
    savings: float,
    salvage: float,
    replacement: float,
    life_span: int,
    study_period: int
) -> np.ndarray:
    """
    Generates a cash flow array for the entire study period.
    """
    if life_span <= 0:
        return np.zeros(study_period + 1)
        
    net_annual = revenue - cost + savings
    flows = np.zeros(study_period + 1)
    
    # Year 0: Initial Investment (Negative)
    flows[0] = -abs(investment)
    
    for t in range(1, study_period + 1):
        # 1. Regular Operation
        flows[t] += net_annual
        
        # 2. End of Life Cycle Events
        if t % life_span == 0:
            # Add Salvage Value
            flows[t] += salvage
            
            # Subtract Replacement Cost (unless it's the very end of study)
            if t != study_period:
                flows[t] -= replacement
                
    return flows

def calculate_npv(flows: np.ndarray, marr_percent: float) -> float:
    """
    Calculates Net Present Value (NPV).
    """
    r = marr_percent / 100.0
    # Create a discount factor array [1, (1+r)^1, (1+r)^2, ...]
    time_indices = np.arange(len(flows))
    discount_factors = (1 + r) ** time_indices
    
    # Vectorized calculation (faster than loops)
    npv = np.sum(flows / discount_factors)
    return float(npv)