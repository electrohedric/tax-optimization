import ctypes
import sys
import time
import image

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import cm
from multiprocessing import Pool, Value, Lock

import investment
from investment import Profile
from loader import load_tax_bracket
import tax_brackets

standard_deduction_2021 = 12550.00
standard_deduction_2021_va = 4500.00
standard_deduction_2021_ss = 0
standard_deduction_2021_med = 0
single_tax_bracket_2021 = load_tax_bracket("data/2021/single_tax.csv")
single_tax_bracket_2021_va = load_tax_bracket("data/2021/va_single_tax.csv")
single_tax_bracket_2021_ss = load_tax_bracket("data/2021/social_security_tax.csv")
single_tax_bracket_2021_med = load_tax_bracket("data/2021/medicare_tax.csv")

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

def test_tax_bracket_va():
    while True:
        try:
            # amount = 100000
            amount = float(input("Enter income: $"))
            # deduction = 0
            deduction = float(input("Enter deduction or nothing: $") or '0')
        except ValueError:
            print("Quit")
            sys.exit()
        tax = single_tax_bracket_2021_va.tax(amount, max(deduction, standard_deduction_2021))
        print(f"${tax.tax_paid:.2f} of ${tax.real_taxable_amount():.2f} taxed")
        for i in range(len(tax.breakdown)):
            print(f"{single_tax_bracket_2021_va.tax_ranges[i]} = {tax.breakdown[i]}")
        print(f"Effective tax rate: {tax.real_effective_tax_rate():.2%}")

def test_tax_bracket_total():
    while True:
        try:
            # amount = 100000
            amount = float(input("Enter income: $"))
            # deduction = 0
            deduction = float(input("Enter deduction or nothing: $") or '0')
        except ValueError:
            print("Quit")
            sys.exit()
        tax_fed = single_tax_bracket_2021.tax(amount, max(deduction, standard_deduction_2021))
        tax_va = single_tax_bracket_2021_va.tax(amount, max(deduction, standard_deduction_2021_va))
        tax_ss = single_tax_bracket_2021_ss.tax(amount, max(deduction, standard_deduction_2021_ss))
        tax_med = single_tax_bracket_2021_med.tax(amount, max(deduction, standard_deduction_2021_med))
        tax_total = tax_fed.tax_paid + tax_va.tax_paid + tax_ss.tax_paid + tax_med.tax_paid
        print(f"${tax_fed.tax_paid:.2f} of ${tax_fed.real_taxable_amount():.2f} taxed (federal)")
        print(f"${tax_va.tax_paid:.2f} of ${tax_va.real_taxable_amount():.2f} taxed (va)")
        print(f"${tax_ss.tax_paid:.2f} of ${tax_ss.real_taxable_amount():.2f} taxed (social security)")
        print(f"${tax_med.tax_paid:.2f} of ${tax_med.real_taxable_amount():.2f} taxed (medicare)")
        print(f"${tax_total:.2f} taxed (total)")
        tax_sum = tax_brackets.Tax(
            [single_tax_bracket_2021, single_tax_bracket_2021_va, single_tax_bracket_2021_ss, single_tax_bracket_2021_med],
            [standard_deduction_2021, standard_deduction_2021_va, standard_deduction_2021_ss, standard_deduction_2021_med]
        )
        print("-" * 100)
        for i in range(len(tax_fed.breakdown)):
            print(f"{single_tax_bracket_2021.tax_ranges[i]} = {tax_fed.breakdown[i]}")
        print("-" * 100)
        for i in range(len(tax_va.breakdown)):
            print(f"{single_tax_bracket_2021_va.tax_ranges[i]} = {tax_va.breakdown[i]}")
        print("-" * 100)
        for i in range(len(tax_ss.breakdown)):
            print(f"{single_tax_bracket_2021_ss.tax_ranges[i]} = {tax_ss.breakdown[i]}")
        print("-" * 100)
        for i in range(len(tax_med.breakdown)):
            print(f"{single_tax_bracket_2021_med.tax_ranges[i]} = {tax_med.breakdown[i]}")
        print("-" * 100)
        print(f"Effective fed tax rate: {tax_fed.real_effective_tax_rate():.2%}")
        print(f"Effective va tax rate: {tax_va.real_effective_tax_rate():.2%}")
        print(f"Effective ss tax rate: {tax_ss.real_effective_tax_rate():.2%}")
        print(f"Effective med tax rate: {tax_med.real_effective_tax_rate():.2%}")

