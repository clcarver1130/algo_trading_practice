# Standard imports:
import sys
import argparse
from datetime import datetime
import os
from importlib import import_module

# Third party imports:
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
import seaborn as sns
import krakenex
from pykrakenapi import KrakenAPI
import warnings
warnings.filterwarnings('ignore')

# Local application imports:

# Constants:


class CryptoStrategy:

    """A class that holds the strategy function"""

    def __init__(self, strategy_name:str, action_func):
        self.name = strategy_name
        self.action_func = action_func


class Trade:

    '''A class that keeps a memory of a trade and it's metadata over the course of the postition '''

    def __init__(self, stop_loss=None):
        self.datetime_buy = None
        self.datetime_sell = None
        self.price_buy = None
        self.price_sell = None
        self.period_count = 0
        self.current_price = None
        self.pct_change = 0
        self.highest_gain = 0
        self.max_drawdown = 0
        self.stop_loss_price = stop_loss

    def log_buy(self, time, price):
        self.datetime_buy = time
        self.price_buy = price
        self.stop_loss_price = self.price_buy * (1 - self.stop_loss_price) if self.stop_loss_price else None

    def log_sell(self, time, price, current_capital, stop_loss=0):
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
                'current_capital': current_capital,
                'stop_loss_flag': stop_loss}

    def log_pass(self, current_price):
        self.period_count += 1
        self.current_price = current_price
        self.pct_change = (self.current_price - self.price_buy) / self.price_buy
        if self.pct_change > self.highest_gain:
            self.highest_gain = self.pct_change
        if self.pct_change < self.max_drawdown:
            self.max_drawdown = self.pct_change

    def stop_loss_flag(self, stop_loss, current_min):

        if self.stop_loss_price:
            if  current_min <= self.stop_loss_price:
                return True
            else:
                return False
        else:
            return False






