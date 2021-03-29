import sys
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import numpy as np

print("Welcome to the stock market simulation!")
try:
    money = float(input("How much money did you invest? $"))
except ValueError:
    print("That's impossible!")
    sys.exit()
print("Lets see how you did...")

now = datetime.now()
xs = [now + timedelta(days=x) for x in range(7)]
ys = np.random.normal(np.linspace(money, 0.0, 7), money/8)
fig = plt.figure(1)
plt.plot(xs, ys, 'r-')
plt.title("You lost all your money!")
plt.ylabel("Your money")
plt.xlabel("Next Week")
fig.autofmt_xdate()
plt.show()