def get_total_tax(amount: float, deduction: float):
    tax_fed = single_tax_bracket_2021.tax(amount, max(deduction, standard_deduction_2021))
    tax_va = single_tax_bracket_2021_va.tax(amount, max(deduction, standard_deduction_2021_va))
    tax_ss = single_tax_bracket_2021_ss.tax(amount, max(deduction, standard_deduction_2021_ss))
    tax_med = single_tax_bracket_2021_med.tax(amount, max(deduction, standard_deduction_2021_med))
    tax_total = tax_fed.tax_paid + tax_va.tax_paid + tax_ss.tax_paid + tax_med.tax_paid

    return tax_total


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

def test_piecewise2_switchyear1_vs_duration_vs_endbalance():
    profile = Profile()
    total = 10
    ir = None
    years = profile.die - profile.age
    retire = profile.retire - profile.age

    x = np.arange(0, retire)
    y = np.arange(0, retire)
    z = np.zeros((len(x), len(y)))  # dims are years x grain
    min_net, min_x, min_y = float('inf'), 0, 0
    for i, sy in enumerate(x):
        for j, d in enumerate(y):
            if sy + d > retire:
                continue
            ir = profile.run(investment.piecewise2_invest, switch_year=sy, switch_duration=d, total_alloc_percent=total)
            net = ir.get_total_trad_assets_post_tax(single_tax_bracket_2021) + ir.get_total_roth_assets() + ir.get_total_incomes().cumsum()
            z[i, j] = net[-1]
            if z[i, j] < min_net:
                min_net = z[i, j]
                min_x = i
                min_y = j

    for i, sy in enumerate(x):
        for j, d in enumerate(y):
            if z[i, j] == 0:
                z[i, j] = min_net

    min_xy, max_xy = get_min_max(z)
    max_x, max_y = divmod(max_xy, len(y))
    print(f"Best switch year, dur: {max_x}, {max_y}")
    print(f"Maximum end balance: ${z[max_x, max_y]:,.2f}")
    print("-" * 100)

    print(f"Minimum end balance: ${z[min_x, min_y]:,.2f}")
    print("-" * 100)
    print(f"End balance difference: ${z[max_x, max_y] - z[min_x, min_y]:,.2f}")

    graph_3d(x, y, z, z_label="Cumulative net worth (post-tax)", x_label="Switch Year", y_label="Duration")

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

def test_linsweep2_slopedecision_vs_age_vs_endbalance():
    profile = Profile()
    total = 10
    ir = None
    years = profile.die - profile.age
    retire = profile.retire - profile.age
    grain = 100

    x = np.arange(0, retire)
    z = np.zeros((retire, years))  # dims are years x grain
    for i in x:
        ir = profile.run_linsweep2_invest(total_alloc_percent=total, switch_year=i)
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

def test_linsweep3_slopedecision_vs_age_vs_endbalance():
    profile = Profile()
    total = 10
    ir = None
    years = profile.die - profile.age
    grain = 100

    x = np.linspace(0, 1, grain)
    z = np.zeros((grain, years))  # dims are years x grain
    for i, sd in enumerate(x):
        ir = profile.run_linsweep3_invest(total_alloc_percent=total, slope_decision=sd)
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

