import pandas as pd
import math

import tax_brackets


def load_tax_bracket(file: str) -> tax_brackets.TaxBracket:
    """
    Loads a tax bracket structure from a csv file. File should have 2 columns (comma separated)
    Column 1 should be upper bound in dollars.
    Column 2 should be interest rate for everything from the previous row to the row's upper bound
    
    :param file: file path to load
    :return: loaded tax bracket
    """
    data = pd.read_csv(file, header=None)
    assert len(data.columns) == 2, "Tax bracket should 2 columns: upper_bound,rate"
    lb = 0
    ranges = []
    for row in data.iterrows():
        rowdata = row[1]
        ub = rowdata[0]
        if math.isnan(ub):
            ub = float('inf')
        rate = rowdata[1]
        taxrange = tax_brackets.TaxRange(lb, ub, rate)
        ranges.append(taxrange)
        lb = ub
    taxbracket = tax_brackets.TaxBracket(*ranges)
    return taxbracket

