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
            amount = float(input("Enter total income: $"))
            deduction = float(input("Enter deduction or nothing: $") or '0')
        except ValueError:
            print("Quit")
            sys.exit()
        tax = single_tax_bracket_2021.tax(amount - max(deduction, standard_deduction_2021))
        print(f"${tax.tax_payed:.2f} of ${tax.real_taxable_amount():.2f} taxed")
        for i in range(len(tax.breakdown)):
            print(f"{single_tax_bracket_2021.tax_ranges[i]} = {tax.breakdown[i]}")
        print(f"Effective tax rate: {tax.real_effective_tax_rate():.2%}")


def test_investment():
    age = 25
    retire = 65
    die = 90
    ir = investment.simple_invest(40000, single_tax_bracket_2021, retirement=retire - age, death=die - age)
    # fig, (ax0,) = plt.subplots(1, 1)
    plt.plot(ir.get_years() + age, ir.get_end_balances())
    plt.show()
    print("=== start investing ===")
    for year in ir.year_results:
        print(f"{year.year + age} ${year.total_end_amount():.2f}")
        if year.year == retire - age - 1:
            print("=== retirement ===")
    print("=== dead ===")


test_investment()
