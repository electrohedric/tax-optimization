import logging
import math
from enum import IntEnum
from typing import Tuple, Iterable

import numpy as np
import igwad
import loader
from loader import load_tax_bracket
from tax_brackets import TaxBracket

single_tax_bracket_2021_AIME = load_tax_bracket("data/2021/AIME_benefit_calculation.csv")


class AccountType(IntEnum):
    """
    A hard value to specify an account type for dictionaries, etc.
    """
    OTHER = -1
    TRAD = 0
    ROTH = 1
    BROKERAGE = 2


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

    def get_taxes_paid(self) -> np.ndarray:
        """
        :return: array of the tax paid on total income from each year
        """
        return np.array([x.income.income_tax.tax_paid for x in self])

    def get_total_trad_assets_post_tax(self, tax_bracket: TaxBracket) -> np.ndarray:
        """
        Computes total net worth after tax is taken out on traditional
        
        :param tax_bracket: tax function to use to tax
        :return: array of the net worth after taxes are taken out from each year,
            assuming full amount is taken as distributions (no deductions are taken, rough calculation)
        """
        trad = self.get_total_trad_assets()
        vfunc = np.vectorize(lambda x: tax_bracket.tax(x, 0).remaining())
        trad_taxed = vfunc(trad)
        return trad_taxed

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
        return Account.Distribution(self, min(max(self.amount, 0), amount))

    def create_roth_contribution(self, amount: float, tax_bracket: TaxBracket, deductions: float, margin: float) -> 'Account.Contribution':
        """
        Helper method to generate a traditional distribution and finds the allocation amount to take out 'amount'

        :param amount: contribution allocation amount
        :param tax_bracket: tax bracket to use to do tax calculations
        :param deductions: deductions to take
        :param margin: margin to pass into the tax function.
            should be set so that this is taxed at the highest margin (most likely = expenses)
        :return: a distribution matching the amount
        """
        assert self.label == AccountType.ROTH
        # compute tax on allocation
        roth_tax_rem = amount - tax_bracket.fast_tax(amount, deductions, margin)
        max_cont = Account.Contribution.LIMITS.get(self.label)
        return Account.Contribution(self, min(roth_tax_rem, max_cont))

    def create_trad_distribution(self, amount: float, tax_bracket: TaxBracket, below_the_line: float) -> Tuple[
        'Account.Distribution', float]:
        """
        Helper method to generate a traditional distribution and finds the allocation amount to take out 'amount'

        :param amount: amount to take in distributions
        :param tax_bracket: tax bracket to use to do tax calculations
        :param below_the_line: sum of below the line deductions
        :return: a distribution matching the amount
        """
        assert self.label == AccountType.TRAD
        # test can't allocate more than in trad account
        trad_dist_alloc = tax_bracket.reverse_tax(amount, below_the_line)
        if self.amount < trad_dist_alloc:  # can't take out full amount in trad
            # allocation is the full amount in the account
            trad_dist_alloc = self.amount
            # recompute the actual distributable amount
            amount = trad_dist_alloc - tax_bracket.fast_tax(trad_dist_alloc, below_the_line)
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
    def __init__(self, salary_amount: float, below_the_line: float, trad_cont_amount: float,
                 trad_dist_alloc_amount: float, roth_dist_amount: float, tax_bracket: TaxBracket,
                 social_security_benefit: float = 0, taxable_social_security_income: float = 0):
        """
        Does all calculations and stores all results from taxing total income

        :param salary_amount: salary before tax
        :param below_the_line: any below the line deductions. probably standard deduction
        :param trad_cont_amount: final contribution amount to all traditional accounts
        :param trad_dist_alloc_amount: final distribution allocation amount from all traditional accounts.
            Either this or trad_cont_amount should be 0
        :param roth_dist_amount: final distribution (allocation) amount from all roth accounts
        :param tax_bracket: tax bracket computer to perform tax calculations
        :param social_security_benefit: this years anual social security benefit
        """
        self.deductions = trad_cont_amount + below_the_line
        """sum of above the line + below the line deductions"""

        self.salary = salary_amount
        """salary before deductions"""

        self.gross_income = salary_amount + trad_dist_alloc_amount + taxable_social_security_income
        """taxable income before deductions. salary + traditional distributions"""

        # TODO: fix agi and deduction calculations
        self.agi = self.gross_income - trad_cont_amount
        """adjusted gross income. salary + traditional distrubtions"""

        self.income_tax = tax_bracket.fast_tax(self.gross_income, self.deductions)
        """tax result for the taxable income"""

        self.taxable_income = self.gross_income - self.deductions
        """gross income - tax deductions"""

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
        :param growths: dictionary mapping an ccount type to an actual growth for an account of that type
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
        self.income = 70000
        self.salary_raise_rate = 1
        self.investment_return_rate = 7
        self.trad_alloc_percent = 4
        self.roth_alloc_percent = 4
        self.percent_salary_expenses = 100
        self.tax_bracket = loader.load_tax_bracket("data/2021/single_tax.csv")

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


