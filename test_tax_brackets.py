from unittest import TestCase

from tax_brackets import TaxRange, TaxBracket


class Test(TestCase):
    def get_bracket(self):
        """
        :return: the 2021 single tax bracket
        """
        single_tax_ranges_2021 = (
            TaxRange(0, 9950, 0.10),
            TaxRange(9950, 40525, 0.12),
            TaxRange(40525, 86375, 0.22),
            TaxRange(86375, 164925, 0.24),
            TaxRange(164925, 209425, 0.32),
            TaxRange(209425, 523600, 0.35),
            TaxRange(523600, float('inf'), 0.37),
        )
        single_tax_bracket_2021 = TaxBracket(*single_tax_ranges_2021)
        return single_tax_bracket_2021

    def test_tax_bracket(self):
        """
        Tests the 2021 single tax bracket from all brackets and margins
        """
        single_tax_bracket_2021 = self.get_bracket()
        standard_deduction_2021 = 12550.00

        def test(amount, tax):
            self.assertAlmostEqual(single_tax_bracket_2021.tax(amount).tax_paid, tax)

        test(0, 0)
        test(5000, 500.00)
        test(5000 - standard_deduction_2021, 0.00)
        test(50000, 6748.50)
        test(100000, 18021.00)
        test(200000, 44827.00)
        test(300000, 79544.25)
        test(600000, 186072.25)

        def mtest(amount, margin):
            tax_upper = single_tax_bracket_2021.tax(amount + margin).tax_paid
            tax_lower = single_tax_bracket_2021.tax(margin).tax_paid
            tax_margin = single_tax_bracket_2021.tax(amount, margin).tax_paid
            self.assertAlmostEqual(tax_upper - tax_lower, tax_margin)

        mtest(0, 0)
        mtest(-100, 4000)
        mtest(1000, -4000)
        mtest(-100, -1000)
        mtest(100, 1000)
        mtest(20000, 1000)
        mtest(1000000, 40000)
        mtest(100, 20000)
        mtest(65002, 123456)
        mtest(42000, 232123)
        mtest(90000, 354123)
        mtest(4500, 654321)
