# Copyright 2025 mercaator
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import sys
import csv
import json
from pprint import pformat

stocks_data = {}
k4_data = {}
k4_transactions = []
currency_rates = {}

# Base currency for all calculations
BASE_CURRENCY = "SEK"

def process_k4_entry(symbol, quantity, trade_price, commission, avg_price, currency, date):
    """Process a sell transaction for K4 tax reporting.

    Args:
        symbol: Stock symbol
        quantity: Number of shares sold (positive number)
        trade_price: Price per share
        commission: Trading commission
        avg_price: Average purchase price per share
        currency: Currency of the transaction
        date: Date of the transaction
    """
    logging.info("==> Processing k4 entry: %s, %s, %s, %s, %s, %s, %s", symbol, quantity, trade_price, commission, avg_price, currency, date)
    if currency == BASE_CURRENCY:
        if symbol not in k4_data:
            k4_data[symbol] = {
                'beteckning': symbol,
                'antal': -quantity,
                'forsaljningspris': -quantity * trade_price + commission,
                'omkostnadsbelopp': -quantity * avg_price
            }
        else:
            k4_data[symbol]['antal'] += -quantity
            k4_data[symbol]['forsaljningspris'] += -quantity * trade_price + commission
            k4_data[symbol]['omkostnadsbelopp'] += -quantity * avg_price

        # Add to k4 transaction list with the following format: beteckning, antal, forsaljningspris, omkostnadsbelopp, vinst
        k4_transactions.append({
            'beteckning': symbol,
            'antal': -quantity,
            'forsaljningspris': -quantity * trade_price + commission,
            'omkostnadsbelopp': -quantity * avg_price,
        })
        logging.info("==> K4 Tax event - Profit/Loss: %s", (-quantity * trade_price + commission) - (-quantity * avg_price))
    else:
        currency_rate = currency_rates[(date, currency)] # USD.SEK rate
        if symbol not in k4_data:
            k4_data[symbol] = {
                'beteckning': symbol,
                'antal': -quantity,
                'forsaljningspris': (-quantity * trade_price + commission) * currency_rate,
                'omkostnadsbelopp': (-quantity * avg_price)
            }
        else:
            k4_data[symbol]['antal'] += -quantity
            k4_data[symbol]['forsaljningspris'] += (-quantity * trade_price + commission) * currency_rate
            k4_data[symbol]['omkostnadsbelopp'] += (-quantity * avg_price)

        # Add to k4 transaction list with the following format: beteckning, antal, forsaljningspris, omkostnadsbelopp, vinst
        k4_transactions.append({
            'beteckning': symbol,
            'antal': -quantity,
            'forsaljningspris': (-quantity * trade_price + commission) * currency_rate,
            'omkostnadsbelopp': (-quantity * avg_price)})
        logging.info("==> K4 Tax event - Profit/Loss: %s", (-quantity * trade_price + commission) * currency_rate - (-quantity * avg_price))

def process_currency_buy(currency, amount, currency_rate):
    """Process a currency buy transaction.

    Args:
        currency: Currency symbol (e.g., 'USD')
        amount: Amount of currency bought
        currency_rate: Exchange rate to SEK
    """
    logging.debug("==> Processing currency buy/selling stock: %s, %s, %s", currency, amount, currency_rate)
    if currency not in stocks_data:
        stocks_data[currency] = {
            'quantity': amount,
            'totalprice': amount * currency_rate,
            'avgprice': currency_rate
        }
    else:
        #k4_currency_data[currency]['antal'] += -amount
        stocks_data[currency]['quantity'] += -amount
        stocks_data[currency]['totalprice'] += -amount * currency_rate
        stocks_data[currency]['avgprice'] = stocks_data[currency]['totalprice'] / stocks_data[currency]['quantity']

def process_buy_entry(symbol, quantity, trade_price, commission, currency, date):
    """Process a buy transaction.

    Args:
        symbol: Stock symbol
        quantity: Number of shares bought
        trade_price: Price per share
        commission: Trading commission
        currency: Currency of the transaction
        date: Date of the transaction
    """
    logging.debug("Processing buy entry: %s, %s, %s, %s, %s, %s", symbol, quantity, trade_price, commission, currency, date)
    if currency == BASE_CURRENCY:

        if symbol not in stocks_data:
            stocks_data[symbol] = {
                'quantity': quantity,
                'totalprice': quantity * trade_price + commission,
                'currency': currency
            }
            stocks_data[symbol]['avgprice'] = stocks_data[symbol]['totalprice'] / stocks_data[symbol]['quantity']
        else:
            stocks_data[symbol]['quantity'] += quantity
            stocks_data[symbol]['totalprice'] += quantity * trade_price + commission
            stocks_data[symbol]['avgprice'] = stocks_data[symbol]['totalprice'] / stocks_data[symbol]['quantity']
    else:
        # Buying stock in foreign currency is a sell transaction of the trading currency
        # TODO: Handle other currency pairs
        currency_rate = currency_rates[(date, currency)] # USD.SEK rate
        process_k4_entry(
            symbol=currency + ".SEK",
            quantity=-quantity*trade_price+commission,
            trade_price=currency_rate,
            commission=0,
            avg_price=stocks_data[currency + ".SEK"]['avgprice'],
            currency='SEK',
            date=date
        )

        if symbol not in stocks_data:
            stocks_data[symbol] = {
                'quantity': quantity,
                'totalprice': (quantity * trade_price + commission) * currency_rate,
                'currency': currency
            }
            stocks_data[symbol]['avgprice'] = stocks_data[symbol]['totalprice'] / stocks_data[symbol]['quantity']
        else:
            stocks_data[symbol]['quantity'] += quantity
            stocks_data[symbol]['totalprice'] += (quantity * trade_price + commission) * currency_rate
            stocks_data[symbol]['avgprice'] = stocks_data[symbol]['totalprice'] / stocks_data[symbol]['quantity']

    logging.debug("Buy entry processed for %s [currency: %s]", symbol, currency)
    logging.debug("Updated stock data for %s: %s", symbol, stocks_data[symbol])

