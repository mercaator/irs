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
import logging
import sys
from pprint import pformat
from k4sru.sru import generate_info_sru, generate_blanketter_sru
from k4sru.data import init_stocks_data, process_transactions, save_stocks_data, print_statistics

INPUT_DIR = 'input/'

stocks_data = {}
k4_data = {}
currency_rates = {}

# Detailed statistics data that will be stored in a CSV file
statistics_data = []

# This script processes stock trading data and generates Swedish tax reports (K4 SRU).

def create_cli_parser():
    parser = argparse.ArgumentParser(
        prog='irs',
        description='''Process trading data and generate Swedish tax reports for eletronic uploading (K4 SRU).

List of generated files:

    - INFO.SRU         - tax payer information
    - BLANKETTER.SRU   - transaction data for each stock sold during the tax year
    - output_portfolio_<year>.json - portfolio data at the end of the tax year
    - output_statistics_<year>.csv - profit/loss statistics for post-processing e.g. pandas

Supported file format:

"DateTime","Symbol","Buy/Sell","Quantity","TradePrice","IBCommission","CurrencyPrimary","Description","ISIN","Exchange"
"20250225;030616","RHMd","BUY","2","985.4","-3","EUR","RHEINMETALL AG","DE0007030009","IBIS"
...
"Date/Time","FromCurrency","ToCurrency","Rate"
"20250225","EUR","USD","1.0515"
...
''',
        formatter_class=argparse.RawTextHelpFormatter)

    subparsers = parser.add_subparsers(dest='command', required=True, help='Available commands')

    # Subcommand: infosru
    k4sru_parser = subparsers.add_parser('k4sru', help='Generate K4 SRU files (INFO.SRU and BLANKETTER.SRU) from trading data.')



    #parser.add_argument('commands', nargs='+', choices=['infosru', 'k4sru'],
    #                   help='Commands to execute')

    # Add other arguments
    k4sru_parser.add_argument('--config', default=f'{INPUT_DIR}config.json', help='path to configuration file')
    k4sru_parser.add_argument('--indata',
                       required=True,
                       help='input CSV file with trade data')
    k4sru_parser.add_argument('--indata2',
                        help='optional secondary input CSV file with additional trade data (e.g., Bitstamp trades)')
    k4sru_parser.add_argument('--debug', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                       default='INFO', help='set logging level')
    k4sru_parser.add_argument('--year', default=2025, help='tax year for which to generate the K4 SRU files')
    k4sru_parser.add_argument('--longnames', action='store_true', default=False,
                       help='output long names in the generated K4 SRU file instead of the ticker symbols')

    return parser

def read_config(config_file):
    """Read configuration from JSON file."""
    with open(config_file) as f:
        return json.load(f)

def handle_k4sru(args):
    config = read_config(args.get('config', INPUT_DIR + 'config.json'))

    # Generate INFO.SRU file
    generate_info_sru(config)

    # Generate BLANKETTER.SRU file
    filepath_ibkr = args.get('indata', INPUT_DIR + 'indata_ibkr.csv')
    filepath_bitstamp = args.get('indata2', INPUT_DIR + 'indata_bitstamp.csv')
    year = args.get('year', 2024)
    longnames = args.get('longnames', False)
    logging.debug("Starting to process parsed CSV data from Interactive Brokers")
    stocks_data = init_stocks_data(year)
    transactions = process_transactions(filepath_ibkr, filepath_bitstamp, year, stocks_data, k4_data, currency_rates, statistics_data)
    # Save the processed data to a JSON file
    save_stocks_data(year, stocks_data)
    generate_blanketter_sru(config, transactions, longnames)
    # Print statistics data
    print_statistics(statistics_data, k4_data, year)

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

    if 'command' not in args or not args['command']:
        parser.print_help()
        sys.exit(1)

    if args['command'] == 'k4sru':
        handle_k4sru(args)

if __name__ == '__main__':
    main()