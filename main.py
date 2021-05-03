import sys

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import cm

import investment
from loader import load_tax_bracket

standard_deduction_2021 = 12550.00
single_tax_bracket_2021 = load_tax_bracket("data/2021/single_tax.csv")


def test_tax_bracket():
    while True:
        try:
            amount = float(input("Enter income: $"))
            deduction = float(input("Enter deduction or nothing: $") or '0')
        except ValueError:
            print("Quit")
            sys.exit()
        tax = single_tax_bracket_2021.tax(amount, max(deduction, standard_deduction_2021))
        print(f"${tax.tax_paid:.2f} of ${tax.real_taxable_amount():.2f} taxed")
        for i in range(len(tax.breakdown)):
            print(f"{single_tax_bracket_2021.tax_ranges[i]} = {tax.breakdown[i]}")
        print(f"Effective tax rate: {tax.real_effective_tax_rate():.2%}")


def plot_investment(ir: investment.InvestmentResult, age: int, retire: int, ax0, ax1, ax2, ax3, ax4, title: str):
    ax0.plot(ir.get_years() + age,
             ir.get_total_trad_assets_post_tax(single_tax_bracket_2021) +
             ir.get_total_roth_assets() +
             ir.get_total_incomes().cumsum(), label=title)
    ax0.set_title("Cumulative net worth (post-tax)")
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
    final_trad_assets = ir.get_total_trad_assets()[-1] - single_tax_bracket_2021.tax(ir.get_total_trad_assets()[-1], 0).tax_paid
    print(f"Sum = ${final_trad_assets + ir.get_total_roth_assets()[-1] + ir.get_total_incomes().sum():,.2f}")


class Profile:
    def __init__(self):
        self.age = 25
        self.retire = 65
        self.die = 90
        self.income = 100000
        self.rate = 7
        self.trad_alloc_percent = 4
        self.roth_alloc_percent = 4
        self.percent_salary_expenses = 90
        self.tax_bracket = single_tax_bracket_2021
    
    def kw(self):
        return {
            "starting_salary": self.income,
            "retirement": self.retire - self.age,
            "death": self.die - self.age,
            "return_rate": self.rate,
            "retirement_expenses_percent": self.percent_salary_expenses,
            "trad_alloc_percent": self.trad_alloc_percent,
            "roth_alloc_percent": self.roth_alloc_percent,
            "tax_bracket": self.tax_bracket
        }
    
    def run_simple_invest(self, **kw):
        keywords = self.kw()
        keywords.update(kw)
        return investment.simple_invest(**keywords)


def test_investment():
    profile = Profile()
    split = 8
    ir_roth = profile.run_simple_invest(trad_alloc_percent=0, roth_alloc_percent=split)
    ir_trad = profile.run_simple_invest(trad_alloc_percent=split, roth_alloc_percent=0)
    ir_5050 = profile.run_simple_invest(trad_alloc_percent=split / 2, roth_alloc_percent=split / 2)
    
    fig, (ax0, ax1, ax2, ax3, ax4) = plt.subplots(5, 1, sharex='all')
    print("All Roth")
    plot_investment(ir_roth, profile.age, profile.retire, ax0, ax1, ax2, ax3, ax4, "All Roth")
    print("All Trad")
    plot_investment(ir_trad, profile.age, profile.retire, ax0, ax1, ax2, ax3, ax4, "All Trad")
    print("50/50")
    plot_investment(ir_5050, profile.age, profile.retire, ax0, ax1, ax2, ax3, ax4, "50/50")
    plt.show()


def test_3d():
    profile = Profile()
    split = 8
    grain: int = 100  # number of points to graph in each dimension
    ax = plt.subplot(111, projection='3d')
    ir = None
    years = profile.die - profile.age
    x = np.linspace(0, split, grain)
    xs = (x / split * 100).reshape((len(x), 1))  # needs to be 2-dim
    z = np.zeros((grain, years))  # dims are years x grain
    for i, tap in enumerate(x):
        rap = split - tap
        ir = profile.run_simple_invest(trad_alloc_percent=tap, roth_alloc_percent=rap)
        net = ir.get_total_trad_assets_post_tax(single_tax_bracket_2021) + ir.get_total_roth_assets() + ir.get_total_incomes().cumsum()
        z[i,] = net
    y = ir.get_years() + profile.age
    ys = y.reshape((1, len(y)))  # needs to be 2-dim
    ax.plot_surface(xs, ys, z, cmap=cm.get_cmap("coolwarm"), label="Cumulative net worth (post-tax)")
    ax.set_xlabel('% Traditional')
    ax.set_ylabel('Years')
    plt.show()


if __name__ == '__main__':
    test_3d()
