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
from datetime import datetime
from pprint import pformat
from .sru import CURRENCY_CODES, OUTPUT_DIR

# Base currency for all calculations
BASE_CURRENCY = "SEK"

SUPPORTED_CURRENCIES = ["USD", "EUR", "DKK" ]

def update_statistics_data(statistics_data, date, symbol, description, initial_quantity, delta, profit_loss, profit_loss_percentage, entry_date):
    # Statistics data is a list of tuples with date, symbol, and profit/loss
    tuple = (date, symbol, description, initial_quantity, delta, profit_loss, profit_loss_percentage, entry_date)
    statistics_data.append(tuple)

def get_currency_rate(date, currency, currency_rates):
    """Get the currency rate for a given date and currency.

    Args:
        date: Date in 'YYYYMMDD;HHMMSS' format
        currency: Currency symbol (e.g., 'USD')
        currency_rates: Dictionary of currency rates

    Returns:
        float: Currency rate for the given date and currency
    """
    short_date = date.split(';')[0]  # Ensure date is in the correct format
    key = (short_date, currency)
    if key in currency_rates:
        return currency_rates[key]
    else:
        logging.error("Currency rate not found for %s on %s", currency, short_date)
        sys.exit(1)

def process_k4_entry(symbol, description, quantity, trade_price, commission, avg_price, currency, date, k4_data, currency_rates, statistics_data, initial_quantity, entry_date):
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
    logging.info("    ==> Processing k4 entry: %s (%s), %s, %s, %s, %s, %s, %s, %s", symbol, description, quantity, trade_price, commission, avg_price, currency, date, entry_date)
    if currency == BASE_CURRENCY:
        if symbol not in k4_data:
            k4_data[symbol] = {
                'beteckning': symbol,
                'beskrivning': description,
                'antal': -quantity,
                'forsaljningspris': -quantity * trade_price - commission,
                'omkostnadsbelopp': -quantity * avg_price
            }
            profit_loss = (-quantity * trade_price - commission) - (-quantity * avg_price)
            profit_loss_percentage = (profit_loss / (-quantity * avg_price)) * 100 if (-quantity * avg_price) != 0 else 0
            update_statistics_data(statistics_data, date, symbol, description, initial_quantity, quantity, profit_loss, profit_loss_percentage, entry_date)
        else:
            k4_data[symbol]['antal'] += -quantity
            k4_data[symbol]['forsaljningspris'] += -quantity * trade_price - commission
            k4_data[symbol]['omkostnadsbelopp'] += -quantity * avg_price
            profit_loss = (-quantity * trade_price - commission) - (-quantity * avg_price)
            profit_loss_percentage = (profit_loss / (-quantity * avg_price)) * 100 if (-quantity * avg_price) != 0 else 0
            update_statistics_data(statistics_data, date, symbol, description, initial_quantity, quantity, profit_loss, profit_loss_percentage, entry_date)

        logging.info("    ==> K4 Tax event - Profit/Loss: %.2f (%.2f%%)", profit_loss, profit_loss_percentage)
    else:
        currency_rate = get_currency_rate(date, currency, currency_rates)
        if symbol not in k4_data:
            k4_data[symbol] = {
                'beteckning': symbol,
                'beskrivning': description,
                'antal': -quantity,
                'forsaljningspris': (-quantity * trade_price - commission) * currency_rate,
                'omkostnadsbelopp': (-quantity * avg_price)
            }
            profit_loss = (-quantity * trade_price - commission) * currency_rate - (-quantity * avg_price)
            profit_loss_percentage = (profit_loss / (-quantity * avg_price)) * 100 if (-quantity * avg_price) != 0 else 0
            update_statistics_data(statistics_data, date, symbol, description, initial_quantity, quantity, profit_loss, profit_loss_percentage, entry_date)
        else:
            k4_data[symbol]['antal'] += -quantity
            k4_data[symbol]['forsaljningspris'] += (-quantity * trade_price - commission) * currency_rate
            k4_data[symbol]['omkostnadsbelopp'] += (-quantity * avg_price)
            profit_loss = (-quantity * trade_price - commission) * currency_rate - (-quantity * avg_price)
            profit_loss_percentage = (profit_loss / (-quantity * avg_price)) * 100 if (-quantity * avg_price) != 0 else 0
            update_statistics_data(statistics_data, date, symbol, description, initial_quantity, quantity, profit_loss, profit_loss_percentage, entry_date)

        logging.info("    ==> K4 Tax event - Profit/Loss: %.2f (%.2f%%)", profit_loss, profit_loss_percentage)

def process_currency_buy(currency, amount, currency_rate, stocks_data, date):
    """Process a currency transaction.

    Args:
        currency: Currency symbol (e.g., 'USD')
        amount: Amount of currency bought
        currency_rate: Exchange rate to SEK
    """
    logging.debug("      buying %s %s, %s/SEK = %s, %s", -amount, currency, currency, currency_rate, date)
    if currency not in stocks_data:
        stocks_data[currency] = {
            'entry_date': date,
            'quantity': -amount,
            'totalprice': -amount * currency_rate,
            'avgprice': currency_rate
        }
    # This function is never called with a positive amount that would change a negative quantity to positive.
    # Thus, we only handle the cases where the quantity is positive and stays positive or zero, or where the
    # quantity is negative and stays negative or zero.
    elif stocks_data[currency]['quantity'] >= 0:
        stocks_data[currency]['quantity'] += -amount
        stocks_data[currency]['totalprice'] += -amount * currency_rate
        stocks_data[currency]['avgprice'] = stocks_data[currency]['totalprice'] / stocks_data[currency]['quantity']
    else:
        # Deferred tax event, margin account
        logging.warning("      paying back %s %s, of total margin loan %s ", -amount, currency, stocks_data[currency]['quantity'])
        stocks_data[currency]['quantity'] += -amount
        stocks_data[currency]['totalprice'] += -amount * stocks_data[currency]['avgprice']
        # Position closed, set average price to zero
        if stocks_data[currency]['quantity'] == 0:
            stocks_data[currency]['avgprice'] = 0.0


