# -*- coding: utf-8 -*-
"""
Created on Thu Oct 20 22:22:32 2022

@author: PAUL208
"""

#%% Libraries
from BacktestBase import *

#%% BacktestLongShort Class

class BacktestLongShort(BacktestBase):
    
    def go_long(self, bar, units=None, amount=None):
        if self.position == -1:
            self.place_buy_order(bar, units=-self.units) # Close existing short position!
        if units:
            self.place_buy_order(bar, units=units)
        elif amount:
            if amount == 'all':
                amount = self.amount
            self.place_buy_order(bar, amount=amount)
            
    def go_short(self, bar, units=None, amount=None):
        if self.position == -1:
            self.place_sell_order(bar, units=self.units) # Close existing long position!
        if units:
            self.place_sell_order(bar, units=units)
        elif amount:
            if amount == 'all':
                amount = self.amount
            self.place_sell_order(bar, amount=amount)
            
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
            if self.position in [0, -1]:
                if self.data['SMA1'].iloc[bar] > self.data['SMA2'].iloc[bar]:
                    self.go_long(bar, amount='all')
                    self.position = 1 # long position
             
            if self.position in [0, 1]:
                if self.data['SMA1'].iloc[bar] < self.data['SMA2'].iloc[bar]:
                    self.position = -1 # short position
                    
        self.close_out(bar)
        
#%% Test
        
lsbt = BacktestLongShort(exchange='bybit',
                         symbol='ETHUSDT',
                         interval=15,
                         start='2022-09-30 11:00',
                         end='2022-10-20 12:00',
                         amount=100,
                         ptc=0.0012)

lsbt.run_sma_strategy(50, 290)
                         