def test_linsweep4_slopedecision_vs_age_vs_endbalance():
    profile = Profile()
    total = 10
    ir = None
    years = profile.die - profile.age
    retire = profile.retire - profile.age
    grain = 100
    maxbalance = 0
    mb = maxbalance

    x = np.arange(0, retire)
    z = np.zeros((retire, years))  # dims are years x grain
    for j in range(100):
        for i in x:
            ir = profile.run_linsweep4_invest(total_alloc_percent=total, switch_year=i, break1=j)
            net = ir.get_total_trad_assets_post_tax(single_tax_bracket_2021) + ir.get_total_roth_assets() + ir.get_total_incomes().cumsum()
            z[i, ] = net
        y = ir.get_years() + profile.age



        last_year = z[:, years - 1]
        min_x, max_x = get_min_max(last_year)
        sy_max = max_x
        sy_min = min_x
        # print(f"Best switch year: {sy_max}")
        # print(f"Maximum end balance: ${last_year[max_x]:,.2f}")
        # print("-" * 100)
        # print(f"Worst switch year: {sy_min}")
        # print(f"Minimum end balance: ${last_year[min_x]:,.2f}")
        # print("-" * 100)
        # print(f"End balance difference: ${last_year[max_x] - last_year[min_x]:,.2f}")

        # graph_3d(x, y, z, z_label="Cumulative net worth (post-tax)", x_label="Switch Year", y_label="Age")
        if last_year[max_x] > mb:
            mb = last_year[max_x]
    print(f"\n\n Max Balance is: ${mb:,.2f}")

def test_erf_switchyear_vs_slope_vs_endbalance():
    profile = Profile()
    total = 10
    ir = None
    years = profile.die - profile.age
    retire = profile.retire - profile.age
    grain = 100

    t = time.time()
    x = np.arange(0, retire)
    y = np.linspace(0, 1, grain)
    z = np.zeros((len(x), len(y)))  # dims are years x grain
    for i, sy in enumerate(x):
        for j, a in enumerate(y):
            ir = profile.run(investment.erf_invest, switch_year=sy, a=a, normalize=True, total_alloc_percent=total)
            net = ir.get_total_trad_assets_post_tax(single_tax_bracket_2021) + ir.get_total_roth_assets() + ir.get_total_incomes().cumsum()
            z[i, j] = net[-1]
        print(i)
    print(time.time() - t)

    min_xy, max_xy = get_min_max(z)
    max_x, max_y = divmod(max_xy, len(y))
    min_x, min_y = divmod(min_xy, len(y))
    print(f"Best switch year, a: {max_x}, {y[max_y]}")
    print(f"Maximum end balance: ${z[max_x, max_y]:,.2f}")
    print("-" * 100)

    print(f"Minimum end balance: ${z[min_x, min_y]:,.2f}")
    print("-" * 100)
    print(f"End balance difference: ${z[max_x, max_y] - z[min_x, min_y]:,.2f}")

    graph_3d(x, y, z, z_label="Cumulative net worth (post-tax)", x_label="Switch Year", y_label="A")

def test_quadratic_slopedecision_vs_age_vs_endbalance():
    profile = Profile()
    total = 10
    ir = None
    years = profile.die - profile.age
    retire = profile.retire - profile.age
    grain = 100
    maxbalance = 0
    mb = maxbalance

    x = np.arange(0, retire)
    z = np.zeros((retire, years))  # dims are years x grain
    j = 1

    for i in x:
        ir = profile.run_quadratic_invest(total_alloc_percent=total, switch_year=i, break1=i)
        net = ir.get_total_trad_assets_post_tax(single_tax_bracket_2021) + ir.get_total_roth_assets() + ir.get_total_incomes().cumsum()
        z[i,] = net
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

def test_exp_slopedecision_vs_age_vs_endbalance():
    profile = Profile()
    total = 10
    ir = None
    years = profile.die - profile.age
    retire = profile.retire - profile.age
    grain = 100
    maxbalance = 0
    mb = maxbalance

    x = np.arange(0, retire)
    z = np.zeros((retire, years))  # dims are years x grain
    j = 1

    for i in x:
        ir = profile.run_exp_invest(total_alloc_percent=total, switch_year=i, break1=i)
        net = ir.get_total_trad_assets_post_tax(single_tax_bracket_2021) + ir.get_total_roth_assets() + ir.get_total_incomes().cumsum()
        z[i,] = net
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