def process_currency_sell(currency, amount, currency_rate, stocks_data, date):
    """Process a currency transaction.

    Args:
        currency: Currency symbol (e.g., 'USD')
        amount: Amount of currency bought
        currency_rate: Exchange rate to SEK
    """
    if currency not in stocks_data:
        logging.warning("Initial short selling of entry %s", currency)
        stocks_data[currency] = {
            'entry_date': date,
            'quantity': 0,
            'totalprice': 0,
            'avgprice': 0
        }

    if stocks_data[currency]['quantity'] > 0:
        logging.debug("      selling %s %s, %s/SEK = %s, %s", -amount, currency, currency, stocks_data[currency]['avgprice'], date)
        stocks_data[currency]['quantity'] += -amount
        stocks_data[currency]['totalprice'] += -amount * stocks_data[currency]['avgprice']
    else:
        logging.debug("      added margin loan %s %s, %s/SEK = %s, %s", -amount, currency, currency, currency_rate, date)
        # Update averge price on margin loan
        stocks_data[currency]['quantity'] += -amount
        stocks_data[currency]['totalprice'] += -amount * currency_rate
        stocks_data[currency]['avgprice'] = stocks_data[currency]['totalprice'] / stocks_data[currency]['quantity']

def print_balances(stocks_data):
    for currency in SUPPORTED_CURRENCIES:
        if currency in stocks_data:
            liquidity = stocks_data[currency]['quantity']
            avgprice = stocks_data[currency]['avgprice']
            if currency == 'USD' or (currency != 'USD' and liquidity != 0):
                logging.debug("   Balance (%s): %.2f -- %s/SEK: %.2f", currency, liquidity, currency, avgprice)

def usd_statistics_add(stocks_data, base, total):
    if base not in ['USD', 'EUR', 'DKK']: # No statistics for these currencies
        if 'totalpriceusd' in stocks_data[base]:
            stocks_data[base]['totalpriceusd'] += total
            stocks_data[base]['avgpriceusd'] = stocks_data[base]['totalpriceusd'] / stocks_data[base]['quantity']

def usd_statistics_first_buy(stocks_data, base, total):
    if base not in ['USD', 'EUR', 'DKK']: # No statistics for these currencies
        stocks_data[base]['totalpriceusd'] = total
        stocks_data[base]['avgpriceusd'] = stocks_data[base]['totalpriceusd'] / stocks_data[base]['quantity']

def usd_statistics_zero(stocks_data, base):
    if base not in ['USD', 'EUR', 'DKK']:
        stocks_data[base]['totalpriceusd'] = 0
        stocks_data[base]['avgpriceusd'] = 0

def usd_statistics_update_total_avg(stocks_data, base, total, average):
    if base not in ['USD', 'EUR', 'DKK']: # No statistics for these currencies
        stocks_data[base]['totalpriceusd'] = total
        stocks_data[base]['avgpriceusd'] = average

