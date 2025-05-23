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
from .sru import CURRENCY_CODES, OUTPUT_DIR

# Base currency for all calculations
BASE_CURRENCY = "SEK"

def update_statistics_data(statistics_data, date, symbol, profit_loss):
    # Statistics data is a list of tuples with date, symbol, and profit/loss
    tuple = (date, symbol, profit_loss)
    statistics_data.append(tuple)

def process_k4_entry(symbol, quantity, trade_price, commission, avg_price, currency, date, k4_data, currency_rates, statistics_data):
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
    logging.info("    ==> Processing k4 entry: %s, %s, %s, %s, %s, %s, %s", symbol, quantity, trade_price, commission, avg_price, currency, date)
    if currency == BASE_CURRENCY:
        if symbol not in k4_data:
            k4_data[symbol] = {
                'beteckning': symbol,
                'antal': -quantity,
                'forsaljningspris': -quantity * trade_price - commission,
                'omkostnadsbelopp': -quantity * avg_price
            }
            update_statistics_data(statistics_data, date, symbol, (-quantity * trade_price - commission) - (-quantity * avg_price))
        else:
            k4_data[symbol]['antal'] += -quantity
            k4_data[symbol]['forsaljningspris'] += -quantity * trade_price - commission
            k4_data[symbol]['omkostnadsbelopp'] += -quantity * avg_price
            update_statistics_data(statistics_data, date, symbol, (-quantity * trade_price - commission) - (-quantity * avg_price))

        logging.info("    ==> K4 Tax event - Profit/Loss: %s", (-quantity * trade_price - commission) - (-quantity * avg_price))
    else:
        currency_rate = currency_rates[(date, currency)] # USD.SEK rate
        if symbol not in k4_data:
            k4_data[symbol] = {
                'beteckning': symbol,
                'antal': -quantity,
                'forsaljningspris': (-quantity * trade_price - commission) * currency_rate,
                'omkostnadsbelopp': (-quantity * avg_price)
            }
            update_statistics_data(statistics_data, date, symbol, (-quantity * trade_price - commission) * currency_rate - (-quantity * avg_price))
        else:
            k4_data[symbol]['antal'] += -quantity
            k4_data[symbol]['forsaljningspris'] += (-quantity * trade_price - commission) * currency_rate
            k4_data[symbol]['omkostnadsbelopp'] += (-quantity * avg_price)
            update_statistics_data(statistics_data, date, symbol, (-quantity * trade_price - commission) * currency_rate - (-quantity * avg_price))

        logging.info("    ==> K4 Tax event - Profit/Loss: %s", (-quantity * trade_price - commission) * currency_rate - (-quantity * avg_price))

def process_currency_buy(currency, amount, currency_rate, stocks_data):
    """Process a currency transaction.

    Args:
        currency: Currency symbol (e.g., 'USD')
        amount: Amount of currency bought
        currency_rate: Exchange rate to SEK
    """
    logging.debug("      buying %s %s, %s/SEK = %s", -amount, currency, currency, currency_rate)
    if currency not in stocks_data:
        stocks_data[currency] = {
            'quantity': -amount,
            'totalprice': -amount * currency_rate,
            'avgprice': currency_rate
        }
    else:
        stocks_data[currency]['quantity'] += -amount
        stocks_data[currency]['totalprice'] += -amount * currency_rate
        stocks_data[currency]['avgprice'] = stocks_data[currency]['totalprice'] / stocks_data[currency]['quantity']

def process_currency_sell(currency, amount, stocks_data):
    """Process a currency transaction.

    Args:
        currency: Currency symbol (e.g., 'USD')
        amount: Amount of currency bought
        currency_rate: Exchange rate to SEK
    """
    if currency not in stocks_data:
        logging.error("Error: No BUY entry found for SELL entry %s", currency)
        sys.exit(1)
    else:
        logging.debug("      selling %s %s, %s/SEK = %s", -amount, currency, currency, stocks_data[currency]['avgprice'])
        stocks_data[currency]['quantity'] += -amount
        stocks_data[currency]['totalprice'] += -amount * stocks_data[currency]['avgprice']