def test_log_slopedecision_vs_age_vs_endbalance():
    profile = Profile()
    total = 10
    ir = None
    years = profile.die - profile.age
    retire = profile.retire - profile.age
    grain = 100
    maxbalance = 0
    mb = maxbalance

    x = np.linspace(0, retire, grain)
    z = np.zeros((grain, years))  # dims are years x grain
    j = 1

    for i, sy in enumerate(x):
        ir = profile.run_log_invest(total_alloc_percent=total, break_=sy)
        net = ir.get_total_trad_assets_post_tax(single_tax_bracket_2021) + ir.get_total_roth_assets() + ir.get_total_incomes().cumsum()
        z[i,] = net
    y = ir.get_years() + profile.age

    last_year = z[:, years - 1]
    min_x, max_x = get_min_max(last_year)
    sy_max = max_x
    sy_min = min_x
    print(f"Best A: {x[sy_max]}")
    print(f"Maximum end balance: ${last_year[max_x]:,.2f}")
    print("-" * 100)
    print(f"Worst A: {x[sy_min]}")
    print(f"Minimum end balance: ${last_year[min_x]:,.2f}")
    print("-" * 100)
    print(f"End balance difference: ${last_year[max_x] - last_year[min_x]:,.2f}")

    graph_3d(x, y, z, z_label="Cumulative net worth (post-tax)", x_label="Switch Year", y_label="Age")

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


def optimize_sorted_random_1():
    profile = Profile()
    retirement = profile.retire - profile.age
    all_trad_year = retirement
    best_net = 0
    best_strategy = None

    for i in range(10000):
        random = np.random.normal(0.5, 2, all_trad_year).clip(0, 1)
        random.sort()
        # strategy = np.append(np.interp(np.arange(0, all_trad_year), np.arange(0, num_rand) * ((all_trad_year + 1) / num_rand), random), np.ones(retirement - all_trad_year))
        strategy = np.append(random, np.ones(retirement - all_trad_year))
        ir = profile.run(investment.array_invest, percentages=strategy)
        net = ir.get_total_trad_assets_post_tax(single_tax_bracket_2021) + ir.get_total_roth_assets() + ir.get_total_incomes().cumsum()
        final_net = net[-1]
        if i % 1000 == 0:
            print(i)
        if final_net > best_net:
            best_net = final_net
            best_strategy = strategy
            print(f"{i=} ${best_net:,.2f}")

    plt.plot(np.arange(0, retirement), best_strategy)
    print(best_strategy)
    print(f"${best_net:,.2f}")

    plt.show()


def optimize_sorted_random_2():
    profile = Profile()
    retirement = profile.retire - profile.age
    all_trad_year = 40
    best_net = 0
    best_strategy = None

    for i in range(1000):
        random = np.random.normal(0.5, 2, all_trad_year).clip(0, 1)
        random.sort()
        # strategy = np.append(np.interp(np.arange(0, all_trad_year), np.arange(0, num_rand) * ((all_trad_year + 1) / num_rand), random), np.ones(retirement - all_trad_year))
        # strategy = np.append(random, np.ones(retirement - all_trad_year))
        strategy = random
        ir = profile.run(investment.array_invest, percentages=strategy)
        net = ir.get_total_trad_assets_post_tax(
            single_tax_bracket_2021) + ir.get_total_roth_assets() + ir.get_total_incomes().cumsum()
        final_net = net[-1]
        if i % 1000 == 0:
            print(i)
        if final_net > best_net:
            best_net = final_net
            best_strategy = strategy
            print(f"{i=} ${best_net:,.2f}")

    plt.plot(np.arange(0, retirement), best_strategy)
    print(best_strategy)
    print(f"${best_net:,.2f}")

    plt.show()

if __name__ == '__main__':
    # test_linsweep_slopedecision_vs_age_vs_endbalance()
    # test_linsweep2_slopedecision_vs_age_vs_endbalance()
    # test_linsweep3_slopedecision_vs_age_vs_endbalance()
    # test_linsweep4_slopedecision_vs_age_vs_endbalance()
    # test_quadratic_slopedecision_vs_age_vs_endbalance()
    # test_exp_slopedecision_vs_age_vs_endbalance()
    # test_log_slopedecision_vs_age_vs_endbalance()
    # test_salary_vs_savingsrate_vs_optimalratio()
    test_simple_ratio_vs_age_vs_endbalance()
    # test_piecewise_switchyear_vs_age_vs_endbalance()
    # test_piecewise2_switchyear1_vs_duration_vs_endbalance()
    # test_erf_switchyear_vs_slope_vs_endbalance()
    # optimize_sorted_random_1()
    # optimize_sorted_random_2()
    # test_investment()
    # test_tax_bracket()
    # test_tax_bracket_va()
    # test_tax_bracket_total()
