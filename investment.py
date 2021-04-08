import numpy as np


class InvestmentYearResult:
    def __init__(self, year, contribution, return_rate, start_balance):
        self.year = year
        self.contribution = contribution
        self.return_rate = return_rate
        self.start_balance = start_balance
        self.interest = start_balance * return_rate
        self.end_balance = start_balance + self.interest


class InvestmentResult:
    def __init__(self):
        self.year_results: list[InvestmentYearResult] = []

    def get_final_end_balance(self):
        return self.year_results[-1].end_balance

    def get_years(self):
        return np.array([x.year for x in self.year_results])

    def get_end_balances(self):
        return np.array([x.end_balance for x in self.year_results])


def invest(starting_amount: float, years: int, return_rates: np.ndarray, add_contributions: np.ndarray):
    assert len(add_contributions) == years
    assert len(return_rates) == years

    result = InvestmentResult()
    balance = starting_amount
    for y in range(years):
        year_result = InvestmentYearResult(y, add_contributions[y], return_rates[y], balance + add_contributions[y])
        result.year_results.append(year_result)
        balance = year_result.end_balance

    return result

