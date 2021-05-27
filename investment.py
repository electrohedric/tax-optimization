import logging
import math
from enum import IntEnum
from typing import Tuple, Iterable

import numpy as np
import igwad
import tax_bracket_consts
from loader import load_tax_bracket
from tax_brackets import TaxBracket, TotalTax

single_tax_bracket_2021_AIME = load_tax_bracket("data/2021/AIME_benefit_calculation.csv")
single_ss_bracket_2021 = load_tax_bracket("data/2021/social_security_provisional_income.csv")


class AccountType(IntEnum):
    """
    A hard value to specify an account type for dictionaries, etc.
    """
    OTHER = -1
    TRAD = 0
    ROTH = 1
    TAXABLE = 2


class BalanceChangeResult:
    def __init__(self, start_amount: float, change_amount: float):
        """
        Describes a change in the balance of an account; either a deposit or withdrawl

        :param start_amount: starting amount before transaction
        :param change_amount: amount to move into/from the account. positive for deposit, negative for withdrawl
        """
        self.start_amount = start_amount
        self.change_amount = change_amount
        self.end_amount = self.start_amount + self.change_amount


class GrowthResult:
    def __init__(self, start_amount: float, return_rate: float):
        """
        Describes the growth of an account via interest over a single period (e.g. a year)

        :param start_amount: starting amount before growth occured
        :param return_rate: (-inf, inf) decimal describing ROI for single growth period.
            0 == 100% == no change. 1 == 100% == doubling, -1 == -100% == all gone, etc.
        """
        self.start_amount = start_amount
        self.return_rate = return_rate
        self.interest = self.start_amount * self.return_rate
        self.end_amount = self.start_amount + self.interest


class InvestmentResult:
    def __init__(self):
        """
        Describes the breakdown of an entire lifetime of investment.
        You may iterate over this class to conveniently yield the contained InvestmentYearResults
        """
        self.year_results: list[InvestmentYearResult] = []

    def get_final_net_worth(self) -> float:
        """
        :return: the last recorded year's net worth
        """
        return self.year_results[-1].net_worth()

    def get_years(self) -> np.ndarray:
        """
        :return: array of integer years from [0, dead)
        """
        return np.array([x.year for x in self])

    def get_net_worths(self) -> np.ndarray:
        """
        :return: array of the net worth from each year
        """
        return np.array([x.net_worth() for x in self])

    def get_total_roth_assets(self) -> np.ndarray:
        """
        :return: array of the ending balance of the roth account from each year
        """
        return np.array([x.growth[AccountType.ROTH].end_amount for x in self])

    def get_total_trad_assets(self) -> np.ndarray:
        """
        :return: array of the ending balance of the traditional account from each year
        """
        return np.array([x.growth[AccountType.TRAD].end_amount for x in self])

    def get_total_taxable_account_assets(self) -> np.ndarray:
        """
        :return: array of the ending balance of the taxable account from each year
        """
        return np.array([x.growth[AccountType.TAXABLE].end_amount for x in self])

    def get_taxes_paid(self) -> np.ndarray:
        """
        :return: array of the tax paid on total income from each year
        """
        return np.array([x.income.income_tax for x in self])

    def get_total_trad_assets_post_tax(self, tax_bracket: TotalTax) -> np.ndarray:
        """
        Computes total net worth after tax is taken out on traditional

        :param tax_bracket: tax function to use to tax
        :return: array of the net worth after taxes are taken out from each year,
            assuming full amount is taken as distributions (no deductions are taken, rough calculation)
        """
        trad = self.get_total_trad_assets()
        vfunc = np.vectorize(lambda x: x - tax_bracket.tax(x))
        trad_taxed = vfunc(trad)
        return trad_taxed

    def get_total_taxable_account_assets_post_tax(self, tax_bracket: TaxBracket) -> np.ndarray:
        """
        Computes total net worth after tax is taken out on taxable account

        :param tax_bracket: tax function to use to tax
        :return: array of the net worth after taxes are taken out from each year,
            assuming full amount is taken as distributions (no deductions are taken, rough calculation)
        """
        trad = self.get_total_taxable_account_assets()
        vfunc = np.vectorize(lambda x: tax_bracket.tax(x, 0).remaining())  # TODO worry about this later
        taxable_account_taxed = vfunc(trad)
        return taxable_account_taxed

    def get_total_incomes(self) -> np.ndarray:
        """
        :return: array of total income from each year
        """
        return np.array([x.income.total_income for x in self])

    def __iter__(self):
        for x in self.year_results:
            yield x


