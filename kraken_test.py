import pandas as pd
import schedule


import krakenex
from pykrakenapi import KrakenAPI
api = krakenex.API()
k = KrakenAPI(api)
api.load_key('kraken_keys.py')


def main():
    schedule.every(1).minutes.do(entry_exit_logic)
    while True:
        schedule.run_pending()
        time.sleep(1)

def entry_exit_logic():

    # Calculate metrics
    currency = 'ZUSD'
    crypto = 'XXRP'
    pair = crypto + currency
    df = k.get_ohlc_data(pair)[0]
    ewm_3 = df['close'].ewm(3).mean()[0]
    ewm_20 = df['close'].ewm(20).mean()[0]

    # Current holdings
    volume = k.get_account_balance()
    try:
        cash_on_hand = volume.loc[currency][0]
    except:
        print('No USD On Hand.')
        pass
    try:
        crypto_on_hand = volume.loc[crypto][0]
        holding_crypto = [True if len(k.get_open_positions()) > 0 else False]
        current_price = df['close'][-1]
        affordable_shares = int(cash_on_hand/current_price)
    except:
        print('No Cryptocurreny On Hand.')
        pass

    # Entry-Exit Logic
    if (ewm_3 > ewm_20) & (holding_crypto==False):
        type = 'buy'
        api.query_private('AddOrder', {'pair': pair, 'type': type, 'ordertype':'market', 'volume': affordable_shares})
    elif (ewm_3 < ewm_20) & (holding_crypto==True):
        type = 'sell'
        api.query_private('AddOrder', {'pair': pair, 'type': type, 'ordertype':'market', 'volume': crypto_on_hand)})
    else:
        print('Holding')
        pass
        
