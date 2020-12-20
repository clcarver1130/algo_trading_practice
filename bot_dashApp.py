### Standard imports:
import datetime

### Third party imports:
import pandas as pd
pd.options.mode.chained_assignment = None
import dash
import dash_table
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
import plotly.graph_objs as go
import krakenex
from pykrakenapi import KrakenAPI

# Constants:
kraken_key_filepath = 'kraken_keys.py'

### Helper Functions:
def load_pastTrades(kraken_key_filepath):

    # Connect to API:
    con = krakenex.API()
    con.load_key(kraken_key_filepath)
    api = KrakenAPI(con)

    # Load past trading data:
    df = api.get_trades_history()[0].reset_index()

    # Convert to Central time:
    df['dtime'] = pd.to_datetime(pd.to_datetime(df['dtime']).dt.tz_localize('UTC').dt.tz_convert('US/Central').dt.strftime('%Y-%m-%d %H:%M:%S'))

    # Merge trades with the same order id:
    df_wrangled = df.reset_index().groupby('ordertxid', as_index=False).agg({'dtime':'min',
                                                               'type':'min',
                                                               'ordertype':'min',
                                                               'price':'min',
                                                               'cost':'sum',
                                                               'fee':'sum',
                                                               'vol':'sum'}
                                                               ).sort_values('dtime').reset_index(drop=True)
    # Build buy/sell matching ids:
    df_wrangled['trade_matchID'] = 0
    buy = False
    matchID = 1
    for i, row in df_wrangled.iterrows():
        # Skip the first trade if it's a sell
        if row['type']=='sell':
            if buy:
                df_wrangled['trade_matchID'][i] = matchID
                matchID += 1
                buy = False
            else:
                continue
        elif row['type']=='buy':
            df_wrangled['trade_matchID'][i] = matchID
            buy = True

    # Put the buy and the sell on the same line:
    df_sell = df_wrangled[df_wrangled['type'] == 'sell'].set_index('trade_matchID')
    df_buy = df_wrangled[df_wrangled['type'] == 'buy'].set_index('trade_matchID')
    df_trade = df_buy.merge(df_sell, how='left', left_index=True, right_index=True, suffixes=['_buy', '_sell'])

    # Build new fields:
    df_trade['time_held'] = df_trade['dtime_sell'] - df_trade['dtime_buy']
    df_trade['time_held'] = [str(x) for x in df_trade['time_held']]
    df_trade['fee_total'] = df_trade['fee_buy'] + df_trade['fee_sell']
    df_trade['abs_return'] = df_trade['cost_sell'] - df_trade['cost_buy']
    df_trade['feeAdjusted_abs_return'] = df_trade['cost_sell'] - df_trade['fee_total'] - df_trade['cost_buy']
    df_trade['pct_return'] = df_trade['abs_return']/df_trade['cost_buy']
    df_trade['feeAdjusted_pct_return'] = df_trade['feeAdjusted_abs_return']/df_trade['cost_buy']
    df_trade['winning_trade'] = [1 if x>0 else 0 for x in df_trade['feeAdjusted_pct_return']]

    df_display = df_trade[['dtime_buy', 'dtime_sell', 'time_held', 'abs_return', 'feeAdjusted_abs_return', 'pct_return', 'feeAdjusted_pct_return']].sort_values('dtime_buy', ascending=False).round(3)
    df_display.columns = ['Buy Datetime', 'Sell Datetime', 'Time Held', 'Abs Return', 'Abs Return - Fee Adjusted', 'Pct Return', 'Pct Return - Fee Adjusted']


    return df_trade, df_display

def calculate_cards(df_trade):

    starting_capital = df_trade.iloc[1]['cost_buy']
    current_capital = df_trade.iloc[-1]['cost_sell']
    abs_change = current_capital - starting_capital
    pct_change = (current_capital - starting_capital)/starting_capital
    return round(current_capital, 2), round(abs_change, 2), round(pct_change*100, 2)

def calculate_color(x):
    if x >= 0:
        return 'success'
    else:
        return 'danger'

### Build the Web App:

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])

def load_layout():

    # Load data:
    df, df_display = load_pastTrades(kraken_key_filepath)

    # BUILD CONTAINERS

    # 1. Header:
    markdown_text = f'''
                    # ETH Trading Bot Dashboard
                    Last refresh was: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}
                    ___
                     '''

    # Cards:
    current_capital, abs_change, pct_change = calculate_cards(df)
    card_equity = dbc.Card(dbc.CardBody([html.H4("Current Equity", className="card-title"), html.P(f"{current_capital}", className="card-text")]))
    card_abs = dbc.Card(dbc.CardBody([html.H4("Profit/Loss", className="card-title"), html.P(f"{abs_change}", className="card-text")]), color=calculate_color(abs_change))
    card_pct = dbc.Card(dbc.CardBody([html.H4("Profit/Loss (%)", className="card-title"), html.P(f"{pct_change}", className="card-text")]), color=calculate_color(pct_change))


    # Table:
    table = dbc.Table.from_dataframe(df_display, striped=True, bordered=True, )


    # BUILD LAYOUT:
    return html.Div([
                # Row 1: Header
                dbc.Row(dbc.Col(html.Div([dcc.Markdown(children=markdown_text)]))),
                # Row 2: Cards:
                dbc.Row([
                        dbc.Col(card_equity),
                        dbc.Col(card_abs),
                        dbc.Col(card_pct)
                        ]),

                # Row 3: Table
                dbc.Row(dbc.Col(table), style={'margin-top': '20px'})



                    ])

app.layout = load_layout

if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0')
