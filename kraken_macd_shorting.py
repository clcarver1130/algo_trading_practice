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
    currency = 'ZUSD'
    crypto = 'XETH'
    pair = crypto + currency
    current_price, macd, signal = calculate_macd(pair)
    cash_on_hand, crypto_on_hand, margin_shares, open_position = calculate_balances(current_price, currency, crypto)
    exit_logic(pair, open_position, macd, signal, current_price, margin_shares)


def calculate_macd(pair, agg=60, fast=12, slow=26, signal=9):

    now = str(pd.Timestamp.today())[0:16]
    logging.info('Calculating MACD for {now}...'.format(now=now))

    # Calculate metrics
    try:
        df = k.get_ohlc_data(pair, interval=agg, ascending=True)[0]
        df.index = df.index.tz_localize(tz='UTC').tz_convert('US/Central')
        macd, macdsignal, macdhist = MACD(df['close'], fastperiod=fast, slowperiod=slow, signalperiod=signal)
        macd_current = macd[-1]
        signal_current = macdsignal[-1]
        current_price = df['close'][-1]
        logging.info('MACD is: {macd} and Signal is: {signal}'.format(macd=macd_current, signal=signal_current))
        return current_price, macd_current, signal_current
    except:
        logging.info('Data Request Error.')
        pass


def calculate_balances(current_price, currency, crypto, leverage=5):
    try:
        volume = k.get_account_balance()
        cash_on_hand = volume.loc[currency][0]
        current_price = current_price
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

    return cash_on_hand, crypto_on_hand, margin_shares, open_position

def calc_position_type():
    positions = k.get_open_positions()
    return 'long' if [positions[p]  for p in positions][0]['type']=='buy' else 'short'

def exit_logic(pair, open_position, macd_current, signal_current, current_price, margin_shares):
    if open_position == True:
        position_type = calc_position_type()
        if position_type == 'long':
            if (macd_current <= signal_current):
                type = 'sell'
                order = api.query_private('AddOrder', {'pair': pair, 'type': type, 'ordertype':'market', 'leverage': str(leverage), 'volume': 0})
                if len(order['error']) == 0:
                    logging.info('Closed long position.')
                    entry_logic(pair, macd_current, signal_current, current_price, margin_shares)
                else:
                    logging.info('Trade Canceled: {error}'.format(error=order['error']))
            else:
                logging.info('Holding current position')
        else: # position_type=='short'
            if (macd_current >= signal_current):
                type = 'buy'
                order = api.query_private('AddOrder', {'pair': pair, 'type': type, 'ordertype':'market', 'leverage': str(leverage), 'volume': 0})
                if len(order['error']) == 0:
                    logging.info('Closed short position')
                    entry_logic(pair, macd_current, signal_current, current_price, margin_shares)
                else:
                    logging.info('Trade Canceled: {error}'.format(error=order['error']))
            else:
                logging.info('Holding current position')
                pass
    else:
        entry_logic(pair, macd_current, signal_current, current_price, margin_shares)


def entry_logic(pair, macd_current, signal_current, current_price, margin_shares, leverage=5):
    if macd_current > signal_current:
        type = 'buy'
        order = api.query_private('AddOrder', {'pair': pair, 'type': type, 'ordertype':'limit', 'price': current_price, 'leverage': str(leverage), 'volume': margin_shares})
        if len(order['error']) == 0:
            logging.info('Opened long positon. {shares} shares at {price}'.format(shares=margin_shares, price=current_price))
        else:
            logging.info('Trade Canceled: {error}'.format(error=order['error']))
    else:
        type = 'sell'
        order = api.query_private('AddOrder', {'pair': pair, 'type': type, 'ordertype':'limit', 'price': current_price, 'leverage': str(leverage), 'volume': margin_shares})
        if len(order['error']) == 0:
            logging.info('Opened short positon. {shares} shares at {price}'.format(shares=margin_shares, price=current_price))
        else:
            logging.info('Trade Canceled: {error}'.format(error=order['error']))



if __name__ == '__main__':
    logging.info('Starting script...')
    schedule.every(1).hours.do(main)
    while True:
        schedule.run_pending()
        time.sleep(1)
