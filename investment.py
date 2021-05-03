from enum import IntEnum
from typing import Tuple, Iterable

import numpy as np

from tax_brackets import TaxBracket


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
        
        :param amount: contribution allocation amount
        :return: a contribution matching the amount
        """
        return Account.Contribution(self, max(amount, 0))
    
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
    
    def create_roth_contribution(self, amount: float, tax_bracket: TaxBracket, margin: float) -> 'Account.Contribution':
        """
        Helper method to generate a traditional distribution and finds the allocation amount to take out 'amount'

        :param amount: contribution allocation amount
        :param tax_bracket: tax bracket to use to do tax calculations
        :param margin: margin to pass into the tax function.
            should be set so that this is taxed at the highest margin (most likely = expenses)
        :return: a distribution matching the amount
        """
        assert self.label == AccountType.ROTH
        # compute tax on allocation
        roth_tax = tax_bracket.tax(amount, 0, margin)
        return Account.Contribution(self, roth_tax.remaining())
    
    def create_trad_distribution(self, amount: float, tax_bracket: TaxBracket, below_the_line: float) -> Tuple['Account.Distribution', float]:
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
            amount = trad_dist_alloc - tax_bracket.tax(trad_dist_alloc, below_the_line).tax_paid
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
                 trad_dist_alloc_amount: float, roth_dist_amount: float, tax_bracket: TaxBracket):
        """
        Does all calculations and stores all results from taxing total income

        :param salary_amount: salary before tax
        :param below_the_line: any below the line deductions. probably standard deduction
        :param trad_cont_amount: final contribution amount to all traditional accounts
        :param trad_dist_alloc_amount: final distribution allocation amount from all traditional accounts.
            Either this or trad_cont_amount should be 0
        :param roth_dist_amount: final distribution (allocation) amount from all roth accounts
        :param tax_bracket: tax bracket computer to perform tax calculations
        """

        self.deductions = trad_cont_amount + below_the_line
        """sum of above the line + below the line deductions"""

        self.gross_income = salary_amount + trad_dist_alloc_amount
        """taxable income before deductions. salary + traditional distributions"""

        self.agi = self.gross_income - trad_cont_amount
        """adjusted gross income. salary + traditional distrubtions"""

        self.income_tax = tax_bracket.tax(self.gross_income, self.deductions)
        """tax result for the taxable income"""

        self.taxable_income = self.income_tax.real_taxable_amount()
        """gross income - tax deductions"""

        self.net_income = self.gross_income - self.income_tax.tax_paid
        """income after taxes. gross income - tax paid on income"""

        self.total_income = self.net_income + roth_dist_amount
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
        self.contributions = [c.put() for c in contributions]
        self.distributions = [d.take() for d in distributions]
        self.growth = [g.grow() for g in growths]
        self.income = income_result
    
    def net_worth(self) -> float:
        """
        :return: sum of ending amounts of all accounts at the end of the growth period, not including income
        """
        return sum([x.end_amount for x in self.growth])
    
    def total_contributions(self) -> float:
        """
        :return: sum of all contributions made to all investment accounts
        """
        return sum([x.change_amount for x in self.contributions])
    
    def total_distributions(self) -> float:
        """
        :return: sum of all distributions taken from all investment accounts
        """
        return sum([-x.change_amount for x in self.distributions])
    
    def total_growth(self) -> float:
        """
        :return: sum of all interest gained on all investment accounts
        """
        return sum([x.interest for x in self.growth])


def simple_invest(starting_salary: float, tax_bracket: TaxBracket, retirement: int = 40, death: int = 60,
                  retirement_expenses_percent: float = 70, below_the_line: float = 12550, salary_raise_rate: float = 0,
                  return_rate: float = 7, trad_alloc_percent: float = 5, roth_alloc_percent: float = 5,
                  trad_start: float = 0, roth_start: float = 0) -> InvestmentResult:
    """
    Performs a simple investment calculation. Makes several assumptions:
    1. salary increases steadily
    2. tax bracket never changes
    3. retirement age and death are known
    4. fixed return rate, interest rate, and standard deduction
    5. roth and traditional allocation percentages are constant
    6. expenses before retirement is always the amount not invested
    7. expenses after retirement is fixed after calculating them (this likely to change)
    this list is non-exhaustive

    :param starting_salary: salary to start at age 0
    :param tax_bracket: tax bracket to remain in for life
    :param retirement: retirement age from 0 index. should be number of years until retirement
    :param death: death age from 0 index. should be number of years until death. should be > retirement
    :param retirement_expenses_percent: percent of net worth from [0, 100] to take every year until you die
    :param below_the_line: standard deduction or any other below the line deduction
    :param salary_raise_rate: adjusted salary raise as a percent (where 1.0 == 1%) every year accounting for inflation
    :param return_rate: adjusted return rate on all accounts every year accounting for inflation
    :param trad_alloc_percent: amount of salary as a percent from [0, 100] to put into traditional assets every year
    :param roth_alloc_percent: amount of salary as a percent from [0, 100] to put into roth assets every year
    :param trad_start: starting amount in traditional account
    :param roth_start: starting amount in roth account
    :return: InvestmentResult containing breakdown of all years
    """
    trad_account = Account(trad_start, AccountType.TRAD)
    roth_account = Account(roth_start, AccountType.ROTH)
    salary = Account(starting_salary)  # keep track of current salary
    salary_growth = salary.create_growth(salary_raise_rate / 100)
    trad_growth = trad_account.create_growth(return_rate / 100)
    roth_growth = roth_account.create_growth(return_rate / 100)
    expenses_percent = 100 - (trad_alloc_percent + roth_alloc_percent)
    result = InvestmentResult()
    for y in range(retirement):
        # determine amount of salary to allocate
        trad_alloc = salary.amount * trad_alloc_percent / 100
        roth_alloc = salary.amount * roth_alloc_percent / 100
        expenses = salary.amount * expenses_percent / 100
    
        # compute contributions to roth and traditional accounts
        trad_cont = trad_account.create_contribution(trad_alloc)
        roth_cont = roth_account.create_roth_contribution(roth_alloc, tax_bracket, expenses)
    
        # compute income
        income_result = IncomeResult(salary.amount, below_the_line, trad_cont.amount, 0, 0, tax_bracket)
    
        # run investment year
        year_result = InvestmentYearResult(y, [trad_cont, roth_cont], [], [trad_growth, roth_growth], income_result)
        result.year_results.append(year_result)
    
        # get a raise. do this outside so it doesn't count it in the total amount
        salary_growth.grow()
    
    # retirement

    retirement_expenses = salary.amount * retirement_expenses_percent / 100

    broke = False
    for y in range(retirement, death):
        # run years until we die. nothing being invested, but accounts still grow
    
        # compute distributions from roth and traditional accounts
        trad_dist, trad_dist_alloc = trad_account.create_trad_distribution(retirement_expenses, tax_bracket, below_the_line)
        needed_roth_dist_amount = retirement_expenses - trad_dist.amount
        # if traditional can cover expenses, this will be 0
        roth_dist = roth_account.create_distribution(needed_roth_dist_amount)
        roth_dist_alloc = roth_dist.amount
    
        # compute income
        income_result = IncomeResult(0, below_the_line, 0, trad_dist_alloc, roth_dist_alloc, tax_bracket)
    
        # run investment year
        year_result = InvestmentYearResult(y, [], [trad_dist, roth_dist], [trad_growth, roth_growth], income_result)
        result.year_results.append(year_result)
    
        # see if broke
        if income_result.total_income < retirement_expenses - 0.001 and not broke:
            print(f"You're broke, fool. Your total income was ${income_result.total_income:.2f}. "
                  f"You needed ${retirement_expenses:.2f}. You had {death - y} years left")
            broke = True

    return result