def process_buy_entry(symbol, description, quantity, trade_price, commission, currency, date, stocks_data, k4_data, currency_rates, statistics_data):
    """Process a buy transaction.

    Args:
        symbol: Stock symbol
        quantity: Number of shares bought
        trade_price: Price per share
        commission: Trading commission
        currency: Currency of the transaction
        date: Date of the transaction
    """
    logging.debug("Processing buy entry: %s (%s), %s, %s, %s, %s, %s", symbol, description, quantity, trade_price, commission, currency, date)

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
            # First buy entry for this stock
            logging.debug("      first buy entry for %s", base)
            stocks_data[base] = {
                'entry_date': date,
                'quantity': quantity,
                'totalprice': quantity * trade_price + commission
            }
            stocks_data[base]['avgprice'] = stocks_data[base]['totalprice'] / stocks_data[base]['quantity']
        elif stocks_data[base]['quantity'] >= 0:
            # Normal case, long position
            stocks_data[base]['quantity'] += quantity
            stocks_data[base]['totalprice'] += quantity * trade_price + commission
            stocks_data[base]['avgprice'] = stocks_data[base]['totalprice'] / stocks_data[base]['quantity']
        elif stocks_data[base]['quantity'] + quantity >= 0:
            # Cover margin loan with new buy entry
            logging.debug("      buying (covering) %s %s, total margin loan %s ", quantity, base, stocks_data[base]['quantity'])
            credit = stocks_data[base]['quantity']  # negative value
            surplus = credit + quantity
            # Since the transaction includes both a covering of a short and the opening of a long position, and only one commission applies,
            # the commission needs to be allocated proportionally to the covering and the long position.
            commission_per_share = commission / quantity
            unit_price = trade_price + commission_per_share

            # TODO: might need an if else to handle currency and stock commissions separately
            entry_date = stocks_data[base]['entry_date'] if 'entry_date' in stocks_data[base] else date
            process_k4_entry(
                symbol=base,
                description=description,
                quantity= credit,
                trade_price=stocks_data[base]['avgprice'],
                commission=0,
                avg_price=unit_price,
                currency=BASE_CURRENCY,
                date=date,
                k4_data=k4_data,
                currency_rates=currency_rates,
                statistics_data=statistics_data,
                initial_quantity=stocks_data[base]['quantity'],
                entry_date=entry_date
            )
            stocks_data[base]['quantity'] = surplus
            if surplus == 0:
                stocks_data[base]['totalprice'] = 0
                stocks_data[base]['avgprice'] = 0
                # Delete entry_date from stocks_data
                if 'entry_date' in stocks_data[base]:
                    del stocks_data[base]['entry_date']
            else:
                stocks_data[base]['totalprice'] = surplus * unit_price
                stocks_data[base]['avgprice'] = unit_price
        else:
            # Cover part of margin loan with new buy entry
            logging.debug("      buying (covering partial) %s %s, total margin loan %s ", quantity, base, stocks_data[base]['quantity'])
            commission_per_share = commission / quantity
            unit_price = trade_price + commission_per_share
            entry_date = stocks_data[base]['entry_date'] if 'entry_date' in stocks_data[base] else date
            process_k4_entry(
                symbol=base,
                description=description,
                quantity= -quantity,
                trade_price=stocks_data[base]['avgprice'],
                commission=0, # Added to unit_price
                avg_price=unit_price,
                currency=BASE_CURRENCY,
                date=date,
                k4_data=k4_data,
                currency_rates=currency_rates,
                statistics_data=statistics_data,
                initial_quantity=stocks_data[base]['quantity'],
                entry_date=entry_date
            )
            stocks_data[base]['quantity'] += quantity
            stocks_data[base]['totalprice'] += quantity * stocks_data[base]['avgprice']

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

        currency_rate = get_currency_rate(date, currency, currency_rates)
        logging.debug(f"   Action (1/2): Sell {currency} for {BASE_CURRENCY}")

        if currency not in stocks_data:
            logging.debug("      first sell entry for %s", base)
            stocks_data[currency] = {
                'entry_date': date,
                'quantity': 0,
                'totalprice': 0,
                'avgprice': 0
            }

        if stocks_data[currency]['quantity'] - (quantity * trade_price + commission) >= 0:
            # Sell currency e.g. USD
            entry_date = stocks_data[currency]['entry_date'] if 'entry_date' in stocks_data[currency] else date
            process_k4_entry(
                symbol=currency,
                description=currency,
                quantity= -(quantity*trade_price+commission),
                trade_price=currency_rate,
                commission=0, # FOREX fee for automatic currency exchange included in IBCommission
                avg_price=stocks_data[currency]['avgprice'],
                currency=BASE_CURRENCY,
                date=date,
                k4_data=k4_data,
                currency_rates=currency_rates,
                statistics_data=statistics_data,
                initial_quantity=stocks_data[currency]['quantity'],
                entry_date=entry_date
            )
            process_currency_sell(currency, quantity*trade_price+commission, currency_rate, stocks_data, date)
        elif stocks_data[currency]['quantity'] >= 0:
            logging.warning("      (margin loan new) selling %s %s, but only %s available ", quantity*trade_price+commission, currency, stocks_data[currency]['quantity'])
            # Sell currency e.g. USD
            total_balance = stocks_data[currency]['quantity']
            credit = (quantity * trade_price + commission) - total_balance
            if total_balance > 0:
                process_currency_sell(currency, total_balance, currency_rate, stocks_data, date)
                entry_date = stocks_data[currency]['entry_date'] if 'entry_date' in stocks_data[currency] else date
                process_k4_entry(
                    symbol=currency,
                    description=currency,
                    quantity= -total_balance,
                    trade_price=currency_rate,
                    commission=0, # FOREX fee for automatic currency exchange included in IBCommission
                    avg_price=stocks_data[currency]['avgprice'],
                    currency=BASE_CURRENCY,
                    date=date,
                    k4_data=k4_data,
                    currency_rates=currency_rates,
                    statistics_data=statistics_data,
                    initial_quantity=stocks_data[currency]['quantity'],
                    entry_date=entry_date
                )
            # Split the sell processing into two parts, first update the stocks_data with the total balance
            # and then process the credit amount separately.
            # This is to handle the case where the total balance is less than the amount to be sold.
            process_currency_sell(currency, credit, currency_rate, stocks_data, date)
        else:
            logging.warning("      (margin loan add) new margin loan %s %s, added to existing loan %s ", quantity*trade_price+commission, currency, stocks_data[currency]['quantity'])
            process_currency_sell(currency, quantity * trade_price + commission, currency_rate, stocks_data, date)


        logging.debug(f"   Action (2/2): Buy {base} for {quote}")

        if base not in stocks_data:
            logging.debug("      first buy entry for %s", base)
            stocks_data[base] = {
                'entry_date': date,
                'quantity': quantity,
                'totalprice': (quantity * trade_price + commission) * currency_rate
            }
            stocks_data[base]['avgprice'] = stocks_data[base]['totalprice'] / stocks_data[base]['quantity']
            usd_statistics_first_buy(stocks_data, base, (quantity * trade_price + commission))
        elif stocks_data[base]['quantity'] >= 0:
            stocks_data[base]['quantity'] += quantity
            stocks_data[base]['totalprice'] += (quantity * trade_price + commission) * currency_rate
            stocks_data[base]['avgprice'] = stocks_data[base]['totalprice'] / stocks_data[base]['quantity']
            usd_statistics_add(stocks_data, base, (quantity * trade_price + commission))
        elif stocks_data[base]['quantity'] + quantity >= 0:
            # Cover margin loan with new buy entry
            logging.debug("      buying (covering) %s %s, total margin loan %s ", quantity, base, stocks_data[base]['quantity'])
            credit = stocks_data[base]['quantity'] # negative value
            surplus = credit + quantity
            # Since the transaction includes both a covering of a short and the opening of a long position, and only one commission applies,
            # the commission needs to be allocated proportionally to the covering and the long position.
            commission_per_share = commission / quantity # negative quantity for sell
            unit_price = (trade_price + commission_per_share) * currency_rate
            entry_date = stocks_data[base]['entry_date'] if 'entry_date' in stocks_data[base] else date
            process_k4_entry(
                symbol=base,
                description=description,
                quantity= credit,
                trade_price=stocks_data[base]['avgprice'],
                commission=0,
                avg_price=unit_price,
                currency=BASE_CURRENCY,
                date=date,
                k4_data=k4_data,
                currency_rates=currency_rates,
                statistics_data=statistics_data,
                initial_quantity=stocks_data[base]['quantity'],
                entry_date=entry_date
            )
            stocks_data[base]['quantity'] = surplus
            if surplus == 0:
                stocks_data[base]['totalprice'] = 0
                stocks_data[base]['avgprice'] = 0
                # Delete entry_date from stocks_data
                if 'entry_date' in stocks_data[base]:
                    del stocks_data[base]['entry_date']
                usd_statistics_zero(stocks_data, base)
            else:
                stocks_data[base]['totalprice'] = surplus * unit_price
                stocks_data[base]['avgprice'] = unit_price
                usd_statistics_update_total_avg(stocks_data, base, surplus * (trade_price + commission_per_share), trade_price + commission_per_share)
        else:
            # Cover part of margin loan with new buy entry
            logging.debug("      buying (covering partial) %s %s, total margin loan %s ", quantity, base, stocks_data[base]['quantity'])
            commission_per_share = commission / quantity
            unit_price = (trade_price + commission_per_share) * currency_rate
            entry_date = stocks_data[base]['entry_date'] if 'entry_date' in stocks_data[base] else date
            process_k4_entry(
                symbol=base,
                description=description,
                quantity= -quantity,
                trade_price=stocks_data[base]['avgprice'],
                commission=0, # Added to unit_price
                avg_price=unit_price,
                currency=BASE_CURRENCY,
                date=date,
                k4_data=k4_data,
                currency_rates=currency_rates,
                statistics_data=statistics_data,
                initial_quantity=stocks_data[base]['quantity'],
                entry_date=entry_date
            )
            stocks_data[base]['quantity'] += quantity
            stocks_data[base]['totalprice'] += quantity * stocks_data[base]['avgprice']
            usd_statistics_sell(stocks_data, base, quantity)


    logging.debug("   Buy entry processed for %s [currency: %s]", symbol, currency)
    logging.debug("   Updated stock data for %s: %s", base, stocks_data[base])
    print_balances(stocks_data)

