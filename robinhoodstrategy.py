import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import time
import datetime
import krakenex
from pykrakenapi import KrakenAPI
from robin_helperfunctions import round_to_hour

class cryptoStrategy:
    
    """docstring for crypto_strategy."""

    def __init__(self, strategy_name):
        self.name = strategy_name
        self.entry_exit_conditions = None
        
    def add_entryExit_conditions(self, func):
        self.entry_exit_conditions  = func
        return

class Trade:
    
    '''An object to hold metadata about a trade'''
    
    def __init__(self):
        self.datetime_buy = None
        self.datetime_sell = None
        self.price_buy = None
        self.price_sell = None
        self.period_count = 0
        self.current_price = None
        self.pct_change = 0
        
    def log_buy(self, time, price):
        self.datetime_buy = time
        self.price_buy = price
        
    def log_sell(self, time, price, current_capital):
        self.datetime_sell = time
        self.price_sell = price
        return {'trade_start':self.datetime_buy, 
                'trade_end':self.datetime_sell, 
                'peirods':self.period_count, 
                'time_held':self.datetime_sell - self.datetime_buy,
                'buy_price': self.price_buy, 
                'sell_price':self.price_sell,
                'pct_change': (self.price_sell-self.price_buy)/self.price_buy,
                'current_capital': current_capital}        
    def log_pass(self, current_price):
        self.period_count += 1
        self.current_price = current_price
        self.pct_change = (self.current_price-self.price_buy)/self.current_price
        
        
    
        
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
        
    def set_parameters(self, starting_capital, kraken_pair, data_agg, period_check, periods_needed):
        self.starting_capital = starting_capital
        self.capital = starting_capital
        self.pair = kraken_pair
        self.data_agg = data_agg
        self.period_check = period_check
        self.periods_needed = periods_needed
        self.backcast_data = None
        return 
    
    def _get_backcast_data(self):
        
        api = krakenex.API()
        k = KrakenAPI(api)
        api.load_key('kraken_keys.py')
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
                position_amount = self.capital/current_price
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
        df['winning_trade'] = df['pct_change'].apply(lambda x: 1 if x>0 else 0)
        wins = df[df['winning_trade'] == 1]
        loss = df[df['winning_trade'] == 0]
        num_wins = len(wins)
        num_loss = len(loss)
        win_pct = num_wins/(num_wins+num_loss)
        win_avg = wins['pct_change'].mean()
        loss_avg = loss['pct_change'].mean()
        abs_return = self.capital - self.starting_capital
        pct_return = (self.capital - self.starting_capital)/self.starting_capital
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

        plt.figure(figsize=(30,8))

        plt.plot(self.backcast_data.index, self.backcast_data['close'], lw=2)
        plt.xticks([])

        plt.scatter(self.trades['trade_start'], self.trades['buy_price'], marker='^',s=70, color='green')
        plt.scatter(self.trades['trade_end'], self.trades['sell_price'], marker='v',s=70, color='red')
    
        for i in range(len(self.trades)):
            plt.annotate(i, (self.trades['trade_start'][i], self.trades['buy_price'][i]), xytext=(-10, -10), textcoords='offset points', fontsize=14, fontweight='bold')
            
        for i in range(len(self.trades)):
            plt.annotate(i, (self.trades['trade_end'][i], self.trades['sell_price'][i]), xytext=(-10, -10), textcoords='offset points', fontsize=14, fontweight='bold')
    
        sns.despine()
        plt.show()
            
            
        
        
        
        
        