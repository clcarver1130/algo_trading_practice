# Main libraries
import pandas as pd
import schedule
import time
from logger import logging

# Robinhood specific libraries and login
import robin_stocks as r
from logins import robin_email, robin_password
login = r.login()