def process_buy_entry(symbol, quantity, trade_price, commission, currency, date, stocks_data, k4_data, currency_rates, statistics_data):
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
        # UC-1. Buy stock in base currency e.g. buy ERIC-B for SEK
        #       Transactions: Buy ERIC-B
        # UC-2. Buy currency pair where quote currency is SEK e.g. USD/SEK
        #       Transactions: Buy USD

        # Split symbol into base currency and quote currency
        if '.' in symbol:
            base = symbol.split('.')[0]
            quote = symbol.split('.')[1]
        else:
            base = symbol
            quote = BASE_CURRENCY

        # Update currency rates with actual rate when available (e.g buying USD/SEK)
        #if base in CURRENCY_CODES and quote == BASE_CURRENCY:
        #    currency_rates[(date, base)] = trade_price
        #    logging.debug(f"   Updated currency rate for {date} {base}: {currency_rates[(date, base)]}")

        logging.debug(f"   Action (1/1): Buy {base} for {quote}")

        if base not in stocks_data:
            stocks_data[base] = {
                'quantity': quantity,
                'totalprice': quantity * trade_price + commission
            }
            stocks_data[base]['avgprice'] = stocks_data[base]['totalprice'] / stocks_data[base]['quantity']
        else:
            stocks_data[base]['quantity'] += quantity
            stocks_data[base]['totalprice'] += quantity * trade_price + commission
            stocks_data[base]['avgprice'] = stocks_data[base]['totalprice'] / stocks_data[base]['quantity']
    else:
        # UC-3. Buy stock in foreign currency e.g. buy AAOI for USD
        #       Transactions: Buy AAOI, Sell USD
        # UC-4. Buy currency pair where quote currency in not SEK e.g. EUR/USD for USD
        #       Transactions: Buy EUR, Sell USD

        # Split symbol into base currency and quote currency
        if '.' in symbol:
            base = symbol.split('.')[0]
            quote = symbol.split('.')[1]
        else:
            base = symbol
            quote = currency

        if ' ' in base and any(c.isdigit() for c in base):
            logging.info(f"    buy entry {base} is an options contract")

        currency_rate = currency_rates[(date, currency)] # <currency> / SEK rate

        logging.debug(f"   Action (1/2): Sell {currency} for {BASE_CURRENCY}")

        # Sell currency e.g. USD
        process_k4_entry(
            symbol=currency,
            quantity= -(quantity*trade_price+commission),
            trade_price=currency_rate,
            commission=0, # FOREX fee for automatic currency exchange included in IBCommission
            avg_price=stocks_data[currency]['avgprice'],
            currency=BASE_CURRENCY,
            date=date,
            k4_data=k4_data,
            currency_rates=currency_rates,
            statistics_data=statistics_data
        )
        process_currency_sell(currency, quantity*trade_price+commission, stocks_data)


        logging.debug(f"   Action (2/2): Buy {base} for {quote}")
        if base not in stocks_data:
            stocks_data[base] = {
                'quantity': quantity,
                'totalprice': (quantity * trade_price + commission) * currency_rate
            }
            stocks_data[base]['avgprice'] = stocks_data[base]['totalprice'] / stocks_data[base]['quantity']
        else:
            stocks_data[base]['quantity'] += quantity
            stocks_data[base]['totalprice'] += (quantity * trade_price + commission) * currency_rate
            stocks_data[base]['avgprice'] = stocks_data[base]['totalprice'] / stocks_data[base]['quantity']

    logging.debug("   Buy entry processed for %s [currency: %s]", symbol, currency)
    logging.debug("   Updated stock data for %s: %s", base, stocks_data[base])

    liquidity_usd = 0
    liquidity_eur = 0
    usd_sek = 0
    eur_sek = 0
    if 'USD' in stocks_data:
        liquidity_usd = stocks_data['USD']['quantity']
        usd_sek = stocks_data['USD']['avgprice']
    if 'EUR' in stocks_data:
        liquidity_eur = stocks_data['EUR']['quantity']
        eur_sek = stocks_data['EUR']['avgprice']

    logging.debug("   Liquidity (USD): %.2f -- USD/SEK: %.2f", liquidity_usd, usd_sek)
    logging.debug("   Liquidity (EUR): %.2f -- EUR/SEK: %.2f", liquidity_eur, eur_sek)

