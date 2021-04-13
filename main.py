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


def plot_investment(ir: investment.InvestmentResult, age: int, retire: int, ax0, ax1, ax2, ax3, ax4, title: str):

    ax0.plot(ir.get_years() + age, ir.get_net_worths(), label=title)
    ax0.set_title("Net worth")
    ax0.legend()
    ax1.plot(ir.get_years() + age, ir.get_total_roth_assets())
    ax1.set_title("Roth assets")
    ax2.plot(ir.get_years() + age, ir.get_total_trad_assets())
    ax2.set_title("Traditional assets")
    ax3.plot(ir.get_years() + age, ir.get_taxes_paid())
    ax3.set_title("Taxes paid")
    ax4.plot(ir.get_years() + age, ir.get_total_incomes())
    ax4.set_title("Total income")
    print("=== start investing ===")
    for year in ir.year_results:
        if year.year < 60:
            continue
        print(f"AGE = {year.year + age}, "
              f"Net worth = ${year.net_worth():,.2f}, "
              f"Taxes paid = ${year.income.income_tax.tax_paid:,.2f}, "
              f"Total income = ${year.income.total_income:,.2f}")
        if year.year == retire - age - 1:
            print("=== retirement ===")
    print("=== dead ===")
    print(f"Total taxes paid = ${ir.get_taxes_paid().sum():,.2f}")
    print(f"Total income = ${ir.get_total_incomes().sum():,.2f}")
    print(f"")


def test_investment():
    age = 25
    retire = 65
    die = 90
    income = 30000
    rate = 8
    split = 6.5
    ir_roth = investment.simple_invest(income, single_tax_bracket_2021, retirement=retire - age, death=die - age, trad_alloc_percent=0, roth_alloc_percent=split, return_rate=rate)
    ir_trad = investment.simple_invest(income, single_tax_bracket_2021, retirement=retire - age, death=die - age, trad_alloc_percent=split, roth_alloc_percent=0, return_rate=rate)
    ir_5050 = investment.simple_invest(income, single_tax_bracket_2021, retirement=retire - age, death=die - age, trad_alloc_percent=split/2, roth_alloc_percent=split/2, return_rate=rate)
    fig, (ax0, ax1, ax2, ax3, ax4) = plt.subplots(5, 1)
    plot_investment(ir_roth, age, retire, ax0, ax1, ax2, ax3, ax4, "Roth")
    plot_investment(ir_trad, age, retire, ax0, ax1, ax2, ax3, ax4, "Trad")
    plot_investment(ir_5050, age, retire, ax0, ax1, ax2, ax3, ax4, "50/50")
    plt.show()


test_investment()
