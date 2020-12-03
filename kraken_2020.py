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
    entry_exit_logic()

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
        shares = cash_on_hand/current_price
    except:
        print('No USD On Hand.')
        pass
    try:
        crypto_on_hand = volume.loc[crypto][0]
        open_position = True if cash_on_hand < 1 else False
    except:
        print('No Cryptocurreny On Hand.')
        open_position = False
        pass

    # Entry Exit Long 
    if (macd_current > signal_current) & (open_position==False):
        otype = 'buy'
        buy_order = api.query_private('AddOrder', {'pair': pair, 
                                               'type': otype, 
                                               'ordertype':'limit', 
                                               'price': current_price, 
                                               'volume': shares,
                                               'expiretm': '+30'})
        if len(buy_order['error']) == 0:
            logging.info('Placed order for {shares} shares at {price}...'.format(shares=shares, price=current_price))
        else:
            logging.info('Trade canceled: {error}'.format(error=buy_order['error']))
        while len(k.get_open_orders()) > 0:
                    time.sleep(1)
        completed_order = k.get_closed_orders()[0].loc[buy_order['result']['txid'][0]]
        if completed_order['status'] == 'expired':
            logging.info('Trade timed out. Re-calculating metrics and retrying trade.')
            entry_exit_logic()
        else:
            logging.info('Buy order complete. Placing stop-loss order.')
            stop_loss_amount = 0.01
            stop_loss_order = api.query_private('AddOrder', {'pair': pair, 
                                                             'type': 'sell', 
                                                             'ordertype':'stop-loss', 
                                                             'price': round(completed_order['price']*(1-stop_loss_amount), 2),
                                                             'volume': completed_order['vol']})
    elif (macd_current <= signal_current) & (open_position==True):
        # Cancel stop loss order:
        stopLoss_id = k.get_open_orders().index[0]
        k.cancel_open_order(stopLoss_id) 
        # Create sell order:
        otype = 'sell'
        sell_order = api.query_private('AddOrder', {'pair': pair, 
                                               'type': otype, 
                                               'ordertype':'limit', 
                                               'price': current_price, 
                                               'volume': crypto_on_hand,
                                               'expiretm': '+30'})
        if len(order['error']) == 0:
            logging.info('Sold {shares} shares at {price}'.format(shares=crypto_on_hand, price=current_price))
        else:
            logging.info('Trade Canceled: {error}'.format(error=order['error']))
    else:
        logging.info('Holding current position')
        pass

if __name__ == '__main__':
    main()