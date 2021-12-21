strategy_config = dict(name='SMA_5_50',
                       fiat_sym='USD',
                       crypto_sym='ETH',
                       starting_capital=1000,
                       agg=240,  # 4 hours
                       start='2021-01-01',
                       end=None,
                       stop_loss=0.03,
                       trailing_stop=None,
                       time_zone='US/Central',
                       periods_needed=50,
                       )

def strategy(hist_data, position_flag):

    # MACD calculation:
    FAST, SLOW = 5, 50
    fast = hist_data['close'].rolling(window=FAST).mean()
    slow = hist_data['close'].rolling(window=SLOW).mean()
    fast_current, slow_current = fast[-1], slow[-1]

    # Action:
    if position_flag:
        if fast_current <= slow_current:
            return 'sell'
        else:
            return 'pass'
    elif fast_current > slow_current:
        return 'buy'
    else:
        return 'pass'