class Account:
    def __init__(self, initial_amount: float = 0, account_label: AccountType = AccountType.OTHER):
        """
        An account which simply holds an amount of money and can perform
        simple actions such as depositing and withdrawing.
        Primary use is to have Result objects which perform actions and contain the results of those actions.

        :param initial_amount: starting amount of the account
        :param account_label: label to put on the account for sorting purposes.
        """
        self.amount = initial_amount
        self.label = account_label

    def grow(self, return_rate: float) -> GrowthResult:
        """
        Multiplies the current amount by the return rate and adds the result to the account

        :param return_rate: see GrowthResult for details
        :return: GrowthResult containing ending amount
        """
        result = GrowthResult(self.amount, return_rate)
        self.amount = result.end_amount
        return result

    def _change(self, amount: float) -> BalanceChangeResult:
        """
        Performs a balance change

        :param amount: delta amount
        :return: BalanceChangeResult
        """
        result = BalanceChangeResult(self.amount, amount)
        self.amount = result.end_amount
        return result

    def deposit(self, amount: float) -> BalanceChangeResult:
        """
        Performs a positive change. Adds money to the account

        :param amount: amount to add
        :return: BalanceChangeResult containing ending amount
        """
        return self._change(amount)

    def withdraw(self, amount: float) -> BalanceChangeResult:
        """
        Performs a negative change. Takes money out of the account

        :param amount: amount to subtract
        :return: BalanceChangeResult containing ending amount
        """
        return self._change(-amount)

    def has(self, amount: float):
        """
        Determines if the amount can be taken out of the account without going negative

        :param amount: amount to test
        :return: True if at least amount is in the account, False otherwise
        """
        return amount <= self.amount

    def create_contribution(self, amount: float) -> 'Account.Contribution':
        """
        Helper method to generate a basic tax-free contribution.
        Ensures the amount contributed is positive
        Also ensure the amount contributed is not over the maximum contribution for the account type

        :param amount: contribution allocation amount
        :return: a contribution matching the amount
        """
        max_cont = Account.Contribution.LIMITS.get(self.label) or float('inf')
        # print(f"max trad contribution = {min(max(amount, 0), max_cont)}")

        return Account.Contribution(self, min(max(amount, 0), max_cont))

    def create_distribution(self, amount: float) -> 'Account.Distribution':
        """
        Helper method to generate a basic tax-free distribution
        Ensures a distribution will never take out more money than is in the account.
        Also ensures the amount distributed is positive\n
        Allocation is == distribution.amount

        :param amount: amount to take in distributions
        :return: a distribution matching the amount, or possibly less if there was not enough money
        """
        return Account.Distribution(self, min(max(amount, 0), self.amount))

    def create_roth_contribution(self, amount: float, tax_bracket: TotalTax, above_the_line: float, margin: float) -> 'Account.Contribution':
        """
        Helper method to generate a traditional contribution and finds the allocation amount to take out 'amount'

        :param amount: contribution allocation amount
        :param tax_bracket: tax bracket to use to do tax calculations
        :param above_the_line: trad cont
        :param margin: margin to pass into the tax function.
            should be set so that this is taxed at the highest margin (most likely = expenses)
        :return: a distribution matching the amount
        """
        assert self.label == AccountType.ROTH
        # compute tax on allocation
        roth_tax_rem = amount - tax_bracket.tax(amount, above_the_line, margin)
        max_cont = Account.Contribution.LIMITS.get(self.label)
        # print(f"max roth contributino = {min(roth_tax_rem, max_cont)}")
        return Account.Contribution(self, min(roth_tax_rem, max_cont))

    def create_taxable_account_contribution(self, amount: float, tax_bracket: TaxBracket, deductions: float,
                                            margin: float) -> 'Account.Contribution':
        """
        Helper method to generate a taxable account distribution and finds the allocation amount to take out 'amount'

        :param amount: contribution allocation amount
        :param tax_bracket: tax bracket to use to do tax calculations
        :param deductions: deductions to take
        :param margin: margin to pass into the tax function.
            should be set so that this is taxed at the highest margin (most likely = expenses)
        :return: a distribution matching the amount
        """
        assert self.label == AccountType.TAXABLE
        # compute tax on allocation
        taxable_account_tax_rem = amount - tax_bracket.fast_tax(amount, deductions, margin)  # TODO: taxable needs cap gains tax
        return Account.Contribution(self, taxable_account_tax_rem)

    def create_trad_distribution(self, amount: float, tax_bracket: TotalTax) -> Tuple['Account.Distribution', float]:
        """
        Helper method to generate a traditional distribution and finds the allocation amount to take out 'amount'

        :param amount: amount to take in distributions
        :param tax_bracket: tax bracket to use to do tax calculations
        :return: a distribution matching the amount
        """
        assert self.label == AccountType.TRAD
        # test can't allocate more than in trad account
        trad_dist_alloc = tax_bracket.reverse_tax(amount)
        if self.amount < trad_dist_alloc:  # can't take out full amount in trad
            # allocation is the full amount in the account
            trad_dist_alloc = self.amount
            # recompute the actual distributable amount
            amount = trad_dist_alloc - tax_bracket.tax(trad_dist_alloc)
        return Account.Distribution(self, amount), trad_dist_alloc

    def create_growth(self, return_rate: float):
        """
        Helper method to generate tax-free growth.
        Basically a wrapper around Account.Growth

        :param return_rate: rate to grow the account. 1.0 is 100% growth. See GrowthResult for more details
        :return: a growth with the return rate
        """
        return Account.Growth(self, return_rate)

    class Contribution:
        LIMITS = {AccountType.TRAD: 29100, AccountType.ROTH: 66600}

        def __init__(self, account: 'Account', amount: float):
            """
            Describes an account contribution. Can perform a deposit of a specified amount to an account.
            Does not actually perform a deposit until put() is called

            :param account: account to access
            :param amount: amount to add
            """
            self.account = account
            self.amount = amount

        def put(self) -> BalanceChangeResult:
            """
            Performs a deposit of the pre-specified amount to the account.
            Can be called multiple times to put the same amount

            :return: BalanceChangeResult from the deposit
            """
            return self.account.deposit(self.amount)

    class Distribution:
        def __init__(self, account: 'Account', amount: float):
            """
            Describes an account distribution. Can perform a withdrawl of a specified amount from an account.
            Does not actually form a withdrawl until take() is called

            :param account: account to access
            :param amount: amount to withdraw
            """
            self.account = account
            self.amount = amount

        def take(self) -> BalanceChangeResult:
            """
            Performs a withdrawl of the pre-specified amount from the account.
            Can be called mulitple times to take the same amount

            :return: BalanceChangeResult from the withdrawl
            """
            return self.account.withdraw(self.amount)

    class Growth:
        def __init__(self, account: 'Account', return_rate: float):
            """
            Describes account growth for a period. Can perform growth at a specified return rate.
            Does not actually grow the account until grow() is called. See GrowthResult details on how growth is done

            :param account: account to access
            :param return_rate: rate to grow the account. See GrowthResult for more details
            """
            self.account = account
            self.return_rate = return_rate

        def grow(self) -> GrowthResult:
            """
            Performs a growth of the account at the pre-specified return rate

            :return: GrowthResult from the growth
            """
            return self.account.grow(self.return_rate)


