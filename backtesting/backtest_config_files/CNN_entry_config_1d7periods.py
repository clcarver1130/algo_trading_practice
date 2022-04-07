strategy_config = dict(name='CNN_entry_1d_7period',
                       fiat_sym='USD',
                       crypto_sym='ETH',
                       starting_capital=1000,
                       agg=1440,  # 1 day
                       start='2020-01-01',
                       end='2020-12-31',
                       stop_loss=None,
                       take_profit=0.1,
                       time_zone='US/Central',
                       periods_needed=21,
                       )

from tensorflow.keras.models import load_model
import numpy as np
model = load_model('../NN_research/1d_7period_cnn.h5')

def normalized_df(X):
    return np.array([x/x[0]-1 for x in X])

def strategy(hist_data, position_flag, trade):
    current_seq = np.array(hist_data.tail(21)[['close', 'open', 'high', 'low', 'volume', 'trades']])
    normalized_seq = normalized_df(current_seq.reshape(1, 21, 6))
    pred = model.predict(normalized_seq)[0][0]

    if position_flag:
        if trade.period_count == 6:
            return 'sell'
        else:
            return 'pass'
    elif (pred > 0.90):
        return 'buy'
    else:
        return 'pass'