def process_sell_entry(symbol, quantity, trade_price, commission, currency, date):
    """Process a sell transaction.

    Args:
        symbol: Stock symbol
        quantity: Number of shares sold
        trade_price: Price per share
        commission: Trading commission
        currency: Currency of the transaction
        date: Date of the transaction
    """
    logging.debug("Processing sell entry: %s, %s, %s, %s, %s, %s", symbol, quantity, trade_price, commission, currency, date)
    if symbol not in stocks_data:
        if ' ' in symbol and any(c.isdigit() for c in symbol):
            # TODO: Handle options contracts
            logging.info(f"Skipping sell entry {symbol} as it is an options contract")
            return
        else:
            logging.error(f"Error: No BUY entry found for SELL entry {symbol}")
            sys.exit(1)

    if currency == BASE_CURRENCY:
        stocks_data[symbol]['quantity'] += quantity
        stocks_data[symbol]['totalprice'] += quantity * stocks_data[symbol]['avgprice'] #+ commission
    else:
        # Selling stock in a foreign currency is a buy transaction of the trading currency
        # TODO: Handle other currency pairs
        currency_rate = currency_rates[(date, currency)] # USD.SEK rate
        process_currency_buy(currency + ".SEK", quantity * trade_price - commission, currency_rate)

        stocks_data[symbol]['quantity'] += quantity
        stocks_data[symbol]['totalprice'] += quantity * stocks_data[symbol]['avgprice'] #+ (commission * currency_rate)

    process_k4_entry(
        symbol=symbol,
        quantity=quantity,
        trade_price=trade_price,
        commission=commission,
        avg_price=stocks_data[symbol]['avgprice'],
        currency=currency,
        date=date
    )

    if stocks_data[symbol]['quantity'] < 0.0001:  # handle float error with fractional shares
        stocks_data[symbol]['quantity'] = 0
        stocks_data[symbol]['avgprice'] = 0
        if stocks_data[symbol]['totalprice'] < 0.0001:
            stocks_data[symbol]['totalprice'] = 0
        else:
            logging.info("Sell entry processed for %s with fractional shares, totalprice not zero: %s", symbol, stocks_data[symbol]['totalprice'])

    logging.debug("Sell entry processed for %s", symbol)
    logging.debug("Updated stock data for %s: %s", symbol, stocks_data[symbol])


def process_input_data(data):
    for entry in data:
        date = entry['DateTime'].split(';')[0]
        symbol = entry['Symbol']
        quantity = float(entry['Quantity'])
        trade_price = float(entry['TradePrice'])
        commission = -float(entry['IBCommission']) # Input is negative in IBKR CSV file
        currency = entry['CurrencyPrimary']

        if entry['Buy/Sell'] == 'BUY':
            process_buy_entry(symbol, quantity, trade_price, commission, currency, date)
        elif entry['Buy/Sell'] == 'SELL':
            process_sell_entry(symbol, quantity, trade_price, commission, currency, date)

def combine_transactions(transactions):
    # Combine transactions with same symbol
    combined_transactions = {}
    for transaction in transactions:
        if transaction['beteckning'] not in combined_transactions:
            combined_transactions[transaction['beteckning']] = transaction
        else:
            combined_transactions[transaction['beteckning']]['antal'] += transaction['antal']
            combined_transactions[transaction['beteckning']]['forsaljningspris'] += transaction['forsaljningspris']
            combined_transactions[transaction['beteckning']]['omkostnadsbelopp'] += transaction['omkostnadsbelopp']

    # Sort by beteckning
    combined_transactions = sorted(combined_transactions.values(), key=lambda x: x['beteckning'])

    return combined_transactions

