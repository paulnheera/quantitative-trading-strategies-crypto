# -*- coding: utf-8 -*-
"""
Created on Fri Aug 19 06:37:00 2022

@author: PAUL208
"""

import numpy as np
import pandas as pd
from pylab import mpl, plt
plt.style.use('seaborn')
mpl.rcParams['font.family'] = 'serif'

from  bybit_download_data import get_bybit_data

#%% User Defined Functions

# Bollinger bands
def bbands(data, window, threshold):
    
    std = data['Close'].rolling(window).std() # Rolling standard deviation
    sma = data['Close'].rolling(window).mean() # Simple moving average
    
    upper_bb = sma + std * threshold
    lower_bb = sma - std * threshold
    
    return [upper_bb, lower_bb]

#%% Backtesting Base Class
class BacktestBase(object):
    '''Base class for event-based backtesting of trading strategies.
    
    Attributes
    -----------
    
    Methods
    -------
    
    '''
    
    def __init__(self, symbol, interval, start, end, amount, 
                 ftc=0.0, ptc=0.0, verbose=True):
        
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
        raw = get_bybit_data(
                symbol = self.symbol,
                interval = self.interval,
                start_time = self.start,
                end_time = self.end
            )
        
        # Calculate return
        raw['return'] = raw['Close']/ raw['Close'].shift(1) - 1

        
        self.data = raw
        
    def plot_data(self, cols=None):
        
        '''Plots the closing prices for symbol.
        '''
        
        if cols is None:
            cols = ['Close']
        
        self.data['Close'].plot(figsize=(10,6), title=self.symbol)
        
    def get_date_price(self, bar):
        
        '''Return data and price for bar
        '''
        
        #date = str(self.data.index[bar])[:10] 
        date = str(self.data.index[bar])
        price = self.data.Close.iloc[bar]
        
        return date, price
    
    def print_balance(self,bar):
        '''Print out current cash balance info.
        '''
        
        date, price = self.get_date_price(bar)
        print(f'{date} | current balance {self.amount:.2f}')
        
    def print_net_wealth(self,bar):
        '''Print out current cash balance info.
        '''
        
        date, price = self.get_date_price(bar)
        net_wealth = self.units * price + self.amount
        print(f'{date} | current net wealth {net_wealth:.2f}')
        
    def place_buy_order(self, bar, units=None, amount=None):
        '''Place a buy order
        '''
        
        date, price = self.get_date_price(bar)
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
        
        date, price = self.get_date_price(bar)
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
        
        date, price = self.get_date_price(bar)
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
        
#%%
        
if __name__ == '__main__':
    bb = BacktestBase('BTCUSDT', 15, '2022-06-01 00:00', '2022-06-30 00:00', 10000)
    print(bb.data.info())
    print(bb.data.tail())
    bb.plot_data()
    
#%% Long-Only Backtesting Class

