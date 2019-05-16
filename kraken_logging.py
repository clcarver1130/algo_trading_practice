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

import dash
import dash_core_components as dcc
import dash_html_components as html

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div(children=[
    html.H1(children='ETH Trading Bot Reporting'),
    dcc.Graph(
    id='example-graph',
    figure={
        'data': [
            {'x': [1, 2, 3], 'y': [4, 1, 2], 'type': 'bar', 'name': 'SF'},
            {'x': [1, 2, 3], 'y': [2, 4, 5], 'type': 'bar', 'name': u'Montréal'},
        ],
        'layout': {
            'title': 'Dash Data Visualization'
        }
    }
)
])

if __name__ == '__main__':
    app.run_server(debug=True)
