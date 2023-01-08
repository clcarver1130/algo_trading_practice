# Standard imports:
from logger import logging
import time

# Third party imports:
import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import REST, TimeFrame


# Local imports:
from alpaca_strategies.alpaca_keys import alpaca_live_keyid, alpaca_live_secret, alpaca_live_url
from alpaca_strategies.alpaca_keys import alpaca_paper_keyid, alpaca_paper_secret, alpaca_paper_url

# Constants:
LIVE = False
CRYPTO_DATA_URL = 'https://data.alpaca.markets/v1beta2/crypto/bars'
SYM = 'ETHUSD'

class AlpacaBot:
    def __init__(self, symbol, timeframe):
        # Variables:
        self.symbol = symbol
        self.timeframe = timeframe

        # Price information
        self.crypto_api = self.connect_crypto_account()
        self.hist_data = self.get_historical_data()
        self.current_price = self.hist_data.iloc[-1]['close']

        # Account information:
        self.api = self.connect_account()
        self.cash_on_hand, self.crypto_on_hand, self.open_position = self.calculate_balances()
        self.affordable_shares = round(self.cash_on_hand / self.current_price, 3)

    @staticmethod
    def connect_account():
        if LIVE:
            return REST(alpaca_live_keyid, alpaca_live_secret, alpaca_live_url, 'v2')
        else:
            return REST(alpaca_paper_keyid, alpaca_paper_secret, alpaca_paper_url, 'v2')

    @staticmethod
    def connect_crypto_account():
        if LIVE:
            return REST(alpaca_live_keyid, alpaca_live_secret, CRYPTO_DATA_URL)
        else:
            return REST(alpaca_paper_keyid, alpaca_paper_secret, CRYPTO_DATA_URL)

    def get_historical_data(self, start=None, end=None, exchanges=['FTXU']):
        return self.crypto_api.get_crypto_bars(self.symbol, self.timeframe, start, end, exchanges=exchanges).df

    def check_open_positions(self):
        return True if self.api.list_positions() else False

    def get_crypto_onhand(self):
        positions = self.api.list_positions()
        if not positions:
            return 0
        else:
            return positions[0].qty

    def get_cash_onhand(self):
        return self.api.get_account().cash

    def calculate_balances(self):
        cash_on_hand = float(self.get_cash_onhand())
        crypto_on_hand = float(self.get_crypto_onhand())
        open_position = self.check_open_positions()
        return cash_on_hand, crypto_on_hand, open_position

    def limit_buy_order(self, seconds_toCancel=30):

        try:
            buy_order = self.api.submit_order(
                            symbol=self.symbol,
                            notional=self.affordable_shares,
                            side='buy',
                            type='limit',
                            time_in_force='gtc',
                            limit_price=self.current_price,
                            )
            logging.info(f'Placed order for {self.affordable_shares} shares at ${self.current_price:.2}...')
            logging.info('Waiting for order to fill...')
            while len(self.api.list_orders(status='open')) > 0:
                time.sleep(3)
            logging.info('Order filled!')
            return buy_order.id
        except:
            logging.info(f'ERROR: Attempted order for {self.affordable_shares} shares at ${self.current_price:.2}')
            return None

    def oto_buy_order(self, stop_price, limit_price=None, side='stop_loss'):

        '''

        Parameters
        ----------
        side: 'stop_loss' or 'take_profit'

        Returns
        -------

        '''

        try:
            if side == 'stop_loss':
                buy_order = self.api.submit_order(
                                symbol=self.symbol,
                                notional=self.affordable_shares,
                                side='buy',
                                type='limit',
                                time_in_force='gtc',
                                order_class='oto',
                                limit_price=self.current_price,
                                stop_loss={'stop_price': stop_price, 'limit_price': limit_price}
                                )
            elif side == 'take_profit':
                buy_order = self.api.submit_order(
                                symbol=self.symbol,
                                notional=self.affordable_shares,
                                side='buy',
                                type='limit',
                                time_in_force='gtc',
                                order_class='oto',
                                limit_price=self.current_price,
                                take_profit={'limit_price': stop_price}
                                )
            logging.info(f'Placed order for {self.affordable_shares} shares at ${self.current_price:.2}...')
            logging.info('Waiting for order to fill...')
            while len(self.api.list_orders(status='open')) > 0:
                time.sleep(3)
            logging.info('Order filled!')
            return buy_order.id
        except:
            logging.info(f'ERROR: Attempted order for {self.affordable_shares} shares at ${self.current_price:.2}')
            return None


if __name__ == '__main__':

    # Test initializing the class:
    symbol = 'ETHUSD'
    timeframe = TimeFrame.Hour
    bot = AlpacaBot(symbol, timeframe)
    print('Current price:', bot.current_price)
    print('Cash on hand:', bot.cash_on_hand)
    print('Crypto on hand:', bot.crypto_on_hand)
    print('Open position:', bot.open_position)
    print('Affordable shares:', bot.affordable_shares)

    # Test orders:
    # buy_orderID = bot.limit_buy_order()
    # oto_orderID = bot.oto_buy_order(stop_price=bot.current_price*0.98)