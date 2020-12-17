import pandas as pd
import schedule
import time
from logger import logging
# from talib import MACD
from tradingbot import Kraken_Trading_Bot

FIAT = 'ZUSD'
CRYPTO = 'XETH'
INTERVAL = 240 # 4 hours
STOP_LOSS_PERCENT = 0.02

def kraken_macdStrategy(hist_data, position_flag):

    # MACD calculation:
    FAST, SLOW, SIGNAL = 12, 26, 9
    
    exp1 = hist_data['close'].ewm(span=FAST, adjust=False).mean()
    exp2 = hist_data['close'].ewm(span=SLOW, adjust=False).mean()
    macd = exp1-exp2
    signal = macd.ewm(span=SIGNAL, adjust=False).mean()
    
    macd_current, signal_current = macd[-1], signal[-1]
    logging.info(f'MACD is: {macd_current} | Signal is: {signal_current}')

    # Action:
    if position_flag:
        if macd_current <= signal_current:
            return 'sell'
        else:
            return 'pass'
    elif macd_current > signal_current:
            return 'buy'
    else:
        return 'pass'

def main():
    bot = Kraken_Trading_Bot(kraken_key_filepath='kraken_keys.py',
                             currency=FIAT,
                             crypto=CRYPTO,
                             interval=INTERVAL,
                             strategy=kraken_macdStrategy)

    action = bot.strategy(bot.hist_data, bot.open_position)
    if action == 'buy':
        placed_order, completed_order = bot.limit_buy_order()
        if completed_order['status'] == 'expired':
            logging.info('Buy order timed out. Re-calculating metrics and retrying trade.')
            main()
        else:
            logging.info('Buy order complete. Placing stop loss order.')
            bot.stop_loss_order(completed_order, STOP_LOSS_PERCENT)
    elif action == 'sell':
        placed_order, completed_order = bot.exit_logic()
        if completed_order['status'] == 'expired':
            logging.info('Sell order timed out. Re-calculating metrics and retrying trade.')
            main()
        else:
            logging.info('Sell order complete.')
    else:
        logging.info('Holding position')
        pass
    logging.info('Check complete.')

if __name__ == '__main__':
    logging.info('Starting script...')
    schedule.every(4).hours.do(main)
    schedule.run_all()
    while True:
        schedule.run_pending()
        time.sleep(1)
