import bisect
import functools
import logging
from typing import List

import numpy as np


class TaxRange:
    def __init__(self, lower_bound: float, upper_bound: float, percent: float):
        """
        A taxable range for ease in computing tax brackets

        :param lower_bound: lower money bound, exclusive. Must be less than upper_bound
        :param upper_bound: upper money bound, inclusive. Must be greater than lower_bound
        :param percent: percent in range [0, 1] to multiply some amount by within this range
        """
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound
        self.percent = percent

        # ensure bounds and percent are what we expect
        assert self.upper_bound >= self.lower_bound, "Bad upper and lower bounds"
        assert 0 <= self.percent <= 1, "Percent not between 0 and 1"

    def amount_in_range(self, total: float):
        """
        Computes the amount of the total that is within the range.
        e.g. if the range is $10.00 -> $25.00 and the total is $15.00,
        the amount_in_range is $5.00. Handles $0.00 lower bound and $INF upper bound.

        :param total: money amount
        :return: amount within the range (taxable amount)
        """
        return min(max(total - self.lower_bound, 0), self.upper_bound - self.lower_bound)

    def tax(self, taxable_amount: float) -> float:
        """
        Computes the amount of tax deducted from the amount where only the
        amount within the range is taxed at the percent

        :param taxable_amount: total amount of money to tax
        :return: amount taxed
        """
        return self.amount_in_range(taxable_amount) * self.percent
    
    def __lt__(self, other):
        return self.upper_bound < other
    
    def __str__(self):
        return f"${self.lower_bound:.2f} -> ${self.upper_bound:.2f} @ {self.percent:.2%}"


class TaxResult:
    def __init__(self):
        """
        Contains all tax information for a Tax Bracket
        """
    
        self.full_amount = 0
        """Full amount, not including deductions"""
    
        self.taxable_amount = 0
        """Amount including deductions which was the actual amount sent through the tax bracket"""
    
        self.margin = 0
        """Amount taxable amount was increased by to raise the bracket"""
    
        self.tax_paid = 0
        """Total amount of taxes paid on the taxable amount"""
    
        self.breakdown: List[float] = []
        """Contains the breakdown of how much each tax range contributed to the final taxed amount.
            Index 0 corresponds to the zeroth tax range in the tax bracket used"""

    def remaining(self):
        """
        :return: Amount left over after taxes are taken out
        """
        return self.full_amount - self.tax_paid

    def real_taxable_amount(self) -> float:
        """
        :return: non-negative taxable amount
        """
        return max(self.taxable_amount, 0)

    def real_effective_tax_rate(self) -> float:
        """
        :return: non-negative effective tax rate (taxes paid / full amount)
        """
        if self.full_amount == 0:
            return 0
        return self.tax_paid / self.full_amount


