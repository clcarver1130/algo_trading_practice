import numpy as np
import pandas as pd
import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, LSTM, Dropout, Activation

class PricePrediction:
    
    def __init__(self):
        self.raw_data = None
        self.n_input = None
        self.n_out = None
        
    def load_dataframe(self,df):
        self.raw_data = df
        
    def split_data(self, training_size=0.8):
        return self.raw_data[:int(training_size*len(self.raw_data))], self.raw_data[int(training_size*len(self.raw_data)):]

    def make_3d(self, array):
        return array.reshape(array.shape[0], array.shape[1], 1)
    
    def to_supervised(self, df, n_input, n_out, _priceCol=3):
        
        data = np.array(df)
        
        self.n_input = n_input
        self.n_out = n_out
        
        X, y = list(), list()
        in_start = 0
        # step over the entire history one time step at a time
        for _ in range(len(data)):
            # define the end of the input sequence
            in_end = in_start + n_input
            out_end = in_end + n_out
            # ensure we have enough data for this instance 
            if out_end <= len(data):
                X.append(data[in_start:in_end, :])
                y.append(data[in_end:out_end, _priceCol])
            # move along one time step
            in_start += 1
        return np.array(X), np.array(y).reshape(-1)
    
    def to_supervised_classification(self, df, n_input, n_out, _priceCol=3):
        data = np.array(df)
        
        self.n_input = n_input
        self.n_out = n_out        
        
        X = list()
        in_start = 0
        for _ in range(len(data)):
            # define the end of the input sequence
            in_end = in_start + n_input
            out_end = in_end + n_out
            # ensure we have enough data for this instance 
            if out_end <= len(data):
                X.append(data[in_start:in_end, :])
            # move along one time step
            in_start += 1
        return np.array(X)
    
    def normalize_inputs(self, X, y):
        
        x_norm = np.array([x/x[0]-1 for x in X])
        y_norm = np.array([y/x[0][3]-1 for x,y in zip(X, y)])
        return x_norm

    def normalize_x_only(self, X):
        x_norm = np.array([x/x[0]-1 for x in X])
        return x_norm
    
    def denormalize_outputs(self, b):
        
        pass
        
        

        