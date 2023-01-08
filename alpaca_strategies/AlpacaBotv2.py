# Standard imports:
from logger import logging
import time
from datetime import datetime

# Third party imports:
from alpaca.trading.client import TradingClient
from alpaca.data import CryptoHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, StopOrderRequest, StopLimitOrderRequest, TrailingStopOrderRequest, StopLossRequest, TakeProfitRequest, GetOrdersRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderStatus, QueryOrderStatus



# Local imports:
from alpaca_strategies.alpaca_keys import alpaca_live_keyid, alpaca_live_secret
from alpaca_strategies.alpaca_keys import alpaca_paper_keyid, alpaca_paper_secret

# Constants:
LIVE = False
SYM = 'ETH/USD'

class AlpacaBot:
    def __init__(self, symbol, timeframe):
        # Variables:
        self.data_symbol = symbol
        self.trade_symbol = ''.join(symbol.split('/'))
        self.timeframe = timeframe

        # Price information
        self.crypto_data_client = CryptoHistoricalDataClient()
        self.hist_data = self.get_historical_data()
        self.current_price = self.hist_data.iloc[-1]['close']

        # Account information:
        self.trading_client = self.connect_account()
        self.cash_on_hand, self.crypto_on_hand, self.open_position = self.calculate_balances()
        self.affordable_shares = round(self.cash_on_hand / self.current_price, 3)

    @staticmethod
    def connect_account():
        if LIVE:
            return TradingClient(alpaca_live_keyid, alpaca_live_secret, paper=False)
        else:
            return TradingClient(alpaca_paper_keyid, alpaca_paper_secret, paper=True)

    def get_historical_data(self, start=None, end=None):

        request_params = CryptoBarsRequest(
            symbol_or_symbols=[self.data_symbol],
            timeframe=self.timeframe,
            start=datetime.strptime(start, '%Y-%m-%d'),
            end=end)

        return self.crypto_data_client.get_crypto_bars(request_params).df

    def check_open_positions(self):
        return True if self.trading_client.get_all_positions() else False

    def get_crypto_onhand(self):
        positions = self.trading_client.get_all_positions()
        if not positions:
            return 0
        else:
            return positions[0].qty

    def get_cash_onhand(self):
        return self.trading_client.get_account().cash

    def calculate_balances(self):
        cash_on_hand = float(self.get_cash_onhand())
        crypto_on_hand = float(self.get_crypto_onhand())
        open_position = self.check_open_positions()
        return cash_on_hand, crypto_on_hand, open_position

    def limit_buy_order(self, seconds_toCancel=30):

        try:
            limit_order_data = LimitOrderRequest(
                symbol=self.trade_symbol,
                limit_price=self.current_price,
                notional=self.affordable_shares,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.GTC
            )

            # Limit order
            limit_order = self.trading_client.submit_order(order_data=limit_order_data)
            logging.info(f'Placed order for {self.affordable_shares} shares at ${self.current_price:.2}...')
            logging.info('Waiting for order to fill...')

            # orders that satisfy params
            order_params = GetOrdersRequest(status=QueryOrderStatus.OPEN, side=OrderSide.BUY)
            while len(self.trading_client.get_orders(filter=order_params)) > 0:
                time.sleep(3)
            logging.info('Order filled!')
            return limit_order.id
        except:
            logging.info(f'ERROR: Attempted order for {self.affordable_shares} shares at ${self.current_price:.2}')
            return None

    def close_all_positions(self):
        self.trading_client.close_all_positions(cancel_orders=True)

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
    symbol = 'ETH/USD'
    timeframe = TimeFrame.Hour
    bot = AlpacaBot(symbol, timeframe)
    print('Current price:', bot.current_price)
    print('Cash on hand:', bot.cash_on_hand)
    print('Crypto on hand:', bot.crypto_on_hand)
    print('Open position:', bot.open_position)
    print('Affordable shares:', bot.affordable_shares)

    # Test orders:
    # buy_orderID = bot.limit_buy_order()
    bot.close_all_positions()
    # oto_orderID = bot.oto_buy_order(stop_price=bot.current_price*0.98)