def get_PIA(all_salaries: np.ndarray):
    amount = sum_largest_values_in_array(all_salaries, 35)
    # print(f"salaries are ${amount:,.2f}")
    average_index_monthly_earnings = amount / 420
    # print(f"AIME is ${average_index_monthly_earnings:,.2f}")
    PIA = single_tax_bracket_2021_AIME.tax(average_index_monthly_earnings, 0)
    # PIA = primary insurance amount
    # print(f"PIA is ${PIA.tax_paid:,.2f}")
    return PIA.tax_paid


def find_actual_social_security_benefit(PIA, year) -> float:
    if year > 70 or year < 62:
        print("invalid year to take social security")
        return 0

    # 62 <= year <= 70
    social_security_benefit = 0.0
    if year <= 63:
        social_security_benefit = (PIA * 12) * (1 + ((year - 64) * 0.05) - 0.1998)
        # print(f"social security_benefit is ${social_security_benefit/12:,.2f} at age {year}")
    elif year <= 66:
        social_security_benefit = (PIA * 12) * (1 + ((year - 67) * 0.0666))
        # print(f"social security_benefit is ${social_security_benefit/12:,.2f} at age {year}")
    else:  # <= 70
        social_security_benefit = (PIA * 12) * (1 + ((year - 67) * 0.08))
        # print(f"social security_benefit is ${social_security_benefit/12:,.2f} at age {year}")

    return social_security_benefit


