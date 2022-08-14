# -*- coding: utf-8 -*-
"""
Created on Sat Aug 13 16:55:32 2022

@author: PAUL208
"""

# Import libraries
import pandas as pd
import time
from datetime import datetime
from datetime import timezone
from pybit import usdt_perpetual

# Connect to API
client = usdt_perpetual.HTTP(endpoint="https://api-testnet.bybit.com")

def get_bybit_data(symbol, interval, start_time, end_time):
    
    ''' Download data from exchange 
    
    Parameters
    ==========
    symbol: string
        asset symbol
    interval: int
        timeframe interval in minutes
    start_time: string
        Starting time of data
    end_time: string
        End point of data
    '''
    
    # Convert time variables to timestamps
    
    # Check that time variables are string
    
    start_time = datetime.strptime(start_time, '%Y-%m-%d')
    end_time = datetime.strptime(end_time, '%Y-%m-%d')
    
    start_ts = int(start_time.replace(tzinfo=timezone.utc).timestamp())
    end_ts = int(end_time.replace(tzinfo=timezone.utc).timestamp())
    
    # set main list object & current time cursor
    raw_ls = []
    c_ts = start_ts
    
    # while loop to download several pages of data
    while c_ts < end_ts:
        
        # time difference
        diff = int( (end_ts - c_ts) / (interval*60) )    # divide by 60 to get to mins, divide by interval to get to frequency
        
        print("Downloading data from {}".format(pd.to_datetime(c_ts, unit='s')))
        print("The difference between current time and end time is {}".format(diff))
        
        print("\n")
        
        # download data
        temp = client.query_kline(
                symbol=symbol,
                interval=interval,
                limit=min(200,diff),
                from_time=c_ts
        )
        
        # append list to main list
        temp = temp['result']
        raw_ls.extend(temp)
    
        # update time cursor
        c_ts = raw_ls[-1]['start_at'] + interval*60  # interval (m) 
        
        # sleep for a bit
        time.sleep(2)
        
        
    
    # convert to dataframe
    df = pd.DataFrame(raw_ls)
    
    # rename colums
    df.rename(columns = {'symbol':'Symbol',
                           'period':'Period',
                           'interval':'Interval',
                           'start_at':'Start_at',
                           'open_time':'Time',
                           'volume':'Volume',
                           'open':'Open',
                           'high':'High',
                           'low':'Low',
                           'close':'Close',
                           'turnover':'Turnover'
                          }, inplace=True)
    
    # Convert time column to datetime
    df['Start_at'] = pd.to_datetime(df['Start_at'], unit='s')
    df['Time'] = pd.to_datetime(df['Time'], unit='s')

    # Convert fields to numerical values
    df[['Volume','Open','High', 'Close', 'Turnover']] = df[['Volume','Open','High', 'Close', 'Turnover']].apply(pd.to_numeric)    
    
    # Set time column to index
    df.set_index('Time',inplace=True)
    
    # Select columns
    cols = ['Open','High','Low', 'Close','Volume']
    df = df[cols]
    
    # return ohlcv dataframe
    return df

if __name__ == '__main__':
    
    data = get_bybit_data(symbol='BTCUSDT', interval=30,start_time='2021-01-01',end_time='2021-01-31')
        
    data['Close'].plot(figsize=(10,6))
    

    
    
    
    