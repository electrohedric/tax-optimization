from unittest import TestCase

import loader


class Test(TestCase):
    def test_tax_bracket(self):
        """
        Tests the 2021 single tax bracket from all brackets and margins
        """
        single_tax_bracket_2021 = loader.load_tax_bracket("data/2021/single_tax.csv")
        standard_deduction_2021 = 12550.00

        def test(amount, tax):
            # test that the tax paid is correct and also the deduction works
            d0 = single_tax_bracket_2021.tax(amount, 0)
            ds = single_tax_bracket_2021.tax(amount, standard_deduction_2021)
            dsalt = single_tax_bracket_2021.tax(amount - standard_deduction_2021, 0)
            self.assertAlmostEqual(d0.tax_paid, tax)
            self.assertAlmostEqual(ds.tax_paid, dsalt.tax_paid)
            self.assertAlmostEqual(amount - d0.tax_paid, d0.remaining())
            self.assertAlmostEqual(amount - ds.tax_paid, ds.remaining())

        test(0, 0)
        test(5000, 500.00)
        test(5000 - standard_deduction_2021, 0.00)
        test(50000, 6748.50)
        test(100000, 18021.00)
        test(200000, 44827.00)
        test(300000, 79544.25)
        test(600000, 186072.25)

        def mtest(amount, margin):
            # test that the margin works
            tax_upper = single_tax_bracket_2021.tax(amount + margin, 0).tax_paid
            tax_lower = single_tax_bracket_2021.tax(margin, 0).tax_paid
            tax_margin = single_tax_bracket_2021.tax(amount, 0, margin=margin).tax_paid
            self.assertAlmostEqual(max(tax_upper - tax_lower, 0), tax_margin, msg=f"{tax_upper} - {tax_lower} = {tax_upper - tax_lower}")

        mtest(0, 0)
        mtest(-100, 4000)
        mtest(1000, -4000)
        mtest(-100, -1000)
        mtest(-100000, 100000)
        mtest(-100000, 10000)
        mtest(-100000, 1000000)
        mtest(100, 1000)
        mtest(20000, 1000)
        mtest(1000000, 40000)
        mtest(100, 20000)
        mtest(65002, 123456)
        mtest(42000, 232123)
        mtest(90000, 354123)
        mtest(4500, 654321)

        def rtest(amount, margin):
            # test that the reverse tax works with deductions and margins
            r1 = single_tax_bracket_2021.reverse_tax(amount, 0, margin)
            r2 = single_tax_bracket_2021.reverse_tax(amount, standard_deduction_2021, margin)
            self.assertAlmostEqual(amount, single_tax_bracket_2021.tax(r1, 0, margin).remaining(),
                                   msg=f"Taxed {r1} at {margin=}")
            self.assertAlmostEqual(amount, single_tax_bracket_2021.tax(r2, standard_deduction_2021, margin).remaining(),
                                   msg=f"Taxed {r2} deduction={standard_deduction_2021} at {margin=}")

        rtest(0, 0)
        rtest(5000, 0)
        rtest(0, 5000)
        rtest(0, 10000)
        rtest(10000, 10000)
        rtest(10000, 0)
        rtest(40525, 0)
        rtest(40525, 100)
        rtest(40425, 100)
        rtest(40000, 0)
        rtest(40000, 200)
        rtest(50000, 10000)
        rtest(50000, 50000)
        rtest(100000, 10000)
        rtest(200000, 0)
        rtest(200000, 10000)
        rtest(200000, 445566)
        rtest(300000, 0)
        rtest(600000, 0)
        rtest(600000, 60000)
