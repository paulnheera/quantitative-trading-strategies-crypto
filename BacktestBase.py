# -*- coding: utf-8 -*-
"""
Created on Thu Oct 20 22:03:23 2022

@author: PAUL208
"""

#%% Libraries
import numpy as np
import pandas as pd
from math import floor
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
                 ftc=0.0, ptc=0.0, sl=None, tp=None, enable_stop_orders=False, enable_filter=False,
                 verbose=True):
        
        self.exchange = exchange
        self.symbol = symbol
        self.interval = interval      ## EDIT
        self.start = start
        self.end = end
        self.initial_amount = amount
        self.amount = amount
        self.ftc = ftc
        self.ptc = ptc
        self.sl = sl
        self.tp = tp
        self.enable_stop_orders = enable_stop_orders
        self.sl_price = None
        self.tp_price = None
        self.enable_filter = enable_filter
        self.units = 0
        self.position = 0
        self.trades = 0
        self.verbose = verbose
        self.get_data()
        self.order_no = 0
        self.order_history = []
        self.results = []
        
    def get_data(self):
        '''Retrieves and prepares the data
        '''

        h5 = pd.HDFStore('data/' + self.exchange + '/' + self.symbol + '_' + str(self.interval) + '.h5', 'r')
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
        
    def update_results(self, bar):
        
        date, price = self.get_time_price(bar)
        net_wealth = self.units * price + self.amount ## NET_WEALTH AKA EQUITY
        self.results.append({'Time':date, 'Equity':net_wealth, 'Available Balance':self.amount,
                            'Position':self.position})
        
    def update_trailling_sl(self, bar):
        
        date, price = self.get_time_price(bar)
        
        if self.position == 1:
            
            if self.sl_price < price * (1 - self.sl):
                self.sl_price = price * (1 - self.sl)
                print(f'Stop loss updated to {self.sl_price:.3f}')
            
        elif self.position == -1:
            if self.sl_price > price * (1 + self.sl):
                self.sl_price = price * (1 + self.sl)
                print(f'Stop loss updated to {self.sl_price:.3f}')
        
    def plot_equity(self, ax=None):
        
        df = pd.DataFrame(self.results)
        df['Time'] = pd.to_datetime(df['Time'])
        df = df.set_index('Time')
        
        title = self.symbol
        
        plot = df['Equity'].plot(title=title,
                                 figsize=(10,6), ax=ax)
        
        return plot
    
    def plot_drawdowns(self, ax=None):
        
        df = pd.DataFrame(self.results)
        df['Time'] = pd.to_datetime(df['Time'])
        df = df.set_index('Time')
        
        df['roll_max'] = df['Equity'].cummax()
        df['draw_down'] = df['Equity'] / df['roll_max'] - 1
        
        plot = df['draw_down'].plot(color='red', linewidth=0.2, ax=ax)
        ax.fill_between(df.index, df['draw_down'], color='red', alpha=0.3)
        
        return plot
                
    def place_buy_order(self, bar, units=None, amount=None, price=None, order_type='Market', sl=None, tp=None):
        '''Place a buy order
        '''
        date = self.get_time_price(bar)[0]
        if price is None:
            price = self.get_time_price(bar)[1]
            
            if sl is not None:
                self.sl_price = round(price * (1 - sl), 4)
            if tp is not None:
                self.tp_price = round(price * (1 + tp), 4)
        if units is None:
            #units = int(amount/ price) # Doesn't have to be int of crypto since unit sizes are divisible.
            units = ((amount - self.ftc)/(1 + self.ptc))/price ## IMPROVE: restrict for the symbols price precision.
            units = floor(units*100)/100
            #ASSUMPTION: the fixed costs are deducted first.
        self.amount -= (units * price) * (1 + self.ptc) + self.ftc
        self.units += units
        self.trades += 1
        self.order_no += 1
        
        if order_type in ['Stop Loss', 'Take Profit']:
            self.sl_price = None
            self.tp_price = None
        
        self.order_history.append({'Symbol':self.symbol, 'Qty':units, 
                                   'Price':price, 'Direction':'Long',
                                   'Order Type':order_type, 'Order No.':self.order_no,
                                   'Order Time':date})
        
        if self.verbose:
            print(f'{date} | buying {units} units a {price:.2f}')
            print(f'{date} | set stop loss at {self.sl_price} | set take profit at {self.tp_price}')
            self.print_balance(bar)
            self.print_net_wealth(bar)
            
    def place_sell_order(self, bar, units=None, amount=None, price=None, order_type='Market', sl=None, tp=None):
        '''Place a sell order
        '''
        
        date = self.get_time_price(bar)[0]
        
        if price is None:
            price = self.get_time_price(bar)[1]
            
            if sl is not None:
                self.sl_price = round(price * (1 + sl), 4)
            if tp is not None:
                self.tp_price = round(price * (1 - tp), 4)
        if units is None:
            #units = int(amount/ price) # Doesn't have to be int of crypto since unit sizes are divisible.
            units = ((amount - self.ftc)/(1 + self.ptc))/price ## IMPROVE: restrict for the symbols price precision.
            units = floor(units*100)/100 # floor to 2 decimal places.
            #ASSUMPTION: the fixed costs are deducted first.
        self.amount += (units * price) * (1 - self.ptc) - self.ftc
        self.units -= units
        self.trades += 1
        self.order_no += 1
        
        if order_type in ['Stop Loss', 'Take Profit']:
            self.sl_price = None
            self.tp_price = None
        
        self.order_history.append({'Symbol':self.symbol, 'Qty':units, 
                                   'Price':price, 'Direction':'Short',
                                   'Order Type':order_type, 'Order No.':self.order_no,
                                   'Order Time':date})
        
        if self.verbose:
            print(f'{date} | selling {units} units at {price:.2f}')
            print(f'{date} | set stop loss at {self.sl_price} | set take profit at {self.tp_price}')
            self.print_balance(bar)
            self.print_net_wealth(bar)
            
    def check_stop_loss(self, bar):
        if self.sl_price is not None:
            if (self.sl_price > self.data['Low'].iloc[bar]) and self.position==1:
                print("Stop loss hit!")
                self.place_sell_order(bar, units=self.units, price=self.sl_price, order_type='Stop Loss')
                self.position = 0
            elif (self.sl_price < self.data['High'].iloc[bar]) and self.position==-1:
                print("Stop loss hit!")
                self.place_buy_order(bar, units=-self.units, price=self.sl_price, order_type='Stop Loss')
                self.position = 0
        
    def check_take_profit(self, bar):
        if self.tp_price is not None:
            if (self.tp_price < self.data['High'].iloc[bar]) and self.position==1:
                print("Take profit hit")
                self.place_sell_order(bar, units=self.units, price=self.tp_price, order_type='Take Profit')
                self.position = 0
            elif (self.tp_price > self.data['Low'].iloc[bar]) and self.position== -1:
                print("Take profit hit")
                self.place_buy_order(bar, units=-self.units, price=self.tp_price, order_type='Take Profit')
                self.position = 0
                
    def close_out(self, bar):
        ''' Closing out a long or short position
        '''
        
        date, price = self.get_time_price(bar)
        # self.amount += self.units * price
        # self.units = 0
        # self.trades +=1
        
        if self.position == 1:
            self.place_sell_order(bar, units=self.units)
        elif self.position == -1:
            self.place_buy_order(bar, units=-self.units)
        
        if self.verbose:
            print(f'{date} | inventory {self.units} units at {price:.2f}')
            print('=' * 55)
        
        print('Final balance [$] {:2f}'.format(self.amount))
        
        perf = ((self.amount - self.initial_amount) / 
                self.initial_amount * 100)
        print('Net Performance [%] {:.2f}'.format(perf))
        print('Trades Executed [#] {:.2f}'.format(self.trades))
        print('=' * 55)
        
    def get_trades(self):
        
        trade_history = pd.DataFrame(self.order_history)
        
        trade_history['Entry Price'] = trade_history['Price']
        trade_history['Exit Price'] = trade_history['Price'].shift(-1)
        trade_history['P&L'] = trade_history['Qty'] * np.where(trade_history['Direction']=='Long', 
                                        trade_history['Exit Price'] - trade_history['Entry Price'],
                                        trade_history['Entry Price'] - trade_history['Exit Price'])
        
        trade_history['P&L (%)'] = np.where(trade_history['Direction']=='Long', 
                                        trade_history['Exit Price']/trade_history['Entry Price']-1,
                                        trade_history['Entry Price']/trade_history['Exit Price']-1) * 100
        
        trade_history['Trade Time'] = trade_history['Order Time']
        trade_history['Exit Type'] = trade_history['Order Type'].shift(-1)
        
        cols = ['Symbol', 'Direction', 'Qty', 'Entry Price', 'Exit Price', 'P&L', 'P&L (%)', 'Exit Type',
                'Trade Time']
        
        trade_history = trade_history[cols]
        trade_history = trade_history.iloc[::2,:]
        
        return trade_history
        
        
        
#%% Test
        
if __name__ == '__main__':
    
    bt = BacktestBase(exchange='bybit',
                      symbol='ETHUSDT',
                      interval=15,
                      start='2022-09-30 11:00',
                      end='2022-10-31 11:00',
                      amount=10000)