class IncomeResult:
    def __init__(self, salary_amount: float, trad_cont_amount: float,
                 trad_dist_alloc_amount: float, roth_dist_amount: float, tax_bracket: TotalTax,
                 social_security_benefit: float = 0, taxable_social_security_income: float = 0,
                 taxable_account_alloc_amount: float = 0):
        """
        Does all calculations and stores all results from taxing total income

        :param salary_amount: salary before tax
        :param trad_cont_amount: final contribution amount to all traditional accounts
        :param trad_dist_alloc_amount: final distribution allocation amount from all traditional accounts.
            Either this or trad_cont_amount should be 0
        :param roth_dist_amount: final distribution (allocation) amount from all roth accounts
        :param tax_bracket: tax bracket computer to perform tax calculations
        :param social_security_benefit: this years anual social security benefit
        """

        self.salary = salary_amount
        """salary before deductions"""

        # TODO fix social security calculations. right now taxable_account_alloc_amount is counted toward total income
        # TODO also tax calculations are complicated when taxable account distributions exist. need margin functionality
        self.gross_income = salary_amount + trad_dist_alloc_amount + taxable_social_security_income \
            + taxable_account_alloc_amount
        """taxable income before deductions. salary + traditional distributions"""

        # TODO: fix agi and deduction calculations

        self.agi = self.gross_income - trad_cont_amount
        """adjusted gross income. gross income - traditional contributions"""

        self.income_tax = tax_bracket.tax(self.gross_income, trad_cont_amount)
        """tax result for the taxable income"""

        self.net_income = self.gross_income - self.income_tax
        """income after taxes. gross income - tax paid on income"""

        self.total_income = self.net_income + roth_dist_amount + social_security_benefit
        """money that shows up in your bank account. net income + roth distributions"""


