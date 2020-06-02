### Libraries
import pandas as pd
import sqlite3

import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go

### Constants
DB_NAME = 'crypto_trading'
sql = '''SELECT * FROM history_log;'''


### Helper Functions:
def load_sqlite_data(sql, DB_NAME):
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql(sql, conn)
    return df

### Build the Web App:
df = load_sqlite_data(sql, DB_NAME)

app = dash.Dash(__name__)

app.layout = html.Div([
                        html.H1('Ethereum Trading Bot'),
                        dcc.Graph(
                            figure = {
                                'data': [
                                    go.Scatter(
                                    x = pd.to_datetime(df['time_period_start']),
                                    y = df['macd_current'],
                                    mode = 'lines+markers'
                                                )
                                        ],
                                 'layout' : go.Layout(
                                    xaxis={'title': 'Time'},
                                    yaxis={'title': 'MACD'},
                                    margin={'l': 50, 'b':50, 't': 10, 'r': 50},
                                            )
                                    })
                        ])

if __name__ == '__main__':
    app.run_server(debug=True)
