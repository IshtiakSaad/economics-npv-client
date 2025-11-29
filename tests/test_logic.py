import pytest
import numpy as np
from logic import calculate_lcm, generate_cash_flows, calculate_npv

def test_lcm_calculation():
    assert calculate_lcm([3, 4]) == 12
    assert calculate_lcm([2, 5]) == 10
    assert calculate_lcm([5, 5]) == 5
    assert calculate_lcm([]) == 0

def test_cash_flow_length():
    # A 3-year project over a 12-year study period should have 13 entries (Year 0 to 12)
    flows = generate_cash_flows(
        investment=100, revenue=10, cost=0, savings=0, 
        salvage=0, replacement=100, life_span=3, study_period=12
    )
    assert len(flows) == 13

def test_npv_basic():
    # Investing $100 today, getting $110 next year at 10% interest
    # NPV should be exactly 0
    flows = np.array([-100.0, 110.0])
    npv = calculate_npv(flows, marr_percent=10.0)
    assert npv == pytest.approx(0.0, abs=0.01)

def test_replacement_cost_logic():
    # Life span 2, Study 4. 
    # Year 0: Inv
    # Year 2: Replacement occurs
    # Year 4: End of study, NO replacement
    flows = generate_cash_flows(
        investment=1000, revenue=0, cost=0, savings=0,
        salvage=0, replacement=1000, life_span=2, study_period=4
    )
    assert flows[2] == -1000 # Replacement happened
    assert flows[4] == 0     # No replacement at end of study