class InvestmentYearResult:
    def __init__(self, year: int,
                 contributions: Iterable[Account.Contribution],
                 distributions: Iterable[Account.Distribution],
                 growths: Iterable[Account.Growth],
                 income_result: IncomeResult):
        """
        Result from a single investment year. Contains information about all distributions and contributions

        :param year: integer year from [0, inf)
        :param contributions: dictionary mapping an account type to an actual contribution to an account of that type
        :param distributions: dictionary mapping an account type to an actual distribution from an account of that type
        :param growths: dictionary mapping an account type to an actual growth for an account of that type
        :param income_result: IncomeResult detailing income
        """
        self.year = year
        self.contributions = {c.account.label: c.put() for c in contributions}
        self.distributions = {d.account.label: d.take() for d in distributions}
        self.growth = {g.account.label: g.grow() for g in growths}
        self.income = income_result

    def net_worth(self) -> float:
        """
        :return: sum of ending amounts of all accounts at the end of the growth period, not including income
        """
        return sum([x.end_amount for x in self.growth.values()])

    def total_contributions(self) -> float:
        """
        :return: sum of all contributions made to all investment accounts
        """
        return sum([x.change_amount for x in self.contributions.values()])

    def total_distributions(self) -> float:
        """
        :return: sum of all distributions taken from all investment accounts
        """
        return sum([-x.change_amount for x in self.distributions.values()])

    def total_growth(self) -> float:
        """
        :return: sum of all interest gained on all investment accounts
        """
        return sum([x.interest for x in self.growth.values()])


