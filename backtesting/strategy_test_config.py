strategy_config = dict(name='MACD_test',
                       fiat_sym='USD',
                       crypto_sym='ETH',
                       starting_capital=1000,
                       agg=240,  # 4 hours
                       start='2021-01-01',
                       end=None,
                       stop_loss=0.03,
                       trailing_stop=None,
                       time_zone='US/Central',
                       periods_needed=26,
                       )

def strategy(hist_data, position_flag):

    # MACD calculation:
    FAST, SLOW, SIGNAL = 12, 26, 9
    exp1 = hist_data['close'].ewm(span=FAST, adjust=False).mean()
    exp2 = hist_data['close'].ewm(span=SLOW, adjust=False).mean()
    macd = exp1-exp2
    signal = macd.ewm(span=SIGNAL, adjust=False).mean()
    macd_current, signal_current = macd[-1], signal[-1]

    # Action:
    if position_flag:
        if macd_current <= signal_current:
            return 'sell'
        else:
            return 'pass'
    elif macd_current > signal_current:
            return 'buy'
    else:
        return 'pass'