def usd_statistics_sell(stocks_data, base, quantity):
    if base not in ['USD', 'EUR', 'DKK']: # No statistics for these currencies
        if 'totalpriceusd' in stocks_data[base]:
            stocks_data[base]['totalpriceusd'] += quantity * stocks_data[base]['avgpriceusd']

def usd_statistics_short_sell(stocks_data, base, total):
    if base not in ['USD', 'EUR', 'DKK']: # No statistics for these currencies
        if 'totalpriceusd' in stocks_data[base]:
            stocks_data[base]['totalpriceusd'] += total
            stocks_data[base]['avgpriceusd'] = stocks_data[base]['totalpriceusd'] / stocks_data[base]['quantity']

def process_sell_entry(symbol, description, quantity, trade_price, commission, currency, date, stocks_data, k4_data, currency_rates, statistics_data):
    """Process a sell transaction.

    Args:
        symbol: Stock symbol
        quantity: Number of shares sold
        trade_price: Price per share
        commission: Trading commission
        currency: Currency of the transaction
        date: Date of the transaction
    """
    logging.debug("Processing sell entry: %s (%s), %s, %s, %s, %s, %s", symbol, description, quantity, trade_price, commission, currency, date)
    if '.' in symbol:
        base = symbol.split('.')[0]
        quote = symbol.split('.')[1]
    else:
        base = symbol
        quote = BASE_CURRENCY
    #logging.debug(f'   Split symbol into base: {base} and quote: {quote}')
    if base not in stocks_data:
        logging.warning(f"    First sell entry for {base}, initializing stocks_data")
        stocks_data[base] = {
            'quantity': 0,
            'totalprice': 0,
            'avgprice': 0
        }

    if currency == BASE_CURRENCY:
        # UC-5. Sell stock in base currency e.g. sell ERIC-B for SEK
        #       Transactions: Sell ERIC-B
        # UC-6. Sell currency pair where quote currency is SEK e.g. USD/SEK
        #       Transactions: Sell USD

        logging.debug(f"   Action (1/1): Sell {base} for {quote}")
        if stocks_data[base]['quantity'] + quantity >= 0:
            # Normal case, selling shares from long position
            entry_date = stocks_data[base]['entry_date'] if 'entry_date' in stocks_data[base] else date
            process_k4_entry(
                symbol=base,
                description=description,
                quantity=quantity,
                trade_price=trade_price,
                commission=commission,
                avg_price=stocks_data[base]['avgprice'],
                currency=currency,
                date=date,
                k4_data=k4_data,
                currency_rates=currency_rates,
                statistics_data=statistics_data,
                initial_quantity=stocks_data[base]['quantity'],
                entry_date=entry_date
            )
            stocks_data[base]['quantity'] += quantity
            if stocks_data[base]['quantity'] == 0:
                stocks_data[base]['totalprice'] = 0
                stocks_data[base]['avgprice'] = 0
                # Delete entry_date from stocks_data
                if 'entry_date' in stocks_data[base]:
                    del stocks_data[base]['entry_date']
            else:
                stocks_data[base]['totalprice'] += quantity * stocks_data[base]['avgprice'] #+ commission

        elif stocks_data[base]['quantity'] > 0:
            # New margin loan, selling more shares than available
            logging.warning("      (new margin loan) selling %s %s, but only %s available ", -quantity, base, stocks_data[base]['quantity'])
            total_balance = stocks_data[base]['quantity']
            credit = total_balance + quantity
            # Since the transaction includes both a realized sale and the opening of a short position, and only one commission applies,
            # the commission needs to be allocated proportionally to the sale and the short position.
            commission_per_share = commission / -quantity # negative quantity for sell
            unit_price = trade_price - commission_per_share
            entry_date = stocks_data[base]['entry_date'] if 'entry_date' in stocks_data[base] else date
            process_k4_entry(
                symbol=base,
                description=description,
                quantity= -total_balance,
                trade_price=unit_price,
                commission=0,
                avg_price=stocks_data[base]['avgprice'],
                currency=currency,
                date=date,
                k4_data=k4_data,
                currency_rates=currency_rates,
                statistics_data=statistics_data,
                initial_quantity=stocks_data[base]['quantity'],
                entry_date=entry_date
            )
            # Credit cannot be negative at this point, so we don't need to check for that.
            stocks_data[base]['quantity'] = credit
            stocks_data[base]['totalprice'] = credit * unit_price
            stocks_data[base]['avgprice'] = unit_price
        else:
            # Add to margin loan, selling more shares than available
            logging.debug("      (margin loan add) new margin loan %s %s, added to existing loan %s ", -quantity, base, stocks_data[base]['quantity'])
            stocks_data[base]['quantity'] += quantity
            stocks_data[base]['totalprice'] += quantity * trade_price + commission
            stocks_data[base]['avgprice'] = stocks_data[base]['totalprice'] / stocks_data[base]['quantity']

    else:
        # UC-7. Sell stock in foreign currency e.g. sell AAOI for USD
        #       Transactions: Sell AAOI, Buy USD
        # UC-8. Sell currency pair where quote currency in not SEK e.g. EUR/USD for USD
        #       Transactions: Sell EUR, Buy USD

        currency_rate = get_currency_rate(date, currency, currency_rates)
        logging.debug(f"   Action (1/2): Buy {currency} for {quote}")
        if currency not in stocks_data:
            logging.debug("      first buy entry for %s", base)
            stocks_data[currency] = {
                'quantity': 0,
                'totalprice': 0,
                'avgprice': 0
            }
            usd_statistics_zero(stocks_data, currency)

        if stocks_data[currency]['quantity'] >= 0:
            # Quantity is negative for sell entries, commission is turned positive in process_input_data.
            # Total amount of currency received is quantity * trade_price + commission e.g. -10 * 10 + 1 = -99
            process_currency_buy(currency, quantity * trade_price + commission, currency_rate, stocks_data, date)
        elif stocks_data[currency]['quantity'] + (-quantity * trade_price - commission) >= 0:
            logging.debug("      paying back %s %s, of total margin loan %s %s", -(quantity * trade_price + commission), currency, stocks_data[currency]['quantity'], currency)
            credit = stocks_data[currency]['quantity'] # negative value
            surplus = credit + -(quantity * trade_price + commission)
            entry_date = stocks_data[currency]['entry_date'] if 'entry_date' in stocks_data[currency] else date
            process_k4_entry(
                symbol=currency,
                description=currency,
                quantity=credit,
                trade_price=stocks_data[currency]['avgprice'], # When covering the sell price is the average price
                commission=0, # FOREX fee for automatic currency exchange included in IBCommission
                avg_price=currency_rate, # When covering the average price is the currency rate
                currency=BASE_CURRENCY,
                date=date,
                k4_data=k4_data,
                currency_rates=currency_rates,
                statistics_data=statistics_data,
                initial_quantity=stocks_data[currency]['quantity'],
                entry_date=entry_date
            )
            process_currency_buy(currency, credit, currency_rate, stocks_data, date)
            # Function expects a negative amount to be processed
            process_currency_buy(currency, -surplus, currency_rate, stocks_data, date)
        else:
            logging.debug("      covering (partial) %s %s, of total margin loan %s %s", -(quantity * trade_price + commission), currency, stocks_data[currency]['quantity'], currency)
            cover_amount = (quantity * trade_price + commission) # Keep the amount negative for processing
            entry_date = stocks_data[currency]['entry_date'] if 'entry_date' in stocks_data[currency] else date
            process_k4_entry(
                symbol=currency,
                description=currency,
                quantity=cover_amount,
                trade_price=stocks_data[currency]['avgprice'], # When covering the sell price is the average price
                commission=0, # FOREX fee for automatic currency exchange included in IBCommission
                avg_price=currency_rate, # When covering the average price is the currency rate
                currency=BASE_CURRENCY,
                date=date,
                k4_data=k4_data,
                currency_rates=currency_rates,
                statistics_data=statistics_data,
                initial_quantity=stocks_data[currency]['quantity'],
                entry_date=entry_date
            )
            # Function expects a negative amount to be processed
            process_currency_buy(currency, quantity * trade_price + commission, currency_rate, stocks_data, date)

        logging.debug(f"   Action (2/2): Sell {base} for {quote}")

        if stocks_data[base]['quantity'] + quantity >= 0:
            # Normal case, selling shares from long position
            entry_date = stocks_data[base]['entry_date'] if 'entry_date' in stocks_data[base] else date
            process_k4_entry(
                symbol=base,
                description=description,
                quantity=quantity,
                trade_price=trade_price,
                commission=commission,
                avg_price=stocks_data[base]['avgprice'],
                currency=currency,
                date=date,
                k4_data=k4_data,
                currency_rates=currency_rates,
                statistics_data=statistics_data,
                initial_quantity=stocks_data[base]['quantity'],
                entry_date=entry_date
            )
            stocks_data[base]['quantity'] += quantity
            if stocks_data[base]['quantity'] == 0:
                stocks_data[base]['totalprice'] = 0
                stocks_data[base]['avgprice'] = 0
                # Delete entry_date from stocks_data
                if 'entry_date' in stocks_data[base]:
                    del stocks_data[base]['entry_date']
                usd_statistics_zero(stocks_data, base)
            else:
                stocks_data[base]['totalprice'] += quantity * stocks_data[base]['avgprice'] #+ (commission * currency_rate)
                usd_statistics_sell(stocks_data, base, quantity)
        elif stocks_data[base]['quantity'] > 0:
            # New margin loan, selling more shares than available
            logging.warning("      (new margin loan) selling %s %s, but only %s available ", -quantity, base, stocks_data[base]['quantity'])
            total_balance = stocks_data[base]['quantity']
            credit = total_balance + quantity
            # Since the transaction includes both a realized sale and the opening of a short position, and only one commission applies,
            # the commission needs to be allocated proportionally to the sale and the short position.
            commission_per_share = commission / -quantity # negative quantity for sell
            unit_price = trade_price - commission_per_share
            entry_date = stocks_data[base]['entry_date'] if 'entry_date' in stocks_data[base] else date
            process_k4_entry(
                symbol=base,
                description=description,
                quantity= -total_balance,
                trade_price=unit_price,
                commission=0, # Commission in included in the trade price TODO: Does this function need a commission?
                avg_price=stocks_data[base]['avgprice'],
                currency=currency,
                date=date,
                k4_data=k4_data,
                currency_rates=currency_rates,
                statistics_data=statistics_data,
                initial_quantity=stocks_data[base]['quantity'],
                entry_date=entry_date
            )
            stocks_data[base]['quantity'] = credit
            stocks_data[base]['totalprice'] = credit * unit_price * currency_rate
            stocks_data[base]['avgprice'] = unit_price * currency_rate
            usd_statistics_update_total_avg(stocks_data, base, credit * unit_price, unit_price)
        else:
            # Add to margin loan, selling more shares than available
            logging.debug("      (margin loan add) new margin loan %s %s, added to existing loan %s ", -quantity, base, stocks_data[base]['quantity'])
            stocks_data[base]['quantity'] += quantity
            stocks_data[base]['totalprice'] += (quantity * trade_price + commission) * currency_rate
            stocks_data[base]['avgprice'] = stocks_data[base]['totalprice'] / stocks_data[base]['quantity']
            usd_statistics_short_sell(stocks_data, base, (quantity * trade_price + commission))

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

    if 0 < abs(stocks_data[base]['quantity']) < 0.0001:  # handle float error with fractional shares
        logging.debug("   Rounding error when processing %s, quantity: %s", base, stocks_data[base]['quantity'])
        stocks_data[base]['quantity'] = 0
        stocks_data[base]['avgprice'] = 0
        # Delete entry_date from stocks_data
        if 'entry_date' in stocks_data[base]:
            del stocks_data[base]['entry_date']
        if 0 < abs(stocks_data[base]['totalprice']) < 0.0001:
            logging.debug("   Rounding error when processing %s, totalprice: %s", base, stocks_data[base]['totalprice'])
            stocks_data[base]['totalprice'] = 0
            usd_statistics_zero(stocks_data, base)
        #else:
        #    logging.error("Sell entry processed for %s with fractional shares, totalprice not zero: %s", base, stocks_data[base]['totalprice'])

    logging.debug("   Sell entry processed for %s [currency: %s]", symbol, currency)
    logging.debug("   Updated stock data for %s: %s", base, stocks_data[base])
    print_balances(stocks_data)

