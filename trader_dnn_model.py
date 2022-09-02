# -*- coding: utf-8 -*-
"""
Created on Fri Aug 26 20:01:57 2022

@author: PAUL208
"""


#%% Import Libraries
import pandas as pd
import numpy as np
from math import floor
import pickle
import time
from datetime import datetime
from datetime import timedelta 
from datetime import timezone
from pybit import usdt_perpetual
from configparser import ConfigParser

from matplotlib import pyplot as plt
from IPython import display

from sklearn.neural_network import MLPClassifier
import tensorflow as tf
from keras.models import Sequential         # Model type
from keras.layers import Dense              # Layers  
from keras.optimizers import Adam, RMSprop  # Optimizers

from  bybit_download_data import get_bybit_data

#%% Config

config = ConfigParser()
config.read('pyalgo.cfg')

api_key = config.get('testnet-bybit', 'api_key')
api_secret = config.get('testnet-bybit', 'api_secret')


#%% Connect to Websocket

# API
client = usdt_perpetual.HTTP(
    endpoint="https://api-testnet.bybit.com",
    api_key=api_key,
    api_secret=api_secret,
    recv_window = 5000
)

# Websocket
ws_linear = usdt_perpetual.WebSocket(
    test=True,
    ping_interval=30,  # the default is 30
    ping_timeout=10,  # the default is 10
    domain="bybit"  # the default is "bybit"
)

#%% Import algorithm

algorithm = pickle.load(open('algorithm.pkl', 'rb'))

model = algorithm['model']
features = algorithm['features']

#%% User Defined functions

# Close position function
def close_position(symbol):
    
    position = client.my_position(symbol=symbol)['result'][0]
    curr_side = position['side']
    size = position['size']
    
    if curr_side != 'None':
        side = str(np.where(curr_side =='Buy', 'Sell', 'Buy'))
        order = client.place_active_order(
                    symbol=symbol,
                    side=side,
                    order_type="Market",
                    qty=size,                              # units = qty
                    #price=8083,
                    time_in_force="GoodTillCancel",
                    reduce_only=False,
                    close_on_trigger=False,
                    position_idx=0            
                )
    
        return print('Order closed...')

# Message to dataframe function
def msg_to_df(msg):
    
        raw = msg['data']
        df = pd.DataFrame(raw)
        
        # rename colums
        df.rename(columns = {'start':'Time',
                               'volume':'Volume',
                               'open':'Open',
                               'high':'High',
                               'low':'Low',
                               'close':'Close',
                               'turnover':'Turnover'
                              }, inplace=True)
        
        # Convert time column to datetime
        df['Time'] = pd.to_datetime(df['Time'], unit='s')
        
        # Set Time column to index
        df.set_index('Time', inplace=True)
        
        # Select columns:
        cols = ['Open','High','Low', 'Close', 'Volume']
        df = df[cols]
        
        # convert to numeric
        df[cols] = df[cols].apply(pd.to_numeric)
        
        return df
   
# Prepare Features function
def prepare_features(hist_data):
    
    data = hist_data.copy()
    
    data['return'] = data['Close']/data['Close'].shift(1) - 1
    data['direction'] = np.where(data['return'] > 0, 1, 0)
    
    # Create the lagged data
    lags = 5
    features = []
    for lag in range(1, lags + 1):
        feature = f'lag_{lag}'
        data[feature] = data['return'].shift(lag)
        features.append(feature)
    
    # Create additional features
    data['momentum'] = data['return'].rolling(5).mean().shift(1)
    data['volatility'] = data['return'].rolling(20).std().shift(1)
    data['distance'] = (data['Close'] - data['Close'].rolling(50).mean().shift(1)) # consider changing to percentage distance
    
    features.extend(['momentum', 'volatility', 'distance'])
    
    cols = features + ['direction']
    
    data = data[cols].copy()
    
    data.dropna(inplace=True)
        
    return {'data':data, 'features':features}

