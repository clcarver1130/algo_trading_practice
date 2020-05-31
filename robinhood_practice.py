# Main libraries
import pandas as pd
import schedule
import time
import datetime
from logger import logging
from talib import MACD, ADX, MINUS_DI, PLUS_DI
from coinapi_rest_v1 import CoinAPIv1


# Robinhood specific libraries and login
import robin_stocks as r
from logins import robin_email, robin_password
login = r.login(robin_email, robin_password)

# CoinAPI login
from logins import CoinAPI_KEY
coin_api = CoinAPIv1(CoinAPI_KEY)

### Constants
symbol_id = 'KRAKEN_SPOT_ETH_USD'
aggregation = '30MIN'
days_of_data = 1


def scheduler():
    logging.info('Starting script...')
    schedule.every(1).hours.do(main)
    while True:
        schedule.run_pending()
        time.sleep(1)

def main():

    now = str(pd.Timestamp.today())[0:16]
    logging.info('Calculating metrics for {now}...'.format(now=now))

    data_since = (pd.Timestamp.today() - datetime.timedelta(days=days_of_data)).date().isoformat()
    df_historical = get_historical_data(symbol_id, aggregation, data_since)
    df_historical.tail()
    current_indicators = calculate_indicators(df_historical)
    print(current_indicators)

def get_historical_data(symbol, agg, time_window):
    df = pd.DataFrame(coin_api.ohlcv_historical_data(symbol, {'period_id':agg, 'time_start':time_window})).set_index('time_period_start')
    return df

def calculate_indicators(df):

    # Build dictionary:
    indicator_dict = dict()

    indicator_dict['current_period_time'] = df.index[-1]

    # MACD
    fast = 12
    slow = 26
    signal = 9
    macd, macdsignal, macdhist = MACD(df['price_close'], fast, slow, signal)
    indicator_dict['macd_current'] = macd[-1]
    indicator_dict['macd_signal'] = macdsignal[-1]

    # ADX
    time_period = 14
    adx = ADX(df['price_high'], df['price_low'], df['price_close'], time_period)
    indicator_dict['adx_current'] = adx[-1]

    # DI+/DI-
    time_period = 14
    di_plus = PLUS_DI(df['price_high'], df['price_low'], df['price_close'], time_period)
    di_minus = MINUS_DI(df['price_high'], df['price_low'], df['price_close'], time_period)
    indicator_dict['di_plus'] = di_plus[-1]
    indicator_dict['di_minus'] = di_minus[-1]

    return indicator_dict