def array_invest(percentages: np.ndarray, starting_salary: float, tax_bracket: TaxBracket, retirement: int = 40,
                 death: int = 60, retirement_expenses_percent: float = 70, below_the_line: float = 12550,
                 salary_raise_rate: float = 1, investment_return_rate: float = 7, total_alloc_percent: float = 10,
                 trad_start: float = 0, roth_start: float = 0, ss_year: int = 70) -> InvestmentResult:
    """

    :param percentages: % of total allocation traditional contributions
    :param starting_salary:
    :param tax_bracket:
    :param retirement:
    :param death:
    :param retirement_expenses_percent:
    :param below_the_line:
    :param salary_raise_rate:
    :param investment_return_rate:
    :param total_alloc_percent:
    :param trad_start:
    :param roth_start:
    :param ss_year:
    :return:
    """

    all_salaries = np.zeros([retirement])
    trad_account = Account(trad_start, AccountType.TRAD)
    roth_account = Account(roth_start, AccountType.ROTH)
    salary = Account(starting_salary)  # keep track of current salary
    salary_growth = salary.create_growth(salary_raise_rate / 100)
    trad_growth = trad_account.create_growth(investment_return_rate / 100)
    roth_growth = roth_account.create_growth(investment_return_rate / 100)
    expenses_percent = 100 - total_alloc_percent
    result = InvestmentResult()
    for y in range(retirement):
        trad_alloc_percent = percentages[y] * total_alloc_percent
        roth_alloc_percent = total_alloc_percent - trad_alloc_percent

        # determine amount of salary to allocate
        trad_alloc = salary.amount * trad_alloc_percent / 100
        roth_alloc = salary.amount * roth_alloc_percent / 100
        expenses = salary.amount * expenses_percent / 100
        # add all salaries to an array for social security calculation
        all_salaries[y] = int(salary.amount)

        # total_salary += salary.amount
        # print(f"total salary is {total_salary}")

        # compute contributions to roth and traditional accounts
        trad_cont = trad_account.create_contribution(trad_alloc)
        roth_cont = roth_account.create_roth_contribution(roth_alloc, tax_bracket, below_the_line, expenses)

        # compute income
        income_result = IncomeResult(salary.amount, below_the_line, trad_cont.amount, 0, 0, tax_bracket)
        # TODO figure out why Roth conrtibutions do not take trad. contribtuion into account?????????
        # assert round(expenses + trad_alloc + roth_alloc, 2) == round(salary.amount, 2), f"Money problem { expenses + trad_alloc + roth_alloc} != {salary.amount}"
        # assert round(income_result.income_tax.tax_paid, 2) == round(roth_alloc - roth_cont.amount + tax_bracket.tax(expenses, below_the_line).tax_paid, 2), \
        #     f"{income_result.income_tax.tax_paid} != {salary.amount=} {trad_alloc=} {roth_alloc=} {roth_cont.amount=} {expenses=} {roth_alloc - roth_cont.amount} + {tax_bracket.tax(expenses, below_the_line).tax_paid} == {roth_alloc - roth_cont.amount + tax_bracket.tax(expenses, below_the_line).tax_paid}"

        # run investment year
        year_result = InvestmentYearResult(y, [trad_cont, roth_cont], [], [trad_growth, roth_growth], income_result)
        result.year_results.append(year_result)

        # get a raise. do this outside so it doesn't count it in the total amount
        salary_growth.grow()

    # retirement
    # TODO make sure that salary includes Traditional Distributions, make this faster
    # Social Security Calculations
    PIA = get_PIA(all_salaries)
    # print(f"PIA is ${PIA:,.2f}")
    ss_benefit = find_actual_social_security_benefit(PIA, ss_year)
    # for x in range(61,71):
    #     print(f" ss benefit is ${find_actual_social_secruity_benefit(PIA, x):,.2f} durring year {x}")
    #

    retirement_expenses = salary.amount * retirement_expenses_percent / 100
    trad_strat = igwad.find_optimal_distribution_secant(trad_account.amount, investment_return_rate / 100, death-retirement)
    # trad_strat = retirement_expenses

    broke = False
    for y in range(retirement, death):
        # run years until we die. nothing being invested, but accounts still grow

        # compute distributions from roth and traditional accounts
        trad_dist, trad_dist_alloc = trad_account.create_trad_distribution(trad_strat, tax_bracket, below_the_line)
        needed_roth_dist_amount = retirement_expenses - trad_dist.amount
        # if traditional can cover expenses, this will be 0
        roth_dist = roth_account.create_distribution(needed_roth_dist_amount)
        roth_dist_alloc = roth_dist.amount

        # determin social security benefit
        if retirement <= ss_year:
            social_security_benefit = 0
        else:
            social_security_benefit = ss_benefit

        # social_security_benefit = 0

        # compute income
        income_result = IncomeResult(0, below_the_line, 0, trad_dist_alloc, roth_dist_alloc, tax_bracket, social_security_benefit)

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