def process_trading_data(data):
    process_input_data(data) # Updates global variables
    combined_transactions = combine_transactions(k4_transactions)

    logging.debug("Final K4 data:\n%s", pformat(k4_data, indent=4))
    logging.debug("Final K4 transactions:\n%s", pformat(k4_transactions, indent=4))
    logging.debug("Final K4 combined transactions:\n%s", pformat(combined_transactions, indent=4))
    logging.debug("Final stocks data:\n%s", pformat(stocks_data, indent=4))

    # Summarize the total profit/loss
    total_profit_loss = sum(transaction['forsaljningspris'] - transaction['omkostnadsbelopp'] for transaction in combined_transactions)
    logging.info("==> Total profit/loss: %s", total_profit_loss)
    return combined_transactions

def read_csv_file(filename):
    """Read CSV file and separate stock trades, forex trades, and currency rates.

    Args:
        filename: Path to the CSV file

    Returns:
        tuple: (stock_trades, forex_trades, currency_rates) where each is a list of dictionaries
    """
    stock_trades = []
    forex_trades = []
    currency_rates = []

    with open(filename, 'r') as csvfile:
        lines = csvfile.readlines()

        # Find where the currency rates section starts
        split_index = next(i for i, line in enumerate(lines) if len(line.strip().split(',')) < len(lines[0].strip().split(',')))

        # Process trades
        trades_reader = list(csv.DictReader(lines[:split_index]))

        # Process currency rates
        rates_reader = list(csv.DictReader(lines[split_index:]))

    logging.debug(f"Processed {len(trades_reader)} stock trades, {len(rates_reader)} currency rates")
    return trades_reader, rates_reader

def process_currency_rates(rates):
    """Process currency exchange rates from the CSV file.

    Args:
        rates: List of dictionaries containing currency rate data
    """
    global currency_rates
    for rate in rates:
        if rate['FromCurrency'] == 'SEK':
            date = rate['Date/Time'].split(';')[0]
            key = (date, rate['ToCurrency'])
            currency_rates[key] = 1 /float(rate['Rate'])
        elif rate['FromCurrency'] == 'EUR':
            date = rate['Date/Time'].split(';')[0]
            key = (date, rate['FromCurrency'])
            currency_rates[key] = float(rate['Rate'])

    for key, value in currency_rates.items():
        if key[1] == 'EUR':
            usdsek = currency_rates[(key[0], 'USD')]
            currency_rates[key] = usdsek * value
    logging.info("==> Currency rates 2:\n%s", pformat(currency_rates, indent=4))

def post_process_trading_data(combined_trades):
    """Post-process the trading data for K4 tax reporting as the system handles only integer values.

    Args:
        combined_trades: List of combined trading data
    """
    output = []
    for trade in combined_trades:
        post_processed_data = {}
        post_processed_data['antal'] = round(float(trade['antal']))
        post_processed_data['beteckning'] = trade['beteckning']
        post_processed_data['forsaljningspris'] = round(float(trade['forsaljningspris']))
        post_processed_data['omkostnadsbelopp'] = round(float(trade['omkostnadsbelopp']))
        output.append(post_processed_data)
    return output

def init_stocks_data(year):
    """Initialize the stocks data for the given year.

    Args:
        year: The year to initialize the stocks data for
    """
    global stocks_data
    try:
        with open(f'input_portfolio_{year}.json', 'r') as file:
            stocks_data = json.load(file)
        logging.info(f"Loaded portfolio data for {year}")
        logging.debug("Portfolio data:\n%s", pformat(stocks_data, indent=4))
    except FileNotFoundError:
        logging.info(f"Portfolio file input_portfolio_{year}.json not found")
    except json.JSONDecodeError:
        logging.error(f"Invalid JSON in input_portfolio_{year}.json")
        sys.exit(1)

def save_stocks_data(year):
    """Save the stocks data to a JSON file.

    Args:
        year: The year to save the stocks data for
    """
    # Filter out stocks with quantity 0
    filtered_stocks_data = {symbol: data for symbol, data in stocks_data.items() if data['quantity'] != 0}
    with open(f'output_portfolio_{year}.json', 'w') as file:
        json.dump(filtered_stocks_data, file, indent=4)
    logging.info(f"Saved portfolio data for {year}")

def process_transactions_ibkr(filename, year):
    """Process the input file and generate tax reports.

    Args:
        filename: Path to the input CSV file
    """
    trades, currency_rates_csv = read_csv_file(filename)

    init_stocks_data(year)

    # Create a sorting key function that puts forex trades before stock trades on the same date
    def sort_key(trade):
        # Extract just the date part (before the semicolon)
        date = trade['DateTime'].split(';')[0]
        # For same date, forex trades (with '.' in symbol) should come first
        is_forex = 1 if '.' in trade['Symbol'] else 2
        return (date, is_forex)

    process_currency_rates(currency_rates_csv)
    logging.debug("Currency rates:\n%s", pformat(currency_rates, indent=4))

    # Combine and sort trades
    sorted_trades = sorted(trades, key=sort_key)
    processed_data = process_trading_data(sorted_trades)

    # Save the processed data to a JSON file
    save_stocks_data(year)

    return post_process_trading_data(processed_data)