class BackcastStrategy:

    '''docstring for backcasting'''

    def __init__(self, strategy):
        self.strategy = strategy
        self.strategy_name = self.strategy.name
        self.capital = None
        self.cryto_sym = None
        self.fiat_sym = None
        self.data_agg = None
        self.period_check = None
        self.periods_needed = None
        self.stop_loss = None
        self.trades = dict()
        self.datestamp = datetime.now().strftime('%Y-%m-%d_%H%M')

    def set_parameters(self, starting_capital:int, crypto_sym:str, fiat_sym:str, data_agg:int, start_dt:str, end_dt:str, min_periods_needed:int, stop_loss:float):
        self.starting_capital = starting_capital
        self.capital = starting_capital
        self.cryto_sym = crypto_sym
        self.fiat_sym = fiat_sym
        self.agg = data_agg  # must be: 1m, 5m, 15m, 1h, 6h, or 1d
        self.start = start_dt
        self.end = end_dt
        self.backcast_data = None
        self.periods_needed = min_periods_needed
        self.stop_loss = stop_loss if stop_loss else None
        return

    def _str_dateTo_unix(self, dt: str):

        """Converts a string representation of a date in the YYYY-MM_DD format to a unix timestamp."""

        return datetime.strptime(dt, '%Y-%m-%d').timestamp()

    def next_smallest_agg(self, agg, current_min_intervals):

        for i, interval in enumerate(current_min_intervals):
            if interval < agg:
                continue
            else:
                return current_min_intervals[i-1]

    def _get_backcast_data(self):

        current_min_intervals = [1, 5, 15, 60, 720, 1440]

        # Load parameters
        pair = self.cryto_sym + self.fiat_sym
        if self.agg in current_min_intervals:
            data_build_flag = False
            query_agg = self.agg
        else:
            data_build_flag = True
            query_agg = self.next_smallest_agg(self.agg, current_min_intervals)
            print(f"{self.agg} is not a currently offered interval. Loading the {query_agg} intervals instead and building up to {self.agg}.")

        # Load dataset
        df = pd.read_csv(f"backcast_csv_data/{pair}_{query_agg}.csv", names=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'trades'])
        df.index = pd.to_datetime(df['timestamp'], unit='s')

        # Convert to correct interval:
        if data_build_flag:
            df = df.resample(f'{self.agg}T').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum',
                'trades': 'sum'
            })
            df = df.ffill() # forward fill early NaN's

        # Filter based on start and end time:
        if self.end:
            df = df.loc[self.start:self.end]
        else:
            df = df.loc[self.start:]
            self.end = df.index[-1].date().strftime('%Y-%m-%d')

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
            action = self.strategy.action_func(df_sliced, position_flag)
            if position_flag and self.stop_loss:
                if trade.stop_loss_flag(self.stop_loss, df_sliced['low'][-1]):
                    self.capital = position_amount * trade.stop_loss_price
                    position_amount = 0
                    position_flag = False
                    trades_dict[i] = trade.log_sell(df_sliced.index[-1], trade.stop_loss_price, self.capital, stop_loss=1)
                    continue
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
                trade = Trade(self.stop_loss)
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

    def build_summary_report(self):
        df = self.trades
        df['winning_trade'] = df['pct_change'].apply(lambda x: 1 if x > 0 else 0)
        wins = df[df['winning_trade'] == 1]
        loss = df[df['winning_trade'] == 0]
        num_wins = len(wins)
        num_loss = len(loss)
        win_pct = num_wins / (num_wins + num_loss)
        win_avg = wins['pct_change'].mean()
        win_max = wins['pct_change'].max()
        loss_avg = loss['pct_change'].mean()
        loss_max = loss['pct_change'].min()
        abs_return = self.capital - self.starting_capital
        pct_return = (self.capital - self.starting_capital) / self.starting_capital

        df = pd.DataFrame([
                            ['Starting Capital', f"${self.starting_capital}"],
                            ['Ending Capital', f"${int(self.capital)}"],
                            ['Overall Return', f"${int(abs_return)}"],
                            ['Percent Return', f"{pct_return:.2%}"],
                            ['Wins', num_wins],
                            ['Average Win', f"{win_avg:.2%}"],
                            ['Largest Win', f"{win_max:.2%}"],
                            ['Win Ratio', f"{win_pct:.2%}"],
                            ['Losses', num_loss],
                            ['Average Loss', f"{loss_avg:.2%}"],
                            ['Largest Loss', f"{loss_max:.2%}"],
                            ['Backcast Range', f"{self.start} to {self.end}"],
                            ["Number of Candlesticks", f"{len(self.backcast_data)}"],
                            ["Number of Trades", f"{len(self.trades)}"],
                            [f"Trade to Candlestick ratio", f"{len(self.trades)/len(self.backcast_data):.2}"]
            ])

        return df

    def build_trades_plot(self):

        # Plot 1:
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

        # Save figure1:
        fname = f"{self.strategy_name}_{self.datestamp}_trades"
        filepath = f'backtest_summaries/{fname}.png'
        plt.savefig(filepath)
        return filepath

    def build_comparison_chart(self):

        df_trades = pd.DataFrame(self.trades)

        # Current strategy dataset:
        df_strategy = df_trades[['pct_change']]
        df_strategy.index = [x.date() for x in df_trades['trade_end']]
        df_strategy.rename(columns={'pct_change': 'strategy'}, inplace=True)
        # plt.plot([-1] + df_trades.index.tolist(), [self.starting_capital] + df_trades['current_capital'].tolist(), lw=2)
        # plt.plot([self.backcast_data])

        # Buy and hold dataset:
        pair = self.cryto_sym + self.fiat_sym
        df_bh = pd.read_csv(f"backcast_csv_data/{pair}_1440.csv", names=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'trades'])
        df_bh.index = pd.to_datetime(df_bh['timestamp'], unit='s')
        df_bh = df_bh.loc[self.start:self.end]
        df = df_bh[['close']].pct_change()
        df.rename(columns={'close': 'buy_and_hold'}, inplace=True)

        # S&P 500 Dataset:
        spy_ohlc_df = yf.download('SPY', start=self.start, end=self.end, progress=False)
        df_spy = spy_ohlc_df[['Close']].pct_change().rename(columns={'Close': 's&p500'})

        # Merge datasets and plot:
        df_merge_temp = df.merge(df_strategy, left_index=True, right_index=True, how='left')
        df_merge = df_merge_temp.merge(df_spy, left_index=True, right_index=True, how='left')
        df_merge.fillna(0, inplace=True)
        plt.style.use('seaborn-whitegrid')
        df_merge.cumsum().plot(figsize=(30, 8))
        fname = f"{self.strategy_name}_{self.datestamp}_compare"
        filepath = f'backtest_summaries/{fname}.png'
        plt.savefig(filepath)

        return filepath

    def build_backcast_report(self):

        # Build the summary tab
        fname = f"{self.strategy_name}_{self.datestamp}"
        writer = pd.ExcelWriter(f"backtest_summaries/{fname}.xlsx", engine='xlsxwriter')
        df_summary = self.build_summary_report()
        df_summary.to_excel(writer, sheet_name='Backtest Summary', index=False, header=False)

        # Build the trades tab:
        df_trades = pd.DataFrame(self.trades)
        df_trades['time_held'] = [str(x) for x in df_trades['time_held']]
        df_trades.to_excel(writer, sheet_name='Trades')

        # Build plots:
        plot1_filepath = self.build_trades_plot()
        plot_worksheet1 = writer.book.add_worksheet(name='Trades Plot')
        plot_worksheet1.insert_image('C2', plot1_filepath)

        plot2_filepath = self.build_comparison_chart()
        plot_worksheet2 = writer.book.add_worksheet(name='Comparison Plot')
        plot_worksheet2.insert_image('C2', plot2_filepath)

        # Save the file:
        writer.save()

        # Delete files:
        os.remove(plot1_filepath)
        os.remove(plot2_filepath)

        return


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
    strategy_file = import_module(args.strategy_config_file)
    func = strategy_file.strategy
    config = strategy_file.strategy_config

    # Load backtest:
    strategy = CryptoStrategy(strategy_name=config['name'], action_func=func)
    backtest = BackcastStrategy(strategy)

    # Load settings:
    backtest.set_parameters(starting_capital=config['starting_capital'],
                            crypto_sym=config['crypto_sym'],
                            fiat_sym=config['fiat_sym'],
                            data_agg=config['agg'],
                            start_dt=config['start'],
                            end_dt=config['end'],
                            min_periods_needed=config['periods_needed'],
                            stop_loss=config['stop_loss'])

    # Run backtest and create report
    backtest.run_backcast()
    backtest.build_backcast_report()
    print('Backtest Complete. Results saved to backtest_summaries/')
    return


if __name__ == '__main__':

    CLI = False
    if not CLI:
        params = ['--strategy_config_file', 'backtest_config_files.MACD_03stoploss_config.py']
    else:
        params = sys.argv[1:]
    run_backtest(params)
