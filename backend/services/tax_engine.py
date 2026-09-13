def calculate_withholding_tax(gross_amount: float, tax_rate: float = 0.03) -> dict:
    tax_amount = round(gross_amount * tax_rate, 2)
    net_amount = round(gross_amount - tax_amount, 2)
    return {
        "gross_amount": round(gross_amount, 2),
        "tax_amount": tax_amount,
        "net_amount": net_amount
    }
