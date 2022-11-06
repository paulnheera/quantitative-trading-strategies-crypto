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
            
            # self.check_stop_loss(bar=bar)
            # self.check_take_profit(bar=bar)
            
            if self.position in [0, -1]:
                if (self.data['SMA1'].iloc[bar] > self.data['SMA2'].iloc[bar] 
                    and self.data['SMA1'].iloc[bar-1] <= self.data['SMA2'].iloc[bar-1]
                    ) :
                    self.go_long(bar, amount='all', sl=0.03, tp=0.03)
                    self.position = 1 # long position
                    print('-' * 55) 

            if self.position in [0, 1]:
                if (self.data['SMA1'].iloc[bar] < self.data['SMA2'].iloc[bar]
                    and self.data['SMA1'].iloc[bar-1] > self.data['SMA2'].iloc[bar-1]
                    ):
                    self.go_short(bar,amount='all', sl=0.03, tp=0.03)
                    self.position = -1 # short position
                    print('-' * 55)       
            
                    
        self.close_out(bar)
        
#%% Test
        
lsbt = BacktestLongShort(exchange='binance',
                         symbol='ETHUSDT',
                         interval=15,
                         start='2022-10-01 00:00',
                         end='2022-11-06 08:00',
                         amount=100,
                         ptc=0.0012)

lsbt.run_sma_strategy(50, 290)

order_history = pd.DataFrame(lsbt.order_history)

trades = lsbt.get_trades()
                         