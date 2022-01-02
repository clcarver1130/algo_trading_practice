strategy_config = dict(name='CNN_entry_1d_7period',
                       fiat_sym='USD',
                       crypto_sym='ETH',
                       starting_capital=1000,
                       agg=1440,  # 4 hours
                       start='2021-01-01',
                       end=None,
                       stop_loss=None,
                       trailing_stop=None,
                       time_zone='US/Central',
                       periods_needed=21,
                       )

from tensorflow.keras.models import load_model
import numpy as np
model = load_model('../NN_research/1d_7period_cnn.h5')

def strategy(hist_data, position_flag, trade):
    current_seq = np.array(hist_data.tail(21)[['close', 'open', 'high', 'low', 'volume', 'trades']])
    pred = model.predict(current_seq.reshape(1, 21, 6))[0][0]

    if position_flag:
        if trade.period_count == 7:
            return 'sell', pred
        else:
            return 'pass', pred
    elif (pred > 0.99):
        return 'buy', pred
    else:
        return 'pass', pred