class Profile:
    def __init__(self):
        self.age = 25
        self.retire = 65
        self.die = 90
        self.income = 50000
        self.salary_raise_rate = 1
        self.investment_return_rate = 7
        self.trad_alloc_percent = 5
        self.roth_alloc_percent = 5
        self.percent_salary_expenses = 100
        self.tax_bracket = tax_bracket_consts.single_combined_tax_2021

    def kw(self):
        return {
            "starting_salary": self.income,
            "retirement": self.retire,
            "death": self.die,
            "age": self.age,
            "investment_return_rate": self.investment_return_rate,
            "retirement_expenses_percent": self.percent_salary_expenses,
            "tax_bracket": self.tax_bracket,
            "salary_raise_rate": self.salary_raise_rate,
            "trad_start": 0,
            "roth_start": 0,
            "taxable_account_start": 0
        }

    def run(self, func, **kwargs):
        keywords = self.kw()
        keywords.update(kwargs)
        return func(**keywords)

    def run_simple_invest(self, **kw):
        keywords = self.kw()
        keywords.update(kw)
        return simple_invest(**keywords)

    def run_piecewise_invest(self, **kw):
        keywords = self.kw()
        keywords.update(kw)
        return piecewise_invest(**keywords)

    def run_linsweep_invest(self, **kw):
        keywords = self.kw()
        keywords.update(kw)
        return linsweep_invest(**keywords)

    def run_linsweep2_invest(self, **kw):
        keywords = self.kw()
        keywords.update(kw)
        return linsweep2_invest(**keywords)

    def run_linsweep3_invest(self, **kw):
        keywords = self.kw()
        keywords.update(kw)
        return linsweep3_invest(**keywords)

    def run_linsweep4_invest(self, **kw):
        keywords = self.kw()
        keywords.update(kw)
        return linsweep4_invest(**keywords)

    def run_quadratic_invest(self, **kw):
        keywords = self.kw()
        keywords.update(kw)
        return quadratic_invest(**keywords)

    def run_exp_invest(self, **kw):
        keywords = self.kw()
        keywords.update(kw)
        return exp_invest(**keywords)

    def run_log_invest(self, **kw):
        keywords = self.kw()
        keywords.update(kw)
        return log_invest(**keywords)


def sum_largest_values_in_array(list1: np.ndarray, n: int):
    list1.sort()
    return list1[-n:].sum()


def get_pia(all_salaries: np.ndarray):
    amount = sum_largest_values_in_array(all_salaries, 35)
    # print(f"salaries are ${amount:,.2f}")
    average_index_monthly_earnings = amount / 420
    # print(f"AIME is ${average_index_monthly_earnings:,.2f}")
    pia = single_tax_bracket_2021_AIME.tax(average_index_monthly_earnings, 0)
    # pia = primary insurance amount
    # print(f"pia is ${pia.tax_paid:,.2f}")
    return pia.tax_paid


def find_actual_social_security_benefit(pia, year) -> float:
    if year > 70 or year < 62:
        print("invalid year to take social security")
        return 0

    # 62 <= year <= 70
    # social_security_benefit = 0.0
    if year <= 63:
        social_security_benefit = (pia * 12) * (1 + ((year - 64) * 0.05) - 0.1998)
        # print(f"social security_benefit is ${social_security_benefit/12:,.2f} at age {year}")
    elif year <= 66:
        social_security_benefit = (pia * 12) * (1 + ((year - 67) * 0.0666))
        # print(f"social security_benefit is ${social_security_benefit/12:,.2f} at age {year}")
    else:  # <= 70
        social_security_benefit = (pia * 12) * (1 + ((year - 67) * 0.08))
        # print(f"social security_benefit is ${social_security_benefit/12:,.2f} at age {year}")

    return social_security_benefit


