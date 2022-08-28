# -*- coding: utf-8 -*-
"""
Created on Fri Aug 26 19:45:12 2022

@author: PAUL208
"""

#%% Import Libraries
import pandas as pd
import numpy as np
import pickle
import time
from datetime import datetime
from datetime import timedelta 
from datetime import timezone
from pybit import usdt_perpetual

from matplotlib import pyplot as plt
from IPython import display

from sklearn.neural_network import MLPClassifier
import tensorflow as tf
from keras.models import Sequential         # Model type
from keras.layers import Dense              # Layers  
from keras.optimizers import Adam, RMSprop  # Optimizers

from  bybit_download_data import get_bybit_data

#%% User Defined Functions

# Prepare data
def prepare_features(data):
    
    df = data.copy()
    
    df['return'] = df['Close']/df['Close'].shift(1) - 1
    df['direction'] = np.where(df['return'] > 0, 1, 0)
    
    # Create the lagged data
    lags = 5
    features = []
    for lag in range(1, lags + 1):
        feature = f'lag_{lag}'
        df[feature] = df['return'].shift(lag)
        features.append(feature)
    
    # Create additional features
    df['momentum'] = df['return'].rolling(5).mean().shift(1)
    df['volatility'] = df['return'].rolling(20).std().shift(1)
    df['distance'] = (df['Close'] - df['Close'].rolling(50).mean().shift(1)) # consider changing to percentage distance
    
    features.extend(['momentum', 'volatility', 'distance'])
    
    cols = features + ['direction']
    
    df = df[cols].copy()
    
    df.dropna(inplace=True)
        
    return {'data':df, 'features':features}


# Set Seeds
def set_seeds(seed=100):
    #random.seed(seed)
    np.random.seed(seed)
    tf.random.set_seed(100)

#%% Connect to API


#%% Download Historical Data
    
# Parameters
symbol = 'ETHUSDT'
interval = 15
start_time = '2022-07-25 00:00'
end_time ='2022-08-25 00:00'

hist_data = get_bybit_data(symbol=symbol,
                    interval=interval,
                    start_time=start_time,
                    end_time=end_time)

#%% Prepare data

# Get features and training data
features = prepare_features(hist_data)['features']    
training_data = prepare_features(hist_data)['data']

# Standardize data
mu, std = training_data.mean(), training_data.std()
training_data_ = (training_data - mu)/std

print(training_data_)
print("features: {}".format(features))


#%% Train Model

# Specify the optimizer
optimizer = Adam(learning_rate=0.0001)

# Set seeds
set_seeds()

# Specify the model
model = Sequential()
model.add(Dense(64, activation='relu', input_shape=(len(features),)))
model.add(Dense(64, activation='relu'))
model.add(Dense(1, activation='sigmoid'))
model.compile(optimizer=optimizer,
             loss='binary_crossentropy',
             metrics=['accuracy'])

# Fit the model
model.fit(training_data_[features], 
          training_data['direction'],
          epochs=50, verbose=False,
          validation_split=0.2, shuffle=False)

# Model Performance
train_acc = model.evaluate(training_data_[features], training_data['direction'])[1]
pred = np.where(model.predict(training_data_[features]) > 0.5, 1, 0)
training_data['prediction'] = np.where(pred > 0, 1, -1)
training_data['prediction'].value_counts().plot.bar()
print("The accuracy of the model on the training data is {}".format(format(train_acc,'.2f')))

#%% Persist the Model

algorithm= {'model':model, 'mu':mu, 'std':std, 'features':features}
pickle.dump(algorithm, open('algorithm.pkl', 'wb'))