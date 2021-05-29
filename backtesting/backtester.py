# Standard imports:
import sys
import argparse
from datetime import datetime

# Third party imports:
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import krakenex
from pykrakenapi import KrakenAPI

# Local application imports:

# Constants:



class CryptoStrategy:

    """A class that holds the strategy function"""

    def __init__(self, strategy_name:str, action_func):
        self.name = strategy_name
        self.action_func = action_func


class Trade:

    '''A class that keeps a memory of a trade and it's metadata over the course of the postition '''

    def __init__(self):
        self.datetime_buy = None
        self.datetime_sell = None
        self.price_buy = None
        self.price_sell = None
        self.period_count = 0
        self.current_price = None
        self.pct_change = 0
        self.highest_gain = 0
        self.max_drawdown = 0

    def log_buy(self, time, price):
        self.datetime_buy = time
        self.price_buy = price

    def log_sell(self, time, price, current_capital):
        self.datetime_sell = time
        self.price_sell = price
        return {'trade_start': self.datetime_buy,
                'trade_end': self.datetime_sell,
                'peirods': self.period_count,
                'time_held': self.datetime_sell - self.datetime_buy,
                'buy_price': self.price_buy,
                'sell_price': self.price_sell,
                'pct_change': (self.price_sell - self.price_buy) / self.price_buy,
                'highest_gain': self.highest_gain,
                'max_drawdown': self.max_drawdown,
                'current_capital': current_capital}

    def log_pass(self, current_price):
        self.period_count += 1
        self.current_price = current_price
        self.pct_change = (self.current_price - self.price_buy) / self.price_buy
        if self.pct_change > self.highest_gain:
            self.highest_gain = self.pct_change
        if self.pct_change < self.max_drawdown:
            self.max_drawdown = self.pct_change


