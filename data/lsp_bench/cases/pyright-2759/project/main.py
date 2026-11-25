# pyright: strict
from itertools import accumulate

cashflows = [1, 2]
lst = list(accumulate(cashflows, lambda bal, pmt: bal * 2 + pmt, initial=0))
