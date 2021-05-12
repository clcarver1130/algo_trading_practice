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

df = k.get_trades_history(start=1558587601)[0]
df.index = df.index.tz_localize(tz='UTC').tz_convert('US/Central')

cols = ['ordertxid','cost', 'fee', 'margin', 'price', 'vol', 'type', 'ordertype']
df2 = df[cols].reset_index().groupby('ordertxid', as_index=False).agg({'dtime':'first', 'cost':'sum', 'fee':'sum', 'margin':'sum', 'price':'sum','vol':'sum', 'type':'first', 'ordertype':'first' })
df3 = df2.set_index('dtime').sort_values('dtime')
df3['is_closing'] = ['open' if x=='limit' else 'close' for x in df3['ordertype']]

def is_long(row):
    order_type = row[0]
    is_closing = row[1]
    if ((order_type=='buy') & (is_closing=='open')) | ((order_type=='sell') & (is_closing=='close')):
        return 'long'
    else:
        return 'short'

df3['is_long'] = df3[['type', 'is_closing']].apply(is_long, axis=1)

df_shifted = df3.add_suffix('_buy').join(df3.shift(-1).add_suffix('_sell'))
df_trades = df_shifted[df_shifted['type_buy'] == 'buy'].copy()
df_trades['pct_return'] = (df_trades['cost_sell'] - df_trades['cost_buy'])/df_trades['cost_sell']
df_trades['abs_return'] = df_trades['cost_sell'] - df_trades['cost_buy']
df_trades['pct_return_adj'] = ((df_trades['cost_sell'] - df_trades['cost_buy']) - (df_trades['fee_buy'] + df_trades['fee_sell']))/df_trades['cost_sell']
df_trades['abs_return_adj'] = (df_trades['cost_sell'] - df_trades['cost_buy']) - (df_trades['fee_buy'] + df_trades['fee_sell'])
df_trades['cumsum'] = df_trades['abs_return_adj'].cumsum()+291.77

import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go

app = dash.Dash(__name__)

app.layout = html.Div([
                        html.H1('Ethereum Trading Bot'),
                        dcc.Graph(
                            figure = {
                                'data': [
                                    go.Scatter(
                                    x = df_trades.index,
                                    y = df_trades['cumsum'],
                                    mode = 'lines+markers'
                                                )
                                        ],
                                 'layout' : go.Layout(
                                    xaxis={'title': 'Time'},
                                    yaxis={'title': 'Portfolio Value ($)'},
                                    margin={'l': 50, 'b':50, 't': 10, 'r': 50},
                                            )
                                    })
                        ])

if __name__ == '__main__':
    app.run_server(debug=True)
