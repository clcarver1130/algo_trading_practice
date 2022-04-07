strategy_config = dict(name='CNN_MACD_hybrid',
                       fiat_sym='USD',
                       crypto_sym='ETH',
                       starting_capital=1000,
                       agg=1440,  # 1 day
                       start='2020-01-01',
                       end='2020-12-31',
                       stop_loss=None,
                       take_profit=0.1,
                       time_zone='US/Central',
                       periods_needed=26,
                       )

from tensorflow.keras.models import load_model
import numpy as np
model = load_model('../NN_research/1d_7period_cnn.h5')

def normalized_df(X):
    return np.array([x/x[0]-1 for x in X])

def strategy(hist_data, position_flag, trade):

    # CNN Prediction:
    current_seq = np.array(hist_data.tail(21)[['close', 'open', 'high', 'low', 'volume', 'trades']])
    normalized_seq = normalized_df(current_seq.reshape(1, 21, 6))
    pred = model.predict(normalized_seq)[0][0]

    # MACD calculation:
    FAST, SLOW, SIGNAL = 12, 26, 9
    exp1 = hist_data['close'].ewm(span=FAST, adjust=False).mean()
    exp2 = hist_data['close'].ewm(span=SLOW, adjust=False).mean()
    macd = exp1-exp2
    signal = macd.ewm(span=SIGNAL, adjust=False).mean()
    macd_current, signal_current = macd[-1], signal[-1]

    if position_flag:
        if macd_current <= signal_current:
            return 'sell'
        else:
            return 'pass'
    elif (pred > 0.90) and macd_current > signal_current:
        return 'buy'
    else:
        return 'pass'