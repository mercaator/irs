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

import unittest
import logging
from k4sru.data import process_k4_entry, process_currency_buy, process_currency_sell, process_buy_entry, process_sell_entry, process_input_data, process_trading_data

class TestDataFunctions(unittest.TestCase):
    stocks_data = {}
    currency_rates = {}

    @classmethod
    def setUpClass(cls):
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

    def setUp(self):
        self.currency_rates = {('20250101', 'USD'): 10.0,
                               ('20250102', 'USD'): 11.0,
                               ('20250101', 'EUR'): 10.5,
                               ('20250102', 'EUR'): 11.5}

    def test_process_k4_entry_001(self):
        k4_data = {}
        process_k4_entry('ERIC-B', -10, 100, 1, 90, 'SEK', '20250101', k4_data, self.currency_rates)
        self.assertIn('ERIC-B', k4_data)
        self.assertEqual(k4_data['ERIC-B']['antal'], 10)
        self.assertEqual(k4_data['ERIC-B']['forsaljningspris'], 10*100-1)
        self.assertEqual(k4_data['ERIC-B']['omkostnadsbelopp'], 900)

    def test_process_k4_entry_002(self):
        k4_data = {}
        process_k4_entry('ERIC-B', -10, 80, 1, 90, 'SEK', '20250101', k4_data, self.currency_rates)
        self.assertIn('ERIC-B', k4_data)
        self.assertEqual(k4_data['ERIC-B']['antal'], 10)
        self.assertEqual(k4_data['ERIC-B']['forsaljningspris'], 10*80-1)
        self.assertEqual(k4_data['ERIC-B']['omkostnadsbelopp'], 900)

    def test_process_k4_entry_003(self):
        k4_data = { 'ERIC-B': {'antal': 10, 'forsaljningspris': 950, 'omkostnadsbelopp': 900} }
        process_k4_entry('ERIC-B', -10, 100, 1, 90, 'SEK', '20250101', k4_data, self.currency_rates)
        self.assertIn('ERIC-B', k4_data)
        self.assertEqual(k4_data['ERIC-B']['antal'], 20)
        self.assertEqual(k4_data['ERIC-B']['forsaljningspris'], 950 + (10*100-1)) # 1949
        self.assertEqual(k4_data['ERIC-B']['omkostnadsbelopp'], 900 + 900) # 1800

    def test_process_k4_entry_004(self):
        k4_data = {}
        process_k4_entry('AAOI', -10, 30, 1, 290, 'USD', '20250101', k4_data, self.currency_rates)
        self.assertIn('AAOI', k4_data)
        self.assertEqual(k4_data['AAOI']['antal'], 10)
        self.assertEqual(k4_data['AAOI']['forsaljningspris'], (10*30-1)*10.0)
        self.assertEqual(k4_data['AAOI']['omkostnadsbelopp'], 10*290)

    def test_process_k4_entry_005(self):
        k4_data = { 'AAOI': {'antal': 10, 'forsaljningspris': 3000, 'omkostnadsbelopp': 2900} }
        process_k4_entry('AAOI', -10, 30, 1, 290, 'USD', '20250102', k4_data, self.currency_rates)
        self.assertIn('AAOI', k4_data)
        self.assertEqual(k4_data['AAOI']['antal'], 20)
        self.assertEqual(k4_data['AAOI']['forsaljningspris'], 3000 + ((10*30-1)*11.0)) # 6289
        self.assertEqual(k4_data['AAOI']['omkostnadsbelopp'], 2900 + 10 * 290) # 2900

    def test_process_currency_buy_001(self):
        stocks_data = {}
        # Currency is bought when foreign stocks or currency pairs are sold, thus the quantity is negative
        process_currency_buy('USD', -100, 10.0, stocks_data)
        self.assertIn('USD', stocks_data)
        self.assertEqual(stocks_data['USD']['quantity'], 100)
        self.assertEqual(stocks_data['USD']['totalprice'], 1000)
        self.assertEqual(stocks_data['USD']['avgprice'], 10.0)

    def test_process_currency_buy_002(self):
        stocks_data = {'USD': {'quantity': 100, 'totalprice': 1000, 'avgprice': 10.0} }
        # Currency is bought when foreign stocks or currency pairs are sold, thus the quantity is negative
        process_currency_buy('USD', -100, 11.0, stocks_data)
        self.assertIn('USD', stocks_data)
        self.assertEqual(stocks_data['USD']['quantity'], 200)
        self.assertEqual(stocks_data['USD']['totalprice'], 1000 + 100*11.0) # 2100
        self.assertEqual(stocks_data['USD']['avgprice'], 10.5)

    def test_process_currency_sell_001(self):
        stocks_data = {}
        stocks_data['USD'] = {'quantity': 100, 'totalprice': 1000, 'avgprice': 10.0}
        process_currency_sell('USD', 50, stocks_data)
        self.assertEqual(stocks_data['USD']['quantity'], 50)
        self.assertEqual(stocks_data['USD']['totalprice'], 500)

    def test_process_currency_sell_002(self):
        stocks_data = {}
        with self.assertRaises(SystemExit) as cm:
            process_currency_sell('USD', 50, stocks_data)
        self.assertEqual(cm.exception.code, 1)

    def test_process_buy_entry_010(self):
        """UC-1. Buy stock in base currency e.g. buy ERIC-B for SEK
                 Transactions: Buy ERIC-B
        """
        stocks_data = {}
        k4_data = {}
        # Commission is changed to positive value when processing buy entry called from process_input_data
        process_buy_entry('ERIC-B', 10, 100, 5, 'SEK', '20250101', stocks_data, k4_data, self.currency_rates)
        self.assertIn('ERIC-B', stocks_data)
        self.assertEqual(stocks_data['ERIC-B']['quantity'], 10)
        self.assertEqual(stocks_data['ERIC-B']['totalprice'], 10*100+5) # 1005
        self.assertEqual(stocks_data['ERIC-B']['avgprice'], 100.5)

    def test_process_buy_entry_011(self):
        """UC-1. Buy stock in base currency e.g. buy ERIC-B for SEK
                 Transactions: Buy ERIC-B
        """
        stocks_data = {'ERIC-B': {'quantity': 10, 'totalprice': 800, 'avgprice': 80}}
        k4_data = {}
        # Commission is changed to positive value when processing buy entry called from process_input_data
        process_buy_entry('ERIC-B', 10, 100, 5, 'SEK', '20250101', stocks_data, k4_data, self.currency_rates)
        self.assertIn('ERIC-B', stocks_data)
        self.assertEqual(stocks_data['ERIC-B']['quantity'], 20)
        self.assertEqual(stocks_data['ERIC-B']['totalprice'], 10*100+5+800) # 1805
        self.assertEqual(stocks_data['ERIC-B']['avgprice'], 90.25)

    def test_process_buy_entry_020(self):
        """UC-2. Buy currency pair where quote currency is SEK e.g. USD/SEK
                 Transactions: Buy USD
        """
        stocks_data = {}
        k4_data = {}
        # Commission is changed to positive value when processing buy entry called from process_input_data
        process_buy_entry('USD.SEK', 100, 10.0, 1, 'SEK', '20250101', stocks_data, k4_data, self.currency_rates)
        self.assertIn('USD', stocks_data)
        self.assertEqual(stocks_data['USD']['quantity'], 100)
        self.assertEqual(stocks_data['USD']['totalprice'], 10*100+1) # 1001
        self.assertEqual(stocks_data['USD']['avgprice'], 10.01)

    def test_process_buy_entry_021(self):
        """UC-2. Buy currency pair where quote currency is SEK e.g. USD/SEK
                 Transactions: Buy USD
        """
        stocks_data = {'USD': {'quantity': 100, 'totalprice': 900, 'avgprice': 9.0} }
        k4_data = {}
        # Commission is changed to positive value when processing buy entry called from process_input_data
        process_buy_entry('USD.SEK', 100, 10.0, 1, 'SEK', '20250101', stocks_data, k4_data, self.currency_rates)
        self.assertIn('USD', stocks_data)
        self.assertEqual(stocks_data['USD']['quantity'], 200)
        self.assertEqual(stocks_data['USD']['totalprice'], 10*100+1+900) # 1901
        self.assertEqual(stocks_data['USD']['avgprice'], 9.505)

    def test_process_buy_entry_030(self):
        """UC-3. Buy stock in foreign currency e.g. buy AAOI for USD
                 Transactions: Buy AAOI, Sell USD
        """
        stocks_data = { 'USD': {'quantity': 500, 'totalprice': 4500, 'avgprice': 9.0} }
        k4_data = {}
        # Commission is changed to positive value when processing buy entry called from process_input_data
        process_buy_entry('AAOI', 10, 30, 1, 'USD', '20250101', stocks_data, k4_data, self.currency_rates)
        self.assertIn('AAOI', stocks_data)
        self.assertEqual(stocks_data['AAOI']['quantity'], 10)
        self.assertEqual(stocks_data['AAOI']['totalprice'], (10*30+1)*10.0) # 3010
        self.assertEqual(stocks_data['AAOI']['avgprice'], 301)
        self.assertIn('USD', stocks_data)
        self.assertEqual(stocks_data['USD']['quantity'], 500-301) # 199
        self.assertEqual(stocks_data['USD']['totalprice'], 199*9.0) # 1791
        self.assertEqual(stocks_data['USD']['avgprice'], 9.0)
        self.assertIn('USD', k4_data)
        self.assertEqual(k4_data['USD']['antal'], 10*30+1) # 301
        self.assertEqual(k4_data['USD']['forsaljningspris'], 301*10.0) # 3010
        self.assertEqual(k4_data['USD']['omkostnadsbelopp'], 301*9.0) # 2709

    def test_process_buy_entry_031(self):
        """UC-3. Buy stock in foreign currency e.g. buy AAOI for USD
                 Transactions: Buy AAOI, Sell USD
        """
        stocks_data = { 'USD': {'quantity': 500, 'totalprice': 4500, 'avgprice': 9.0},
                        'AAOI': {'quantity': 10, 'totalprice': 2250, 'avgprice': 225}}
        k4_data = {}
        # Commission is changed to positive value when processing buy entry called from process_input_data
        process_buy_entry('AAOI', 10, 30, 1, 'USD', '20250101', stocks_data, k4_data, self.currency_rates)
        self.assertIn('AAOI', stocks_data)
        self.assertEqual(stocks_data['AAOI']['quantity'], 20)
        self.assertEqual(stocks_data['AAOI']['totalprice'], (10*30+1)*10.0+2250) # 5260
        self.assertEqual(stocks_data['AAOI']['avgprice'], 263)
        self.assertIn('USD', stocks_data)
        self.assertEqual(stocks_data['USD']['quantity'], 500-301) # 199
        self.assertEqual(stocks_data['USD']['totalprice'], 199*9.0) # 1791
        self.assertEqual(stocks_data['USD']['avgprice'], 9.0)
        self.assertIn('USD', k4_data)
        self.assertEqual(k4_data['USD']['antal'], 10*30+1) # 301
        self.assertEqual(k4_data['USD']['forsaljningspris'], 301*10.0) # 3010
        self.assertEqual(k4_data['USD']['omkostnadsbelopp'], 301*9.0) # 2709

    def test_process_buy_entry_032(self):
        """UC-3. Buy stock in foreign currency e.g. buy AAOI for USD
                 Transactions: Buy AAOI, Sell USD
                 Test that options contracts are not processed. E.g:
                 "20241211;133120","IBIT  241213P00055000","BUY","1","0.28","-0.29395","USD"
        """
        stocks_data = { 'USD': {'quantity': 500, 'totalprice': 4500, 'avgprice': 9.0} }
        k4_data = {}
        # Commission is changed to positive value when processing buy entry called from process_input_data
        process_buy_entry('IBIT  241213P00055000', 1, 0.28, 0.29, 'USD', '20250101', stocks_data, k4_data, self.currency_rates)
        self.assertNotIn('IBIT  241213P00055000', stocks_data)

    def test_process_buy_entry_040(self):
        """UC-4. Buy currency pair where quote currency in not SEK e.g. EUR/USD for USD
                 Transactions: Buy EUR, Sell USD
        """
        stocks_data = { 'USD': {'quantity': 500, 'totalprice': 4500, 'avgprice': 9.0} }
        k4_data = {}
        # Commission is changed to positive value when processing buy entry called from process_input_data
        process_buy_entry('EUR.USD', 100, 1.05, 1, 'USD', '20250101', stocks_data, k4_data, self.currency_rates)
        self.assertIn('USD', stocks_data)
        self.assertEqual(stocks_data['USD']['quantity'], 500-105-1) # 394
        self.assertEqual(stocks_data['USD']['totalprice'], 394*9.0) # 3546
        self.assertEqual(stocks_data['USD']['avgprice'], 9.0)
        self.assertIn('EUR', stocks_data)
        self.assertEqual(stocks_data['EUR']['quantity'], 100)
        self.assertEqual(stocks_data['EUR']['totalprice'], (100*1.05+1)*10.0) # 1060
        self.assertEqual(stocks_data['EUR']['avgprice'], 10.6)
        self.assertIn('USD', k4_data)
        self.assertEqual(k4_data['USD']['antal'], 105+1) # 106
        self.assertEqual(k4_data['USD']['forsaljningspris'], 106*10.0) # 1060
        self.assertEqual(k4_data['USD']['omkostnadsbelopp'], 106*9.0) # 954

    def test_process_buy_entry_041(self):
        """UC-4. Buy currency pair where quote currency in not SEK e.g. EUR/USD for USD
                 Transactions: Buy EUR, Sell USD
        """
        stocks_data = { 'USD': {'quantity': 500, 'totalprice': 4500, 'avgprice': 9.0},
                        'EUR': {'quantity': 100, 'totalprice': 950, 'avgprice': 9.5} }
        k4_data = {}
        # Commission is changed to positive value when processing buy entry called from process_input_data
        process_buy_entry('EUR.USD', 100, 1.05, 1, 'USD', '20250101', stocks_data, k4_data, self.currency_rates)
        self.assertIn('USD', stocks_data)
        self.assertEqual(stocks_data['USD']['quantity'], 500-105-1) # 394
        self.assertEqual(stocks_data['USD']['totalprice'], 394*9.0) # 3546
        self.assertEqual(stocks_data['USD']['avgprice'], 9.0)
        self.assertIn('EUR', stocks_data)
        self.assertEqual(stocks_data['EUR']['quantity'], 200)
        self.assertEqual(stocks_data['EUR']['totalprice'], (100*1.05+1)*10.0+950) # 2010
        self.assertEqual(stocks_data['EUR']['avgprice'], 10.05)
        self.assertIn('USD', k4_data)
        self.assertEqual(k4_data['USD']['antal'], 105+1) # 106
        self.assertEqual(k4_data['USD']['forsaljningspris'], 106*10.0) # 1060
        self.assertEqual(k4_data['USD']['omkostnadsbelopp'], 106*9.0) # 954

    def test_process_sell_entry_010(self):
        """UC-5. Sell stock in base currency e.g. sell ERIC-B for SEK
                 Transactions: Sell ERIC-B
        """
        stocks_data = {}
        k4_data = {}
        stocks_data['ERIC-B'] = {'quantity': 10, 'totalprice': 1005, 'avgprice': 100.5}
        process_sell_entry('ERIC-B', -5, 110, 5, 'SEK', '2025-01-01', stocks_data, k4_data, self.currency_rates)
        self.assertEqual(stocks_data['ERIC-B']['quantity'], 5)
        self.assertEqual(stocks_data['ERIC-B']['totalprice'], 502.5)
        self.assertEqual(stocks_data['ERIC-B']['avgprice'], 100.5)
        self.assertIn('ERIC-B', k4_data)
        self.assertEqual(k4_data['ERIC-B']['antal'], 5)
        self.assertEqual(k4_data['ERIC-B']['forsaljningspris'], 5*110-5) # 545
        self.assertEqual(k4_data['ERIC-B']['omkostnadsbelopp'], 5*100.5) # 502.5

    def test_process_sell_entry_011(self):
        """UC-5. Sell stock in base currency e.g. sell ERIC-B for SEK
                 Transactions: Sell ERIC-B
        """
        stocks_data = {}
        k4_data = {}
        with self.assertRaises(SystemExit) as cm:
            # TODO: Short selling not supported
            process_sell_entry('ERIC-B', -5, 110, 5, 'SEK', '2025-01-01', stocks_data, k4_data, self.currency_rates)
        self.assertEqual(cm.exception.code, 1)

    def test_process_sell_entry_012(self):
        """UC-5. Sell stock in base currency e.g. sell ERIC-B for SEK
                 Transactions: Sell ERIC-B
        """
        stocks_data = {}
        k4_data = {}
        stocks_data['ERIC-B'] = {'quantity': 5, 'totalprice': 502.5, 'avgprice': 100.5}
        # TODO: Short selling not supported
        process_sell_entry('ERIC-B', -10, 110, 5, 'SEK', '2025-01-01', stocks_data, k4_data, self.currency_rates)
        self.assertIn('ERIC-B', k4_data)
        self.assertEqual(stocks_data['ERIC-B']['quantity'], -5)
        self.assertEqual(stocks_data['ERIC-B']['totalprice'], -502.5)
        self.assertEqual(stocks_data['ERIC-B']['avgprice'], 100.5)

    def test_process_sell_entry_020(self):
        """UC-6. Sell currency pair where quote currency is SEK e.g. USD/SEK
                 Transactions: Sell USD
        """
        stocks_data = {'USD': {'quantity': 100, 'totalprice': 900, 'avgprice': 9.0} }
        k4_data = {}
        # Commission is changed to positive value when processing buy entry called from process_input_data
        process_sell_entry('USD.SEK', -100, 10.0, 1, 'SEK', '20250101', stocks_data, k4_data, self.currency_rates)
        self.assertIn('USD', stocks_data)
        self.assertEqual(stocks_data['USD']['quantity'], 0)
        self.assertEqual(stocks_data['USD']['totalprice'], 0)
        self.assertEqual(stocks_data['USD']['avgprice'], 0)
        self.assertIn('USD', k4_data)
        self.assertEqual(k4_data['USD']['antal'], 100)
        self.assertEqual(k4_data['USD']['forsaljningspris'], 100*10.0-1) # 999
        self.assertEqual(k4_data['USD']['omkostnadsbelopp'], 100*9.0) # 900

    def test_process_sell_entry_021(self):
        """UC-6. Sell currency pair where quote currency is SEK e.g. USD/SEK
                 Transactions: Sell USD
        """
        stocks_data = {}
        k4_data = {}
        with self.assertRaises(SystemExit) as cm:
            # TODO: Short selling not supported
            process_sell_entry('USD', -100, 10.0, 1, 'SEK', '20250101', stocks_data, k4_data, self.currency_rates)
        self.assertEqual(cm.exception.code, 1)

    def test_process_sell_entry_022(self):
        """UC-6. Sell currency pair where quote currency is SEK e.g. USD/SEK
                 Transactions: Sell USD
        """
        stocks_data = {}
        k4_data = {}
        stocks_data['USD'] = {'quantity': 100, 'totalprice': 900, 'avgprice': 9.0}
        # TODO: Short selling not supported
        process_sell_entry('USD', -200, 10.0, 1, 'SEK', '20250101', stocks_data, k4_data, self.currency_rates)
        self.assertIn('USD', k4_data)
        self.assertEqual(stocks_data['USD']['quantity'], -100)
        self.assertEqual(stocks_data['USD']['totalprice'], -900)
        self.assertEqual(stocks_data['USD']['avgprice'], 9.0)

    def test_process_input_data_001(self):
        stocks_data = {}
        k4_data = {}
        data = [
            {'DateTime': '20250101;120000', 'Symbol': 'ERIC-B', 'Buy/Sell': 'BUY', 'Quantity': '10', 'TradePrice': '100', 'IBCommission': '-5', 'CurrencyPrimary': 'SEK'},
            {'DateTime': '20250102;120000', 'Symbol': 'ERIC-B', 'Buy/Sell': 'SELL', 'Quantity': '-5', 'TradePrice': '110', 'IBCommission': '-5', 'CurrencyPrimary': 'SEK'}
        ]
        process_input_data(data, stocks_data, k4_data, self.currency_rates)
        self.assertIn('ERIC-B', stocks_data)
        self.assertEqual(stocks_data['ERIC-B']['quantity'], 5)
        self.assertEqual(stocks_data['ERIC-B']['totalprice'], 5*100.5) # 502.5
        self.assertIn('ERIC-B', k4_data)
        self.assertEqual(k4_data['ERIC-B']['antal'], 5)
        self.assertEqual(k4_data['ERIC-B']['forsaljningspris'], 5*110-5) # 545
        self.assertEqual(k4_data['ERIC-B']['omkostnadsbelopp'], 5*100.5) # 502.5

    def test_process_trading_data_001(self):
        stocks_data = {}
        k4_data = {}
        data = [
            {'DateTime': '20250101;120000', 'Symbol': 'ERIC-B', 'Buy/Sell': 'BUY', 'Quantity': '10', 'TradePrice': '100', 'IBCommission': '-5', 'CurrencyPrimary': 'SEK'},
            {'DateTime': '20250102;120000', 'Symbol': 'ERIC-B', 'Buy/Sell': 'SELL', 'Quantity': '-5', 'TradePrice': '110', 'IBCommission': '-5', 'CurrencyPrimary': 'SEK'}
        ]
        output = process_trading_data(data, stocks_data, k4_data, self.currency_rates)
        self.assertEqual(len(output), 1)
        self.assertEqual(output[0]['beteckning'], 'ERIC-B')
        self.assertEqual(output[0]['antal'], 5)
        self.assertEqual(output[0]['forsaljningspris'], 5*110-5) # 545
        self.assertEqual(output[0]['omkostnadsbelopp'], 5*100.5) # 502.5

if __name__ == '__main__':
    unittest.main()
