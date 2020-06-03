### Libraries
import pandas as pd
import sqlite3
import datetime

import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

### Constants
DB_NAME = 'crypto_trading'
sql = '''SELECT * FROM history_log;'''


### Helper Functions:
def load_sqlite_data(sql, DB_NAME):
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql(sql, conn)
    return df

### Build the Web App:

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

def load_layout():
    df = load_sqlite_data(sql, DB_NAME)

    candle_fig = go.Figure(data=[go.Candlestick(x=df['time_period_start'],
                    open=df['price_open'],
                    high=df['price_high'],
                    low=df['price_low'],
                    close=df['price_close'])])

    markdown_text = '''
    # ETH Trading Bot Dashboard
    Last refresh was: {}
    ___
    '''.format(str(datetime.datetime.now()))

    return html.Div([
                # Title
                html.Div([dcc.Markdown(children=markdown_text)]),
                # html.H1('Ethereum Trading Bot'),
                # html.H6('Last refresh was: ' + str(datetime.datetime.now())),

                # Candlestick Chart:
                html.Div([
                html.H5('ETH Price Chart:'),
                dcc.Graph(figure=candle_fig),
                        ]),

                html.Div([
                    html.H5('Moving Average Convergence-Divergence (MACD):'),
                    # MACD Chart:
                    dcc.Graph(
                        figure = {
                            'data': [
                                go.Scatter(
                                x = pd.to_datetime(df['time_period_start']),
                                y = df['macd_current'],
                                mode = 'lines',
                                name='MACD (12, 26)'
                                            ),
                                go.Scatter(
                                x = pd.to_datetime(df['time_period_start']),
                                y = df['macd_signal_current'],
                                mode = 'lines',
                                name = 'MACD Signal (9)'
                                            )
                                    ],
                             'layout' : go.Layout(
                                xaxis={'title': 'Time (Zulu)'},
                                yaxis={'title': 'MACD'},
                                margin={'l': 50, 'b':50, 't': 10, 'r': 50},
                                        )
                                },
                            )
                        ]),

                html.Div([
                    html.H5('ADX and Directional Indicator (ADX and DI):'),
                    # MACD Chart:
                    dcc.Graph(
                        figure = {
                            'data': [
                                go.Scatter(
                                x = pd.to_datetime(df['time_period_start']),
                                y = df['adx_current'],
                                mode = 'lines',
                                name='ADX (12)'
                                            ),
                                go.Scatter(
                                x = pd.to_datetime(df['time_period_start']),
                                y = df['di_plus_current'],
                                mode = 'lines',
                                name = 'DI Plus (12)'
                                            ),
                                go.Scatter(
                                x = pd.to_datetime(df['time_period_start']),
                                y = df['di_minus_current'],
                                mode = 'lines',
                                name = 'DI Minus (12)'
                                            ),
                                    ],
                             'layout' : go.Layout(
                                xaxis={'title': 'Time (Zulu)'},
                                yaxis={'title': 'ADX and DI'},
                                margin={'l': 50, 'b':50, 't': 10, 'r': 50},
                                        )
                                },
                            )
                        ])
                    ]) # Overall divider

app.layout = load_layout

if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0')
