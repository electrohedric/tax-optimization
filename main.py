import sys

from tax_brackets import TaxBracket, TaxRange

single_tax_ranges_2021 = (
    TaxRange(0,   9950, 0.10),
    TaxRange(9950, 40525, 0.12),
    TaxRange(40525, 86375, 0.22),
    TaxRange(86375, 164925, 0.24),
    TaxRange(164925, 209425, 0.32),
    TaxRange(209425, 523600, 0.35),
    TaxRange(523600, float('inf'), 0.37),
)
single_tax_bracket_2021 = TaxBracket(*single_tax_ranges_2021)

while True:
    try:
        amount = float(input("Enter taxable income: $"))
    except ValueError:
        print("Quit")
        sys.exit()
    tax = single_tax_bracket_2021.tax(amount)
    print(f"${tax:.2f} taxed")