def process_input_data(data, stocks_data, k4_data, currency_rates, statistics_data):
    for entry in data:
        date = entry['DateTime']
        symbol = entry['Symbol']
        description = entry['Description']
        quantity = float(entry['Quantity'])
        trade_price = float(entry['TradePrice'])
        commission = -float(entry['IBCommission']) # Input is negative in IBKR CSV file
        currency = entry['CurrencyPrimary']

        if entry['Buy/Sell'] == 'BUY':
            process_buy_entry(symbol, description, quantity, trade_price, commission, currency, date, stocks_data, k4_data, currency_rates, statistics_data)
        elif entry['Buy/Sell'] == 'SELL':
            process_sell_entry(symbol, description, quantity, trade_price, commission, currency, date, stocks_data, k4_data, currency_rates, statistics_data)

def process_trading_data(data, stocks_data, k4_data, currency_rates, statistics_data):
    """Process the trading data for K4 tax reporting.
    """
    process_input_data(data, stocks_data, k4_data, currency_rates, statistics_data)

    logging.debug("Final K4 data:\n%s", pformat(k4_data, indent=4))
    logging.debug("Final stocks data:\n%s", pformat(stocks_data, indent=4))

    output = sorted(k4_data.values(), key=lambda x: x['beteckning'])
    return output

