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


stocks_data = {}
k4_data = {}
k4_transactions = []

k4_currency_data = { 'USD': {'antal': 0,
                             'omkostnadsbelopp': 0},
                     'EUR': {'antal': 0,
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


def handle_oldinfosru(args):
    file_content = (f"#DATABESKRIVNING_START\n"
                    f"#PRODUKT SRU\n"
                    f"#FILNAMN BLANKETTER.SRU\n"
                    f"#DATABESKRIVNING_SLUT\n"
                    f"#MEDIELEV_START\n"
                    f"#ORGNR {args['orgnr']}\n"
                    f"#NAMN {args['namn']}\n"
                    f"#ADRESS {args['adress']}\n"
                    f"#POSTNR {args['postnr']}\n"
                    f"#POSTORT {args['postort']}\n"
                    f"#EMAIL {args['email']}\n"
                    f"#MEDIELEV_SLUT\n")

    with open("INFO.SRU", "w") as file:
        file.write(file_content)

    logging.info("INFO.SRU file generated successfully.")


def read_config(config_file='config.json'):
    try:
        with open(config_file, 'r') as file:
            config = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Error reading config file: {e}")
        sys.exit(1)
    return config

def generate_info_sru(config):
    file_content = (f"#DATABESKRIVNING_START\n"
                   f"#PRODUKT SRU\n"
                   f"#FILNAMN BLANKETTER.SRU\n"
                   f"#DATABESKRIVNING_SLUT\n"
                   f"#MEDIELEV_START\n"
                   f"#ORGNR {config.get('orgnr', '')}\n"
                   f"#NAMN {config.get('namn', '')}\n"
                   f"#ADRESS {config.get('adress', '')}\n"
                   f"#POSTNR {config.get('postnr', '')}\n"
                   f"#POSTORT {config.get('postort', '')}\n"
                   f"#EMAIL {config.get('email', '')}\n"
                   f"#MEDIELEV_SLUT\n")

    with open("INFO.SRU", "w") as file:
        file.write(file_content)

    logging.info("INFO.SRU file generated successfully.")

def handle_infosru(args):
    config_file = args.get('config', 'config.json')
    config = read_config(config_file)
    generate_info_sru(config)

def handle_k4(args):
    filepath = args.get('indata_ibkr', 'indata_ibkr.csv')
    logging.debug("Starting to process parsed CSV data from Interactive Brokers")
    process_data(filepath)

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

        k4_data[symbol]['vinst'] = k4_data[symbol]['forsaljningspris'] - k4_data[symbol]['omkostnadsbelopp']
        # Add to k4 transaction list with the following format: beteckning, antal, forsaljningspris, omkostnadsbelopp, vinst
        k4_transactions.append({
            'beteckning': symbol,
            'antal': -quantity,
            'forsaljningspris': -quantity * trade_price + commission,
            'omkostnadsbelopp': -quantity * avg_price,
            'vinst': k4_data[symbol]['vinst']
        })
    else:
        currency_rate = 1 / currency_rates[(date, currency)] # USD.SEK rate
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

        k4_data[symbol]['vinst'] = k4_data[symbol]['forsaljningspris'] - k4_data[symbol]['omkostnadsbelopp']
        # Add to k4 transaction list with the following format: beteckning, antal, forsaljningspris, omkostnadsbelopp, vinst
        k4_transactions.append({
            'beteckning': symbol,
            'antal': -quantity,
            'forsaljningspris': (-quantity * trade_price + commission) * currency_rate,
            'omkostnadsbelopp': (-quantity * avg_price),
            'vinst': k4_data[symbol]['vinst']
        })

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

    # TODO
    # If currency is not equal to base currency the buy transaction is also a sell transaction of the trading currency

    if currency == BASE_CURRENCY:

        if symbol not in stocks_data:
            stocks_data[symbol] = {
                'quantity': quantity,
                'totalprice': quantity * trade_price + commission,
                'avgprice': trade_price,
                'currency': currency
            }
        else:
            stocks_data[symbol]['quantity'] += quantity
            stocks_data[symbol]['totalprice'] += quantity * trade_price + commission
            stocks_data[symbol]['avgprice'] = stocks_data[symbol]['totalprice'] / stocks_data[symbol]['quantity']
    else:
        # Fectch time of transaction as param and get currency rate from currency_rates
        currency_rate = 1 / currency_rates[(date, currency)] # USD.SEK rate
        if symbol not in stocks_data:
            stocks_data[symbol] = {
                'quantity': quantity,
                'totalprice': (quantity * trade_price + commission) * currency_rate,
                'avgprice': trade_price * currency_rate,
                'currency': currency
            }
        else:
            stocks_data[symbol]['quantity'] += quantity
            stocks_data[symbol]['totalprice'] += (quantity * trade_price + commission) * currency_rate
            stocks_data[symbol]['avgprice'] = stocks_data[symbol]['totalprice'] / stocks_data[symbol]['quantity']

    logging.debug("Buy entry processed for %s [currency: %s]", symbol, currency)
    logging.debug("Updated stock data: %s", stocks_data[symbol])

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
    if symbol not in stocks_data:
        logging.error(f"Error: No BUY entry found for SELL entry {symbol}")
        sys.exit(1)

    if currency == BASE_CURRENCY:
        stocks_data[symbol]['quantity'] += quantity
        stocks_data[symbol]['totalprice'] += quantity * stocks_data[symbol]['avgprice'] + commission
    else:
        currency_rate = 1 / currency_rates[(date, currency)] # USD.SEK rate
        stocks_data[symbol]['quantity'] += quantity
        stocks_data[symbol]['totalprice'] += quantity * stocks_data[symbol]['avgprice'] + (commission * currency_rate)

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

    logging.debug("Sell entry processed for %s", symbol)
    logging.debug("Updated stock data: %s", stocks_data[symbol])

def process_trading_data(data):
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

    logging.debug("Final K4 data:\n%s", pformat(k4_data, indent=4))
    logging.debug("Final K4 transactions:\n%s", pformat(k4_transactions, indent=4))
    logging.debug("Final stocks data:\n%s", pformat(stocks_data, indent=4))

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
        trades_reader = csv.DictReader(lines[:split_index])
        for row in trades_reader:
            if '.' in row['Symbol']:
                forex_trades.append(row)
            else:
                stock_trades.append(row)

        # Process currency rates
        rates_reader = csv.DictReader(lines[split_index:])
        currency_rates = list(rates_reader)

    logging.debug(f"Processed {len(stock_trades)} stock trades, {len(forex_trades)} forex trades, and {len(currency_rates)} currency rates")
    return stock_trades, forex_trades, currency_rates

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
            currency_rates[key] = float(rate['Rate'])


def process_data(filename):
    """Process the input file and generate tax reports.

    Args:
        filename: Path to the input CSV file
    """
    stock_trades, forex_trades, currency_rates_csv = read_csv_file(filename)

    # Create a sorting key function that puts forex trades before stock trades on the same date
    def sort_key(trade):
        # Extract just the date part (before the semicolon)
        date = trade['DateTime'].split(';')[0]
        # For same date, forex trades (with '.' in symbol) should come first
        is_forex = 1 if '.' in trade['Symbol'] else 2
        return (date, is_forex)

    process_currency_rates(currency_rates_csv)
    logging.debug("Currency rates: %s", currency_rates)

    # Combine and sort trades
    combined_trades = sorted(stock_trades + forex_trades, key=sort_key)
    process_trading_data(combined_trades)
    # TODO: Add forex and currency rate processing if needed


if __name__ == '__main__':
    main()