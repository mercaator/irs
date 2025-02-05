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

import argparse
import json
import sys
import csv
import logging
from pprint import pformat
from k4_sru import generate_info_sru, generate_blanketter_sru

# This script processes stock trading data and generates Swedish tax reports.

stocks_data = {}
k4_data = {}
k4_transactions = []
k4_combined_transactions = {}

k4_currency_data = { 'USD.SEK': {'antal': 0,
                             'forsaljningspris': 0,
                             'omkostnadsbelopp': 0},
                     'EUR.SEK': {'antal': 0,
                            'forsaljningspris': 0,
                            'omkostnadsbelopp': 0} }

currency_rates = {}

# Base currency for all calculations
BASE_CURRENCY = "SEK"

def main():
    parser = create_cli_parser()
    args = vars(parser.parse_args())

    # Set up logging based on debug level
    logging_level = getattr(logging, args['debug'])
    logging.basicConfig(level=logging_level,
                       format='%(asctime)s - %(levelname)s - %(message)s')

    logging.debug("Parsed arguments: %s", args)

    if 'commands' not in args or not args['commands']:
        parser.print_help()
        sys.exit(1)

    for command in args['commands']:
        if command == 'oldinfosru':
            handle_oldinfosru(args)
        elif command == 'infosru':
            handle_infosru(args)
        elif command == 'k4':
            handle_k4(args)



def create_cli_parser():
    parser = argparse.ArgumentParser(prog='irs')
    parser.add_argument('commands', nargs='+', choices=['oldinfosru', 'infosru', 'k4'],
                       help='Commands to execute')

    # Add other arguments
    parser.add_argument('--orgnr', help='Organization number')
    parser.add_argument('--namn', help='Name of the organization/person')
    parser.add_argument('--adress', help='Street address')
    parser.add_argument('--postnr', help='Postal code')
    parser.add_argument('--postort', help='City')
    parser.add_argument('--email', help='Email address')
    parser.add_argument('--config', default='config.json', help='Path to configuration file')
    parser.add_argument('--indata_ibkr', default='indata_ibkr.csv',
                       help='Path to the input CSV file for k4 command')
    parser.add_argument('--debug', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                       default='INFO', help='Set the debug level')

    return parser


def read_config(config_file):
    """Read configuration from JSON file."""
    with open(config_file) as f:
        return json.load(f)

def handle_oldinfosru(args):
    generate_info_sru(args)

def handle_infosru(args):
    config = read_config(args.get('config', 'config.json'))
    generate_info_sru(config)

def handle_k4(args):
    config = read_config(args.get('config', 'config.json'))
    filepath = args.get('indata_ibkr', 'indata_ibkr.csv')
    logging.debug("Starting to process parsed CSV data from Interactive Brokers")
    k4_combined_transactions = process_transactions_ibkr(filepath)
    generate_blanketter_sru(config, k4_combined_transactions)

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

def process_currency_sell(currency, amount, currency_rate):
    """Process a currency sell transaction.

    Args:
        symbol: Currency symbol (e.g., 'USD')
        amount: Amount of currency sold
        currency_rate: Exchange rate to SEK
    """
    logging.debug("k4_currency_data: %s", k4_currency_data)
    logging.debug("stocks_data: %s", stocks_data)
    if currency not in k4_currency_data:
        if k4_currency_data[currency]['antal'] + amount < 0:
            k4_currency_data[currency]['antal'] = 0
        else:
            k4_currency_data[currency]['antal'] += amount
        k4_currency_data[currency]['forsaljningspris'] += -amount * currency_rate
        k4_currency_data[currency]['omkostnadsbelopp'] += -amount * stocks_data[currency]['avgprice']
    else:
        k4_currency_data[currency]['antal'] += amount
        k4_currency_data[currency]['forsaljningspris'] += -amount * currency_rate
        k4_currency_data[currency]['omkostnadsbelopp'] += -amount * stocks_data[currency]['avgprice']

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
        # TODO: Buying stock in foreign currency is a sell transaction of the trading currency
        currency_rate = currency_rates[(date, currency)] # USD.SEK rate
        #process_currency_sell(currency + ".SEK", quantity * trade_price + commission, currency_rate)
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
        logging.error(f"Error: No BUY entry found for SELL entry {symbol}")
        sys.exit(1)

    if currency == BASE_CURRENCY:
        stocks_data[symbol]['quantity'] += quantity
        stocks_data[symbol]['totalprice'] += quantity * stocks_data[symbol]['avgprice'] #+ commission
    else:
        # TODO: Selling stock in a foreign currency is a buy transaction of the trading currency
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



def process_trading_data(data):
    process_input_data(data)

    # Combine transactions with same symbol
    for transaction in k4_transactions:
        if transaction['beteckning'] not in k4_combined_transactions:
            k4_combined_transactions[transaction['beteckning']] = transaction
        else:
            k4_combined_transactions[transaction['beteckning']]['antal'] += transaction['antal']
            k4_combined_transactions[transaction['beteckning']]['forsaljningspris'] += transaction['forsaljningspris']
            k4_combined_transactions[transaction['beteckning']]['omkostnadsbelopp'] += transaction['omkostnadsbelopp']

    logging.debug("Final K4 data:\n%s", pformat(k4_data, indent=4))
    logging.debug("Final K4 transactions:\n%s", pformat(k4_transactions, indent=4))
    logging.debug("Final K4 combined transactions:\n%s", pformat(k4_combined_transactions, indent=4))
    logging.debug("Final stocks data:\n%s", pformat(stocks_data, indent=4))
    logging.debug("Final currency data:\n%s", pformat(k4_currency_data, indent=4))
    # Summarize the total profit/loss
    total_profit_loss = sum(transaction['forsaljningspris'] - transaction['omkostnadsbelopp'] for transaction in k4_combined_transactions.values())
    logging.info("==> Total profit/loss: %s", total_profit_loss)

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

def post_process_trading_data(combined_trades):
    """Post-process the trading data for K4 tax reporting as the system handles only integer values.

    Args:
        combined_trades: List of combined trading data
    """
    output = {}
    for symbol, trade in combined_trades.items():
        post_processed_data = {}
        post_processed_data['antal'] = int(trade['antal'])
        post_processed_data['forsaljningspris'] = int(trade['forsaljningspris'])
        post_processed_data['omkostnadsbelopp'] = int(trade['omkostnadsbelopp'])
        output[symbol] = post_processed_data
    return output


def process_transactions_ibkr(filename):
    """Process the input file and generate tax reports.

    Args:
        filename: Path to the input CSV file
    """
    trades, currency_rates_csv = read_csv_file(filename)

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
    process_trading_data(sorted_trades)
    return post_process_trading_data(k4_combined_transactions)

if __name__ == '__main__':
    main()