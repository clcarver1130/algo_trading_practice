import pandas as pd
import matplotlib.pyplot as plt
import boto
import schedule
import time
from logger import logging
import requests
session = requests.Session()
session.verify = False

import krakenex
from pykrakenapi import KrakenAPI
api = krakenex.API()
k = KrakenAPI(api)
api.load_key('kraken_keys.py')

df = k.get_trades_history()[0]

df2 = df[['cost', 'fee', 'margin', 'price', 'type', 'vol']]
df_shifted = df2.add_suffix('_buy').join(df2.shift(1).add_suffix('_sell'))
df_trades = df_shifted[df_shifted['type_buy'] == 'buy'].copy()

df_trades['pct_return'] = (df_trades['cost_sell'] - df_trades['cost_buy'])/df_trades['cost_sell']
df_trades['abs_return'] = df_trades['cost_sell'] - df_trades['cost_buy']
df_trades['pct_return_adj'] = ((df_trades['cost_sell'] - df_trades['cost_buy']) - (df_trades['fee_buy'] + df_trades['fee_sell']))/df_trades['cost_sell']
df_trades['abs_return_adj'] = (df_trades['cost_sell'] - df_trades['cost_buy']) - (df_trades['fee_buy'] + df_trades['fee_sell'])
