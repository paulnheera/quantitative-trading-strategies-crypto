# Strategy Class

# Import Libraries
import pandas as pd
import numpy as np
from math import floor
import pickle
import time
from datetime import datetime
from datetime import timedelta 
from datetime import timezone
from data_download import get_bybit_data
from trader_base import TraderBase

class Strategy:
    def __init__(self, symbol, interval):
        self.symbol = symbol
        self.interval = interval
        #self.parameters = parameters
        # Other initialization code
        self.data = None
        
    def get_hist_data(self, min_length):
        '''Retrieves and prepares the latest data
        
        Returns
        =======
        DataFrame

        '''
        now =  datetime.utcnow()        # get the current time (UTC)
        start_time = now - timedelta(minutes=self.interval * min_length)
        start_time = start_time.strftime('%Y-%m-%d %H:%M:%S')
        end_time = now.strftime('%Y-%m-%d %H:%M:%S')
        
        print(f'Time now is {now}')
        print(f'Minimum length is {min_length}')
        print(f'Downloading data from {start_time} ...')
        
        # historical data (Warning: This opens up seperate API from the trader base)
        hist_data = get_bybit_data(product_type='linear',
                            symbol = self.symbol,
                            interval= self.interval,
                            start_time=start_time,
                            end_time=end_time) # ADD TIME!
        
        print('Download done!')
        print("=" * 60)
        self.data = hist_data # Should the historical data belong to the strategy class or the trader class?

    def start_trading(self, data):
        # Print details of the strategy
        print("Starting strategy at:", datetime.now())
        print("Symbol:", self.symbol)
        # Download prerequisite data and store for future use
        
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
        

    def process_new_data(self, msg):
        # Process new data from the websocket stream
        # Calculate indicators, generate trading signals, etc.
        
        # Get the time
        ts = msg['data'][0]['timestamp']
        dt = pd.to_datetime(ts, unit='ms')
        
        # Check if close of bar and run trading logic
        if msg['data'][0]['confirm']:
            print('')
            print(msg)
            
            # Append the kline to the history
            curr_kline = self.msg_to_df(msg)
            print(curr_kline)
            self.data = pd.concat([self.data, curr_kline])
            
            # Show the updated historical data
            print((self.data.tail))
            
            # Apply logic to historical data
            
            # Generate signal
            
# Example usage:
if __name__ == '__main__':
    strategy = Strategy(symbol='BTCUSDT', interval=1)
    trader = TraderBase(conf_file='algo_trading.cfg', 
                        exchange="bybit", 
                        symbol="BTCUSDT",
                        interval=1,
                        strategy=strategy)
    
    # Start trading
    trader.start_trading()
            
            
            
            
            