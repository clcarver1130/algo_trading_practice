from decimal import Decimal, ROUND_DOWN

def round_down(num, decimals=0):
    power = '0.' + '0' * decimals
    return Decimal(num).quantize(Decimal(power), rounding=ROUND_DOWN)