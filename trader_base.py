# Trader Base

# Import Libraries
import pandas as pd
import numpy as np
import math
from math import floor
import pickle
import time
from datetime import datetime
from datetime import timedelta 
from datetime import timezone
from pybit.unified_trading import HTTP 
from pybit.unified_trading import WebSocket
from configparser import ConfigParser

from matplotlib import pyplot as plt
from IPython import display

from data_download import get_bybit_data

import sys
import signal

class TraderBase(object):
    ''' Base class for trading an instrument
    
    Attributes
    ==========
    
    
    Methods
    =======
    '''
    
    def __init__(self, conf_file, exchange, symbol, interval, strategy=None, leverage=None, sl=None, tp=None, verbose=True):
        
        self.conf_file =conf_file
        self.exchange = exchange
        self.symbol = symbol
        self.interval = interval
        self.leverage = 1
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
            self.client = HTTP(testnet=True,
                               api_key=api_key,
                               api_secret=api_secret)
            # Websocket
            self.ws = WebSocket(testnet=True, channel_type='linear')
            print('Connected to API and Websocket...') 
        elif exchange == 'bybit':
            # API
            self.client = HTTP(testnet=False,
                               api_key=api_key,
                               api_secret=api_secret)
            # Websocket
            self.ws = WebSocket(testnet=False, channel_type='linear')
            print('Connected to API and Websocket...') 
        else:
            print("Exchange not currently supported!")
            
        # Get symbol properties    
        self.symbol_properties = self.get_symbol_properties()
            
        # Set the leverage
        if self.leverage is not None:
            try:
                self.client.set_leverage(symbol=self.symbol,
                                    buy_leverage=self.leverage,
                                    sell_leverage=self.leverage)
                print(f'leverage modified to {self.leverage}')
                
            except:
                print('Leverage not modified.')
                
    def get_symbol_properties(self):
        res = self.client.get_instruments_info(category='linear', symbol=self.symbol)
        result = res['result']['list'][0]
        
        tick_size = float(result['priceFilter']['tickSize'])
        price_prec = int(-math.log10(tick_size))
        
        qty_step = float(result['lotSizeFilter']['qtyStep'])
        qty_prec = int(-math.log10(qty_step))
        
        return {'Tick Size':tick_size, 'Price Precision':price_prec, 
                'Qty Step':qty_step, 'Quantity Precision':qty_prec}
            
    def get_data(self, min_length):
        '''Retrieves and prepares the latest data
        

        Returns
        =======
        DataFrame

        '''
        now =  datetime.utcnow()        # get the current time (UTC)
        start_time = now - timedelta(minutes=self.interval * min_length)
        start_time = start_time.strftime('%Y-%m-%d %H:%M:%S')
        end_time = now.strftime('%Y-%m-%d %H:%M:%S') # bar migh not be complete!!!
        
        print(f'Time now is {now}')
        print(f'Minimum length is {min_length}')
        print(f'Downloading data from {start_time} ...')
        
        # historical data
        hist_data = get_bybit_data(product_type='linear',
                            symbol = self.symbol,
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
        res = self.client.get_tickers(category='linear', symbol = self.symbol)
        time = pd.to_datetime(res['time'], unit='ms')
        ask_price = float(res['result']['list'][0]['ask1Price'])
        bid_price = float(res['result']['list'][0]['bid1Price'])
        
        # return tuple/ dataframe/ dictionary
        return {'time':time, 'ask_price':ask_price, 'bid_price':bid_price}
    
    def get_available_balance(self, coin='USDT', accountType='UNIFIED'):
        res = self.client.get_wallet_balance(accountType=accountType, coin=coin)
        balance = float(res['result']['list'][0]['coin'][0]['walletBalance']) 
        return balance
        
    def print_balance(self):
        '''Print out current available balance info.
        
        Returns
        -------
        None.

        '''
        res = self.client.get_wallet_balance(coin="USDT")['result']
        avail_bal = res['USDT']['available_balance']  
        #print(f'{date} | current balance {avail_bal:.2f}')
        
    def print_net_wealth(self):
        '''Print out current net wealth
        

        Returns
        -------
        None.

        '''
        res = self.client.get_wallet_balance(coin="USDT")['result']
        net_wealth = res['USDT']['equity']
        #print(f'{date} | current net wealth {net_wealth:.2f}')
    
    def place_buy_order(self, units=None, amount=None, sl=None, tp=None):
        # Get quote
        quote = self.get_quote()
        time = quote['time']
        ask_price = quote['ask_price']
        
        # Get available balance (TODO: only if units is not specified.)
        amount = self.get_available_balance() 
        
        # Symbol Properties
        tick_size = self.symbol_properties['Tick Size']
        price_prec = self.symbol_properties['Price Precision']
        qty_step = self.symbol_properties['Qty Step']
        qty_prec = self.symbol_properties['Quantity Precision']
        
        # Set stop prices
        if tp is not None:
            take_profit = round(ask_price * (1 + tp) / tick_size) * tick_size
            take_profit = f'{take_profit:.{price_prec}f}' # convert take profit to a string
        else:
            take_profit = None
        if sl is not None:
            stop_loss = round(ask_price * (1 - sl) / tick_size) * tick_size
            stop_loss = f'{stop_loss:.{price_prec}f}' # convert stop loss to a string
        else: stop_loss = None
        
        # Calculate qty (using fees) (if units is none)
        if units is None:
            units = (amount * self.leverage) / (ask_price * (0.0012 * self.leverage + 0.9994))
            units = floor(units / qty_step) * qty_step
            units = f'{units:.{qty_prec}f}'
        
        # Place order
        order = self.client.place_order(
                    category='linear',
                    symbol = self.symbol,
                    side = "Buy",
                    orderType = "Market",
                    qty= units,                              # units = qty
                    #price=8083,
                    take_profit = take_profit ,
                    stop_loss = stop_loss,
                    timeInForce = "PostOnly",                                  # WHAT IS POST ONLY
                    orderLinkId = f"{self.symbol} - {datetime.now()}",
                    isLeverage = 0,
                    orderFilter = "Order"       
                )
        
        # Update order history
        self.order_history.append(order['result']) ### TODO: Check out response.
        
        # Print
        if self.verbose:
            print(f'{time:%Y-%m-%d %H:%M:%S} | buying {units} units at {ask_price:.2f}')
            #self.print_balance()   ## *** Still need to fix these functions ***
            #self.print_net_wealth()  ## *** Still need to fix these functions ***
        
        
    def place_sell_order(self, units=None, amount=None, sl=None, tp=None):
        # Get quote
        quote = self.get_quote()
        time = quote['time']
        bid_price = quote['bid_price']
        
        # Get available balance (TODO: only if units is not specified.)
        amount = self.get_available_balance()
        
        # Symbol Properties
        tick_size = self.symbol_properties['Tick Size']
        price_prec = self.symbol_properties['Price Precision']
        qty_step = self.symbol_properties['Qty Step']
        qty_prec = self.symbol_properties['Quantity Precision']
        
         # Set stop prices
        if tp is not None:
            take_profit = round(bid_price * (1 - tp) / tick_size) * tick_size
            take_profit = f'{take_profit:.{price_prec}f}'
        else:
            take_profit = None
        if sl is not None:
            stop_loss = round(bid_price * (1 + sl) / tick_size) * tick_size
            stop_loss = f'{stop_loss:.{price_prec}f}'
        else: stop_loss = None

        # caculate qty (using fees) (if units is none)
        if units is None:
            units = (amount * self.leverage)/ (bid_price * (0.0012 * self.leverage + 1.0006))
            units = floor(units / qty_step) * qty_step
            units = f'{units:.{qty_prec}f}'
        
        # place order
        order = self.client.place_order(
                    category='linear',
                    symbol = self.symbol,
                    side = "Sell",
                    orderType = "Market",
                    qty= units,                              # units = qty
                    #price=8083,
                    take_profit = take_profit,
                    stop_loss = stop_loss,
                    timeInForce = "PostOnly",                                  # WHAT IS POST ONLY
                    orderLinkId = f"{self.symbol} - {datetime.now()}",
                    isLeverage = 0,
                    orderFilter = "Order"       
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
                               'turnover':'Turnover',
                               'confirm':'Confirm'
                              }, inplace=True)
        
        # Convert time column to datetime
        df['Time'] = pd.to_datetime(df['Time'], unit='ms')
        
        # Filter for confirm bar only
        df = df[df['Confirm']==True]
        
        # Set Time column to index
        df.set_index('Time', inplace=True)
        
        # Select columns:
        cols = ['Open','High','Low', 'Close', 'Volume']
        df = df[cols]
        
        # convert to numeric
        df[cols] = df[cols].apply(pd.to_numeric)
        
        return df
    
    def print_kline(self,msg):
        df = self.msg_to_df(msg)
        print(df)
    
    
if __name__ == '__main__':
    trader = TraderBase(conf_file='algo_trading.cfg',
                    exchange='bybit',
                    symbol='SOLUSDT',
                    interval=1)
    
    # tb.get_data(100)
    trader.get_quote()

