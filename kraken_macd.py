import pandas as pd
import schedule
import time
from logger import logging

import krakenex
from pykrakenapi import KrakenAPI
from talib import MACD
api = krakenex.API()
k = KrakenAPI(api)
api.load_key('kraken_keys.py')


def main():
    logging.info('Starting script...')
    schedule.every(1).hours.do(entry_exit_logic)
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
    try:
        df = k.get_ohlc_data(pair, interval=60, ascending=True)[0]
        df.index = df.index.tz_localize(tz='UTC').tz_convert('US/Central')
        macd, macdsignal, macdhist = MACD(df['close'], fastperiod=12, slowperiod=26, signalperiod=9)
        macd_current = macd[-1]
        signal_current = macdsignal[-1]
        logging.info('MACD is: {macd} and Signal is: {signal}'.format(macd=macd_current, signal=signal_current))
    except:
        logging.info('Data Request Error.')
        pass


    # Current holdings
    try:
        volume = k.get_account_balance()
        cash_on_hand = volume.loc[currency][0]
        current_price = df['close'][-1]
        leverage = 5
        margin_shares = (cash_on_hand*leverage)/current_price
    except:
        print('No USD On Hand.')
        pass
    try:
        crypto_on_hand = volume.loc[crypto][0]
        open_position = [True if len(k.get_open_positions()) > 0 else False][0]
    except:
        print('No Cryptocurreny On Hand.')
        open_position = False
        pass

    # # Check for open position
    # if open_position == True:
    #
    #     # If open position
    #     if
    #     # Check sell logic
    #
    #         # If sell logic true
    #              #  Sell
    #              # Check buy logic
    #         # Else hold
    #
    #
    #     # Else buy logic


    # Open Long
    if (macd_current > signal_current) & (open_position==False):
        type = 'buy'
        order = api.query_private('AddOrder', {'pair': pair, 'type': type, 'ordertype':'limit', 'price': current_price, 'leverage': str(leverage), 'volume': margin_shares})
        if len(order['error']) == 0:
            logging.info('Bought {shares} shares at {price}'.format(shares=margin_shares, price=current_price))
        else:
            logging.info('Trade Canceled: {error}'.format(error=order['error']))
    elif (macd_current <= signal_current) & (open_position==True):
        type = 'sell'
        order = api.query_private('AddOrder', {'pair': pair, 'type': type, 'ordertype':'market', 'leverage': str(leverage), 'volume': 0})
        if len(order['error']) == 0:
            logging.info('Sold {shares} shares at {price}'.format(shares=crypto_on_hand, price=current_price))
        else:
            logging.info('Trade Canceled: {error}'.format(error=order['error']))
    else:
        logging.info('Holding current position')
        pass

if __name__ == '__main__':
    main()
