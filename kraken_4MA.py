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
#     logging.info('Starting script...')
#     schedule.every(1).hours.do(entry_exit_logic)
#     while True:
#         schedule.run_pending()
#         time.sleep(1)
    entry_exit_logic()

def Four_MA(close):
    
    ma_3 = close.rolling(3).mean()
    ma_8 = close.rolling(8).mean()
    ma_13 = close.rolling(13).mean()
    ma_21 = close.rolling(21).mean()
    ma_55 = close.rolling(55).mean()
    return ma_3, ma_8, ma_13, ma_21, ma_55
    
def entry_exit_logic():

    now = str(pd.Timestamp.today())[0:16]
    logging.info('Calculating metrics for {now}...'.format(now=now))

    # Calculate metrics
    currency = 'ZUSD'
    crypto = 'XETH'
    pair = crypto + currency
    try:
        df = k.get_ohlc_data(pair, interval=240, ascending=True)[0]
        df.index = df.index.tz_localize(tz='UTC').tz_convert('US/Central')
        ma_3, ma_8, ma_13, ma_21, ma_55 = Four_MA(df['close'])
        logging.info(f'MA are (8, 13, 21, 55): {ma_8[-1]:.2f} | {ma_13[-1]:.2f} | {ma_21[-1]:.2f} | {ma_55[-1]:.2f}')
    except:
        logging.info('Data Request Error.')
        pass


    # Current holdings
    try:
        volume = k.get_account_balance()
        cash_on_hand = volume.loc[currency][0]
        current_price = df['close'][-1]
#         leverage = 5
#         margin_shares = (cash_on_hand*leverage)/current_price
        shares = cash_on_hand/current_price
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

    # Entry Exit Long 
    if (ma_8[-1] > ma_13[-1] > ma_21[-1] > ma_55[-1]) & (open_position==False):
        otype = 'buy'
        order = api.query_private('AddOrder', {'pair': pair, 'type': otype, 'ordertype':'limit', 'price': current_price, 'volume': shares, 'close[ordertype]':'stop-loss', 'close[price]':'-0.01%'})
        if len(order['error']) == 0:
            logging.info('Bought {shares} shares at {price}'.format(shares=margin_shares, price=current_price))
        else:
            logging.info('Trade Canceled: {error}'.format(error=order['error']))
    elif (ma_3[-1] <= ma_8[-1]) & (open_position==True):
        otype = 'sell'
        order = api.query_private('AddOrder', {'pair': pair, 'type': otype, 'ordertype':'market', 'volume': 0})
        if len(order['error']) == 0:
            logging.info('Sold {shares} shares at {price}'.format(shares=crypto_on_hand, price=current_price))
        else:
            logging.info('Trade Canceled: {error}'.format(error=order['error']))
    else:
        logging.info('Holding current position')
        pass

if __name__ == '__main__':
    main()