def process_sell_entry(symbol, quantity, trade_price, commission, currency, date, stocks_data, k4_data, currency_rates, statistics_data):
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
    if '.' in symbol:
        base = symbol.split('.')[0]
        quote = symbol.split('.')[1]
    else:
        base = symbol
        quote = BASE_CURRENCY

    if base not in stocks_data:
        if ' ' in base and any(c.isdigit() for c in base):
            logging.info(f"    sell entry {base} is an options contract")
            stocks_data[base] = {
                'quantity': 0,
                'totalprice': 0,
                'avgprice': 0
            }
        else:
            logging.debug(f"stocks_data: {stocks_data}")
            logging.error(f"Error: No BUY entry found for SELL entry {base}")
            sys.exit(1)

    if currency == BASE_CURRENCY:
        # UC-5. Sell stock in base currency e.g. sell ERIC-B for SEK
        #       Transactions: Sell ERIC-B
        # UC-6. Sell currency pair where quote currency is SEK e.g. USD/SEK
        #       Transactions: Sell USD

        logging.debug(f"   Action (1/1): Sell {base} for {quote}")
        if stocks_data[base]['quantity'] + quantity < 0:
            # TODO: Implement short selling
            logging.warning("      Trying to sell %s %s, but only %s available ", -quantity, base, stocks_data[base]['quantity'])

        stocks_data[base]['quantity'] += quantity
        stocks_data[base]['totalprice'] += quantity * stocks_data[base]['avgprice'] #+ commission
    else:
        # UC-7. Sell stock in foreign currency e.g. sell AAOI for USD
        #       Transactions: Sell AAOI, Buy USD
        # UC-8. Sell currency pair where quote currency in not SEK e.g. EUR/USD for USD
        #       Transactions: Sell EUR, Buy USD

        currency_rate = currency_rates[(date, currency)] # USD.SEK rate
        logging.debug(f"   Action (1/2): Buy {currency} for {quote}")
        # Quantity is negative for sell entries, commission is turned positive in process_input_data.
        # Total amount of currency received is quantity * trade_price + commission e.g. -10 * 10 + 1 = -99
        process_currency_buy(currency, quantity * trade_price + commission, currency_rate, stocks_data)

        logging.debug(f"   Action (2/2): Sell {base} for {quote}")
        stocks_data[base]['quantity'] += quantity
        stocks_data[base]['totalprice'] += quantity * stocks_data[base]['avgprice'] #+ (commission * currency_rate)

    process_k4_entry(
        symbol=base,
        quantity=quantity,
        trade_price=trade_price,
        commission=commission,
        avg_price=stocks_data[base]['avgprice'],
        currency=currency,
        date=date,
        k4_data=k4_data,
        currency_rates=currency_rates,
        statistics_data=statistics_data
    )

    # Handle fractional "shares" (satoshis) of BTC as most probably fees cause final quantity to be more than 0.0001
    # that was set to handle float errors with fractional shares.
    if base == 'BTC' and abs(stocks_data[base]['quantity']) < 0.002:
        logging.warning("Sell entry processed for %s with satoshis, quantity: %s", base, stocks_data[base]['quantity'])
        stocks_data[base]['quantity'] = 0
        stocks_data[base]['avgprice'] = 0
        if stocks_data[base]['totalprice'] < 100.0:
            stocks_data[base]['totalprice'] = 0
        else:
            logging.info("Sell entry processed for %s with satoshis, totalprice not zero: %s", base, stocks_data[base]['totalprice'])

    if abs(stocks_data[base]['quantity']) < 0.0001:  # handle float error with fractional shares
        stocks_data[base]['quantity'] = 0
        stocks_data[base]['avgprice'] = 0
        if stocks_data[base]['totalprice'] < 0.0001:
            stocks_data[base]['totalprice'] = 0
        else:
            logging.info("Sell entry processed for %s with fractional shares, totalprice not zero: %s", base, stocks_data[base]['totalprice'])

    logging.debug("   Sell entry processed for %s [currency: %s]", symbol, currency)
    logging.debug("   Updated stock data for %s: %s", base, stocks_data[base])
    liquidity_usd = 0
    liquidity_eur = 0
    usd_sek = 0
    eur_sek = 0
    if 'USD' in stocks_data:
        liquidity_usd = stocks_data['USD']['quantity']
        usd_sek = stocks_data['USD']['avgprice']
    if 'EUR' in stocks_data:
        liquidity_eur = stocks_data['EUR']['quantity']
        eur_sek = stocks_data['EUR']['avgprice']

    logging.debug("   Liquidity (USD): %.2f -- USD/SEK: %.2f", liquidity_usd, usd_sek)
    logging.debug("   Liquidity (EUR): %.2f -- EUR/SEK: %.2f", liquidity_eur, eur_sek)



