# -*- coding: utf-8 -*-
"""
Created on Thu Oct 20 22:22:32 2022

@author: PAUL208
"""

#%% Libraries
from BacktestBase import *

#%% BacktestLongShort Class

class BacktestLongShort(BacktestBase):
        
    def go_long(self, bar, units=None, amount=None, sl=None, tp=None):
        if self.position == -1:
            print('****Closing existing short trade.****')
            self.place_buy_order(bar, units=-self.units) # Close existing short position!
        if units:
            print('**** Placing a long trade with units specified.****')
            self.place_buy_order(bar, units=units, sl=sl, tp=tp)
        elif amount:
            if amount == 'all':
                amount = self.amount
            print('**** Placing a long trade with amount specified.****')
            self.place_buy_order(bar, amount=amount, sl=sl, tp=tp)
            
    def go_short(self, bar, units=None, amount=None, sl=None, tp=None):
        if self.position == 1:
            print('****Closing existing long trade.****')
            self.place_sell_order(bar, units=self.units) # Close existing long position!
        if units:
            print('**** Placing a short trade with units specified.****')
            self.place_sell_order(bar, units=units, sl=sl, tp=tp)
        elif amount:
            if amount == 'all':
                amount = self.amount
            print('**** Placing a short trade with amount specified.****')
            self.place_sell_order(bar, amount=amount, sl=sl, tp=tp)
            
    def run_sma_strategy(self, SMA1, SMA2):
        msg = f'\nRunning SMA strategy | SMA1={SMA1} & SMA2={SMA2}'
        msg += f'\nfrom: {self.start} to: {self.end}'
        msg += f'\nfixed costs {self.ftc} | '
        msg += f'proportional costs {self.ptc}'       
        print(msg)
        print('=' * 55)

        self.position = 0 # initial netural position
        self.trades = 0 # no of trades yet
        self.amount = self.initial_amount # reset initial capital
        
        self.data['return'] = self.data['Close']/ self.data['Close'].shift(1) - 1
        self.data['SMA1'] = self.data['Close'].rolling(SMA1).mean()
        self.data['SMA2'] = self.data['Close'].rolling(SMA2).mean()
        
        start_bar = self.data.index.get_loc(self.start)
        end_bar = self.data.index.get_loc(self.end)
        
        for bar in range(start_bar, end_bar + 1):
            
            # Enable stop loss and take profit orders
            if self.enable_stop_orders == True:
                self.check_stop_loss(bar=bar)
                self.check_take_profit(bar=bar)
            # Check for Long entry signal
            if self.position in [0, -1]:
                if (self.data['SMA1'].iloc[bar] > self.data['SMA2'].iloc[bar] 
                    and self.data['SMA1'].iloc[bar-1] <= self.data['SMA2'].iloc[bar-1]
                    ) :
                    self.go_long(bar, amount='all', sl=self.sl, tp=self.tp)
                    self.position = 1 # long position
                    print('-' * 55) 
            # Check for Short entry signal
            if self.position in [0, 1]:
                if (self.data['SMA1'].iloc[bar] < self.data['SMA2'].iloc[bar]
                    and self.data['SMA1'].iloc[bar-1] >= self.data['SMA2'].iloc[bar-1]
                    ):
                    self.go_short(bar,amount='all', sl=self.sl, tp=self.tp)
                    self.position = -1 # short position
                    print('-' * 55)
            
            self.update_results(bar)
            
            #self.update_trailling_sl(bar)

        self.close_out(bar)
    
    def run_channel_breakout_strategy(self, x, y):
        '''
        Channel Breakout Rules
        -----------------------
        Entry:
            Buy if current bar's close is the highest close of the past x bars.
            Sell if current bar's close is the lowest close of the past x bars.
        Exit:
            Exit long position if close is the lowest close of the past y bars.
            Exit short position if close is the highest close of the past y bars.

        Parameters
        ----------
        x : TYPE
            Channel length (for entry).
        y : TYPE
            Channel length (for exit).

        Returns
        -------
        None.

        '''
        
        self.position = 0 # initial netural position
        self.trades = 0 # no of trades yet
        self.amount = self.initial_amount # reset initial capital
        
        # Calculate required indicators:
        self.data['return'] = self.data['Close']/ self.data['Close'].shift(1) - 1
        self.data['xMax'] = self.data['Close'].rolling(x).max().shift(1)
        self.data['xMin'] = self.data['Close'].rolling(x).min().shift(1)
        self.data['yMax'] = self.data['Close'].rolling(x).max().shift(1)
        self.data['yMin'] = self.data['Close'].rolling(x).min().shift(1)
        
        # Trading period:
        start_bar = self.data.index.get_loc(self.start)
        end_bar = self.data.index.get_loc(self.end)
        
        # Run Strategy:
        for bar in range(start_bar, end_bar + 1):
            
            # Enable stop loss and take profit orders
            if self.enable_stop_orders == True:
                self.check_stop_loss(bar=bar)
                self.check_take_profit(bar=bar)
            # Check for Long entry signal
            if self.position in [0, -1]:
                if (self.data['Close'].iloc[bar] > self.data['xMax'].iloc[bar] 
                    and self.data['Close'].iloc[bar-1] <= self.data['xMax'].iloc[bar-1]
                    ) :
                    self.go_long(bar, amount='all', sl=self.sl, tp=self.tp)
                    self.position = 1 # long position
                    print('-' * 55) 
            # Check for Long exit signal
            if self.position == 1:
                if (self.data['Close'].iloc[bar] < self.data['yMin'].iloc[bar]
                    and self.data['Close'].iloc[bar-1] >= self.data['yMin'].iloc[bar-1]
                    ):
                    self.place_sell_order(bar=bar,units=self.units)
                    self.position = 0 # neutral position
                    print('-' * 55)
                    
            # Check for Short entry signal
            if self.position in [0, 1]:
                if (self.data['Close'].iloc[bar] < self.data['xMin'].iloc[bar]
                    and self.data['Close'].iloc[bar-1] >= self.data['xMin'].iloc[bar-1]
                    ):
                    self.go_short(bar,amount='all', sl=self.sl, tp=self.tp)
                    self.position = -1 # short position
                    print('-' * 55)
            # Check for Short exit signal
            if self.position in [0, 1]:
                if (self.data['Close'].iloc[bar] > self.data['yMax'].iloc[bar]
                    and self.data['Close'].iloc[bar-1] <= self.data['yMax'].iloc[bar-1]
                    ):
                    self.place_sell_order(bar=bar,units=-self.units)
                    self.position = 0 # neutral position
                    print('-' * 55)
            
            self.update_results(bar)
            
        self.close_out(bar)
        
#%% Test
        
lsbt = BacktestLongShort(exchange='bybit',
                         symbol='ETHUSDT',
                         interval=15,
                         start='2022-10-01 00:00',
                         end='2022-11-23 12:00',
                         amount=100,
                         ptc=0.0012,
                         enable_stop_orders=False,
                         sl=0.025,
                         tp=0.10)

lsbt.run_sma_strategy(50, 290)

lsbt.run_channel_breakout_strategy(100, 50)

order_history = pd.DataFrame(lsbt.order_history)

trades = lsbt.get_trades()

lsbt.plot_equity()
                         