import time

import numpy as np

import loader


def time_test():
    single_tax_bracket_2021 = loader.load_tax_bracket("data/2021/single_tax.csv")
    standard_deduction_2021 = 12550.00
    
    numcases = 5000000
    test_cases = np.linspace(0, 1000000, numcases)
    results = np.zeros(numcases)
    
    # t0 = time.time()
    # for i, case in enumerate(test_cases):
    #     results[i] = single_tax_bracket_2021.reverse_tax(case, 0, epsilon=1e-5, iters=50)
    # dt1 = time.time() - t0
    #
    # print(f"{dt1} = {dt1 / numcases}/run")
    #
    # t0 = time.time()
    # for i, case in enumerate(test_cases):
    #     results[i] = single_tax_bracket_2021.fast_reverse_tax(case, 0, epsilon=1e-5, iters=50)
    # dt1 = time.time() - t0

    t0 = time.time()
    for i in range(10000000):
        amount = i / 5.0
        single_tax_bracket_2021.fast_tax(amount, 0)
    t1 = time.time()
    dt1 = t1 - t0

    print(f"{dt1} = {dt1 / numcases}/run")
    
    # plt.plot(test_cases, results)
    # plt.plot(test_cases, test_cases)
    # polys = []
    # for r in single_tax_bracket_2021.tax_ranges:
    #     upper = r.upper_bound
    #     if upper == float('inf'):
    #         upper = 1.2 * r.lower_bound + 100
    #     dispersion = np.linspace(r.lower_bound, upper, 10)
    #     answers = np.zeros(10)
    #     for i, ea_case in enumerate(dispersion):
    #         answers[i] = single_tax_bracket_2021.reverse_tax(ea_case, 0, epsilon=1e-5, iters=50)
    #     poly = np.poly1d(np.polyfit(dispersion, answers, 1))
    #     polys.append(poly)
    #     plt.plot(dispersion, poly(dispersion), 'r-')
    # plt.show()
    
    
time_test()