class TaxBracket:
    def __init__(self, *tax_ranges: TaxRange):
        """
        A tax bracket consisting of multiple tax ranges for computing taxes

        :param tax_ranges: All tax ranges, starting from 0.00 and ending at infinity.
            there can be no gap between the end of one range and the start of the next
        """
        self.tax_ranges = tax_ranges

        # ensure extreme lower bounds and upper bounds are what we expect
        assert self.tax_ranges[0].lower_bound == 0.0, "Lower bound not 0"
        assert self.tax_ranges[-1].upper_bound == float('inf'), "Upper bound not infinity"
        # ensure boundaries have no gaps
        for i in range(len(self.tax_ranges) - 1):
            assert self.tax_ranges[i].upper_bound == self.tax_ranges[i + 1].lower_bound, "Gap between lower and upper bounds"

        # precompute fixed tax amounts within the ranges
        range_tax_amounts = [0.] + [(x.upper_bound - x.lower_bound) * x.percent for x in self.tax_ranges[:-1]]
        self.cum_range_tax_amounts = np.cumsum(range_tax_amounts)

    def tax(self, full_amount: float, deduction: float, margin: float = 0) -> TaxResult:
        """
        Computes the amount of tax deducted from the amount in a step pattern.
        The amount of money within the first range is deducted at it's taxable
        percent, moving onto subsequent ranges until all tax has been computed.

        :param full_amount: amount to tax (like income) without any deductions
        :param deduction: amount to subtract from 'full_amount' where 'full_amount' - this == taxable amount
        :param margin: amount to move the taxable amount up the bracket by. everything under the margin is taxed at 0%.
            thus: tax(a, margin=m) == tax(a+m) - tax(a)
        :return: amount taxed as a nice result with full breakdown
        """
        tax = TaxResult()
        tax.full_amount = full_amount
        tax.taxable_amount = full_amount - deduction
        tax.margin = margin
        if tax.taxable_amount + margin <= 0 or margin < 0:  # can't tax a non-positive amount
            return tax  # (0)
        if margin > 0:
            upper = self.tax(full_amount + margin, deduction)
            lower = self.tax(margin, deduction)
            tax.tax_paid = upper.tax_paid - lower.tax_paid
            # TODO: if you feel like it add a breakdown
            return tax
        for tr in self.tax_ranges:
            if tr.amount_in_range(tax.taxable_amount + margin) == 0.0:
                break  # no more can possibly be taxed since there's no money in the range and ranges always increase
            amount = tr.tax(tax.taxable_amount + margin) - tr.tax(margin)
            tax.breakdown.append(amount)
            tax.tax_paid += amount
        return tax
    
    def fast_tax(self, full_amount: float, deduction: float, margin: float = 0) -> float:
        """
        Faster method which computes the amount of tax deducted from the amount in a step pattern.
        The amount of money within all preceding ranges is precomputed to save time. Also, no
        TaxResult object initialization takes place. Note that this method does not have a breakdown
        available for this reason.

        :param full_amount: amount to tax (like income) without any deductions
        :param deduction: amount to subtract from 'full_amount' where 'full_amount' - this == taxable amount
        :param margin: amount to move the taxable amount up the bracket by. everything under the margin is taxed at 0%.
            thus: tax(a, margin=m) == tax(a+m) - tax(a)
        :return: amount taxed as a float
        """
        taxable_amount = full_amount - deduction
        if taxable_amount + margin <= 0 or margin < 0:
            return 0
        if margin > 0:
            return self.fast_tax(margin + full_amount, deduction) - self.fast_tax(margin, deduction)
        # find first tax range where the upper bound is less than the taxable amount
        partial_index = bisect.bisect_left(self.tax_ranges, taxable_amount)
        partial_tr = self.tax_ranges[partial_index]
        # compute amount in that range, given that lower_bound < taxable_amount <= upper_bound
        partial_amount = (taxable_amount - partial_tr.lower_bound) * partial_tr.percent
        # add the sum of all previous tax ranges (pre-computed) to the result
        return self.cum_range_tax_amounts[partial_index] + partial_amount
        
    
    @functools.cache
    def reverse_tax(self, final_amount: float, deduction: float, margin: float = 0, epsilon: float = 1e-2, iters=20):
        """
        Computes the reverse of a tax using a newton-like recursive method.
        i.e. the amount of money that needs to be taxed to result in 'final_amount' leftover.
        In other words: tax(?) == 'final_amount'
        
        :param final_amount: amount required to be left over after tax is taken out
        :param deduction: deduction to take out of tax (likely is standard deduction)
        :param margin: amount to move the taxable amount up the bracket by. everything under the margin is taxed at 0%.
            thus: tax(a, margin=m) == tax(a+m) - tax(a)
        :param epsilon: fine-grainness of the result.
        :param iters: maximum number of iterations before returning the final answer.
            Most reasonable epsilons result in around 12 iters on average
        :return:
        """
        guess = final_amount
        for i in range(iters):
            leftover = self.tax(guess, deduction, margin).remaining()
            off = final_amount - leftover
            guess += off
            if abs(off) < epsilon:
                return guess
        # U+03B5 is epsilon
        logging.warning(f"Could not find solution to tax(?, {deduction=}, {margin=}) == {final_amount} with \u03B5={epsilon} after {iters} iters")
        return guess

    def __str__(self):
        return self.__class__.__name__ + "\n" + "\n".join([str(x) for x in self.tax_ranges])


class Tax:
    def __init__(self, tax_brackets: List[TaxBracket], standard_deductions: List[float]):
        assert len(tax_brackets) == len(standard_deductions), "Bracket length != SD length"
        self.tax_brackets = tax_brackets
        self.standard_deductions = standard_deductions

    def tax(self, full_amount: float) -> float:
        total_taxed = 0
        for tb, sd in zip(self.tax_brackets, self.standard_deductions):
            total_taxed += tb.tax(full_amount, sd).tax_paid
        return total_taxed

    @functools.cache
    def reverse_tax(self, final_amount: float, epsilon: float = 1e-2, iters=20):
        guess = final_amount
        for i in range(iters):
            leftover = guess - self.tax(guess)
            off = final_amount - leftover
            guess += off
            if abs(off) < epsilon:
                return guess
        # U+03B5 is epsilon
        logging.warning(f"Could not find solution to tax(?) == {final_amount} with \u03B5={epsilon} after {iters} iters")
        return guess


ZERO_TAX = TaxBracket(TaxRange(0, float('inf'), 0))