def array_invest(percentages: np.ndarray, starting_salary: float, tax_bracket: TotalTax, retirement: int = 65,
                 death: int = 90, retirement_expenses_percent: float = 70, age: int = 25,
                 salary_raise_rate: float = 1, investment_return_rate: float = 7,
                 taxable_account_alloc_percent: float = 0, total_alloc_percent: float = 10, trad_start: float = 0,
                 roth_start: float = 0, taxable_account_start: float = 0, ss_year: int = 70) -> InvestmentResult:
    """
    Performs a simple investment calculation. Makes several assumptions:\n
    1. salary increases steadily\n
    2. tax bracket never changes\n
    3. retirement age and death are known\n
    4. fixed return rate, interest rate, and standard deduction\n
    5. roth and traditional allocation percentages are constant\n
    6. expenses before retirement is always the amount not invested\n
    7. expenses after retirement is fixed after calculating them (this likely to change)\n
    this list is non-exhaustive

    :param ss_year:
    :param total_alloc_percent:
    :param age:
    :param percentages:
    :param starting_salary: salary to start at age 0
    :param tax_bracket: tax bracket to remain in for life
    :param retirement: retirement age from 0 index. should be number of years until retirement
    :param death: death age from 0 index. should be number of years until death. should be > retirement
    :param retirement_expenses_percent: percent of net worth from [0, 100] to take every year until you die
    :param salary_raise_rate: adjusted salary raise as a percent (where 1.0 == 1%) every year accounting for inflation
    :param investment_return_rate: adjusted return rate on all accounts every year accounting for inflation
    :param taxable_account_alloc_percent: amount of salary as a percent from [0, 100] to put into taxable account
        assets every year
    :param trad_start: starting amount in traditional account
    :param roth_start: starting amount in roth account
    :param taxable_account_start: starting amount in the taxable account
    :return: InvestmentResult containing breakdown of all years
    """
    # taxable_account_start = 10000
    # taxable_account = Account(taxable_account_start, AccountType.TAXABLE)
    # taxable_growth = taxable_account.create_growth(investment_return_rate / 100)
    # print(f"taxable account amount is {taxable_growth.account.amount}")
    # print(f"taxable account start amount is {taxable_account_start}")

    all_salaries = np.zeros([retirement - age])
    trad_account = Account(trad_start, AccountType.TRAD)
    roth_account = Account(roth_start, AccountType.ROTH)
    salary = Account(starting_salary)  # keep track of current salary
    salary_growth = salary.create_growth(salary_raise_rate / 100)
    trad_growth = trad_account.create_growth(investment_return_rate / 100)
    roth_growth = roth_account.create_growth(investment_return_rate / 100)
    expenses_percent = 100 - total_alloc_percent
    result = InvestmentResult()
    for y in range(age, retirement):
        trad_alloc_percent = percentages[y - age] * total_alloc_percent
        roth_alloc_percent = total_alloc_percent - trad_alloc_percent
        # taxable_account_alloc_percent = 0

        # determine amount of salary to allocate
        trad_alloc = salary.amount * trad_alloc_percent / 100
        roth_alloc = salary.amount * roth_alloc_percent / 100
        # taxable_alloc = salary.amount * taxable_account_alloc_percent / 100

        expenses = salary.amount * expenses_percent / 100
        # add all salaries to an array for social security calculation
        all_salaries[y - age] = int(salary.amount)

        # total_salary += salary.amount
        # print(f"total salary is {total_salary}")

        # compute contributions to roth and traditional accounts
        trad_cont = trad_account.create_contribution(trad_alloc)
        above_the_line = trad_cont.amount
        roth_cont = roth_account.create_roth_contribution(roth_alloc, tax_bracket, above_the_line, expenses)
        # taxable_account_cont = taxable_account.create_taxable_account_contribution(taxable_alloc, tax_bracket,
        #                                                                            below_the_line, expenses)
        # compute income
        income_result = IncomeResult(salary.amount, trad_cont.amount, 0, 0, tax_bracket)

        # TODO figure out why Roth contributions do not take trad. contribution into account?????????

        assert round(expenses + trad_alloc + roth_alloc, 2) == round(salary.amount, 2), \
            f"Money problem { expenses + trad_alloc + roth_alloc} != {salary.amount}"
        # assert round(income_result.income_tax.tax_paid, 2) == \
        #        round(roth_alloc - roth_cont.amount + tax_bracket.tax(expenses, below_the_line).tax_paid, 2), \
        #     f"{income_result.income_tax.tax_paid} != {salary.amount=} {trad_alloc=} {roth_alloc=} " \
        #     f"{roth_cont.amount=} {expenses=} {roth_alloc - roth_cont.amount} + " \
        #     f"{tax_bracket.tax(expenses, below_the_line).tax_paid} == " \
        #     f"{roth_alloc - roth_cont.amount + tax_bracket.tax(expenses, below_the_line).tax_paid}"

        # print Salary
        # print(f"Salary in year {y} is {salary.amount}.")

        # run investment year
        year_result = InvestmentYearResult(y, [trad_cont, roth_cont], [],
                                           [trad_growth, roth_growth], income_result)
        result.year_results.append(year_result)

        # get a raise. do this outside so it doesn't count it in the total amount
        salary_growth.grow()

    # retirement
    # TODO make sure that salary includes Traditional Distributions, make this faster
    # Social Security Calculations
    pia = get_pia(all_salaries)
    # print(f"PIA is ${PIA:,.2f}")
    ss_benefit = find_actual_social_security_benefit(pia, ss_year)
    # for x in range(61,71):
    #     print(f" ss benefit is ${find_actual_social_security_benefit(PIA, x):,.2f} during year {x}")

    # find social security taxable income
    pi_subject_to_income_tax = single_ss_bracket_2021.tax(pia, 0)
    social_security_taxable_income = pi_subject_to_income_tax.tax_paid

    retirement_expenses = salary.amount * retirement_expenses_percent / 100
    trad_strat = igwad.find_optimal_distribution_secant(trad_account.amount, investment_return_rate / 100, death - retirement)
    # print(f"igwad strat is ${trad_strat:,.2f}")
    # trad_strat = retirement_expenses

    # print(f"retirement T=${trad_account.amount}, R={roth_account.amount}")

    broke = False
    for y in range(retirement, death):
        # run years until we die. nothing being invested, but accounts still grow

        # compute distributions from roth and traditional accounts
        trad_dist, trad_dist_alloc = trad_account.create_trad_distribution(trad_strat, tax_bracket)
        needed_roth_dist_amount = retirement_expenses - trad_dist.amount

        # if traditional can cover expenses, this will be 0
        roth_dist = roth_account.create_distribution(needed_roth_dist_amount)
        roth_dist_alloc = roth_dist.amount

        # if roth_dist_alloc != 0:
        #     print(f"roth distribution is ${roth_dist_alloc:,.2f}!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

        # determine social security benefit
        # print(f"retirement is {retirement}, death is {death}, y is {y}")
        if y <= ss_year:
            social_security_benefit = 0
            # print(f"ss bene is {social_security_benefit} in year {y + 25}")
        else:
            social_security_benefit = ss_benefit
            # print(f"ss bene is {social_security_benefit} in year {y + 25}")

        # social_security_benefit = 0

        # compute income
        income_result = IncomeResult(0, 0, trad_dist_alloc, roth_dist_alloc, tax_bracket,
                                     social_security_benefit=social_security_benefit,
                                     taxable_social_security_income=social_security_taxable_income)

        # print Salary
        # print(f"Salary in year {y} is {income_result.taxable_income}.")

        # run investment year
        year_result = InvestmentYearResult(y, [], [trad_dist, roth_dist], [trad_growth, roth_growth], income_result)
        result.year_results.append(year_result)

        # see if broke
        if income_result.total_income < retirement_expenses - 0.001 and not broke:
            logging.debug(f"You're broke, fool. Your total income was ${income_result.total_income:.2f}. "
                          f"You needed ${retirement_expenses:.2f}. You had {death - y} years left. "
                          f"Strategy: {percentages}")
            broke = True

    return result