class BackcastStrategy:

    '''docstring for backcasting'''

    def __init__(self, strategy):
        self.strategy = strategy
        self.capital = None
        self.symbol = None
        self.data_agg = None
        self.period_check = None
        self.periods_needed = None
        self.trades = dict()

    def set_parameters(self, starting_capital:int, kraken_pair:str, data_agg:int, start_dt:str, end_dt:str, period_check, periods_needed):
        self.starting_capital = starting_capital
        self.capital = starting_capital
        self.pair = kraken_pair
        self.agg = data_agg
        self.start = start_dt
        self.end = end_dt
        self.period_check = period_check
        self.periods_needed = periods_needed
        self.backcast_data = None
        return

    def str_dateTo_unix(dt: str):

        '''Converts a string representation of a date in the YYYY-MM_DD format to datetime object.'''

        date = datetime.strptime(dt, '%Y-%m-%d')

    def _get_backcast_data(self):

        # Connect to Kraken:
        con = krakenex.API()
        api = KrakenAPI(con)

        # Load past trading data:
        last = 0
        total_count = 1
        df_list = []
        unix_start = api.datetime_to_unixtime(datetime.strptime(self.start, '%Y-%m-%d'))
        while unix_start < total_count:
            df, last = api.get_ohlc_data(pair=self.pair, interval=self.agg, since=unix_start)
            df_list.append(df)
            total_count = all_count
            count += len(df)
        df = pd.concat(df_list).reset_index()
        df, last = k.get_ohlc_data(self.pair, interval=self.data_agg, ascending=True)
        df.index = df.index.tz_localize(tz='UTC').tz_convert('US/Central')
        return df

    def run_backcast(self):

        print(f'Running backcast. Staring with ${self.capital}')

        position_amount = 0
        position_flag = False
        trades_dict = dict()

        self.backcast_data = self._get_backcast_data()
        for i in range(len(self.backcast_data) - self.periods_needed):
            df_sliced = self.backcast_data[i:self.periods_needed + i]
            current_price = df_sliced['close'][-1]
            if position_flag:
                action = self.strategy.entry_exit_conditions(df_sliced, position_flag, trade)
            else:
                action = self.strategy.entry_exit_conditions(df_sliced, position_flag)
            if action == 'sell':
                # Execute sell
                self.capital = position_amount * current_price
                position_amount = 0
                position_flag = False
                trades_dict[i] = trade.log_sell(df_sliced.index[-1], current_price, self.capital)
            elif action == 'buy':
                # Execute buy:
                position_amount = self.capital / current_price
                self.capital = 0
                position_flag = True
                trade = Trade()
                trade.log_buy(df_sliced.index[-1], current_price)
            elif action == 'pass':
                if position_flag:
                    trade.log_pass(current_price)
                pass

        # Close position at the end of the backcast:
        if position_flag:
            self.capital = position_amount * current_price
            position_amount = 0
            position_flag = False
            trades_dict[i] = trade.log_sell(df_sliced.index[-1], current_price, self.capital)

        self.trades = pd.DataFrame.from_dict(trades_dict, orient='index').reset_index(drop=True)

    def backcast_results(self):
        df = self.trades
        df['winning_trade'] = df['pct_change'].apply(lambda x: 1 if x > 0 else 0)
        wins = df[df['winning_trade'] == 1]
        loss = df[df['winning_trade'] == 0]
        num_wins = len(wins)
        num_loss = len(loss)
        win_pct = num_wins / (num_wins + num_loss)
        win_avg = wins['pct_change'].mean()
        loss_avg = loss['pct_change'].mean()
        abs_return = self.capital - self.starting_capital
        pct_return = (self.capital - self.starting_capital) / self.starting_capital
        print(f'''
                # Wins: {num_wins}\n
                Average Win: {win_avg}\n
                # Losses: {num_loss}\n
                Average Loss: {loss_avg}\n
                Win %: {win_pct}\n
                Overall return: {abs_return}\n
                Percent return: {pct_return}\n
                ''')
        return

    def plot_trades(self):

        plt.style.use('seaborn-whitegrid')

        plt.figure(figsize=(30, 8))

        plt.plot(self.backcast_data.index, self.backcast_data['close'], lw=2)
        plt.xticks([])

        plt.scatter(self.trades['trade_start'], self.trades['buy_price'], marker='^', s=70, color='green')
        plt.scatter(self.trades['trade_end'], self.trades['sell_price'], marker='v', s=70, color='red')

        for i in range(len(self.trades)):
            plt.annotate(i, (self.trades['trade_start'][i], self.trades['buy_price'][i]), xytext=(-10, -10),
                         textcoords='offset points', fontsize=14, fontweight='bold')

        for i in range(len(self.trades)):
            plt.annotate(i, (self.trades['trade_end'][i], self.trades['sell_price'][i]), xytext=(-10, -10),
                         textcoords='offset points', fontsize=14, fontweight='bold')

        sns.despine()
        plt.show()

def round_to_hour(dt):

    '''Datetime helper function. Rounds the current time to the closest hour.'''

    dt_start_of_hour = dt.replace(minute=0, second=0, microsecond=0)
    dt_half_hour = dt.replace(minute=30, second=0, microsecond=0)
    if dt >= dt_half_hour:
        # round up
        dt = dt_start_of_hour + datetime.timedelta(hours=1)
    else:
        # round down
        dt = dt_start_of_hour
    return dt

def parse_args(args):
    parser = argparse.ArgumentParser(description='')

    parser.add_argument('--strategy_config_file',
                        help='The path to the strategy configuration file. File should include strategy and settings.')

    options = parser.parse_args(args)
    return options


def run_backtest(params):

    # Load strategy file:
    args = parse_args(params)
    if '.py' in args.strategy_config_file:
        args.strategy_config_file = args.strategy_config_file.replace('.py', '')
    strategy_file = __import__(args.strategy_config_file)
    func = strategy_file.strategy
    config = strategy_file.strategy_config
    print(func)
    print(config)

    # Run backtest:
    strategy = CryptoStrategy(strategy_name=config['name'], action_func=func)
    backtest = BackcastStrategy(strategy)

    # Load settings:
    STARTING_CAPITAL = config['starting_capital']
    PAIR = config['crypto'] + config['fiat']
    START = config['start']
    END = config['end']

    backtest.set_parameters(2500, 'XETHZUSD', '240', 1, 39)
    backtest.run_backcast()


if __name__ == '__main__':

    CLI = False
    if not CLI:
        params = ['--strategy_config_file', 'strategy_test_config.py']
    else:
        params = sys.argv[1:]
    run_backtest(params)
