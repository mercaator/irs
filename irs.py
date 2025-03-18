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
import logging
from pprint import pformat
from k4sru.sru import generate_info_sru, generate_blanketter_sru
from k4sru.data import process_transactions

INPUT_DIR = 'input/'

stocks_data = {}
k4_data = {}
currency_rates = {}

# This script processes stock trading data and generates Swedish tax reports (K4 SRU).

def main():
    parser = create_cli_parser()
    args = vars(parser.parse_args())

    # Set up logging based on debug level
    logging_level = getattr(logging, args['debug'])

    # Create a logger
    logger = logging.getLogger()
    logger.setLevel(logging_level)

    # Create a console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging_level)

    # Create a file handler
    file_handler = logging.FileHandler('output/irs.log')
    file_handler.setLevel(logging_level)

    # Create a formatter and set it for both handlers
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # Add both handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)


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
    parser.add_argument('--config', default=f'{INPUT_DIR}config.json', help='Path to configuration file')
    parser.add_argument('--indata_ibkr', default=f'{INPUT_DIR}indata_ibkr.csv',
                       help='Path to the input CSV file for k4 command')
    parser.add_argument('--indata_bitstamp', default=f'{INPUT_DIR}indata_bitstamp.csv',
                       help='Path to the input CSV file for k4 command')
    parser.add_argument('--debug', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                       default='INFO', help='Set the debug level')
    parser.add_argument('--year', default=2024, help='Year to process')

    return parser


def read_config(config_file):
    """Read configuration from JSON file."""
    with open(config_file) as f:
        return json.load(f)

def handle_oldinfosru(args):
    generate_info_sru(args)

def handle_infosru(args):
    config = read_config(args.get('config', 'input/config.json'))
    generate_info_sru(config)

def handle_k4(args):
    config = read_config(args.get('config', INPUT_DIR + 'config.json'))
    filepath_ibkr = args.get('indata_ibkr', INPUT_DIR + 'indata_ibkr.csv')
    filepath_bitstamp = args.get('indata_bitstamp', INPUT_DIR + 'indata_bitstamp.csv')
    year = args.get('year', 2024)
    logging.debug("Starting to process parsed CSV data from Interactive Brokers")
    transactions = process_transactions(filepath_ibkr, filepath_bitstamp, year, stocks_data, k4_data, currency_rates)
    generate_blanketter_sru(config, transactions)

if __name__ == '__main__':
    main()