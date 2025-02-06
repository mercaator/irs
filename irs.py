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
from sru import generate_info_sru, generate_blanketter_sru
from data import process_transactions_ibkr

# This script processes stock trading data and generates Swedish tax reports (K4 SRU).


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
    parser.add_argument('--year', default=2024, help='Year to process')

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
    year = args.get('year', 2024)
    logging.debug("Starting to process parsed CSV data from Interactive Brokers")
    transactions = process_transactions_ibkr(filepath, year)
    generate_blanketter_sru(config, transactions)

if __name__ == '__main__':
    main()