def simple_invest(starting_salary: float, tax_bracket: TaxBracket, retirement: int = 40, death: int = 60,
                  retirement_expenses_percent: float = 70, below_the_line: float = 12550, salary_raise_rate: float = 0,
                  investment_return_rate: float = 7, trad_alloc_percent: float = 5, roth_alloc_percent: float = 5,
                  trad_start: float = 0, roth_start: float = 0, **_) -> InvestmentResult:
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

    :param starting_salary: salary to start at age 0
    :param tax_bracket: tax bracket to remain in for life
    :param retirement: retirement age from 0 index. should be number of years until retirement
    :param death: death age from 0 index. should be number of years until death. should be > retirement
    :param retirement_expenses_percent: percent of net worth from [0, 100] to take every year until you die
    :param below_the_line: standard deduction or any other below the line deduction
    :param salary_raise_rate: adjusted salary raise as a percent (where 1.0 == 1%) every year accounting for inflation
    :param investment_return_rate: adjusted return rate on all accounts every year accounting for inflation
    :param trad_alloc_percent: amount of salary as a percent from [0, 100] to put into traditional assets every year
    :param roth_alloc_percent: amount of salary as a percent from [0, 100] to put into roth assets every year
    :param trad_start: starting amount in traditional account
    :param roth_start: starting amount in roth account
    :return: InvestmentResult containing breakdown of all years
    """
    total = trad_alloc_percent + roth_alloc_percent
    strategy = np.full(retirement, trad_alloc_percent / total)
    return array_invest(strategy, starting_salary, tax_bracket, retirement, death, retirement_expenses_percent,
                        below_the_line, salary_raise_rate, investment_return_rate, total, trad_start, roth_start)


def piecewise_invest(starting_salary: float, tax_bracket: TaxBracket, retirement: int = 40, death: int = 60,
                     retirement_expenses_percent: float = 70, below_the_line: float = 12550,
                     salary_raise_rate: float = 1,
                     investment_return_rate: float = 7, total_alloc_percent: float = 8, switch_year: int = 20,
                     trad_start: float = 0, roth_start: float = 0, **_) -> InvestmentResult:
    strategy = np.append(np.zeros(switch_year), np.ones(retirement - switch_year))
    return array_invest(strategy, starting_salary, tax_bracket, retirement, death, retirement_expenses_percent,
                        below_the_line, salary_raise_rate, investment_return_rate, total_alloc_percent,
                        trad_start, roth_start)


def linsweep_invest(starting_salary: float, tax_bracket: TaxBracket, retirement: int = 40, death: int = 60,
                    retirement_expenses_percent: float = 70, below_the_line: float = 12550,
                    salary_raise_rate: float = 1,
                    investment_return_rate: float = 7, total_alloc_percent: float = 8, slope_decision: float = 0.5,
                    trad_start: float = 0, roth_start: float = 0, **_) -> InvestmentResult:
    starting_roth = slope_decision
    ending_roth = 1 - slope_decision
    strategy = np.linspace(1 - starting_roth, 1 - ending_roth, retirement)
    # print(strategy)
    return array_invest(strategy, starting_salary, tax_bracket, retirement, death, retirement_expenses_percent,
                        below_the_line, salary_raise_rate, investment_return_rate, total_alloc_percent,
                        trad_start, roth_start)


def linsweep2_invest(starting_salary: float, tax_bracket: TaxBracket, retirement: int = 40, death: int = 60,
                     retirement_expenses_percent: float = 70, below_the_line: float = 12550,
                     salary_raise_rate: float = 1,
                     investment_return_rate: float = 7, total_alloc_percent: float = 8, switch_year: int = 20,
                     trad_start: float = 0, roth_start: float = 0, **_) -> InvestmentResult:
    strategy = np.append(np.linspace(0, 1, switch_year), np.ones(retirement - switch_year))
    # print(strategy)
    return array_invest(strategy, starting_salary, tax_bracket, retirement, death, retirement_expenses_percent,
                        below_the_line, salary_raise_rate, investment_return_rate, total_alloc_percent,
                        trad_start, roth_start)


def linsweep3_invest(starting_salary: float, tax_bracket: TaxBracket, retirement: int = 40, death: int = 60,
                     retirement_expenses_percent: float = 70, below_the_line: float = 12550,
                     salary_raise_rate: float = 1,
                     investment_return_rate: float = 7, total_alloc_percent: float = 8, slope_decision: float = 0.5,
                     trad_start: float = 0, roth_start: float = 0, **_) -> InvestmentResult:
    starting_trad = slope_decision
    ending_roth = 1
    strategy = np.linspace(starting_trad, 1, retirement)
    # print(strategy)
    return array_invest(strategy, starting_salary, tax_bracket, retirement, death, retirement_expenses_percent,
                        below_the_line, salary_raise_rate, investment_return_rate, total_alloc_percent,
                        trad_start, roth_start)


def linsweep4_invest(starting_salary: float, tax_bracket: TaxBracket, retirement: int = 40, death: int = 60,
                     retirement_expenses_percent: float = 70, below_the_line: float = 12550,
                     salary_raise_rate: float = 1,
                     investment_return_rate: float = 7, total_alloc_percent: float = 8, switch_year: int = 20,
                     trad_start: float = 0, roth_start: float = 0, break1: int = 0, **_) -> InvestmentResult:
    break1 = break1 / 1000 + .9
    switch_year2 = switch_year

    strategy = np.append(np.linspace(0, break1, switch_year), np.linspace(break1, 1, (retirement - switch_year)))
    # print(strategy)
    return array_invest(strategy, starting_salary, tax_bracket, retirement, death, retirement_expenses_percent,
                        below_the_line, salary_raise_rate, investment_return_rate, total_alloc_percent,
                        trad_start, roth_start)


def quadratic_invest(starting_salary: float, tax_bracket: TaxBracket, retirement: int = 40, death: int = 60,
                     retirement_expenses_percent: float = 70, below_the_line: float = 12550,
                     salary_raise_rate: float = 1,
                     investment_return_rate: float = 7, total_alloc_percent: float = 8, switch_year: int = 20,
                     trad_start: float = 0, roth_start: float = 0, break1: int = 0, **_) -> InvestmentResult:
    strategy = np.ones(retirement)
    a = -0.5
    b = 1
    c = 0
    a = (break1 + 1 / retirement) * .1 - 0.5
    print(f"a is {a}")
    input1 = np.linspace(0, 1, retirement)

    for x in range(retirement):
        y = (a * (input1[x] * input1[x])) + (b * input1[x]) + c
        if a == 0:
            x_vertex = 0
        else:
            x_vertex = -b / (2 * a)

        y_vertex = (a * (x_vertex * x_vertex)) + (b * x_vertex) + c

        if (a + b + c) == 0:
            strategy[x] = 0
        else:
            strategy[x] = y / (a + b + c)
    print(strategy)

    # strategy = np.append(np.linspace(0, break1, switch_year), np.linspace(break1, 1, (retirement - switch_year)))
    # print(strategy)
    return array_invest(strategy, starting_salary, tax_bracket, retirement, death, retirement_expenses_percent,
                        below_the_line, salary_raise_rate, investment_return_rate, total_alloc_percent,
                        trad_start, roth_start)


def exp_invest(starting_salary: float, tax_bracket: TaxBracket, retirement: int = 40, death: int = 60,
               retirement_expenses_percent: float = 70, below_the_line: float = 12550, salary_raise_rate: float = 1,
               investment_return_rate: float = 7, total_alloc_percent: float = 8, switch_year: int = 20,
               trad_start: float = 0, roth_start: float = 0, break1: int = 0, **_) -> InvestmentResult:
    strategy = np.ones(retirement)
    a = -0.5

    a = (break1 * 2) + 0.01
    print(f"a is {a}")
    input1 = np.linspace(-5, 0, retirement)

    for x in range(retirement):
        y = a * np.exp(input1[x])

        strategy[x] = (y / a)
    print(strategy)

    # strategy = np.append(np.linspace(0, break1, switch_year), np.linspace(break1, 1, (retirement - switch_year)))
    # print(strategy)
    return array_invest(strategy, starting_salary, tax_bracket, retirement, death, retirement_expenses_percent,
                        below_the_line, salary_raise_rate, investment_return_rate, total_alloc_percent,
                        trad_start, roth_start)


def log_invest(starting_salary: float, tax_bracket: TaxBracket, retirement: int = 40, death: int = 60,
               retirement_expenses_percent: float = 70, below_the_line: float = 12550, salary_raise_rate: float = 1,
               investment_return_rate: float = 7, total_alloc_percent: float = 8, switch_year: int = 20,
               trad_start: float = 0, roth_start: float = 0, break_: int = 0, **_) -> InvestmentResult:
    a = math.e ** break_
    print(f"a is {a}")

    def logfunc(x):
        return math.log(a * x + 1) / math.log(a + 1)

    nplogfunc = np.vectorize(logfunc)
    strategy = nplogfunc(np.linspace(0, 1, retirement))
    print(strategy)

    return array_invest(strategy, starting_salary, tax_bracket, retirement, death, retirement_expenses_percent,
                        below_the_line, salary_raise_rate, investment_return_rate, total_alloc_percent,
                        trad_start, roth_start)


def piecewise2_invest(switch_year: int = 20, switch_duration: int = 30, **kwargs):
    strategy = np.zeros(switch_year)
    strategy = np.append(strategy, np.linspace(0, 1, switch_duration))
    strategy = np.append(strategy, np.ones(kwargs["retirement"] - switch_duration - switch_year))
    # print(strategy)

    return array_invest(strategy, **kwargs)


def erf_invest(a: float = 0.5, switch_year: int = 0, normalize=False, **kwargs):
    erf = np.vectorize(math.erf)
    offset = 1 - 2 * (switch_year / kwargs["retirement"])
    strategy = 0.5 * (1 + erf(np.linspace(-1 + offset, 1 + offset, kwargs["retirement"]) * (40 ** a)))
    if normalize:
        strategy -= strategy.min()
        strategy /= strategy.max()
    logging.debug(strategy)

    return array_invest(strategy, **kwargs)