def verify_input_fields(required_fields, data):
    """Verify the input fields in the transaction data.

    Args:
        required_fields: List of required fields that should be present in each transaction entry
        data: List of dictionaries containing transaction data

    Returns:
        bool: True if the data is valid, False otherwise
    """
    for entry in data:
        missing = [field for field in required_fields if field not in entry]
        if missing:
            logging.error("Missing required fields in entry: %s", entry)
            logging.error("Missing fields: %s", missing)
            return False
    return True

def verify_input_data(lines):
    """Verify the input data for Interactive Brokers transactions.

    Args:
        data: List of dictionaries containing transaction data

    Returns:
        bool: True if the data is valid, False otherwise
    """

    # Find where the currency rates section starts
    try:
        # Find the index where the currency rates section starts
        # This is determined by the first line that has fewer fields than the first line
        # of the trades section, which is assumed to be the longest line.
        split_index = next(i for i, line in enumerate(lines) if len(line.strip().split(',')) < len(lines[0].strip().split(',')))
    except StopIteration:
        logging.error("No currency rates section found in the input data.")
        sys.exit(1)

    # Read trades
    trades_reader = list(csv.DictReader(lines[:split_index]))

    # Mandatory fields in the IBKR CSV file:
    # "DateTime","Symbol","Buy/Sell","Quantity","TradePrice","IBCommission","CurrencyPrimary","Description","ISIN","Exchange"
    # Not used fields: "ISIN", "Exchange"
    required_fields = ['DateTime', 'Symbol', 'Buy/Sell', 'Quantity', 'TradePrice', 'IBCommission', 'CurrencyPrimary', 'Description', 'ISIN', 'Exchange']
    if not verify_input_fields(required_fields, trades_reader):
        logging.error("Trade data verification failed.")
        sys.exit(1)

    # Read currency rates
    rates_reader = list(csv.DictReader(lines[split_index:]))

    # Mandatory fields in the currency rates section:
    # "Date/Time","FromCurrency","ToCurrency","Rate"
    required_fields_rates = ['Date/Time', 'FromCurrency', 'ToCurrency', 'Rate']
    if not verify_input_fields(required_fields_rates, rates_reader):
        logging.error("Currency rates data verification failed.")
        sys.exit(1)

    return trades_reader, rates_reader

def read_csv_ibkr(filename):
    """Read CSV file with Interactive Brokers transactions.

    Args:
        filename: Path to the CSV file

    Returns:
        tuple: (stock_trades, forex_trades, currency_rates) where each is a list of dictionaries
    """

    with open(filename, 'r') as csvfile:
        lines = csvfile.readlines()
        trades_reader, rates_reader = verify_input_data(lines)

    logging.info(f"{len(trades_reader)} stock trades and {len(rates_reader)} currency rates have been read from {filename}.")
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
        elif rate['FromCurrency'] == 'DKK':
            date = rate['Date/Time'].split(';')[0]
            key = (date, rate['FromCurrency'])
            currency_rates[key] = float(rate['Rate'])

    for key, value in currency_rates.items():
        if key[1] == 'EUR':
            usdsek = currency_rates[(key[0], 'USD')]
            currency_rates[key] = usdsek * value
        if key[1] == 'DKK':
            usdsek = currency_rates[(key[0], 'USD')]
            currency_rates[key] = usdsek * value

    # Load predefined currency rates and merge with the processed rates above
    currency_rates_init = init_currency_rates(year)

    # Merge the two dictionaries
    for key, value in currency_rates_init.items():
        if key not in currency_rates:
            currency_rates[key] = value

    logging.debug("==> Currency rates:\n%s", pformat(currency_rates, indent=4))

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
        post_processed_data['beskrivning'] = trade['beskrivning']
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

