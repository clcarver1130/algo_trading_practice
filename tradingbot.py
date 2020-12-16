import pandas as pd
import schedule
import time
from logger import logging
import krakenex
from pykrakenapi import KrakenAPI 



class Kraken_Trading_Bot:

    """
    A class used to execute trading strategies and place orders on Kraken.

    ...

    Attributes
    ----------

    api : pykrakenapi object



    Methods
    -------

    connect_account()
        connects to your kraken account and initializes the api object.

    get_historical_data()
        returns a dataframe of OHLCV data for the inputed ticker.

    add_strategy()
        adds a strategy function that returns the action of the bot.

    calculate_balances()
        calcuates current balances and volumes of your account.

    """

    def __init__(self, kraken_key_filepath, currency, crypto, interval, strategy):

        """
        Parameters
        ----------
        kraken_key_filepath : str
            Path to the file that holds your kraken account credentials.

        pair : str
            string representing the trading ticker

        strategy : function
            funciton that returns the action the bot should take.
            Strategy funciton must return either 'buy', 'sell', or 'pass'

        hist_data : dataframe
            dataframe with OHLCV information
        """

        self.api, self.con = self.connect_account(kraken_key_filepath)
        self.currency = currency
        self.crypto = crypto
        self.interval = interval
        self.strategy = strategy
        self.pair = self.crypto + self.currency
        self.hist_data = self.get_historical_data(self.pair, self.interval)
        self.current_price = self.hist_data.iloc[-1]['close']
        self.cash_on_hand, self.crypto_on_hand, self.open_position = self.calculate_balances()
        self.affordable_shares = self.cash_on_hand/self.current_price

    def connect_account(self, kraken_key_filepath):

        '''Connects to a private Kraken account.

        kraken_key_filepath : str
            kraken_key_filepath must be a Python file in the format:

            <API_KEY>
            <API_SECRET_KEY>

            On the first two lines.

        pair : ticker pair that you are trading
        interval : aggregation of the historical data
        '''

        # Connect to API:
        con = krakenex.API()
        con.load_key(kraken_key_filepath)
        api = KrakenAPI(con)
        return api, con

    def get_historical_data(self, pair:str, interval:int, timezone='US/Central'):

        '''Return OHLCV data for the inputed pair and aggregation'''

        df = self.api.get_ohlc_data(self.pair, interval=240, ascending=True)[0]
        df.index = df.index.tz_localize(tz='UTC').tz_convert(timezone)
        return df

    def check_openPosition(self, crypto_on_hand, crypto_thresh=0.01):

        '''Check if there is a current open crypto position.'''

        if crypto_on_hand >= crypto_thresh:
            return True
        else:
            return False

    def calculate_balances(self):

        '''Calculate the current crypto and fiat volume on hand'''

        volume = self.api.get_account_balance()
        cash_on_hand = volume.loc[self.currency][0]
        crypto_on_hand = volume.loc[self.crypto][0]
        open_position = self.check_openPosition(crypto_on_hand)
        return cash_on_hand, crypto_on_hand, open_position

    def calculate_affordable_shares(self):
        
        self.affordable_shares = self.cash_on_hand/self.current_price
        return

    def limit_buy_order(self, seconds_toCancel=30):

        '''Create an entry order and a stop loss order to match it'''

        # Place buy order:
        buy_order = self.con.query_private('AddOrder', {'pair': self.pair,
                                                        'type': 'buy',
                                                        'ordertype': 'limit',
                                                        'price': self.current_price,
                                                        'volume': self.affordable_shares,
                                                        'expiretm': f'+{seconds_toCancel}'})
        # Confirm there are no erros:
        if len(buy_order['error']) == 0:
            logging.info(f'Placed order for {self.affordable_shares} shares at {self.current_price}...')
            # Wait for it to fill or expire:
            logging.info('Waiting for order to fill...')
            while len(self.api.get_open_orders()) > 0:
                time.sleep(3)
            completed_order = self.api.get_closed_orders()[0].loc[buy_order['result']['txid'][0]]
            return buy_order, completed_order
        else:
            logging.info(f"Buy order error: {buy_order['error'][0]}")
            return

    def stop_loss_order(self, completed_order):
        
        stop_loss_percent = 0.01
        stop_loss_price = round(completed_order['price']*(1-stop_loss_percent), 2)
        stop_loss_order = self.con.query_private('AddOrder', {'pair': self.pair, 
                                                         'type': 'sell', 
                                                         'ordertype':'stop-loss', 
                                                         'price': stop_loss_price,
                                                         'volume': completed_order['vol']})
         if len(stop_loss_order['error']) == 0:
            logging.info(f'Placed stop loss order {stop_loss_price}.')
            return
        else:
            logging.info(f"Stop loss order error: {stop_loss_order['error'][0]}")
            return
        
        return
    
    def exit_logic(self, seconds_toCancel=60):
        
        '''Cancel our outstanding stop-loss order and close our open position - hopefully for a large return :)'''
        
        # Cancel stop loss order:
        try:
            stopLoss_id = self.api.get_open_orders().index[0]
            self.api.cancel_open_order(stopLoss_id)
        except:
            logging.info('No stop loss order to cancel.')
        
        # Create sell order:
        sell_order = self.con.query_private('AddOrder', {'pair': self.pair,
                                               'type': 'sell',
                                               'ordertype':'limit',
                                               'price': self.current_price,
                                               'volume': self.crypto_on_hand,
                                               'expiretm': f'+{seconds_toCancel}'})
        if len(sell_order['error']) == 0:
            logging.info(f'Placed order to sell {self.crypto_on_hand} shares at {self.current_price}.')
            # Wait for it to fill or expire:
            logging.info('Waiting for order to fill...')
            while len(self.api.get_open_orders()) > 0:
                time.sleep(3)
            completed_order = self.api.get_closed_orders()[0].loc[sell_order['result']['txid'][0]]
            return sell_order, completed_order
        else:
            logging.info(f"Sell order error: {sell_order['error'][0]}.")
