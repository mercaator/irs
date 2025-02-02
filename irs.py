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
    data = read_csv_file(filepath)
    logging.debug("Starting to process parsed CSV data from Interactive Brokers")
    process_trading_data(data)

def process_trading_data(data):
    for entry in data:
        if entry['Buy/Sell'] == 'BUY':
            if entry['Symbol'] not in stocks_data:
                stocks_data[entry['Symbol']] = {
                    'quantity': float(entry['Quantity']),
                    'totalprice': float(entry['Quantity']) * float(entry['TradePrice']) - float(entry['IBCommission'])
                }
                stocks_data[entry['Symbol']]['avgprice'] = stocks_data[entry['Symbol']]['totalprice'] / stocks_data[entry['Symbol']]['quantity']
            else:
                stocks_data[entry['Symbol']]['quantity'] += float(entry['Quantity'])
                stocks_data[entry['Symbol']]['totalprice'] += float(entry['Quantity']) * float(entry['TradePrice']) - float(entry['IBCommission'])
                stocks_data[entry['Symbol']]['avgprice'] = stocks_data[entry['Symbol']]['totalprice'] / stocks_data[entry['Symbol']]['quantity']
            logging.debug("Buy entry: %s", entry)
            logging.debug("Updated stock data: %s", stocks_data[entry['Symbol']])
        elif entry['Buy/Sell'] == 'SELL':
            if entry['Symbol'] not in stocks_data:
                logging.error(f"Error: No BUY entry found for SELL entry {entry['Symbol']}")
                sys.exit(1)
            else:
                stocks_data[entry['Symbol']]['quantity'] += float(entry['Quantity'])
                stocks_data[entry['Symbol']]['totalprice'] += float(entry['Quantity']) * stocks_data[entry['Symbol']]['avgprice']
                if entry['Symbol'] not in k4_data:
                    k4_data[entry['Symbol']] = {
                        'antal': -float(entry['Quantity']),
                        'forsaljningspris': -float(entry['Quantity']) * float(entry['TradePrice']) + float(entry['IBCommission']),
                        'omkostnadsbelopp': -float(entry['Quantity']) * float(stocks_data[entry['Symbol']]['avgprice'])
                    }
                else:
                    k4_data[entry['Symbol']]['antal'] += -float(entry['Quantity'])
                    k4_data[entry['Symbol']]['forsaljningspris'] += -float(entry['Quantity']) * float(entry['TradePrice']) + float(entry['IBCommission'])
                    k4_data[entry['Symbol']]['omkostnadsbelopp'] += -float(entry['Quantity']) * float(stocks_data[entry['Symbol']]['avgprice'])

                k4_data[entry['Symbol']]['vinst'] = k4_data[entry['Symbol']]['forsaljningspris'] - k4_data[entry['Symbol']]['omkostnadsbelopp']
                if stocks_data[entry['Symbol']]['quantity'] < 0.0001:  # handle float error with fractional shares
                    stocks_data[entry['Symbol']]['quantity'] = 0
                    stocks_data[entry['Symbol']]['avgprice'] = 0

                logging.debug("Sell entry: %s", entry)
                logging.debug("Updated stock data: %s", stocks_data[entry['Symbol']])

    logging.debug("Final K4 data:\n%s", pformat(k4_data, indent=4))

def read_csv_file(filepath):
    data = []
    try:
        with open(filepath, mode='r') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                data.append(row)
    except FileNotFoundError:
        logging.error(f"Error: File {filepath} not found.")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error reading file: {e}")
        sys.exit(1)
    return data

if __name__ == '__main__':
    main()