from unittest import TestCase

import loader
import tax_brackets


class Test(TestCase):
    def test_load_tax_bracket(self):
        single_tax_ranges_2021 = (
            tax_brackets.TaxRange(0, 9950, 0.10),
            tax_brackets.TaxRange(9950, 40525, 0.12),
            tax_brackets.TaxRange(40525, 86375, 0.22),
            tax_brackets.TaxRange(86375, 164925, 0.24),
            tax_brackets.TaxRange(164925, 209425, 0.32),
            tax_brackets.TaxRange(209425, 523600, 0.35),
            tax_brackets.TaxRange(523600, float('inf'), 0.37),
        )
        single_tax_bracket_2021_h = tax_brackets.TaxBracket(*single_tax_ranges_2021)
        single_tax_bracket_2021_f = loader.load_tax_bracket("data/2021/single_tax.csv")
        # FIXME: sloppily using str for equality checks
        self.assertEqual(str(single_tax_bracket_2021_h), str(single_tax_bracket_2021_f))
