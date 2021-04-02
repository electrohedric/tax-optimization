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

    def tax(self, amount: float) -> float:
        """
        Computes the amount of tax deducted from the amount where only the
        amount within the range is taxed at the percent

        :param amount: total amount of money to tax
        :return: amount taxed
        """
        return self.amount_in_range(amount) * self.percent


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

    def tax(self, amount: float) -> float:
        """
        Computes the amount of tax deducted from the amount in a step pattern.
        The amount of money within the first range is deducted at it's taxable
        percent, moving onto subsequent ranges until all tax has been computed.

        :param amount: total amount of money to tax
        :return: amount taxed
        """
        total_taxed = 0.0
        for tr in self.tax_ranges:
            if tr.amount_in_range(amount) == 0.0:
                break  # no more can possibly be taxed since there's no money in the range and ranges always increase
            total_taxed += tr.tax(amount)
        return total_taxed