def save_statistics_data(year, journal):
    """Save the statistics data to a CSV file.

    Args:
        year: The year to save the statistics data for
    """
    # Save win rate statistics to a CSV file
    logging.debug("Saving statistics data (%s trades)", len(journal))
    with open(f'{OUTPUT_DIR}trading_statistics_{year}.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Date', 'Symbol', 'Description', 'Profit/Loss', 'Percent', 'Win'])
        for entry in journal:
            writer.writerow([entry['date'], entry['symbol'], entry['description'], entry['profit_loss'], entry['profit_loss_percentage'], entry['win']])

def print_k4_statistics(k4_data):
    """Print the statistics data to the console.

    Args:
        statistics_data: List of statistics data
    """
    logging.info("K4 statistics data:")
    # Print header
    logging.info("=" * 87)
    logging.info(f"{'Symbol':<25} {'Description':<40} {'Profit/Loss (SEK)':>20}")
    logging.info("-" * 87)

    # Print each row, left-align profit/loss
    for transaction in k4_data.values():
        symbol = transaction['beteckning']
        description = transaction['beskrivning']
        profit = transaction['forsaljningspris'] - transaction['omkostnadsbelopp']
        profit_str = f"{profit:.2f}"
        # Print the row with left alignment
        if profit < 0:
            profit_abs = abs(profit)
            profit_negative = f"({profit_abs:.2f})"  # Enclose negative profit/loss in parentheses
            logging.info(f"{symbol:<25} {description:<40} {profit_negative:>20}")
        else:
            # Right-align positive profit/loss
            logging.info(f"{symbol:<25} {description:<40} {profit_str:<20}")

    logging.info("-" * 87)
    # Print total profit/loss
    total_profit = sum(transaction['forsaljningspris'] - transaction['omkostnadsbelopp'] for transaction in k4_data.values())
    total_profit_str = f"{total_profit:.0f}"
    capital_tax = f"{total_profit * 0.3:.0f}"
    logging.info(f"{'Total Capital Income':<65} {total_profit_str:>20}")
    # Tax to be paid
    logging.info(f"{'Tax':<65} {capital_tax:>20}")
    logging.info("=" * 87)

def calculate_profit_loss_percentage(profit_loss_percentage_list):
    """Calculate the average profit/loss percentage from a list of tuples.

    Args:
        profit_loss_percentage_list: List of tuples containing (delta, profit_loss_percentage)
    """
    if not profit_loss_percentage_list:
        return 0.0
    total_delta = sum(delta for delta, _ in profit_loss_percentage_list)
    if total_delta == 0:
        return 0.0
    total_profit_loss_percentage = sum(delta * profit_loss_percentage for delta, profit_loss_percentage in profit_loss_percentage_list)
    return total_profit_loss_percentage / total_delta if total_delta != 0 else 0.0

def print_monthly_tracker(journal):
    """Print the monthly tracker to the console.

    Args:
        journal: List of journal entries
    """
    logging.info("Monthly Tracker:")
    logging.info("=" * 98)
    logging.info(f"{'YYYYMM':<10} {'Avg Gain':>10} {'Avg Loss':>10} {'Win %':>10} {'Trades #':>10} {'LG Gain':>10} {'LG Loss':>10} {'Avg Days G':>10} {'Avg Days L':>10}")
    logging.info("-" * 98)

    # Get a list of months in the journal
    months = sorted(set(entry['date'][:6] for entry in journal))  # YYYY-MM format
    #logging.info("Months in journal: %s", months)
    for month in months:
        month_entries = [entry for entry in journal if entry['date'].startswith(month)]
        total_trades = len(month_entries)
        if total_trades == 0:
            continue
        total_wins = sum(1 for entry in month_entries if entry['win'])
        total_losses = total_trades - total_wins
        win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0.0
        average_gain = sum(entry['profit_loss_percentage'] for entry in month_entries if entry['win']) / total_wins if total_wins > 0 else 0.0
        average_loss = sum(entry['profit_loss_percentage'] for entry in month_entries if not entry['win']) / total_losses if total_losses > 0 else 0.0
        # Largest gain and loss percentage
        largest_gain = max((entry['profit_loss_percentage'] for entry in month_entries if entry['win']), default=0.0)
        largest_loss = min((entry['profit_loss_percentage'] for entry in month_entries if not entry['win']), default=0.0)
        # Calculate average number of days a gain or loss position was held
        average_days_gain = sum(entry['duration'] for entry in month_entries if entry['win']) / total_wins if total_wins > 0 else 0.0
        average_days_loss = sum(entry['duration'] for entry in month_entries if not entry['win']) / total_losses if total_losses > 0 else 0.0

        # Print the monthly statistics
        logging.info(f"{month:<10} {average_gain:>10.2f} {average_loss:>10.2f} {win_rate:>10.2f} {total_trades:>10} {largest_gain:>10.2f} {largest_loss:>10.2f} {average_days_gain:>10.2f} {average_days_loss:>10.2f}")

    logging.info("-" * 98)
    logging.info("")

def print_trading_summary(journal):
    """Print the trading summary to the console.

    Args:
        journal: List of journal entries
    """
    logging.info("Trading Summary:")
    logging.info("=" * 98)
    logging.info(f"{'Metric':<30} {'Value':>15}")
    logging.info("-" * 98)
    total_trades = len(journal)
    total_wins = sum(1 for entry in journal if entry['win'])
    total_losses = total_trades - total_wins
    win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0.0
    average_gain = sum(entry['profit_loss_percentage'] for entry in journal if entry['win']) / total_wins if total_wins > 0 else 0.0
    average_loss = sum(entry['profit_loss_percentage'] for entry in journal if not entry['win']) / total_losses if total_losses > 0 else 0.0
    win_loss_ratio = (average_gain / abs(average_loss)) if average_loss != 0 else float('inf')
    adjusted_win_loss_ratio = average_gain * (win_rate / 100) / (abs(average_loss) * (1 - (win_rate / 100))) if average_loss != 0 and win_rate < 100 else float('inf')
    logging.info(f"{'Winning Percentage':<30} {win_rate:>15.2f}")
    logging.info(f"{'Average Gain':<30} {average_gain:>15.2f}")
    logging.info(f"{'Average Loss':<30} {average_loss:>15.2f}")
    logging.info(f"{'Win/Loss Ratio':<30} {win_loss_ratio:>15.2f}")
    logging.info(f"{'Adj. Win/Loss Ratio':<30} {adjusted_win_loss_ratio:>15.2f}")
    logging.info("-" * 98)
    logging.info("")

