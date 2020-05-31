# Main libraries
import pandas as pd
import schedule
import time
from logger import logging
from talib import MACD, ADX, MINUS_DI, PLUS_DI

# Robinhood specific libraries and login
import robin_stocks as r
from logins import robin_email, robin_password
login = r.login(robin_email, robin_password)

def scheduler():
    logging.info('Starting script...')
    schedule.every(1).hours.do(main)
    while True:
        schedule.run_pending()
        time.sleep(1)

def main():

    now = str(pd.Timestamp.today())[0:16]
    logging.info('Calculating metrics for {now}...'.format(now=now))

    df_historical = get_historical_data('ETH', 'hour', '3month')
    current_indicators = calculate_indicators(df_historical)
    print(current_indicators)

def get_historical_data(symbol, agg, time_window):
    df = pd.DataFrame(r.get_crypto_historical(symbol, agg, time_window, '24_7')['data_points'])
    print(df.info)
    df['begins_at'] = df['begins_at'].dt.tz_convert('Central')
    df.set_index('begins_at')
    return df

def calculate_indicators(df):

    # MACD
    fast = 12
    slow = 26
    signal = 9
    macd, macdsignal, macdhist = MACD(df['close_price'], fast, slow, signal)
    macd_current = macd[-1]
    signal_current = macdsignal[-1]
    return macd
    # ADX
    ADX
    # DI+/DI-
