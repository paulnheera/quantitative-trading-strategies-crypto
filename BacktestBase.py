# -*- coding: utf-8 -*-
"""
Created on Thu Oct 20 22:03:23 2022

@author: PAUL208
"""

#%% Libraries
import numpy as np
import pandas as pd
from pylab import mpl, plt
plt.style.use('seaborn')
mpl.rcParams['font.family'] = 'serif'


#%% Backtesting Base Class
class BacktestBase(object):
    '''Base class for event-based backtesting of trading strategies.
    
    Attributes
    -----------
    
    Methods
    -------
    
    '''
    
    def __init__(self, exchange, symbol, interval, start, end, amount, 
                 ftc=0.0, ptc=0.0, verbose=True):
        
        self.exchange = exchange
        self.symbol = symbol
        self.interval = interval      ## EDIT
        self.start = start
        self.end = end
        self.initial_amount = amount
        self.amount = amount
        self.ftc = ftc
        self.ptc = ptc
        self.units = 0
        self.position = 0
        self.trades = 0
        self.verbose = verbose
        self.get_data()
        
    def get_data(self):
        '''Retrieves and prepares the data
        '''

        h5 = pd.HDFStore('data/bybit/' + self.symbol + '_' + str(self.interval) + '.h5', 'r')
        raw = h5['data']
        h5.close()
        
        self.data = raw ## IMPROVE: SPLIT BETWEEN ALL DATA & AVAILABLE DATA AT CURRENT BAR
        
    def plot_data(self, cols=None):
        '''Plots the closing prices for symbol.
        '''
        
        if cols is None:
            cols = ['Close']
        
        self.data[cols].plot(figsize=(10,6), title=self.symbol)
        
    def get_time_price(self, bar):
        '''Return data and price for bar
        '''
        
        #date = str(self.data.index[bar])[:10] 
        date = str(self.data.index[bar])
        price = self.data.Close.iloc[bar]
        
        return date, price
    
    def print_balance(self,bar):
        '''Print out current cash balance info.
        '''
        
        date, price = self.get_time_price(bar)
        print(f'{date} | current balance {self.amount:.2f}')
        
    def print_net_wealth(self,bar):
        '''Print out current cash balance info.
        '''
        
        date, price = self.get_time_price(bar)
        net_wealth = self.units * price + self.amount ## NET_WEALTH AKA EQUITY
        print(f'{date} | current net wealth {net_wealth:.2f}')
        
    def place_buy_order(self, bar, units=None, amount=None):
        '''Place a buy order
        '''
        
        date, price = self.get_time_price(bar)
        if units is None:
            #units = int(amount/ price) # Doesn't have to be int of crypto since unit sizes are divisible.
            units = amount/price ## IMPROVE: restrict for the symbols price precision.
        
        self.amount -= (units * price) * (1 + self.ptc) + self.ftc
        self.units += units
        self.trades += 1
        
        if self.verbose:
            print(f'{date} | buying {units} units a {price:.2f}')
            self.print_balance(bar)
            self.print_net_wealth(bar)
            
    def place_sell_order(self, bar, units=None, amount=None):
        '''Place a sell order
        '''
        
        date, price = self.get_time_price(bar)
        if units is None:
            #units = int(amount/ price) # Doesn't have to be int of crypto since unit sizes are divisible.
            units = amount/price ## IMPROVE: restrict for the symbols price precision.
        
        self.amount += (units * price) * (1 - self.ptc) - self.ftc
        self.units -= units
        self.trades += 1
        
        if self.verbose:
            print(f'{date} | selling {units} units at {price:.2f}')
            self.print_balance(bar)
            self.print_net_wealth(bar)
            
    def close_out(self, bar):
        ''' Closing out a long or short position
        '''
        
        date, price = self.get_time_price(bar)
        self.amount += self.units * price
        self.units = 0
        self.trades +=1
        
        if self.verbose:
            print(f'{date} | inventory {self.units} units at {price:.2f}')
            print('=' * 55)
        
        print('Final balance [$] {:2f}'.format(self.amount))
        
        perf = ((self.amount - self.initial_amount) / 
                self.initial_amount * 100)
        print('Net Performance [%] {:.2f}'.format(perf))
        print('Trades Executed [#] {:.2f}'.format(self.trades))
        print('=' * 55)
        
#%% Test
        
if __name__ == '__main__':
    
    bt = BacktestBase(exchange='bybit',
                      symbol='ETHUSDT',
                      interval=15,
                      start='2022-09-30 11:00',
                      end='2022-10-31 11:00',
                      amount=100)