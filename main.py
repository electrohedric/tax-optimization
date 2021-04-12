import sys

import matplotlib.pyplot as plt

import investment
from tax_brackets import TaxBracket, TaxRange

single_tax_ranges_2021 = (
    TaxRange(0, 9950, 0.10),
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
            amount = float(input("Enter income: $"))
            deduction = float(input("Enter deduction or nothing: $") or '0')
        except ValueError:
            print("Quit")
            sys.exit()
        tax = single_tax_bracket_2021.tax(amount - max(deduction, standard_deduction_2021))
        print(f"${tax.tax_paid:.2f} of ${tax.real_taxable_amount():.2f} taxed")
        for i in range(len(tax.breakdown)):
            print(f"{single_tax_bracket_2021.tax_ranges[i]} = {tax.breakdown[i]}")
        print(f"Effective tax rate: {tax.real_effective_tax_rate():.2%}")


def test_investment():
    age = 25
    retire = 65
    die = 90
    ir = investment.simple_invest(40000, single_tax_bracket_2021, retirement=retire - age, death=die - age, trad_alloc_percent=5, roth_alloc_percent=5)
    fig, (ax0, ax1) = plt.subplots(2, 1)
    ax0.plot(ir.get_years() + age, ir.get_net_worths())
    ax1.plot(ir.get_years() + age, ir.get_taxes_paid())
    plt.show()
    print("=== start investing ===")
    for year in ir.year_results:
        print(f"AGE = {year.year + age}, "
              f"Net worth = ${year.net_worth():.2f}, "
              f"Taxes paid = ${year.income.income_tax.tax_paid:.2f}, "
              f"Total income = ${year.income.total_income:.2f}")
        if year.year == retire - age - 1:
            print("=== retirement ===")
    print("=== dead ===")
    print(f"Total taxes paid = ${ir.get_taxes_paid().sum():.2f}")


test_investment()
