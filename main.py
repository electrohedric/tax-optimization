import ctypes
import sys

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import cm
from multiprocessing import Pool, Value, Lock

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
        self.salary_raise_rate = 1
        self.investment_return_rate = 7
        self.trad_alloc_percent = 4
        self.roth_alloc_percent = 4
        self.percent_salary_expenses = 70
        self.tax_bracket = single_tax_bracket_2021
    
    def kw(self):
        return {
            "starting_salary": self.income,
            "retirement": self.retire - self.age,
            "death": self.die - self.age,
            "investment_return_rate": self.investment_return_rate,
            "retirement_expenses_percent": self.percent_salary_expenses,
            "tax_bracket": self.tax_bracket,
            "below_the_line": 12550,
            "salary_raise_rate": self.salary_raise_rate,
            "trad_start": 0,
            "roth_start": 0
        }
    
    def run_simple_invest(self, **kw):
        keywords = self.kw()
        keywords.update(kw)
        return investment.simple_invest(**keywords)

    def run_piecewise_invest(self, **kw):
        keywords = self.kw()
        keywords.update(kw)
        return investment.piecewise_invest(**keywords)

    def run_linsweep2_invest(self, **kw):
        keywords = self.kw()
        keywords.update(kw)
        return investment.linsweep2_invest(**keywords)


def test_investment():
    profile = Profile()
    split = 10
    ir_roth = profile.run_simple_invest(trad_alloc_percent=0, roth_alloc_percent=split)
    ir_trad = profile.run_simple_invest(trad_alloc_percent=split, roth_alloc_percent=0)
    ir_5050 = profile.run_simple_invest(trad_alloc_percent=split / 2, roth_alloc_percent=split / 2)
    ir_sweep = profile.run_linsweep2_invest(total_alloc_percent=split, slope_decision=1)
    # ir_60 = profile.run_simple_invest(trad_alloc_percent=split * 0.60, roth_alloc_percent=split * 0.40)
    # ir_80 = profile.run_simple_invest(trad_alloc_percent=split * 0.80, roth_alloc_percent=split * 0.20)

    fig, (ax0, ax1, ax2, ax3, ax4) = plt.subplots(5, 1, sharex='all')
    print("All Roth")
    plot_investment(ir_roth, profile.age, profile.retire, ax0, ax1, ax2, ax3, ax4, "All Roth")
    print("All Trad")
    plot_investment(ir_trad, profile.age, profile.retire, ax0, ax1, ax2, ax3, ax4, "All Trad")
    print("50/50")
    plot_investment(ir_5050, profile.age, profile.retire, ax0, ax1, ax2, ax3, ax4, "50/50")
    print("swep")
    plot_investment(ir_sweep, profile.age, profile.retire, ax0, ax1, ax2, ax3, ax4, "Sweep")
    # print("60")
    # plot_investment(ir_60, profile.age, profile.retire, ax0, ax1, ax2, ax3, ax4, "60/40")
    # print("80")
    # plot_investment(ir_80, profile.age, profile.retire, ax0, ax1, ax2, ax3, ax4, "80/20")
    plt.show()


def graph_3d(x: np.ndarray, y: np.ndarray, z: np.ndarray, colormap="coolwarm", z_label="Plot", x_label="x", y_label="y"):
    ax = plt.subplot(111, projection='3d')
    x = x.reshape((len(x), 1))  # needs to be 2-dim
    y = y.reshape((1, len(y)))  # needs to be 2-dim
    ax.plot_surface(x, y, z, cmap=cm.get_cmap(colormap))
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_zlabel(z_label)
    plt.show()


def get_min_max(n):
    max_x = n.argmax()
    min_x = n.argmin()
    return min_x, max_x


def test_simple_ratio_vs_age_vs_endbalance():
    profile = Profile()
    split = 10
    grain: int = 100  # number of points to graph in each dimension
    ir = None
    years = profile.die - profile.age

    x = np.linspace(0, split, grain)
    z = np.zeros((grain, years))  # dims are years x grain
    for i, tap in enumerate(x):
        rap = split - tap
        ir = profile.run_simple_invest(trad_alloc_percent=tap, roth_alloc_percent=rap)
        net = ir.get_total_trad_assets_post_tax(single_tax_bracket_2021) + ir.get_total_roth_assets() + ir.get_total_incomes().cumsum()
        z[i, ] = net
    y = ir.get_years() + profile.age

    last_year = z[:, years - 1]
    min_x, max_x = get_min_max(last_year)
    ptrad_max = max_x / (len(x) - 1) * 100
    ptrad_min = min_x / (len(x) - 1) * 100
    print(f"Best ratio: {ptrad_max:.1f}% trad, {100 - ptrad_max:.1f}% roth")
    print(f"Best savings percentage: {ptrad_max / 100 * split:.1f}% trad, "
          f"{(100 - ptrad_max) / 100 * split:.1f}% roth.. out of {split}% total savings")
    print(f"Maximum end balance: ${last_year[max_x]:,.2f}")
    print("-" * 100)
    print(f"Worst ratio: {ptrad_min:.1f}% trad, {100 - ptrad_min:.1f}% roth")
    print(f"Worst savings percentage: {ptrad_min / 100 * split:.1f}% trad, "
          f"{(100 - ptrad_min) / 100 * split:.1f}% roth.. out of {split}% total savings")
    print(f"Minimum end balance: ${last_year[min_x]:,.2f}")
    print("-" * 100)
    print(f"End balance difference: ${last_year[max_x] - last_year[min_x]:,.2f}")

    graph_3d(x / split * 100, y, z, z_label="Cumulative net worth (post-tax)", x_label="% Traditional", y_label="Age")


