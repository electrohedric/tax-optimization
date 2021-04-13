from typing import Dict

from enum import IntEnum
import numpy as np

from tax_brackets import TaxBracket


class AccountType(IntEnum):
    TRAD = 0
    ROTH = 1


class BalanceChangeResult:
    def __init__(self, start_amount: float, change_amount: float):
        self.start_amount = start_amount
        self.change_amount = change_amount
        self.end_amount = self.start_amount + self.change_amount
    
    def is_contribution(self):
        return self.change_amount > 0


class GrowthResult:
    def __init__(self, start_amount: float, return_rate: float):
        self.start_amount = start_amount
        self.return_rate = return_rate
        self.interest = self.start_amount * self.return_rate
        self.end_amount = self.start_amount + self.interest


class InvestmentResult:
    def __init__(self):
        self.year_results: list[InvestmentYearResult] = []
    
    def get_final_net_worth(self):
        return self.year_results[-1].net_worth()
    
    def get_years(self):
        return np.array([x.year for x in self])
    
    def get_net_worths(self):
        return np.array([x.net_worth() for x in self])

    def get_total_roth_assets(self):
        return np.array([x.growth[AccountType.ROTH].end_amount for x in self])

    def get_total_trad_assets(self):
        return np.array([x.growth[AccountType.TRAD].end_amount for x in self])
    
    def get_taxes_paid(self):
        return np.array([x.income.income_tax.tax_paid for x in self])

    def get_total_incomes(self):
        return np.array([x.income.total_income for x in self])

    def __iter__(self):
        for x in self.year_results:
            yield x


class Account:
    def __init__(self, initial_amount: float = 0):
        self.amount = initial_amount
    
    def grow(self, return_rate: float) -> GrowthResult:
        result = GrowthResult(self.amount, return_rate)
        self.amount = result.end_amount
        return result
    
    def _change(self, amount: float) -> BalanceChangeResult:
        result = BalanceChangeResult(self.amount, amount)
        self.amount = result.end_amount
        return result
    
    def deposit(self, amount: float) -> BalanceChangeResult:
        return self._change(amount)
    
    def withdraw(self, amount: float) -> BalanceChangeResult:
        return self._change(-amount)


class Contribution:
    def __init__(self, account: Account, amount: float):
        self.account = account
        self.amount = amount
    
    def put(self) -> BalanceChangeResult:
        return self.account.deposit(self.amount)


class Distribution:
    def __init__(self, account: Account, amount: float):
        self.account = account
        self.amount = amount
    
    def take(self) -> BalanceChangeResult:
        return self.account.withdraw(self.amount)


class Growth:
    def __init__(self, account: Account, return_rate: float):
        self.account = account
        self.return_rate = return_rate
    
    def grow(self) -> GrowthResult:
        return self.account.grow(self.return_rate)


class IncomeResult:
    def __init__(self, salary_amount: float, below_the_line: float, trad_cont_amount: float,
                 trad_dist_alloc_amount: float, roth_dist_amount: float, tax_bracket: TaxBracket):
        self.deductions = trad_cont_amount + below_the_line  # above + below
        self.gross_income = salary_amount + trad_dist_alloc_amount
        self.agi = self.gross_income - trad_cont_amount  # adjusted gross income
        self.taxable_income = self.gross_income - self.deductions
        self.income_tax = tax_bracket.tax(self.taxable_income)
        self.net_income = self.gross_income - self.income_tax.tax_paid  # leftover dollars after tax is paid
        self.total_income = self.net_income + roth_dist_amount


class InvestmentYearResult:
    def __init__(self, year: int,
                 contributions: Dict[AccountType, Contribution],
                 distributions: Dict[AccountType, Distribution],
                 growths: Dict[AccountType, Growth],
                 income_result: IncomeResult):
        self.year = year
        self.contributions = [c.put() for c in contributions.values()]
        self.distributions = [d.take() for d in distributions.values()]
        self.growth = [g.grow() for g in growths.values()]
        self.income = income_result
    
    def net_worth(self):
        return sum([x.end_amount for x in self.growth])
    
    def total_contributions(self):
        return sum([x.change_amount for x in self.contributions])
    
    def total_distributions(self):
        return sum([-x.change_amount for x in self.distributions])
    
    def total_growth(self):
        return sum([x.interest for x in self.growth])


def simple_invest(starting_salary: float, tax_bracket: TaxBracket, retirement: int = 40, death: int = 60,
                  retirement_expenses_percent: float = 8, below_the_line: float = 12550, salary_raise_rate: float = 1,
                  return_rate: float = 7, trad_alloc_percent: float = 5, roth_alloc_percent: float = 5,
                  trad_start: float = 0, roth_start: float = 0) -> InvestmentResult:
    trad_account = Account(trad_start)
    roth_account = Account(roth_start)
    salary = Account(starting_salary)  # keep track of current salary
    salary_growth = Growth(salary, salary_raise_rate / 100)
    trad_growth = Growth(trad_account, return_rate / 100)
    roth_growth = Growth(roth_account, return_rate / 100)
    expenses_percent = 100 - (trad_alloc_percent + roth_alloc_percent)
    result = InvestmentResult()
    for y in range(retirement):
        # determine amount of salary to allocate
        trad_alloc = salary.amount * trad_alloc_percent / 100
        roth_alloc = salary.amount * roth_alloc_percent / 100
        
        expenses = salary.amount * expenses_percent / 100
        
        # compute tax on allocations
        trad_tax_contr_alloc = trad_alloc
        roth_tax_contr_alloc = tax_bracket.tax(roth_alloc, expenses)
        
        # compute how much is contributions to roth and traditional accounts
        trad_cont = Contribution(trad_account, trad_tax_contr_alloc)  # == trad_dist
        roth_cont = Contribution(roth_account, roth_tax_contr_alloc.leftover())
        
        # compute income
        income_result = IncomeResult(salary.amount, below_the_line, trad_cont.amount, 0, 0, tax_bracket)
        
        # run investment year
        year_result = InvestmentYearResult(y, {AccountType.TRAD: trad_cont, AccountType.ROTH: roth_cont}, {},
                                           {AccountType.TRAD: trad_growth, AccountType.ROTH: roth_growth}, income_result)
        result.year_results.append(year_result)
        
        # get a raise. do this outside so it doesn't count it in the total amount
        salary_growth.grow()
    
    # retirement

    retirement_expenses = result.get_final_net_worth() * retirement_expenses_percent / 100

    total_alloc_percent = roth_alloc_percent + trad_alloc_percent
    trad_dist_percent = trad_alloc_percent / total_alloc_percent
    roth_dist_percent = roth_alloc_percent / total_alloc_percent

    # "determine" amount to take in distributions
    trad_dist = Distribution(trad_account, retirement_expenses * trad_dist_percent)
    roth_dist = Distribution(roth_account, retirement_expenses * roth_dist_percent)

    trad_tax_dist_alloc = tax_bracket.tax(trad_dist.amount).tax_paid + trad_dist.amount
    roth_tax_dist_alloc = roth_dist.amount
    
    for y in range(retirement, death):
        # run years until we die. nothing being invested, but accounts still grow
        # roth_dist_alloc == roth_dist
        income_result = IncomeResult(0, below_the_line, 0, trad_tax_dist_alloc, roth_tax_dist_alloc, tax_bracket)
        year_result = InvestmentYearResult(y, {}, {AccountType.TRAD: trad_dist, AccountType.ROTH: roth_dist},
                                           {AccountType.TRAD: trad_growth, AccountType.ROTH: roth_growth}, income_result)
        result.year_results.append(year_result)
    return result