def process_input_data(data, stocks_data, k4_data, currency_rates, statistics_data):
    for entry in data:
        date = entry['DateTime'].split(';')[0]
        symbol = entry['Symbol']
        quantity = float(entry['Quantity'])
        trade_price = float(entry['TradePrice'])
        commission = -float(entry['IBCommission']) # Input is negative in IBKR CSV file
        currency = entry['CurrencyPrimary']

        if entry['Buy/Sell'] == 'BUY':
            process_buy_entry(symbol, quantity, trade_price, commission, currency, date, stocks_data, k4_data, currency_rates, statistics_data)
        elif entry['Buy/Sell'] == 'SELL':
            process_sell_entry(symbol, quantity, trade_price, commission, currency, date, stocks_data, k4_data, currency_rates, statistics_data)

def process_trading_data(data, stocks_data, k4_data, currency_rates, statistics_data):
    """Process the trading data for K4 tax reporting.
    """
    process_input_data(data, stocks_data, k4_data, currency_rates, statistics_data)

    logging.debug("Final K4 data:\n%s", pformat(k4_data, indent=4))
    logging.debug("Final stocks data:\n%s", pformat(stocks_data, indent=4))

    # Summarize the total profit/loss
    total_profit_loss = sum(transaction['forsaljningspris'] - transaction['omkostnadsbelopp'] for transaction in k4_data.values())
    logging.info("==> Total profit/loss: %s", total_profit_loss)
    output = sorted(k4_data.values(), key=lambda x: x['beteckning'])
    return output

