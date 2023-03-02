# -*- coding: utf-8 -*-
"""
Created on Wed Sep 21 19:18:59 2022

@author: PAUL208
"""

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

from  bybit_download_data import get_bybit_data

import sys
import signal

#%% TraderBase Class
class TraderBase(object):
    ''' Base class for trading strategies
    
    Attributes
    ==========
    
    
    Methods
    =======
    '''
    
    def __init__(self, conf_file, exchange, symbol, interval, leverage=1, sl=None, tp=None, verbose=True):
        
        self.conf_file =conf_file
        self.exchange = exchange
        self.symbol = symbol
        self.interval = interval
        self.leverage = leverage
        self.sl = sl
        self.tp = tp
        #self.initial_amount = amount
        #self.amount = amount
        self.units = 0
        self.position = 0
        self.no_trades = 0
        self.order_history = []
        self.trades = pd.DataFrame()
        self.last_time = None
        self.verbose = verbose
        
        # Connect to API and Websocket
        config = ConfigParser()
        config.read(conf_file)
        api_key = config.get(exchange, 'api_key')
        api_secret = config.get(exchange, 'api_secret')

        if exchange == 'testnet-bybit':
            # API
            self.client = usdt_perpetual.HTTP(
                endpoint="https://api-testnet.bybit.com",
                api_key=api_key,
                api_secret=api_secret,
                recv_window = 5000
            )
            # Websocket
            self.ws = usdt_perpetual.WebSocket(
                test=True,
                ping_interval=30,  # the default is 30
                ping_timeout=10,  # the default is 10
                domain="bybit"  # the default is "bybit"
            )
            print('Connected to API and Websocket...') 
            
        elif exchange == 'bybit':
            # API
            self.client = usdt_perpetual.HTTP(
                endpoint="https://api.bybit.com",
                api_key=api_key,
                api_secret=api_secret,
                recv_window = 5000
            )
            # Websocket
            self.ws = usdt_perpetual.WebSocket(
                test=False,
                ping_interval=30,  # the default is 30
                ping_timeout=10,  # the default is 10
                domain="bybit"  # the default is "bybit"
            )
            print('Connected to API and Websocket...') 
            
        else:
            
            print("Exchange not currently supported!")
            
        # Set the leverage
        try:
            self.client.set_leverage(symbol=self.symbol,
                                buy_leverage=self.leverage,
                                sell_leverage=self.leverage)
            
            print(f'leverage modified to {self.leverage}')
            
        except:
            print('Leverage not modified.')
            
        
        
    
    def get_data(self, min_length):
        '''Retrieves and prepares the latest data
        

        Returns
        =======
        DataFrame

        '''
        now =  datetime.utcnow()        # get the current time (UTC)
        start_time = now - timedelta(minutes=self.interval * min_length)
        start_time = start_time.strftime('%Y-%m-%d %H:%M')
        end_time = now.strftime('%Y-%m-%d %H:%M')
        
        print(f'Time now is {now}')
        print(f'Minimum length is {min_length}')
        print(f'Downloading data from {start_time} ...')
        
        # historical data
        hist_data = get_bybit_data(symbol = self.symbol,
                            interval= self.interval,
                            start_time=start_time,
                            end_time=end_time) # ADD TIME!
        
        print('Download done!')
        print("=" * 60)
        self.data = hist_data
        
    def get_quote(self):
        ''' Return current market qoute
        
        Returns
        -------
        Time, Bid, Ask

        '''
        quote = self.client.latest_information_for_symbol(symbol = self.symbol)
        time = pd.to_datetime(quote['time_now'], unit='s')
        ask_price = float(quote['result'][0]['ask_price'])
        bid_price = float(quote['result'][0]['bid_price'])
        
        # return tuple/ dataframe/ dictionary
        return {'time':time, 'ask_price':ask_price, 'bid_price':bid_price}
    
    def get_available_balance(self):
        res = self.client.get_wallet_balance(coin="USDT")['result']
        avail_bal = res['USDT']['available_balance'] 
        
        return avail_bal
        
    def print_balance(self):
        '''Print out current available balance info.
        
        Returns
        -------
        None.

        '''
        
        res = self.client.get_wallet_balance(coin="USDT")['result']
        avail_bal = res['USDT']['available_balance']  
        
        print(f'{date} | current balance {avail_bal:.2f}')
        
    def print_net_wealth(self):
        '''Print out current net wealth
        

        Returns
        -------
        None.

        '''
        res = self.client.get_wallet_balance(coin="USDT")['result']
        net_wealth = res['USDT']['equity']
        
        print(f'{date} | current net wealth {net_wealth:.2f}')
    
    def place_buy_order(self, units=None, amount=None, sl=None, tp=None):
        # get quote
        quote = self.get_quote()
        time = quote['time']
        ask_price = quote['ask_price']
        
        # get available balance
        res = self.client.get_wallet_balance(coin="USDT")['result']
        amount = res['USDT']['available_balance']  
        
        # set stop prices
        if tp is not None:
            take_profit = round(ask_price * (1 + tp), 3)
        else:
            take_profit = None
        if sl is not None:
            stop_loss = round(ask_price * (1 - sl), 3)
        else: stop_loss = None
        
        # caculate qty (using fees) (if units is none)
        if units is None:
            units = (amount * self.leverage)/ (ask_price * (0.0012 * self.leverage + 0.9994))
            units = floor(units*100)/100
        
        # place order
        order = self.client.place_active_order(
            symbol = self.symbol,
            side = "Buy",
            order_type = "Market",
            qty= units,                              # units = qty
            #price=8083,
            take_profit = take_profit,
            stop_loss = stop_loss,
            time_in_force = "GoodTillCancel",
            reduce_only = False,
            close_on_trigger = False,
            position_idx = 0            
        )
        
        # Update order history
        self.order_history.append(order['result'])
        
        # print
        if self.verbose:
            print(f'{time:%Y-%m-%d %H:%M:%S} | buying {units} units at {ask_price:.2f}')
            #self.print_balance()   ## *** Still need to fix these functions ***
            #self.print_net_wealth()  ## *** Still need to fix these functions ***
        
        
    def place_sell_order(self, units=None, amount=None, sl=None, tp=None):
        # get quote
        quote = self.get_quote()
        time = quote['time']
        bid_price = quote['bid_price']
        
        # get available balance
        # if amount == all
        res = self.client.get_wallet_balance(coin="USDT")['result']
        amount = res['USDT']['available_balance'] 
        
        # set stop prices
        if tp is not None:
            take_profit = round(bid_price * (1 - tp), 3)
        else:
            take_profit = None
        if sl is not None:
            stop_loss = round(bid_price * (1 + sl), 3)
        else:
            stop_loss = None

        # caculate qty (using fees) (if units is none)
        if units is None:
            units = (amount * self.leverage)/ (bid_price * (0.0012 * self.leverage + 1.0006))
            units = floor(units*100)/100
        
        # place order
        order = self.client.place_active_order(
            symbol = self.symbol,
            side = "Sell",
            order_type = "Market",
            qty= units,                              # units = qty
            #price=8083,
            take_profit = take_profit,
            stop_loss = stop_loss,
            time_in_force = "GoodTillCancel",
            reduce_only = False,
            close_on_trigger = False,
            position_idx = 0            
        )
        
        # Update order history
        self.order_history.append(order['result'])
        
        # print
        if self.verbose:
            print(f'{time:%Y-%m-%d %H:%M:S} | selling {units} units at {bid_price:.2f}')
            #self.print_balance()
            #self.print_net_wealth()
        
    def close_out(self):
        '''Close out all strategy positions
        

        Returns
        -------
        None.

        '''
        
    def close_position(self, position=None):
        
        if position is None:
            position = self.client.my_position(symbol = self.symbol)['result'][0]
            
        curr_side = position['side']
        size = position['size']
        
        if curr_side != 'None':
            side = str(np.where(position['side'] =='Buy', 'Sell', 'Buy'))
            order = self.client.place_active_order(
                        symbol=self.symbol,
                        side=side,
                        order_type="Market",
                        qty=size,                              # units = qty
                        #price=8083,
                        time_in_force="GoodTillCancel",
                        reduce_only=False,
                        close_on_trigger=False,
                        position_idx=0            
                    )
        
            print('Order closed...')
    
    def msg_to_df(self, msg):
    
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
    

        
#%% TraderLongShort Class  
class TraderLongShort(TraderBase):
    
    def go_long(self, units=None, amount=None, sl=None, tp=None):
        
        # Get current position
        position = self.client.my_position(symbol = self.symbol)['result'][0]
        
        # Close short position
        if position['side'] == 'Sell':
            self.close_position(position)
        
        # Open long position
        if units:
            self.place_buy_order(units=units, sl=sl, tp=tp)
        elif amount:
            if amount == 'all':
                amount == self.get_available_balance()
            self.place_buy_order(amount=amount, sl=sl, tp=tp)
        
    
        
    def go_short(self, units=None, amount=None, sl=None, tp=None):
        
        # Get current position
        position = self.client.my_position(symbol = self.symbol)['result'][0]
        
        # Close long position
        if position['side'] == 'Buy':
            self.close_position(position)
        
        # Open short position
        if units:
            self.place_buy_order(units=units, sl=sl, tp=tp)
        elif amount:
            if amount == 'all':
                amount == self.get_available_balance()
            self.place_sell_order(amount=amount, sl=sl, tp=tp)
            
    def run_sma_strategy(self, SMA1, SMA2):
        
        msg = f'\n\nRunning SMA strategy | SMA1={SMA1} & SMA2={SMA2}'
        #msg += f'\nfixed costs {self.ftc} | '
        #msg += f'proportional costs {self.ptc}'
        print(msg)
        print("=" * 60)
        
        
        #self.position = 0 # initial neutral position
        #self.trades = 0 # no trades yet
        #self.amount = self.get_available_balance()
        self.get_data(min_length = SMA2+1)
        #self.data['SMA1'] = self.data['price'].rolling(SMA1).mean()
        #self.data['SMA2'] = self.data['price'].rolling(SMA2).mean()
        
        def handle_message(msg):
            
            # convert message to dataframe
            df = self.msg_to_df(msg)
            # print(pd.to_datetime(msg['timestamp_e6'],unit='us'))
            # print(df)
            # print("=" * 60)
            
            # add the new data
            self.data = pd.concat([self.data, df])
            self.data = self.data[~self.data.index.duplicated(keep='last')]
            
            data = self.data.copy()
            
            if self.last_time != data.index[-1]:
                # Update last time
                self.last_time = data.index[-1]
                
                print("CURRENT BAR: {}".format(self.last_time))
                print("-" * 60)
                
                # Calculate SMAs
                data['SMA1'] = data['Close'].rolling(SMA1).mean()
                data['SMA2'] = data['Close'].rolling(SMA2).mean()
                
                print(data.tail(5))
                print("-" * 60)
                
                # Get current position
                position = self.client.my_position(symbol = self.symbol)['result'][0]
                
                print(f"CURRENT POSITION: {position['side']}")
                
                # Trade
                if position['side'] in  ['None', 'Sell']:
                    # Check for Long signal
                    if (data['SMA1'].iloc[-2] > data['SMA2'].iloc[-2]
                        and data['SMA1'].iloc[-3] <= data['SMA2'].iloc[-3]
                        ):
                        print(f"SIGNAL: BUY")
                        self.go_long(amount='all', sl=self.sl, tp=self.tp) # long position
                    else:
                        print(f"SIGNAL: None")
                    
                
                if position['side'] in ['None', 'Buy']:
                    # Check for short signal
                    if (data['SMA1'].iloc[-2] < data['SMA2'].iloc[-2]
                        and data['SMA1'].iloc[-3] >= data['SMA2'].iloc[-3]
                        ):
                        print(f"SIGNAL: SELL")
                        self.go_short(amount='all', sl=self.sl, tp=self.tp) # short position
                    else:
                        print(f"SIGNAL: None")
                
                print("=" * 60)
                      
        # stream data
        self.last_time = self.data.index[-1]
        self.ws.kline_stream(
                handle_message, self.symbol, str(self.interval)
            )

        # Stop Streaming
        if False:
            self.ws.active_connections[0].exit()
            self.ws.active_connections.clear()
            
            print('Data streaming and trading stopped!')      
            
#%% 
            
def exception_hook(exctype, value, traceback):
    
    # Print the exception type and value
    print(f'Error occured: {exctype} - {value}')
    
#%%
            
if __name__ == '__main__':
    
    # Set the exception hook
    sys.excepthook = exception_hook
    
    # Register exit signals to be handled by on_exit function
    
    tb = TraderLongShort(conf_file='pyalgo.cfg',
                    exchange='bybit',
                    symbol='ETHUSDT',
                    interval=15,
                    sl=0.02,
                    tp=0.06
                    )
    
    tb.run_sma_strategy(SMA1=50, SMA2=290)
    
    time.sleep(60*15) 
    
    if True:
        tb.ws.active_connections[0].exit()
        tb.ws.active_connections.clear()
        print("WebSocket connections closed!")
        