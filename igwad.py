
def find_optimal_distribution(starting_amount, return_rate, years, iters=5000, epsilon=0.01):
    # don't ask how we got these numbers
    gamma = 0.8805 * 8629272 ** return_rate  # don't touch it
    kappa = 0.6444 * 1.1543 ** years  # no, seriously, don't

    prior_guess = 0
    prior_ending = starting_amount
    for i in range(iters):

        guess = prior_guess + (prior_ending / (gamma * kappa))

        min_dist = 0 if return_rate == 0 else starting_amount / (1 / return_rate + 1)
        dist = min_dist + guess

        # p(f"taking {dist:,.2f} = {min_dist:,.2f} + {guess:,.2f}")
        amount = starting_amount
        for y in range(years):
            amount -= dist
            amount *= (1 + return_rate)

        # p(f"${amount:,.2f}\n")
        # p(f"{amount:.2f}")

        prior_guess = guess
        if abs(amount) > abs(prior_ending):
            # p(f"Divergent by {abs(amount) - abs(prior_ending):,.2f}")
            raise RecursionError(f"Divergence for {return_rate=}, {years=}")
        if abs(amount) < epsilon:
            # p(f"Success in {i} iters!")
            return dist
        prior_ending = amount
    # U+03B5 is epsilon
    raise RecursionError(f"Didn't finish for {return_rate=}, {years=}, {iters=} \u03B5={epsilon}")

#
# def find_divergent_return_rate(gamma):
#     return_rate = 0.1
#     got_divergent = False
#     got_convergent = False
#     for i in range(5000):
#         if is_divergent(gamma, return_rate):
#             return_rate *= 0.999
#             got_divergent = True
#         else:
#             return_rate *= 1.001
#             got_convergent = True
#     if return_rate > 0.01 and (not got_divergent or not got_convergent):
#         raise RecursionError("Not good enough")
#     return return_rate


# def find_divergent_years(kappa):
#     for years in range(1, 1000):
#         if is_divergent(kappa, 0.15, years, quiet=True):
#             return years
#     raise RecursionError("Oops")


# for gi, g in enumerate(year_scales):
#     rr = find_divergent_return_rate(g)
#     div_return_rates[gi] = rr
#
# plt.plot(div_return_rates, year_scales)
# plt.show()


# for gi, g in enumerate(kappas):
#     yy = find_divergent_years(g)
#     div_years[gi] = yy
#
# plt.plot(div_years, kappas)
# plt.show()