def read_csv_ibkr(filename):
    """Read CSV file with Interactive Brokers transactions.

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


def read_csv_bitstamp(filename):
    """Read CSV file with Bitstamp transactions. The file is expected to be in IBRK format.

    Args:
        filename: Path to the CSV file

    Returns:
        tuple: (stock_trades, forex_trades, currency_rates) where each is a list of dictionaries
    """
    with open(filename, 'r') as csvfile:
        lines = csvfile.readlines()
        trades_reader = list(csv.DictReader(lines))
        logging.debug(f"Processed {len(trades_reader)} Bitstamp trades")
        logging.debug("==> Bitstamp trades:\n%s", pformat(trades_reader, indent=4))

    return trades_reader


def process_currency_rates(rates, currency_rates, year):
    """Process currency exchange rates from the CSV file.

    Args:
        rates: List of dictionaries containing currency rate data
    """
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

    # Load predefined currency rates and merge with the processed rates above
    currency_rates_init = init_currency_rates(year)

    # Merge the two dictionaries
    for key, value in currency_rates_init.items():
        if key not in currency_rates:
            currency_rates[key] = value

    logging.info("==> Currency rates:\n%s", pformat(currency_rates, indent=4))

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
    try:
        with open(f'input/input_portfolio_{year}.json', 'r') as file:
            stocks_data = json.load(file)
        logging.info(f"Loaded portfolio data for {year}")
        logging.debug("Portfolio data:\n%s", pformat(stocks_data, indent=4))
        return stocks_data
    except FileNotFoundError:
        logging.info(f"Portfolio file input_portfolio_{year}.json not found")
        # Initialize an empty portfolio if the file is not found
        return {}
    except json.JSONDecodeError:
        logging.error(f"Invalid JSON in input_portfolio_{year}.json")
        sys.exit(1)

def init_currency_rates(year):
    """Initialize the currency rates for the given year.

    Args:
        year: The year to initialize the currency rates for
    """
    try:
        with open(f'input/input_currency_rates_{year}.json', 'r') as file:
            currency_rates_raw = json.load(file)
            # Convert string keys back to tuple keys
            currency_rates = {tuple(key.split("_")): value for key, value in currency_rates_raw.items()}
        logging.info(f"Loaded currency rates for {year}")
        logging.debug("Currency rates:\n%s", pformat(currency_rates, indent=4))
        return currency_rates
    except FileNotFoundError:
        logging.info(f"Currency rates file input_currency_rates_{year}.json not found")
        return {}
    except json.JSONDecodeError:
        logging.error(f"Invalid JSON in input_currency_rates_{year}.json")
        sys.exit(1)

def save_stocks_data(year, stocks_data):
    """Save the stocks data to a JSON file.

    Args:
        year: The year to save the stocks data for
    """
    # Filter out stocks with quantity 0
    filtered_stocks_data = {symbol: data for symbol, data in stocks_data.items() if data['quantity'] != 0}
    with open(f'{OUTPUT_DIR}output_portfolio_{year}.json', 'w') as file:
        json.dump(filtered_stocks_data, file, indent=4)
    logging.info(f"Saved portfolio data for {year}")

def save_statistics_data(year, statistics_data):
    """Save the statistics data to a CSV file.

    Args:
        year: The year to save the statistics data for
    """
    logging.debug("Saving statistics data: %s", statistics_data)
    with open(f'{OUTPUT_DIR}output_statistics_{year}.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Date', 'Symbol', 'Profit/Loss'])
        writer.writerows(statistics_data)
    logging.info(f"Saved statistics data for {year}")

def process_transactions(filename_ibkr, filename_bitstamp, year, stocks_data, k4_data, currency_rates, statistics_data):
    """Process the input file and generate tax reports.

    Args:
        filename: Path to the input CSV file
    """
    trades, currency_rates_csv = read_csv_ibkr(filename_ibkr)

    # Read Bitstamp trades
    trades_bitstamp = []
    if filename_bitstamp:
        trades_bitstamp = read_csv_bitstamp(filename_bitstamp)

    # Combine trades from both sources
    trades.extend(trades_bitstamp)

    # Create a sorting key function that puts forex trades before stock trades on the same date
    # and puts BUY entries before SELL entries for options
    def sort_key_combined(trade):
        date = trade['DateTime'].split(';')[0]
        is_forex = 1 if '.' in trade['Symbol'] else 2
        if ' ' in trade['Symbol'] and any(c.isdigit() for c in trade['Symbol']):
            # For options, multiply the trade price by 100 as the quantity is in lots
            trade['TradePrice'] = float(trade['TradePrice']) * 100
            return (trade['Symbol'], 1 if trade['Buy/Sell'] == 'BUY' else 2)
        else:
            return (date, is_forex, 3)

    process_currency_rates(currency_rates_csv, currency_rates, year)

    # Combine and sort trades
    sorted_trades = sorted(trades, key=sort_key_combined)
    processed_data = process_trading_data(sorted_trades, stocks_data, k4_data, currency_rates, statistics_data)

    return post_process_trading_data(processed_data)
