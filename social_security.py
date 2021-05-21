from loader import load_tax_bracket

single_ss_bracket_2021 = load_tax_bracket("data/2021/social_security_provisional_income.csv")


def get_provisional_income_subject_to_income_tax (social_security_benefit: float = 0,
                                                  all_other_tax_free_income: float = 0):
    # print(f"social security benefit is ${social_security_benefit:,.2f}")
    half_ss_benefit = social_security_benefit / 2
    # print(f"all_other_tax_free_income is ${all_other_tax_free_income:,.2f}")
    provisional_income = half_ss_benefit + all_other_tax_free_income
    # print(f"provisional income is ${provisional_income:,.2f}")

    pi_subject_to_income_tax = single_ss_bracket_2021.tax(provisional_income, 0)
    # print("-" * 100)
    # for i in range(len(pi_subject_to_income_tax.breakdown)):
    #     print(f"{single_ss_bracket_2021.tax_ranges[i]} = {pi_subject_to_income_tax.breakdown[i]}")
    #
    #
    # print("-" * 100)
    print(f"provisional income subject to income tax is $ {pi_subject_to_income_tax.tax_paid:,.2f}")
    return pi_subject_to_income_tax


# get_provisional_income_subject_to_income_tax(social_security_benefit=24000, all_other_tax_free_income=20000)
# get_provisional_income_subject_to_income_tax(social_security_benefit=24000, )
