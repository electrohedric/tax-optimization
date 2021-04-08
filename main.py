import sys

import matplotlib.pyplot as plt
import numpy as np

import investment

from tax_brackets import TaxBracket, TaxRange

single_tax_ranges_2021 = (
    TaxRange(0,   9950, 0.10),
    TaxRange(9950, 40525, 0.12),
    TaxRange(40525, 86375, 0.22),
    TaxRange(86375, 164925, 0.24),
    TaxRange(164925, 209425, 0.32),
    TaxRange(209425, 523600, 0.35),
    TaxRange(523600, float('inf'), 0.37),
)
single_tax_bracket_2021 = TaxBracket(*single_tax_ranges_2021)
standard_deduction_2021 = 12550.00


def test_tax_bracket():
    while True:
        try:
            amount = float(input("Enter total income: $"))
            deduction = float(input("Enter deduction or nothing: $") or '0')
        except ValueError:
            print("Quit")
            sys.exit()
        tax = single_tax_bracket_2021.tax(amount - max(deduction, standard_deduction_2021))
        print(f"${tax.total_taxed:.2f} of ${tax.real_taxable_amount():.2f} taxed")
        for i in range(len(tax.breakdown)):
            print(f"{single_tax_bracket_2021.tax_ranges[i]} = {tax.breakdown[i]}")
        print(f"Effective tax rate: {tax.real_effective_tax_rate():.2%}")


def test_investment():
    return_rates = np.random.normal(np.full(40, 0.07), 0.07)
    contributions = np.full(40, 1000)
    ir = investment.invest(0, 40, return_rates, contributions)
    fig, (ax0, ax1) = plt.subplots(2, 1)
    ax0.plot(ir.get_years(), ir.get_end_balances())
    ax1.plot(ir.get_years(), return_rates * 100)
    plt.show()
    for balance in ir.get_end_balances():
        print(f"${balance:.2f}")
    print(ir.get_final_end_balance())


test_investment()
