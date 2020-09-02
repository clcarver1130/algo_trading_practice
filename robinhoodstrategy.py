import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import time
import datetime
from coinapi_rest_v1 import CoinAPIv1
from robin_helperfunctions import round_to_hour

class cryptoStrategy:
    
    """docstring for crypto_strategy."""

    def __init__(self, strategy_name):
        self.name = strategy_name
        self.entry_func = None
        self.exit_func = None
        
    def add_entry_conditions(self, entry_func):
        self.entry_func = entry_func
        return
        
    def add_exit_conditions(self, exit_func):
        self.exit_func = exit_func
        return
        
    def change_position(self, position_flag, func_args):     
        if position_flag:
            return self.exit_func(**func_args)
        else:
            return self.entry_func(**func_args)

class Trade:
    
    '''An object to hold metadata about a trade'''
    
    def __init__(self):
        self.datetime_buy = None
        self.datetime_sell = None
        self.price_buy = None
        self.price_sell = None
        self.period_count = 0
        self.current_price = None
        self.pct_change = None
        
    def log_buy(self, time, price):
        self.datetime_buy = time
        self.price_buy = price
        
    def log_sell(self, time, price):
        self.datetime_sell = time
        self.price_sell = price
        return {'trade_start':self.datetime_buy, 
                'trade_end':self.datetime_sell, 
                'peirods':self.period_count, 
                'buy_price': self.price_buy, 
                'sell_price':self.price_sell,
                'pct_change': (self.price_sell-self.price_buy)/self.price_buy}
        
    def log_pass(self, current_price):
        self.period_count += 1
        self.current_price = current_price
        self.pct_change = (self.current_price-self.price_buy)/self.current_price
        
        
    
        
class BackcastStrategy:
    
    '''docstring for backcasting'''
    
    def __init__(self, strategy):
        self.strategy = strategy
        self.starting_capital = None
        self.symbol = None
        self.start_datetime = None
        self.end_datetime = None
        self.data_agg = None
        self.period_check = None
        self.periods_needed = None
        self.trades = dict()
        
    def set_parameters(self, starting_capital, coinapi_symbol, start_datetime, end_datetime, data_agg, period_check, periods_needed):
        self.capital = starting_capital
        self.symbol = coinapi_symbol
        self.start_datetime = start_datetime
        self.end_datetime = end_datetime
        self.data_agg = data_agg
        self.period_check = period_check
        self.periods_needed = periods_needed
        self.backcast_data = None
        return 
    
    def _get_backcast_data(self, CoinAPI_KEY):
        
        coin_api = CoinAPIv1(CoinAPI_KEY)
        params = {'period_id':self.data_agg, 'time_start':self.start_datetime, 'time_end':self.end_datetime, 'limit':100000}
        df = pd.DataFrame(coin_api.ohlcv_historical_data(self.symbol, params)).set_index('time_period_start')
        return df
    
    def run_backcast(self, CoinAPI_KEY):
        
        print(f'Running backcast between {self.start_datetime} and {self.end_datetime}. Staring with ${self.starting_capital}')
        
        position_amount = 0
        position_flag = False
        trades_dict = dict()
        
        self.backcast_data = self._get_backcast_data(CoinAPI_KEY)
        for i in range(len(self.backcast_data) - self.periods_needed):
            df_sliced = self.backcast_data[i:self.periods_needed + i]
            current_price = df_sliced['price_close'][-1]
            if self.strategy.change_position(position_flag, {'hist_data':df_sliced}):
                if position_flag:
                    # Execute sell
                    self.capital = position_amount * current_price
                    position_amount = 0
                    position_flag = False
                    trades_dict[i] = trade.log_sell(df_sliced.index[-1], current_price)
                else:
                    # Execute buy:
                    position_amount = self.capital/current_price
                    self.capital = 0
                    position_flag = True
                    trade = Trade()
                    trade.log_buy(df_sliced.index[-1], current_price)
            else:
                if position_flag:
                    trade.log_pass(current_price)
                pass
        
        # Close position at the end of the backcast:
        if position_flag:
            self.capital = position_amount * current_price
            
        
        self.trades = pd.DataFrame.from_dict(trades_dict, orient='index').reset_index(drop=True)
        
    def plot_trades(self):
        
        plt.style.use('seaborn-whitegrid')

        plt.figure(figsize=(30,8))

        plt.plot(self.backcast_data.index, self.backcast_data['price_close'], lw=2)
        plt.xticks([])

        plt.scatter(self.trades['trade_start'], self.trades['buy_price'], marker='^',s=70, color='green')
        plt.scatter(self.trades['trade_end'], self.trades['sell_price'], marker='v',s=70, color='red')
    
        sns.despine()
        plt.show()
            
            
        
        
        
        
        