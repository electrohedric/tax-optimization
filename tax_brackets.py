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

    def __str__(self):
        return f"${self.lower_bound:.2f} -> ${self.upper_bound:.2f} @ {self.percent:.1%}"


class TaxResult:
    def __init__(self):
        """
        Contains all tax information for a Tax Bracket
        """
        self.taxable_amount = 0
        self.margin = 0
        self.tax_paid = 0
        self.breakdown = []
    
    def leftover(self) -> float:
        return self.taxable_amount - self.tax_paid
    
    def real_taxable_amount(self) -> float:
        return max(self.taxable_amount, 0)

    def effective_tax_rate(self) -> float:
        return self.tax_paid / self.taxable_amount

    def real_effective_tax_rate(self) -> float:
        return max(self.effective_tax_rate(), 0)


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

    def tax(self, taxable_amount: float, margin: float = 0) -> TaxResult:
        """
        Computes the amount of tax deducted from the amount in a step pattern.
        The amount of money within the first range is deducted at it's taxable
        percent, moving onto subsequent ranges until all tax has been computed.

        :param taxable_amount: total amount of money to tax
        :param margin: amount to move the taxable amount up the bracket by. everything under the margin is taxed at 0%.
            thus: tax(a, margin=m) == tax(a+m) - tax(a)
        :return: amount taxed
        """
        tax = TaxResult()
        tax.taxable_amount = taxable_amount
        tax.margin = margin
        for tr in self.tax_ranges:
            if tr.amount_in_range(taxable_amount + margin) == 0.0:
                break  # no more can possibly be taxed since there's no money in the range and ranges always increase
            amount = tr.tax(taxable_amount + margin) - tr.tax(margin)
            tax.breakdown.append(amount)
            tax.tax_paid += amount
        return tax


ZERO_TAX = TaxBracket(TaxRange(0, float('inf'), 0))


