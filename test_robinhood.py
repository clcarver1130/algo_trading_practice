### Main libraries
import pandas as pd
import schedule
import time
import datetime
from logger import logging
import sqlite3
from talib import MACD, ADX, MINUS_DI, PLUS_DI
from coinapi_rest_v1 import CoinAPIv1
from robin_helperfunctions import round_to_hour
from robinhood_practice import *

### Robinhood specific libraries and login
import robin_stocks as r
from logins import robin_email, robin_password


### CoinAPI login
from logins import CoinAPI_KEY
coin_api = CoinAPIv1(CoinAPI_KEY)
