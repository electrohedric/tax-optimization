from typing import Iterable, List

import numpy as np

from tax_brackets import TaxBracket


class ContributionResult:
    def __init__(self, start_amount: float, put_amount: float, tax_payed: float):
        self.start_amount = start_amount
        self.put_amount = put_amount
        self.tax_payed = tax_payed
        self.net_amount = self.put_amount - self.tax_payed
        self.end_amount = self.start_amount + self.net_amount  # only net is contributed


class DistributionResult:
    def __init__(self, start_amount: float, take_amount: float, tax_payed: float):
        self.start_amount = start_amount
        self.take_amount = take_amount
        self.tax_payed = tax_payed
        self.net_amount = self.take_amount - self.tax_payed
        self.end_amount = self.start_amount - self.take_amount  # full amount is taken


class GrowthResult:
    def __init__(self, start_amount: float, return_rate: float):
        self.start_amount = start_amount
        self.return_rate = return_rate
        self.interest = self.start_amount * self.return_rate
        self.end_amount = self.start_amount + self.interest


class InvestmentYearResult:
    def __init__(self, year: int):
        self.year = year
        self.contributions: List[ContributionResult] = []
        self.distributions: List[DistributionResult] = []
        self.growth: List[GrowthResult] = []

    def total_end_amount(self):
        return sum([x.end_amount for x in self.growth])


class InvestmentResult:
    def __init__(self):
        self.year_results: list[InvestmentYearResult] = []

    def get_final_end_balance(self):
        return self.year_results[-1].total_end_amount()

    def get_years(self):
        return np.array([x.year for x in self.year_results])

    def get_end_balances(self):
        return np.array([x.total_end_amount() for x in self.year_results])


class Account:
    def __init__(self, initial_amount: float = 0):
        self.amount = initial_amount

    def grow(self, return_rate: float) -> GrowthResult:
        result = GrowthResult(self.amount, return_rate)
        self.amount = result.end_amount
        return result

    def deposit(self, amount: float, taxer: TaxBracket) -> ContributionResult:
        tax = taxer.tax(amount).tax_payed if self.tax_deposit() else 0
        result = ContributionResult(self.amount, amount, tax)
        self.amount = result.end_amount
        return result

    def tax_deposit(self) -> bool:
        return False

    def withdraw(self, amount: float, taxer: TaxBracket) -> DistributionResult:
        tax = taxer.tax(amount).tax_payed if self.tax_withdraw() else 0
        result = DistributionResult(self.amount, amount, tax)
        self.amount = result.end_amount
        return result

    def tax_withdraw(self):
        return False


class TraditionalAccount(Account):
    def tax_deposit(self) -> bool:
        return False

    def tax_withdraw(self):
        return True


class RothAccount(Account):
    def tax_deposit(self) -> bool:
        return True

    def tax_withdraw(self):
        return False


class Contribution:
    def __init__(self, account: Account, amount: float, taxer: TaxBracket):
        self.account = account
        self.amount = amount
        self.taxer = taxer

    def put(self) -> ContributionResult:
        return self.account.deposit(self.amount, self.taxer)


class Distribution:
    def __init__(self, account: Account, amount: float, taxer: TaxBracket):
        self.account = account
        self.amount = amount
        self.taxer = taxer

    def take(self) -> DistributionResult:
        return self.account.withdraw(self.amount, self.taxer)


class Growth:
    def __init__(self, account: Account, return_rate: float):
        self.account = account
        self.return_rate = return_rate

    def grow(self) -> GrowthResult:
        return self.account.grow(self.return_rate)


class InvestmentYear:
    def __init__(self, contributions: Iterable[Contribution], distributions: Iterable[Distribution], growths: Iterable[Growth]):
        self.contributions = contributions
        self.distributions = distributions
        self.growths = growths

    def compute(self, year: int) -> InvestmentYearResult:
        result = InvestmentYearResult(year)
        result.contributions = [c.put() for c in self.contributions]
        result.distributions = [d.take() for d in self.distributions]
        result.growth = [g.grow() for g in self.growths]
        return result


def simple_invest(starting_salary: float, tax_bracket: TaxBracket, retirement: int = 40, death: int = 60,
                  retire_income_percent: float = 8, below_the_line: float = 12550, salary_raise_rate: float = 1,
                  return_rate: float = 7, trad_cont_percent: float = 5, roth_cont_percent: float = 5,
                  trad_start: float = 0, roth_start: float = 0) -> InvestmentResult:
    trad_account = TraditionalAccount(trad_start)
    roth_account = RothAccount(roth_start)
    salary = Account(starting_salary)  # keep track of current salary
    salary_growth = Growth(salary, salary_raise_rate / 100)
    trad_growth = Growth(trad_account, return_rate / 100)
    roth_growth = Growth(roth_account, return_rate / 100)
    standard_account = TraditionalAccount()  # keep track of taxable income
    result = InvestmentResult()
    for y in range(retirement):
        # investing in both accounts, as a percentage of salary each year
        trad_cont = Contribution(trad_account, salary.amount * trad_cont_percent / 100, tax_bracket)
        roth_cont = Contribution(roth_account, salary.amount * roth_cont_percent / 100, tax_bracket)

        # compute salary
        deductions = trad_cont.amount + below_the_line  # above + below
        standard_account.amount = salary.amount - deductions  # set taxable income directly, minus deductions
        salary_dist = Distribution(standard_account, standard_account.amount, tax_bracket)  # take fully taxed income

        # run investment year
        invest_year = InvestmentYear([trad_cont, roth_cont], [salary_dist], [trad_growth, roth_growth])
        year_result = invest_year.compute(y)
        result.year_results.append(year_result)

        # get a raise. do this outside so it doesn't count it in the total amount
        salary_growth.grow()

    # retirement
    trad_dist_amount = trad_account.amount * retire_income_percent / 100
    roth_dist_amount = roth_account.amount * retire_income_percent / 100

    # taking out from both accounts
    trad_dist = Distribution(trad_account, trad_dist_amount, tax_bracket)
    roth_dist = Distribution(roth_account, roth_dist_amount, tax_bracket)
    for y in range(retirement, death):
        # run years until we die. nothing being invested, but accounts still grow
        invest_year = InvestmentYear([], [trad_dist, roth_dist], [trad_growth, roth_growth])
        year_result = invest_year.compute(y)
        result.year_results.append(year_result)
    return result