class BacktestLongOnly(BacktestBase):
    
    def run_sma_strategy(self, SMA1, SMA2):
        '''Backtesting an SMA-based strategy

        Parameters
        ----------
        SMA1 : TYPE
            DESCRIPTION.
        SMA2 : TYPE
            DESCRIPTION.

        Returns
        -------
        None.

        '''
        
        msg = f'\n\Running SMA strategy | SMA1={SMA1} & SMA2={SMA2}'
        msg += f'\nfixed costs {self.ftc}|'
        msg += f'proportional costs {self.ptc}'
        print(msg)
        print('=' * 55)
        
        self.position = 0 # initial netural position
        self.trades = 0 # no of trades yet
        self.amount = self.initial_amount # reset initial capital
        self.data['SMA1'] = self.data['Close'].rolling(SMA1).mean()
        self.data['SMA2'] = self.data['Close'].rolling(SMA2).mean()
        
        ## IMPROVE: Make sure SMA2 > SMA1
        
        for bar in range(SMA2, len(self.data)):
            
            if self.position == 0:
                if self.data['SMA1'].iloc[bar] > self.data['SMA2'].iloc[bar]:
                    self.place_buy_order(bar, amount=self.amount)
                    self.position = 1 # long position
            elif self.position == 1:
                if self.data['SMA1'].iloc[bar] < self.data['SMA2'].iloc[bar]:
                    self.place_sell_order(bar, units=self.units)
                    self.position = 0 # market neutral
        
        self.close_out(bar)
        
    def run_momentum_strategy(self, momentum):
        '''Backtesting a momentum-based strategy
        

        Parameters
        ----------
        momentum : TYPE
            DESCRIPTION.

        Returns
        -------
        None.

        '''
        
        msg = f'\n\Running momentum strategy | {momentum} bars'
        msg += f'\nfixed costs {self.ftc}|'
        msg += f'proportional costs {self.ptc}'
        print(msg)
        print('=' * 55)
        
        self.postion = 0 # initial neutral position
        self.trades = 0 # no trades yet
        self.amount = self.initial_amount # reset initial capital
        
        self.data['momentum'] = self.data['return'].rolling(momentum).mean()
        
        for bar in range(momentum, len(self.data)):
            if self.position == 0:
                if self.data['momentum'].iloc[bar] > 0:
                    self.place_buy_order(bar, amount=self.amount)
                    self.position = 1 # long position
            elif self.position == 1:
                if self.data['momentum'].iloc[bar] < 0:
                    self.place_sell_order(bar, units=self.units)
                    self.position = 0 # market neutral
        
        self.close_out(bar)
        
        
    def run_mean_reversion_strategy(self, SMA, threshold):
        ''' Backtesting a mean reversion-based strategy.
        

        Parameters
        ----------
        SMA : TYPE
            DESCRIPTION.
        threshold : TYPE
            DESCRIPTION.

        Returns
        -------
        None.

        '''
        
        msg = f'\n\Running mean reversion | '
        msg += f'SMA={SMA} & thr={threshold}'
        msg += f'\nfixed costs {self.ftc}|'
        msg += f'proportional costs {self.ptc}'
        print(msg)
        print('=' * 55)
        
        self.postion = 0 # initial neutral position
        self.trades = 0 # no trades yet
        self.amount = self.initial_amount # reset initial capital
        
        # Bollinger bands
        self.data['upper_bb'] = bbands(self.data, window=SMA, threshold=threshold)[0]
        self.data['lower_bb'] = bbands(self.data, window=SMA, threshold=threshold)[1]
        
        for bar in range(SMA, len(self.data)):
            if self.position == 0:
                if (self.data['Close'].iloc[bar] < self.data['lower_bb'].iloc[bar]):
                    self.place_buy_order(bar, amount=self.amount)
                    self.position = 1
            elif self.position == 1:
                if (self.data['Close'].iloc[bar] >= self.data['upper_bb'].iloc[bar]):
                    self.place_sell_order(bar, units=self.units)
                    self.position = 0
        
        self.close_out(bar)
        
#%%
        
if __name__ == '__main__':
    
    def run_strategies():
        lobt.run_sma_strategy(42,252)
        lobt.run_momentum_strategy(60)
        lobt.run_mean_reversion_strategy(50,2)
        
    lobt = BacktestLongOnly(symbol='BTCUSDT', interval=15, 
                            start='2022-06-01 00:00', 
                            end='2022-06-30 00:00',
                            amount=100,
                            verbose=False)
    
    run_strategies()
    
    # transaction costs: 0 USD fix, 0.1% proportional
    lobt = BacktestLongOnly(symbol='BTCUSDT', interval=15,
                            start='2022-06-01 00:00', 
                            end='2022-06-30 00:00',
                            amount=100,
                            ptc = 0.1/100,
                            verbose=False)
    
    run_strategies()
                            
        
        
                    
                
        
        
        
        
        
        
        