def simple_invest(retirement: int = 65, age: int = 25, trad_alloc_percent: float = 5, roth_alloc_percent: float = 5,
                  taxable_account_alloc_percent: float = 0, **kwargs) -> InvestmentResult:

    total = trad_alloc_percent + roth_alloc_percent + taxable_account_alloc_percent
    strategy = np.full(retirement - age, trad_alloc_percent / total)
    return array_invest(strategy, **kwargs)


def piecewise_invest(retirement: int = 65, age: int = 25, switch_year: int = 20, **kwargs) -> InvestmentResult:
    strategy = np.append(np.zeros(switch_year), np.ones(retirement - switch_year - age))
    return array_invest(strategy, **kwargs)


def linsweep_invest(retirement: int = 65, age: int = 25, slope_decision: float = 0.5, **kwargs) -> InvestmentResult:
    starting_roth = slope_decision
    ending_roth = 1 - slope_decision
    strategy = np.linspace(1 - starting_roth, 1 - ending_roth, retirement - age)
    print(strategy)
    return array_invest(strategy, **kwargs)


def linsweep2_invest(retirement: int = 65, age: int = 25, switch_year: int = 20, **kwargs) -> InvestmentResult:
    strategy = np.append(np.linspace(0, 1, switch_year), np.ones(retirement - switch_year - age))
    # print(strategy)
    return array_invest(strategy, **kwargs)


