import datetime
import logging

import azure.functions as func

from config import conection_string

from pymongo import MongoClient
import yfinance as yf

symbols = ["MSFT","AMD", "SPOT", "AMZN", "NVDA", "GOOGL", "TSLA", "NFLX", "AAPL"]

def priceUpdator(symbol):
    msft = yf.Ticker(symbol)
    current_data = msft.history(period="2d")

    current_open = current_data['Open'].iloc[-1]
    current_close = current_data['Close'].iloc[-1]
    current_high = current_data['High'].iloc[-1]
    current_low = current_data['Low'].iloc[-1]

    previous_close = current_data['Close'].iloc[-2]
    percentage_change = ((current_close - previous_close) / previous_close) * 100

    client = MongoClient(conection_string)
    db = client["stock"]
    collection = db["companies"]
    filter_criteria = {'code': symbol}

    new_values = {'$set': {'open': current_open, 'close': current_close, 'high': current_high, 'low': current_low, 'increase': percentage_change}}

    collection.update_one(filter_criteria, new_values)


def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    if mytimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger function ran at %s', utc_timestamp)

    for i in symbols:
        priceUpdator(i)

