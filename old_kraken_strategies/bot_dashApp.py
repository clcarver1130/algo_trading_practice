### Standard imports:
import datetime
import time

### Third party imports:
import pandas as pd
pd.options.mode.chained_assignment = None
import dash
import dash_table
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import krakenex
from pykrakenapi import KrakenAPI

# Constants:
kraken_key_filepath = 'kraken_keys.py'
FIAT = 'ZUSD'
CRYPTO = 'XETH'
INTERVAL = 240 # 4 hours

### Helper Functions:
def load_data(start):

    # Connect to API:
    con = krakenex.API()
    con.load_key(kraken_key_filepath)
    api = KrakenAPI(con)

    # Load past trading data:
    count = 0
    total_count = 1
    df_list = []
    unix_start = api.datetime_to_unixtime(pd.to_datetime(start))
    while count < total_count:
        df, all_count = api.get_trades_history(start=unix_start, ofs=count)
        df = df[df['pair'] == CRYPTO + FIAT]
        df_list.append(df)
        total_count = all_count
        count += len(df)
        time.sleep(1)
    df = pd.concat(df_list).reset_index()
    df = df.drop_duplicates()

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
    return df_trade

def as_currency(amount):
    if amount >= 0:
        return f"${amount:,.2f}"
    else:
        return f"-${-amount:,.2f}"

def as_percent(amount):
    return f"{amount*100:.2f}%"

def load_displayTable(start):

    df_trade = load_data(start)

    if isNaN(df_trade.iloc[-1]['cost_sell']):
        current_capital = calculate_capital()
        df_trade.iloc[-1, df_trade.columns.get_loc('cost_sell')] = current_capital
        df_trade['abs_return'] = df_trade['cost_sell'] - df_trade['cost_buy']
        df_trade['pct_return'] = df_trade['abs_return']/df_trade['cost_buy']
        df_trade = df_trade.fillna('Not sold yet')
    else:
        pass

    df_display = df_trade[['dtime_buy', 'dtime_sell', 'time_held', 'abs_return', 'feeAdjusted_abs_return', 'pct_return', 'feeAdjusted_pct_return']].sort_values('dtime_buy', ascending=False).round(3)
    df_display.columns = ['Buy Datetime', 'Sell Datetime', 'Time Held', 'Abs Return', 'Abs Return - Fee Adjusted', 'Pct Return', 'Pct Return - Fee Adjusted']

    df_display['Abs Return'] = df_display['Abs Return'].apply(lambda x: as_currency(x) if isinstance(x, float) else x)
    df_display['Abs Return - Fee Adjusted'] = df_display['Abs Return - Fee Adjusted'].apply(lambda x: as_currency(x) if isinstance(x, float) else x)
    df_display['Pct Return'] = df_display['Pct Return'].apply(lambda x: as_percent(x) if isinstance(x, float) else x)
    df_display['Pct Return - Fee Adjusted'] = df_display['Pct Return - Fee Adjusted'].apply(lambda x: as_percent(x) if isinstance(x, float) else x)

    return df_display

def check_openPosition(crypto_on_hand, crypto_thresh=0.01):

    '''Check if there is a current open crypto position.'''

    if crypto_on_hand >= crypto_thresh:
        return True
    else:
        return False

def calculate_color(x):
    if x >= 0:
        return 'success'
    else:
        return 'danger'

def load_cash():
    current_capital = calculate_capital()
    return dbc.Card(dbc.CardBody([html.H4("Current Equity", className="card-title"), html.P(f"${current_capital}", className="card-text")]))

def isNaN(num):
    return num != num

def calculate_capital():

    # Connect to API:
    con = krakenex.API()
    con.load_key(kraken_key_filepath)
    api = KrakenAPI(con)

    volume = api.get_account_balance()
    crypto_on_hand = volume.loc[CRYPTO][0]
    open_position = check_openPosition(crypto_on_hand)
    if open_position:
        current_price = float(api.get_ticker_information(CRYPTO+FIAT)['c'][0][0])
        return round(current_price * crypto_on_hand, 2)
    else:
        return round(float(volume.loc[FIAT][0]), 2)

def calculate_changes(start):
    df_trade = load_data(start)
    starting_capital = df_trade.iloc[1]['cost_buy']
    current_capital = calculate_capital()
    abs_change = round(current_capital - starting_capital, 2)
    pct_change = round(((current_capital - starting_capital)/starting_capital)*100, 2)
    num_trades = len(df_trade)
    num_wins = len(df_trade[df_trade['winning_trade'] == 1])
    win_pct = int(100*(num_wins/num_trades))
    avg_win = round(df_trade[df_trade['winning_trade'] == 1]['pct_return'].mean(), 3)
    avg_loss = round(df_trade[df_trade['winning_trade'] == 0]['pct_return'].mean(), 3)
    return current_capital, abs_change, pct_change, num_trades, num_wins, win_pct, avg_win, avg_loss

