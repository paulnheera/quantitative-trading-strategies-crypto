# -*- coding: utf-8 -*-
"""
Created on Thu Oct 20 22:22:32 2022

@author: PAUL208
"""

#%% Libraries
from BacktestBase import *
import talib as ta

#%% BacktestLongShort Class

class BacktestLongShort(BacktestBase):
        
    def go_long(self, bar, units=None, amount=None, sl=None, tp=None):
        if self.position == -1:
            self.place_buy_order(bar, units=-self.units) # Close existing short position!
        if units:
            self.place_buy_order(bar, units=units, sl=sl, tp=tp)
        elif amount:
            if amount == 'all':
                amount = self.amount
            self.place_buy_order(bar, amount=amount, sl=sl, tp=tp)
            
    def go_short(self, bar, units=None, amount=None, sl=None, tp=None):
        if self.position == 1:
            self.place_sell_order(bar, units=self.units) # Close existing long position!
        if units:
            self.place_sell_order(bar, units=units, sl=sl, tp=tp)
        elif amount:
            if amount == 'all':
                amount = self.amount
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
        self.results = [] # reset results dictionary
        self.order_history = [] # reset order_history
        
        self.data['return'] = self.data['Close']/ self.data['Close'].shift(1) - 1
        self.data['SMA1'] = self.data['Close'].rolling(SMA1).mean()
        self.data['SMA2'] = self.data['Close'].rolling(SMA2).mean()
        
        self.data['ADX'] = ta.ADX(self.data['High'], self.data['Low'], self.data['Close']) # Filter indicator
                
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
                    ):
                    if self.enable_filter:
                        if(self.data['ADX'].iloc[bar-1] > 25): # If filter is passed go long!
                            self.go_long(bar, amount='all', sl=self.sl, tp=self.tp)
                            self.position = 1 # long position
                            print('-' * 55)
                        else:
                            if self.position == -1:
                                self.place_buy_order(bar, units=-self.units)    
                    else:
                        self.go_long(bar, amount='all', sl=self.sl, tp=self.tp)
                        self.position = 1 # long position
                        print('-' * 55)
                        
            # Check for Short entry signal
            if self.position in [0, 1]:
                if (self.data['SMA1'].iloc[bar] < self.data['SMA2'].iloc[bar]
                    and self.data['SMA1'].iloc[bar-1] >= self.data['SMA2'].iloc[bar-1]
                    ):
                    if self.enable_filter:
                        if(self.data['ADX'].iloc[bar-1] > 25): # If filter is passed go short!
                            self.go_short(bar,amount='all', sl=self.sl, tp=self.tp)
                            self.position = -1 # short position
                            print('-' * 55)
                        # else:
                        #     if self.position == 1:
                        #         self.place_sell_order(bar, units=self.units)
                    else:
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
        self.results =[] # reset results dictionary
        self.order_history = [] # reset order_history
        
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
                    self.place_buy_order(bar=bar,units=-self.units)
                    self.position = 0 # neutral position
                    print('-' * 55)
            
            self.update_results(bar)
            
        self.close_out(bar)
        
        
    def run_vol_breakout_strategy(self, n=14 ,m=1):
        '''
        

        Parameters
        ----------
        n : TYPE, optional
            DESCRIPTION. The default is 14.
        m : TYPE, optional
            DESCRIPTION. The default is 1.

        Returns
        -------
        None.

        '''
        
        self.position = 0 # initial netural position
        self.trades = 0 # no of trades yet
        self.amount = self.initial_amount # reset initial capital
        self.results = [] # reset results dictionary
        self.order_history = [] # reset order_history
        
        data = self.data.copy()
        
        # Indicators
        data['return'] = data['Close']/ data['Close'].shift(1) - 1
        data['ATR'] = ATR(data,n=14)
        data['Upper_trigger'] = data['Close'].shift() + m * data['ATR']
        data['Lower_trigger'] = data['Close'].shift() - m * data['ATR']
        
        # Trading period:
        start_bar = self.data.index.get_loc(self.start)
        end_bar = self.data.index.get_loc(self.end)
        
        for bar in range(start_bar, end_bar + 1):
            
            # Enable stop loss and take profit orders
            if self.enable_stop_orders == True:
                self.check_stop_loss(bar=bar)
                self.check_take_profit(bar=bar)
            # Check for Long entry signal
            if self.position in [0, -1]:
                if (data['Close'].iloc[bar] > data['Upper_trigger'].iloc[bar] 
                    and data['Close'].iloc[bar-1] <= data['Upper_trigger'].iloc[bar-1]
                    ):
                    self.go_long(bar, amount='all', sl=self.sl, tp=self.tp)
                    self.position = 1 # long position
                    print('-' * 55) 
            # Check for Short entry signal
            if self.position in [0, 1]:
                if (data['Close'].iloc[bar] < data['Lower_trigger'].iloc[bar]
                    and data['Close'].iloc[bar-1] >= data['Lower_trigger'].iloc[bar-1]
                    ):
                    self.go_short(bar,amount='all', sl=self.sl, tp=self.tp)
                    self.position = -1 # short position
                    print('-' * 55)
            
            self.update_results(bar)
            
            #self.update_trailling_sl(bar)

        self.close_out(bar)
        
        
    
    def run_buy_and_hold(self):
        '''
        

        Returns
        -------
        None.

        '''
        
        # Reset:
        self.position = 0 # initial netural position
        self.trades = 0 # no of trades yet
        self.amount = self.initial_amount # reset initial capital
        self.results =[] # reset results dictionary
        self.order_history = [] # reset order_history
        
        # Trading period:
        start_bar = self.data.index.get_loc(self.start)
        end_bar = self.data.index.get_loc(self.end)
        
        # Run Strategy:
        for bar in range(start_bar, end_bar + 1):
            
            # Check for Long entry signal
            if self.position in [0, -1]:
                self.go_long(bar, amount='all', sl=self.sl, tp=self.tp)
                self.position = 1 # long position
                print('-' * 55) 
 
            self.update_results(bar)
            
        self.close_out(bar)
        
#%% Test

if __name__ == '__main__':   
    lsbt = BacktestLongShort(exchange='bybit',
                             symbol='ETHUSDT',
                             interval=15,
                             start='2021-01-01 00:00',
                             end='2022-12-20 12:00',
                             amount=10000,
                             ptc=0.0012,
                             enable_stop_orders=False,
                             enable_filter=True,
                             sl=0.04,
                             tp=0.9)
    
    lsbt.run_sma_strategy(20, 300)
    fig, axs = plt.subplots(2, gridspec_kw={'height_ratios': [2, 1]}, sharex=True)
    lsbt.plot_equity(ax=axs[0])
    lsbt.plot_drawdowns(ax=axs[1])

