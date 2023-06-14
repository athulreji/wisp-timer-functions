import datetime
import logging


from config import conection_string
import azure.functions as func

import numpy as np
import yfinance as yf
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from pymongo import MongoClient

symbols = ["MSFT","AMD", "SPOT", "AMZN", "NVDA", "GOOGL", "TSLA", "NFLX", "AAPL"]
startdate = '2010-01-01'

def Predict(symbol):
    #download the historical data
    data = yf.download(symbol, start=startdate)

    # Preprocess the data
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(data["Close"].values.reshape(-1, 1))

    # Prepare the training dataset
    sequence_length = 30  # Set the desired sequence length
    x_train = []
    y_train = []
    for i in range(len(scaled_data) - sequence_length - 1):
        x_train.append(scaled_data[i:i+sequence_length])
        y_train.append(scaled_data[i+sequence_length])
    x_train = np.array(x_train)
    y_train = np.array(y_train)

    # Build the LSTM model
    model = Sequential()
    model.add(LSTM(50, return_sequences=True, input_shape=(sequence_length, 1)))
    model.add(LSTM(50))
    model.add(Dense(1))
    model.compile(optimizer="adam", loss="mean_squared_error")

    # Train the model
    model.fit(x_train, y_train, epochs=50, batch_size=32)

    # Make predictions for the next 20 days
    x_test = scaled_data[-sequence_length:]  # Use the last sequence from the available data
    predictions = []
    for _ in range(20):
        x = np.array([x_test])
        x = np.reshape(x, (x.shape[0], x.shape[1], 1))
        y = model.predict(x)
        predictions.append(y[0, 0])
        x_test = np.roll(x_test, -1, axis=0)
        x_test[-1] = predictions[-1]

    # Inverse transform the predictions to get the actual stock prices
    predictions = scaler.inverse_transform(np.array(predictions).reshape(-1, 1)).flatten().tolist()
    y_train = scaler.inverse_transform(y_train).flatten().tolist()


    client = MongoClient(connection_string)
    db = client["stock"]
    collection = db["predictions"]
    filter_criteria = {'name': symbol}
    new_values = {'$set': { "data": y_train, "predictions": predictions}}


    collection.update_one(filter_criteria,new_values)

def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    if mytimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger function ran at %s', utc_timestamp)

    for i in symbols:
        Predict(i)