def calculate_duration(date, entry_date):
    """Calculate the duration in days between two dates.

    Args:
        date: The date of the transaction
        entry_date: The entry date of the position
    """
    date_obj = datetime.strptime(date.split(';')[0], '%Y%m%d')
    entry_date_obj = datetime.strptime(entry_date.split(';')[0], '%Y%m%d')
    return (date_obj - entry_date_obj).days

def print_win_rate_statistics(statistics_data, year):
    """Print the win rate statistics to the console.

    Args:
        statistics_data: List of statistics data
    """
    journal = []
    positions = {}

    for (date, symbol, description, initial_quantity, delta, profit_loss, profit_loss_percentage, entry_date) in statistics_data:
        # Skip BTC transactions
        if symbol == 'BTC':
            continue
        # Check if the symbol is an options contract
        if ' ' in symbol and any(c.isdigit() for c in symbol):
            continue  # Skip options contracts
        # Skip currencies
        if symbol in ['USD', 'EUR', 'SEK', 'DKK']:
            continue

        if symbol not in positions:
            if (initial_quantity + delta) == 0 and profit_loss < 0:
                duration_days = calculate_duration(date, entry_date)
                journal.append({
                    'date': date,
                    'symbol': symbol,
                    'description': description,
                    'profit_loss': profit_loss,
                    'profit_loss_percentage': profit_loss_percentage,
                    'duration': duration_days,
                    'win': False
                })
            elif (initial_quantity + delta == 0) and profit_loss >= 0:
                duration_days = calculate_duration(date, entry_date)
                journal.append({
                    'date': date,
                    'symbol': symbol,
                    'description': description,
                    'profit_loss': profit_loss,
                    'profit_loss_percentage': profit_loss_percentage,
                    'duration': duration_days,
                    'win': True
                })
            elif (initial_quantity + delta) > 0:
                positions[symbol] = {
                    'profit_loss': profit_loss,
                    'profit_loss_percentage': [(delta, profit_loss_percentage)]
                }
        else:
            if (initial_quantity + delta) == 0 and (positions[symbol]['profit_loss'] + profit_loss) < 0:
                positions[symbol]['profit_loss_percentage'].append((delta, profit_loss_percentage))
                duration_days = calculate_duration(date, entry_date)
                journal.append({
                    'date': date,
                    'symbol': symbol,
                    'description': description,
                    'profit_loss': (positions[symbol]['profit_loss'] + profit_loss),
                    'profit_loss_percentage': calculate_profit_loss_percentage(positions[symbol]['profit_loss_percentage']),
                    'duration': duration_days,
                    'win': False
                })
                del positions[symbol]
            elif (initial_quantity + delta == 0) and  (positions[symbol]['profit_loss'] + profit_loss) >= 0:
                positions[symbol]['profit_loss_percentage'].append((delta, profit_loss_percentage))
                duration_days = calculate_duration(date, entry_date)
                journal.append({
                    'date': date,
                    'symbol': symbol,
                    'description': description,
                    'profit_loss': (positions[symbol]['profit_loss'] + profit_loss),
                    'profit_loss_percentage': calculate_profit_loss_percentage(positions[symbol]['profit_loss_percentage']),
                    'duration': duration_days,
                    'win': True
                })
                del positions[symbol]
            elif (initial_quantity + delta) > 0:
                positions[symbol]['profit_loss'] += profit_loss
                positions[symbol]['profit_loss_percentage'].append((delta, profit_loss_percentage))

    # Print the journal
    logging.info("Win Rate Journal:")
    logging.info("=" * 115)
    logging.info(f"{'Date':<18} {'Symbol':<10} {'Description':<40} {'Profit/Loss (SEK)':>20} {'P/L (%)':>8} {'Day(s)':>8} {'Win':>5}")
    logging.info("-" * 115)
    for entry in journal:
        date = entry['date']
        symbol = entry['symbol']
        description = entry['description']
        profit_loss = entry['profit_loss']
        profit_loss_percentage = entry['profit_loss_percentage']
        duration = entry['duration']
        win = 'Yes' if entry['win'] else 'No'
        if profit_loss < 0:
            profit_loss_str = f"({abs(profit_loss):.2f})"
            profit_loss_percentage_str = f"{profit_loss_percentage:.2f}%"
            logging.info(f"{date:<18} {symbol:<10} {description:<40} {profit_loss_str:>20} {profit_loss_percentage_str:>8} {duration:>8} {win:>5}")
        else:
            profit_loss_str = f"{profit_loss:.2f}"
            profit_loss_percentage_str = f"{profit_loss_percentage:.2f}%"
            logging.info(f"{date:<18} {symbol:<10} {description:<40} {profit_loss_str:<20} {profit_loss_percentage_str:>8} {duration:>8} {win:>5}")
    logging.info("-" * 115)
    # Win rate calculation
    total_trades = len(journal)
    total_wins = sum(1 for entry in journal if entry['win'])
    total_losses = total_trades - total_wins
    win_rate = (total_wins / total_trades * 100)
    # Calculate average gain and the average loss over all trades
    average_gain = sum(entry['profit_loss_percentage'] for entry in journal if entry['win']) / total_wins if total_wins > 0 else 0
    average_loss = sum(entry['profit_loss_percentage'] for entry in journal if not entry['win']) / total_losses if total_losses > 0 else 0

    logging.info(f"Total Trades: {total_trades}, Total Wins: {total_wins}, Win Rate: {win_rate:.2f}%")
    logging.info(f"Average Gain: {average_gain:.2f}%, Average Loss: {average_loss:.2f}%")
    logging.info("=" * 115)
    logging.info("")
    print_monthly_tracker(journal)
    print_trading_summary(journal)
    save_statistics_data(year, journal)

def print_statistics(statistics_data, k4_data, year):
    """Print the statistics data to the console.

    Args:
        statistics_data: List of statistics data
    """
    print_k4_statistics(k4_data)
    print_win_rate_statistics(statistics_data, year)

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
        date = trade['DateTime']
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
