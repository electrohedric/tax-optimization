import tax_brackets
from loader import load_tax_bracket


standard_deduction_2021 = 12550.00
standard_deduction_2021_va = 4500.00
standard_deduction_2021_ss = 0
standard_deduction_2021_med = 0
single_tax_bracket_2021 = load_tax_bracket("data/2021/single_tax.csv")
single_tax_bracket_2021_va = load_tax_bracket("data/2021/va_single_tax.csv")
single_tax_bracket_2021_ss = load_tax_bracket("data/2021/social_security_tax.csv")
single_tax_bracket_2021_med = load_tax_bracket("data/2021/medicare_tax.csv")
single_ss_pi_bracket_2021 = load_tax_bracket("data/2021/social_security_provisional_income.csv")

single_combined_tax_2021 = tax_brackets.TotalTax(
    [single_tax_bracket_2021, single_tax_bracket_2021_va, single_tax_bracket_2021_ss, single_tax_bracket_2021_med],
    [standard_deduction_2021, standard_deduction_2021_va, standard_deduction_2021_ss, standard_deduction_2021_med]
)
