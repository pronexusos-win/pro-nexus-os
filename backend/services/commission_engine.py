from typing import List, Dict

def calculate_unilevel_plan(sale_amount: float) -> List[Dict]:
    rates = [0.10, 0.05, 0.03, 0.02]  # ชั้นที่ 1-4
    payouts = []
    for level, rate in enumerate(rates, start=1):
        gross = sale_amount * rate
        payouts.append({
            "level": level,
            "rate_percent": rate * 100,
            "gross_amount": gross
        })
    return payouts
