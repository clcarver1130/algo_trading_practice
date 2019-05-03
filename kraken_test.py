import pandas as pd
import schedule
import time
from logger import logging


import krakenex
from pykrakenapi import KrakenAPI
from talib import EMA
api = krakenex.API()
k = KrakenAPI(api)
api.load_key('kraken_keys.py')


def main():
    logging.info('Starting script...')
    schedule.every(1).minutes.do(entry_exit_logic)
    while True:
        schedule.run_pending()
        time.sleep(1)

def entry_exit_logic():

    now = str(pd.Timestamp.today())[0:16]
    logging.info('Calculating metrics for {now}...'.format(now=now))

    # Calculate metrics
    currency = 'ZUSD'
    crypto = 'XETH'
    pair = crypto + currency
    df = k.get_ohlc_data(pair, interval=15, ascending=True)[0]
    df.index = df.index.tz_localize(tz='UTC').tz_convert('US/Central')
    ewm_3 = EMA(df['close'], 3)[-1]
    ewm_15 = EMA(df['close'], 15)[-1]
    ewm_25 = EMA(df['close'], 25)[-1]

    logging.info('3-EMA is: {ewm_3} and 15-EMA is: {ewm_15} and 25-EMA is: {ewm_25}'.format(ewm_3=ewm_3, ewm_15=ewm_15, ewm_25=ewm_25))

    # Current holdings
    volume = k.get_account_balance()
    try:
        cash_on_hand = volume.loc[currency][0]
        current_price = df['close'][-1]
        affordable_shares = int(cash_on_hand/current_price)
    except:
        print('No USD On Hand.')
        pass
    try:
        crypto_on_hand = volume.loc[crypto][0]
        holding_crypto = [True if volume.loc[crypto][0] >= 1 else False][0]
    except:
        print('No Cryptocurreny On Hand.')
        holding_crypto = False
        pass

    # Entry-Exit Logic
    if (ewm_3 > ewm_25) & (holding_crypto==False):
        type = 'buy'
        order = api.query_private('AddOrder', {'pair': pair, 'type': type, 'ordertype':'market', 'volume': affordable_shares})
        logging.info('Bought {shares} shares at {price}'.format(shares=affordable_shares, price=current_price))
    elif ((ewm_3 < ewm_15) | (ewm_3 < ewm_25)) & (holding_crypto==True):
        type = 'sell'
        order = api.query_private('AddOrder', {'pair': pair, 'type': type, 'ordertype':'market', 'volume': crypto_on_hand})
        logging.info('Sold {shares} shares at {price}'.format(shares=crypto_on_hand, price=current_price))
    else:
        logging.info('Holding current position')
        pass

if __name__ == '__main__':
    main()