def linsweep3_invest(retirement: int = 65, age: int = 25, slope_decision: float = 0.5, **kwargs) -> InvestmentResult:
    starting_trad = slope_decision
    # ending_roth = 1
    strategy = np.linspace(starting_trad, 1, retirement - age)
    # print(strategy)
    return array_invest(strategy, **kwargs)


def linsweep4_invest(retirement: int = 65, age: int = 25, switch_year: int = 20, break_: int = 0, **kwargs) -> InvestmentResult:
    break_ = break_ / 1000 + .9
    # switch_year2 = switch_year

    strategy = np.append(np.linspace(0, break_, switch_year), np.linspace(break_, 1, (retirement - switch_year - age)))
    # print(strategy)
    return array_invest(strategy, **kwargs)


def quadratic_invest(retirement: int = 65, age: int = 25, break_: int = 0, **kwargs) -> InvestmentResult:
    strategy = np.ones(retirement - age)
    # a = -0.5
    b = 1
    c = 0
    a = (break_ + 1 / retirement - age) * .1 - 0.5
    print(f"a is {a}")
    input1 = np.linspace(0, 1, retirement - age)

    for x in range(retirement - age):
        y = (a * (input1[x] * input1[x])) + (b * input1[x]) + c
        # if a == 0:
        #     x_vertex = 0
        # else:
        #     x_vertex = -b / (2 * a)

        # y_vertex = (a * (x_vertex * x_vertex)) + (b * x_vertex) + c

        if (a + b + c) == 0:
            strategy[x] = 0
        else:
            strategy[x] = y / (a + b + c)
    print(strategy)

    # strategy = np.append(np.linspace(0, break1, switch_year), np.linspace(break1, 1, (retirement - switch_year)))
    # print(strategy)

    return array_invest(strategy, **kwargs)


def exp_invest(retirement: int = 65, age: int = 25, break_: int = 0, **kwargs) -> InvestmentResult:
    strategy = np.ones(retirement - age)
    # a = -0.5

    a = (break_ * 2) + 0.01
    print(f"a is {a}")
    input1 = np.linspace(-5, 0, retirement - age)

    for x in range(retirement - age):
        y = a * np.exp(input1[x])
        strategy[x] = (y / a)

    print(strategy)

    # strategy = np.append(np.linspace(0, break1, switch_year), np.linspace(break1, 1, (retirement - switch_year)))
    # print(strategy)
    return array_invest(strategy, **kwargs)


def log_invest(retirement: int = 65, age: int = 25, break_: int = 0, **kwargs) -> InvestmentResult:
    a = math.e ** break_
    print(f"a is {a}")

    def logfunc(x):
        return math.log(a * x + 1) / math.log(a + 1)

    np_log_func = np.vectorize(logfunc)
    strategy = np_log_func(np.linspace(0, 1, retirement - age))
    print(strategy)

    return array_invest(strategy, **kwargs)


def piecewise2_invest(retirement: int = 65, age: int = 25, switch_year: int = 20, switch_duration: int = 30, **kwargs):
    strategy = np.zeros(switch_year)
    strategy = np.append(strategy, np.linspace(0, 1, switch_duration))
    strategy = np.append(strategy, np.ones(retirement - age - switch_duration - switch_year))
    # print(strategy)

    return array_invest(strategy, **kwargs)


def erf_invest(retirement: int = 65, age: int = 25, a: float = 0.5, switch_year: int = 0, normalize=False, **kwargs):
    erf = np.vectorize(math.erf)
    offset = 1 - 2 * (switch_year / (retirement - age))
    strategy = 0.5 * (1 + erf(np.linspace(-1 + offset, 1 + offset, retirement - age) * (40 ** a)))
    if normalize:
        strategy -= strategy.min()
        strategy /= strategy.max()
    logging.debug(strategy)

    return array_invest(strategy, **kwargs)