def table_card(df):
    return dbc.Table.from_dataframe(df, style={'textAlign': 'left'})

def capital_card(current_capital):
    return dbc.Card(dbc.CardBody([html.H4("Current Equity", className="card-title"), html.P(f"${current_capital}", className="card-text")]))

def absChange_card(abs_change):
    return dbc.Card(dbc.CardBody([html.H4("Profit/Loss", className="card-title"), html.P(f"${abs_change}", className="card-text")]), color=calculate_color(abs_change))

def pctChange_card(pct_change):
    return dbc.Card(dbc.CardBody([html.H4("Profit/Loss (%)", className="card-title"), html.P(f"{pct_change}%", className="card-text")]), color=calculate_color(pct_change))

def numTrades_card(num_trades):
    return dbc.Card(dbc.CardBody([html.H4("Trades", className="card-title"), html.P(num_trades, className="card-text")]))

def numWins_card(num_wins):
    return dbc.Card(dbc.CardBody([html.H4("Wins", className="card-title"), html.P(num_wins, className="card-text")]))

def winPct_card(win_pct):
    return dbc.Card(dbc.CardBody([html.H4("Win Percentage", className="card-title"), html.P(f"{win_pct}%", className="card-text")]))

def avgWin_card(avg_win):
    return dbc.Card(dbc.CardBody([html.H4("Average Win", className="card-title"), html.P(as_percent(avg_win), className="card-text")]))

def avgLoss_card(avg_loss):
    return dbc.Card(dbc.CardBody([html.H4("Average Loss", className="card-title"), html.P(as_percent(avg_loss), className="card-text")]))

### Build the Web App:
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])


# BUILD CONTAINERS

# 1. Header:
def load_layout():
    markdown_text = f'''
                    # ETH Trading Bot Dashboard
                    *Last refresh was: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}*
                    ___
                     '''

    # Slider:
    table_filter = dbc.FormGroup([
                                dbc.Label("Trades Since:"),
                                dbc.Input(id="date-input", type="date", value="2020-12-20")
                                ])

    # BUILD LAYOUT:
    return html.Div(
                            [
                # Row 1: Header
                dbc.Row(dbc.Col(html.Div([dcc.Markdown(children=markdown_text)]))),
                # Row 2: Filter
                dbc.Row(dbc.Col(table_filter, width=4), style={'margin-top': '20px'}),
                html.Hr(),
                # Row 3: Profit/Loss Cards
                html.H4('Performance metrics:'),
                dbc.Row([
                        dbc.Col(html.Div(id='capital')),
                        dbc.Col(html.Div(id='abs_change')),
                        dbc.Col(html.Div(id='pct_change'))
                        ]),
                html.Hr(),
                html.H4('Strategy metrics:'),
                # Row 4: Strategy info:
                dbc.Row([
                        dbc.Col(html.Div(id='num_trades')),
                        dbc.Col(html.Div(id='num_wins')),
                        dbc.Col(html.Div(id='win_pct')),
                        dbc.Col(html.Div(id='avg_win')),
                        dbc.Col(html.Div(id='avg_loss'))
                        ]),
                html.Hr(),
                # Row 5: Table
                html.H4('Trade data:'),
                dbc.Row(dbc.Col(html.Div(id='trade_table')), style={'margin-top': '20px'})
                            ], style={'marginLeft': 25, 'marginTop': 25, 'marginRight': 25, 'marginBottom': 25}
                        )

app.layout = load_layout
# - CALLBACKS -

# FILTER TABLE:
@app.callback(Output('trade_table', 'children'), [Input('date-input', 'value')])
def load_table(since_date):
    df_display = load_displayTable(since_date)
    return table_card(df_display)

@app.callback(Output('capital', 'children'),
              Output('abs_change', 'children'),
              Output('pct_change', 'children'),
              Output('num_trades', 'children'),
              Output('num_wins', 'children'),
              Output('win_pct', 'children'),
              Output('avg_win', 'children'),
              Output('avg_loss', 'children'),
              [Input('date-input', 'value')])
def load_changes(since_date):
    current_capital, abs_change, pct_change, num_trades, num_wins, win_pct, avg_win, avg_loss = calculate_changes(since_date)
    return capital_card(current_capital), absChange_card(abs_change), pctChange_card(pct_change), numTrades_card(num_trades), numWins_card(num_wins), winPct_card(win_pct), avgWin_card(avg_win), avgLoss_card(avg_loss)



if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=7000)
