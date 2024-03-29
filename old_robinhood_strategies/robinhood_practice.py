### Main libraries
import pandas as pd
import schedule
import time
import datetime
from logger import logging
import sqlite3
from talib import MACD, ADX, MINUS_DI, PLUS_DI
from coinapi_rest_v1 import CoinAPIv1
from robin_helperfunctions import round_to_hour


### Robinhood specific libraries and login
import robin_stocks as r
from logins import robin_email, robin_password

### CoinAPI login
from logins import CoinAPI_KEY
coin_api = CoinAPIv1(CoinAPI_KEY)

### Constants
crypto_symbol = 'ETH'
symbol_id = 'KRAKEN_SPOT_ETH_USD'
aggregation = '30MIN'
hours_of_data = 30
DB_NAME = 'crypto_trading'


def main():
    # Login:
    try:
        login = r.login(robin_email, robin_password)
    except:
        logging.info('Login Issue.')
        print(login)
        return

    # Pull data:
    try:
        now = str(pd.Timestamp.today())[0:16]
        logging.info('Calculating metrics for {now}...'.format(now=now))
        data_since = round_to_hour(pd.Timestamp.today() - datetime.timedelta(hours=hours_of_data)).isoformat()
        df_historical = get_historical_data(symbol_id, aggregation, data_since)
    except:
        logging.info('Data Request Issue.')
        return

    # Calculate indicators:
    try:
        current_indicators = calculate_indicators(df_historical)
    except:
        logging.info('Indicator calculation issue.')
        return

    # Calcualte current holdings:
    try:
        current_balances =  calculate_balances()
    except:
        logging.info('Issue Looking Up Current Balances.')
        return

    # Log information:
    try:
        logging.info('Logging current indicators...')
        history_dict = df_historical.tail(1).reset_index().to_dict('records')[0]
        current_log = {**history_dict, **current_indicators, **current_balances}
        log_info_sqlite(current_log, DB_NAME)
    except:
        logging.info('Issue Logging Data.')
        return

    # Entry/Exit Logic:
    if current_balances['open_position']:
        try:
            exit_logic(current_indicators, current_balances)
        except:
            logging.info('Issue with Exit Order')
            return
    else:
        try:
            entry_logic(current_indicators, current_balances)
        except:
            logging.info('Issue with Entry Order.')
            return

def get_historical_data(symbol, agg, time_window):
    df = pd.DataFrame(coin_api.ohlcv_historical_data(symbol, {'period_id':agg, 'time_start':time_window})).set_index('time_period_start')
    return df

def calculate_indicators(df):

    logging.info('Calculating indicators...')

    # Build dictionary:
    indicator_dict = dict()

    # MACD
    fast = 12
    slow = 26
    signal = 9
    macd, macdsignal, macdhist = MACD(df['price_close'], fast, slow, signal)
    indicator_dict['macd_current'] = macd[-1]
    indicator_dict['macd_signal_current'] = macdsignal[-1]

    # ADX
    time_period = 14
    adx = ADX(df['price_high'], df['price_low'], df['price_close'], time_period)
    indicator_dict['adx_current'] = adx[-1]

    # DI+/DI-
    time_period = 14
    di_plus = PLUS_DI(df['price_high'], df['price_low'], df['price_close'], time_period)
    di_minus = MINUS_DI(df['price_high'], df['price_low'], df['price_close'], time_period)
    indicator_dict['di_plus_current'] = di_plus[-1]
    indicator_dict['di_minus_current'] = di_minus[-1]

    return indicator_dict

def calculate_balances():

    logging.info('Looking up current balances...')

    # Calculate our on hand cash and the ETH amount:
    try:
        cash_on_hand = r.load_account_profile()['crypto_buying_power']
    except:
        logging.info('Issue determining buying power')

    try:
        crypto_to_sell = float(r.get_crypto_positions()[0]['quantity_available'])
    except:
        logging.info('Problem determining {} amount on hand'.format(crypto_symbol))

    # Calculate an open_position flag:
    open_position = True if crypto_to_sell > 0 else False
    open_position


    # Save to a dictionary and return:
    current_balances = {'cash_on_hand':float(cash_on_hand), 'crypto_to_sell':float(crypto_to_sell), 'open_position': open_position}

    return current_balances

def entry_logic(current_indicators, current_balances):

    # Unpack dictionary:
    macd_current = current_indicators['macd_current']
    macd_signal_current = current_indicators['macd_signal_current']
    adx_current = current_indicators['adx_current']
    di_plus_current = current_indicators['di_plus_current']
    di_minus_current = current_indicators['di_minus_current']
    # Calculate entry logic:
    if (macd_current > macd_signal_current) & (adx_current > 30) & (di_plus_current > di_minus_current) & (macd_current > 0):
        place_entry_order(current_balances)
        logging.info('Entry order placed')
    else:
        logging.info('Entry conditions not met. Waiting to enter.')
        pass

def exit_logic(current_indicators, current_balances):
    # Unpack dictionary:
    macd_current = current_indicators['macd_current']
    # Calculate exit logic:
    if macd_current <= 0:
        place_exit_order(current_balances)
        logging.info('Exit order placed.')
    else:
        logging.info('Exit conditons not met. Holding position.')
        pass

def place_entry_order(current_balances, priceType='ask_price'):
    cash_on_hand = current_balances['cash_on_hand']
    crypto_info = r.crypto.get_crypto_info(crypto_symbol)
    price = r.helper.round_price(r.crypto.get_crypto_quote_from_id(crypto_info['id'], info=priceType))
    shares = round(cash_on_hand/price, 4)
    order = r.orders.order_buy_crypto_by_quantity(crypto_symbol, shares, priceType=priceType)
    print(order)

def place_exit_order(current_balances, priceType='bid_price'):
    crypto_to_sell = round(current_balances['crypto_to_sell'], 4)
    order = r.orders.order_sell_crypto_by_quantity(crypto_symbol, quantity=crypto_to_sell)
    print(order)

def log_info_sqlite(current_log, DB_NAME):

    conn = sqlite3.connect(DB_NAME)
    curs = conn.cursor()
    columns = ', '.join(current_log.keys())
    placeholders = ':'+', :'.join(current_log.keys())
    sql = 'INSERT INTO history_log ({}) VALUES ({})'.format(columns, placeholders)
    curs.execute(sql, current_log)
    conn.commit()

if __name__ == '__main__':
    # main()
    logging.info('Starting script...')
    schedule.every(30).minutes.do(main)
    logging.info('Script Complete.')
    while True:
        schedule.run_pending()
        time.sleep(1)