def test_piecewise_switchyear_vs_age_vs_endbalance():
    profile = Profile()
    total = 10
    ir = None
    years = profile.die - profile.age
    retire = profile.retire - profile.age

    x = np.arange(0, retire)
    z = np.zeros((retire, years))  # dims are years x grain
    for i in x:
        ir = profile.run_piecewise_invest(total_alloc_percent=total, switch_year=i)
        net = ir.get_total_trad_assets_post_tax(single_tax_bracket_2021) + ir.get_total_roth_assets() + ir.get_total_incomes().cumsum()
        z[i, ] = net
    y = ir.get_years() + profile.age

    last_year = z[:, years - 1]
    min_x, max_x = get_min_max(last_year)
    sy_max = max_x
    sy_min = min_x
    print(f"Best switch year: {sy_max}")
    print(f"Maximum end balance: ${last_year[max_x]:,.2f}")
    print("-" * 100)
    print(f"Worst switch year: {sy_min}")
    print(f"Minimum end balance: ${last_year[min_x]:,.2f}")
    print("-" * 100)
    print(f"End balance difference: ${last_year[max_x] - last_year[min_x]:,.2f}")

    graph_3d(x, y, z, z_label="Cumulative net worth (post-tax)", x_label="Switch Year", y_label="Age")


def test_linsweep_slopedecision_vs_age_vs_endbalance():
    profile = Profile()
    total = 10
    ir = None
    years = profile.die - profile.age
    grain = 100

    x = np.linspace(0, 1, grain)
    z = np.zeros((grain, years))  # dims are years x grain
    for i, sd in enumerate(x):
        ir = profile.run_linsweep_invest(total_alloc_percent=total, slope_decision=sd)
        net = ir.get_total_trad_assets_post_tax(single_tax_bracket_2021) + ir.get_total_roth_assets() + ir.get_total_incomes().cumsum()
        z[i, ] = net
    y = ir.get_years() + profile.age

    last_year = z[:, years - 1]
    min_x, max_x = get_min_max(last_year)
    sd_max = x[max_x]
    sd_min = x[min_x]
    print(f"Best slope decision: {sd_max}")
    print(f"Maximum end balance: ${last_year[max_x]:,.2f}")
    print("-" * 100)
    print(f"Worst slope decision: {sd_min}")
    print(f"Minimum end balance: ${last_year[min_x]:,.2f}")
    print("-" * 100)
    print(f"End balance difference: ${last_year[max_x] - last_year[min_x]:,.2f}")

    graph_3d(x, y, z, z_label="Cumulative net worth (post-tax)", x_label="Slope Decision", y_label="Age")


def find_best_ratio(profile, x, **kwargs):  # super inefficient!
    best_net = 0
    best_ratio = 0
    for i, tap in enumerate(x):
        rap = x[-1] - tap
        ir = profile.run_simple_invest(trad_alloc_percent=tap, roth_alloc_percent=rap, **kwargs)
        net = ir.get_total_trad_assets_post_tax(single_tax_bracket_2021) + ir.get_total_roth_assets() + ir.get_total_incomes().cumsum()
        if net[-1] > best_net:
            best_net = net[-1]
            best_ratio = tap
    return best_ratio


def multi_compute_ratio(arg):
    counter, profile, grain, sr, sal = arg
    print(f"\r{counter}", end='')
    return find_best_ratio(profile, np.linspace(0, sr, grain // 2), starting_salary=sal)


def test_salary_vs_savingsrate_vs_optimalratio():
    profile = Profile()
    sal_grain: int = 10
    savings_grain: int = 20
    best_ratio_grain: int = 50
    min_salary = 15000
    max_salary = 300000
    min_savings_rate = 5
    max_savings_rate = 50
    print(f"waiting for {savings_grain * sal_grain}")

    x = np.linspace(min_salary, max_salary, sal_grain)
    y = np.linspace(min_savings_rate, max_savings_rate, savings_grain)
    args = []
    i = 0
    for salary in x:
        for savings_rate in y:
            args.append((i, profile, best_ratio_grain, savings_rate, salary))
            i += 1
    with Pool(4) as p:
        z = np.array(p.map(multi_compute_ratio, args)).reshape((len(x), len(y)))  # dims are x * y
    z = z / y * 100
    graph_3d(x, y, z, z_label="Optimal ratio", x_label="Salary", y_label="Savings rate")


if __name__ == '__main__':
    # test_linsweep_slopedecision_vs_age_vs_endbalance()
    # test_salary_vs_savingsrate_vs_optimalratio()
    # test_simple_ratio_vs_age_vs_endbalance()
    # test_piecewise_switchyear_vs_age_vs_endbalance()
    test_investment()
