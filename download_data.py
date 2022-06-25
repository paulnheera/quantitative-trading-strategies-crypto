# -*- coding: utf-8 -*-
"""
Created on Fri May 20 05:34:28 2022

@author: PAUL208
"""
# Load libraries
import config
from kucoin.client import Client
import pandas as pd
import numpy as np
from datetime import datetime
from datetime import timezone

# Connect to API
api_key = config.kucoin_api_key
api_secret = config.kucoin_api_secret
api_passphrase = config.kucoin_api_passphrase

client = Client(api_key, api_secret, api_passphrase)

# parameters:
symbol = 'BTC-USDT'
start_time = '2022-04-01 00:00'
end_time = '2022-04-30 23:59'

# convert time to timestamps
start_timestamp = datetime.strptime(start_time , '%Y-%m-%d %H:%M').replace(tzinfo=timezone.utc).timestamp()
end_timestamp = datetime.strptime(end_time , '%Y-%m-%d %H:%M').replace(tzinfo=timezone.utc).timestamp()
start_timestamp = format(int(start_timestamp))
end_timestamp = format(int(end_timestamp))

# check time objects:
print(pd.to_datetime(end_timestamp, unit='s'))

# get historical data
ohlc_data = client.get_kline_data(symbol=symbol, kline_type='1hour', start=start_timestamp)

# convert data to dataframe
ohlc_data = pd.DataFrame(ohlc_data, columns=['Time','Open','Close','High','Low','Amount','Volume'])

# convert time column
ohlc_data['Time'] = pd.to_datetime(ohlc_data['Time'], unit='s')

# sort by time
ohlc_data = ohlc_data.sort_values(by='Time', ascending=True)
ohlc_data = ohlc_data.reset_index(drop=True)

# export data
ohlc_data.to_csv('Kucoin_BTCUSDT_1H_data.csv', index=False)



