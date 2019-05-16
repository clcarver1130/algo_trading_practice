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
df.index = df.index.tz_localize(tz='UTC').tz_convert('US/Central')

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
import plotly.graph_objs as go

app = dash.Dash(__name__)

app.layout = html.Div([
                        html.H1('Ethereum Trading Bot'),
                        dcc.Graph(
                            figure = {
                                'data': [
                                    go.Scatter(
                                    x = df_trades.index,
                                    y = df_trades['pct_return'],
                                    mode = 'lines+markers'
                                                )
                                        ],
                                 'layout' : go.Layout(
                                    xaxis={'title': 'Time'},
                                    yaxis={'title': 'Percent Return'},
                                    margin={'l': 40, 'b': 40, 't': 10, 'r': 10},
                                            )
                                    })
                        ])

if __name__ == '__main__':
    app.run_server(debug=True)