# Callback function
def handle_message(msg):
    
    global model
    global hist_data
    global predictions
    global last_time
    global mu, std
    global position
    global symbol
    global leverage
    global units
    global order
    
    
    # convert to dataframe
    df = msg_to_df(msg)
    
    # Update historical data
    hist_data = pd.concat([hist_data, df])
    hist_data = hist_data[~hist_data.index.duplicated(keep='last')]
    # hist_data = hist_data.resample(timedelta(minutes=interval),
    #                               label='right').last().ffill()
    
    
    print(pd.to_datetime(msg['timestamp_e6'],unit='us'))
    print(df)
    
    
    if last_time != hist_data.index[-1]:
        
        # Update last time
        last_time = hist_data.index[-1]
        
        print("-" * 60)
        print("CURRENT BAR: {}".format(last_time))
        print("=" * 60)
    
        # Prepare data
        data = prepare_features(hist_data)['data']
        print("MOST RECENT DATA")
        print(data)
        print("=" * 60)
        
        # Data point
        data_point = data.tail(1)
        
        # Standardize data
        data_point_ = (data_point - mu)/std
        print("features:")
        print(data_point_)
        print("=" * 60)
        
        # Predict (signal)
        pred = np.where(model.predict(data_point_[features]) > 0.5, 1, -1)[0]
        print("signal: {}".format(pred))
        
        # Get current position
        position = client.my_position(symbol=symbol)['result'][0]['side']
        
        if position in ['None', 'Sell'] and pred == 1:                          # LOOK TO OPEN LONG POSITION
            print("{} : GOING LONG ...".format(last_time))
            
            # close short position                                              # **** EXEPTION ****
            order_close = close_position(symbol)
            
            # get account balance
            res = client.get_wallet_balance(coin="USDT")['result']
            amount = res['USDT']['available_balance']
             
            # calculate order_size
            price = float(client.latest_information_for_symbol(symbol=symbol)['result'][0]['ask_price'])
            units = (amount * leverage)/ (price * (0.0012 * leverage + 0.9994))
            units = floor(units*100)/100
            
            # go long
            order = client.place_active_order(
                symbol=symbol,
                side="Buy",
                order_type="Market",
                qty=units,                              # units = qty
                #price=8083,
                time_in_force="GoodTillCancel",
                reduce_only=False,
                close_on_trigger=False,
                position_idx=0            
            )
            
            # print order success
            
            # position = 1 # don't need this we are check position directly
        elif position in ['None', 'Buy'] and pred == -1:                        # LOOK TO OPEN SHORT POSITION
            print("{} : GOING SHORT ...".format(last_time))
            
            # close long position
            close_position(symbol)
            
            # get account balance
            res = client.get_wallet_balance(coin="USDT")['result']
            amount = res['USDT']['available_balance'] 
            
            # calculate order_size
            price = float(client.latest_information_for_symbol(symbol=symbol)['result'][0]['bid_price'])
            units = (amount * leverage)/ (price * (0.0012 * leverage + 1.0006))
            units = floor(units*100)/100
            
            # go short
            order = client.place_active_order(
                symbol=symbol,
                side="Sell",
                order_type="Market",
                qty=units,                              # units = qty
                #price=8083,
                time_in_force="GoodTillCancel",
                reduce_only=False,
                close_on_trigger=False,
                position_idx=0            
            )

            # print order success            
            
            #position = -1
        else:
            print("*** NO TRADE PLACED ***")             
        
        # Store predictions
        p = pd.DataFrame({'Prediction':pred}, index = data_point_.index)
        predictions =pd.concat([predictions, p])
    
    print('=' * 60)
    print("\n")


#%% Initialize variables and data

symbol = 'ETHUSDT'
leverage = 1 
## IMPROVE ACTUALLY SET THE LEVERAGE
interval = 15  

model = algorithm['model']
features = algorithm['features']
mu = algorithm['mu']
std = algorithm['std']

units = 0
position = 'None'

min_length = 100
now =  datetime.utcnow()        # get the current time (UTC)
start_time = now - timedelta(minutes=interval*min_length)
start_time = start_time.strftime('%Y-%m-%d %H:%M')

# historical data
hist_data = get_bybit_data(symbol=symbol,
                    interval=interval,
                    start_time=start_time)

last_time = hist_data.index[-1]

predictions = pd.DataFrame()

#%% Start Trading

# Start Streaming
ws_linear.kline_stream(
    handle_message, symbol, str(interval)
)

# Wait
time.sleep(3*60*60*24*7) # Run for 7 days

# Stop Streaming
if False:
    ws_linear.active_connections[0].exit()
    ws_linear.active_connections.clear()
    
    print('Data streaming and trading stopped!')
    
#%%