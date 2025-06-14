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
        statistics_data = []
        process_k4_entry('ERIC-B', 'Ericsson', -10, 100, 1, 90, 'SEK', '20250101', k4_data, self.currency_rates, statistics_data, 10)
        self.assertIn('ERIC-B', k4_data)
        self.assertEqual(k4_data['ERIC-B']['antal'], 10)
        self.assertEqual(k4_data['ERIC-B']['forsaljningspris'], 10*100-1)
        self.assertEqual(k4_data['ERIC-B']['omkostnadsbelopp'], 900)

    def test_process_k4_entry_002(self):
        k4_data = {}
        statistics_data = []
        process_k4_entry('ERIC-B', 'Ericsson', -10, 80, 1, 90, 'SEK', '20250101', k4_data, self.currency_rates, statistics_data, 10)
        self.assertIn('ERIC-B', k4_data)
        self.assertEqual(k4_data['ERIC-B']['antal'], 10)
        self.assertEqual(k4_data['ERIC-B']['forsaljningspris'], 10*80-1)
        self.assertEqual(k4_data['ERIC-B']['omkostnadsbelopp'], 900)

    def test_process_k4_entry_003(self):
        k4_data = { 'ERIC-B': {'antal': 10, 'forsaljningspris': 950, 'omkostnadsbelopp': 900} }
        statistics_data = []
        process_k4_entry('ERIC-B', 'Ericsson',-10, 100, 1, 90, 'SEK', '20250101', k4_data, self.currency_rates, statistics_data, 10)
        self.assertIn('ERIC-B', k4_data)
        self.assertEqual(k4_data['ERIC-B']['antal'], 20)
        self.assertEqual(k4_data['ERIC-B']['forsaljningspris'], 950 + (10*100-1)) # 1949
        self.assertEqual(k4_data['ERIC-B']['omkostnadsbelopp'], 900 + 900) # 1800

    def test_process_k4_entry_004(self):
        k4_data = {}
        statistics_data = []
        process_k4_entry('AAOI', 'Applied Optoelectronics Inc', -10, 30, 1, 290, 'USD', '20250101', k4_data, self.currency_rates, statistics_data, 10)
        self.assertIn('AAOI', k4_data)
        self.assertEqual(k4_data['AAOI']['antal'], 10)
        self.assertEqual(k4_data['AAOI']['forsaljningspris'], (10*30-1)*10.0)
        self.assertEqual(k4_data['AAOI']['omkostnadsbelopp'], 10*290)

    def test_process_k4_entry_005(self):
        k4_data = { 'AAOI': {'antal': 10, 'forsaljningspris': 3000, 'omkostnadsbelopp': 2900} }
        statistics_data = []
        process_k4_entry('AAOI', 'Applied Optoelectronics Inc', -10, 30, 1, 290, 'USD', '20250102', k4_data, self.currency_rates, statistics_data, 10)
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
        process_currency_sell('USD', 50, 10.0, stocks_data)
        self.assertEqual(stocks_data['USD']['quantity'], 50)
        self.assertEqual(stocks_data['USD']['totalprice'], 500)

    def test_process_currency_sell_002(self):
        stocks_data = {}
        process_currency_sell('USD', 50, 10.0, stocks_data)
        self.assertIn('USD', stocks_data)
        self.assertEqual(stocks_data['USD']['quantity'], -50)
        self.assertEqual(stocks_data['USD']['totalprice'], -500)
        self.assertEqual(stocks_data['USD']['avgprice'], 10.0)

    def test_process_buy_entry_010(self):
        """UC-1. Buy stock in base currency e.g. buy ERIC-B for SEK
                 Transactions: Buy ERIC-B
        """
        stocks_data = {}
        k4_data = {}
        statistics_data = []
        # Commission is changed to positive value when processing buy entry called from process_input_data
        process_buy_entry('ERIC-B', 'Ericsson', 10, 100, 5, 'SEK', '20250101', stocks_data, k4_data, self.currency_rates, statistics_data)
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
        statistics_data = []
        # Commission is changed to positive value when processing buy entry called from process_input_data
        process_buy_entry('ERIC-B', 'Ericsson', 10, 100, 5, 'SEK', '20250101', stocks_data, k4_data, self.currency_rates, statistics_data)
        self.assertIn('ERIC-B', stocks_data)
        self.assertEqual(stocks_data['ERIC-B']['quantity'], 20)
        self.assertEqual(stocks_data['ERIC-B']['totalprice'], 10*100+5+800) # 1805
        self.assertEqual(stocks_data['ERIC-B']['avgprice'], 90.25)

    def test_process_buy_entry_012(self):
        """UC-1. Buy stock in base currency e.g. buy ERIC-B for SEK
                 Transactions: Buy ERIC-B
                 short position, normal buy, cover all
        """
        stocks_data = {'ERIC-B': {'quantity': -5, 'totalprice': -400, 'avgprice': 80}}
        k4_data = {}
        statistics_data = []
        # Commission is changed to positive value when processing buy entry called from process_input_data
        process_buy_entry('ERIC-B', 'Ericsson', 10, 100, 5, 'SEK', '20250101', stocks_data, k4_data, self.currency_rates, statistics_data)
        self.assertIn('ERIC-B', k4_data)
        self.assertEqual(k4_data['ERIC-B']['antal'], 5)
        # Since the transaction includes both a covering of a short position and the opening of a long position, and only one commission applies,
        # the commission needs to be allocated proportionally to the covering and the long position.
        self.assertEqual(k4_data['ERIC-B']['forsaljningspris'], 400) # 5 * 80 = 400
        self.assertEqual(k4_data['ERIC-B']['omkostnadsbelopp'], 502.5) # 5 * (100 + 0.5) = 502.5
        self.assertIn('ERIC-B', stocks_data)
        self.assertEqual(stocks_data['ERIC-B']['quantity'], 5)
        self.assertEqual(stocks_data['ERIC-B']['totalprice'], 502.5) # 10 * (100 + 0.5) = 502.5
        self.assertEqual(stocks_data['ERIC-B']['avgprice'], 100.5)

    def test_process_buy_entry_013(self):
        """UC-1. Buy stock in base currency e.g. buy ERIC-B for SEK
                 Transactions: Buy ERIC-B
                 short position, normal buy, cover partial
        """
        stocks_data = {'ERIC-B': {'quantity': -10, 'totalprice': -800, 'avgprice': 80}}
        k4_data = {}
        statistics_data = []
        # Commission is changed to positive value when processing buy entry called from process_input_data
        process_buy_entry('ERIC-B', 'Ericsson', 5, 100, 5, 'SEK', '20250101', stocks_data, k4_data, self.currency_rates, statistics_data)
        self.assertIn('ERIC-B', k4_data)
        self.assertEqual(k4_data['ERIC-B']['antal'], 5)
        self.assertEqual(k4_data['ERIC-B']['forsaljningspris'], 400) # 5 * 80 = 400
        self.assertEqual(k4_data['ERIC-B']['omkostnadsbelopp'], 505) # 5 * 100 + 5 = 505
        self.assertIn('ERIC-B', stocks_data)
        self.assertEqual(stocks_data['ERIC-B']['quantity'], -5)
        self.assertEqual(stocks_data['ERIC-B']['totalprice'], -400) # -800 + 5 * 80 = -400
        self.assertEqual(stocks_data['ERIC-B']['avgprice'], 80)

    def test_process_buy_entry_014(self):
        """UC-1. Buy stock in base currency e.g. buy ERIC-B for SEK
                 Transactions: Buy ERIC-B
                 short position, normal buy, cover (quantity=0)
        """
        stocks_data = {'ERIC-B': {'quantity': -5, 'totalprice': -400, 'avgprice': 80}}
        k4_data = {}
        statistics_data = []
        # Commission is changed to positive value when processing buy entry called from process_input_data
        process_buy_entry('ERIC-B', 'Ericsson', 5, 100, 5, 'SEK', '20250101', stocks_data, k4_data, self.currency_rates, statistics_data)
        self.assertIn('ERIC-B', k4_data)
        self.assertEqual(k4_data['ERIC-B']['antal'], 5)
        self.assertEqual(k4_data['ERIC-B']['forsaljningspris'], 400) # 5 * 80 = 400
        self.assertEqual(k4_data['ERIC-B']['omkostnadsbelopp'], 505) # 5 * 100 + 5 = 505
        self.assertIn('ERIC-B', stocks_data)
        self.assertEqual(stocks_data['ERIC-B']['quantity'], 0)
        self.assertEqual(stocks_data['ERIC-B']['totalprice'], 0)
        self.assertEqual(stocks_data['ERIC-B']['avgprice'], 0)

    def test_process_buy_entry_020(self):
        """UC-2. Buy currency pair where quote currency is SEK e.g. USD/SEK
                 Transactions: Buy USD
        """
        stocks_data = {}
        k4_data = {}
        statistics_data = []
        # Commission is changed to positive value when processing buy entry called from process_input_data
        process_buy_entry('USD.SEK', '', 100, 10.0, 1, 'SEK', '20250101', stocks_data, k4_data, self.currency_rates, statistics_data)
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
        statistics_data = []
        # Commission is changed to positive value when processing buy entry called from process_input_data
        process_buy_entry('USD.SEK', '', 100, 10.0, 1, 'SEK', '20250101', stocks_data, k4_data, self.currency_rates, statistics_data)
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
        statistics_data = []
        # Commission is changed to positive value when processing buy entry called from process_input_data
        process_buy_entry('AAOI', 'Applied Optoelectronics Inc', 10, 30, 1, 'USD', '20250101', stocks_data, k4_data, self.currency_rates, statistics_data)
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
        statistics_data = []
        # Commission is changed to positive value when processing buy entry called from process_input_data
        process_buy_entry('AAOI', 'Applied Optoelectronics Inc', 10, 30, 1, 'USD', '20250101', stocks_data, k4_data, self.currency_rates, statistics_data)
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
        statistics_data = []
        # Commission is changed to positive value when processing buy entry called from process_input_data
        process_buy_entry('IBIT  241213P00055000', '', 1, 28, 0.29, 'USD', '20250101', stocks_data, k4_data, self.currency_rates, statistics_data)
        self.assertIn('IBIT  241213P00055000', stocks_data)
        self.assertEqual(stocks_data['IBIT  241213P00055000']['quantity'], 1)
        self.assertEqual(stocks_data['IBIT  241213P00055000']['totalprice'], (28+0.29)*10) # 28.29
        self.assertEqual(stocks_data['IBIT  241213P00055000']['avgprice'], 282.9)
        self.assertIn('USD', stocks_data)
        self.assertEqual(stocks_data['USD']['quantity'], 500 - 28.29) # 471.71
        self.assertEqual(stocks_data['USD']['totalprice'], 4500 - 28.29*9.0) # 4500 - 254.61 = 4245.39
        self.assertEqual(stocks_data['USD']['avgprice'], 9.0)

    def test_process_buy_entry_033(self):
        """UC-3. Buy stock in foreign currency e.g. buy AAOI for USD
                 Transactions: Buy AAOI, Sell USD
                 USD long, stock short, stock cover all, new USD short
        """
        stocks_data = { 'USD': {'quantity': 200, 'totalprice': 1800, 'avgprice': 9.0},
                        'AAOI': {'quantity': -5, 'totalprice': -1125, 'avgprice': 225}}
        k4_data = {}
        statistics_data = []
        # Commission is changed to positive value when processing buy entry called from process_input_data
        process_buy_entry('AAOI', 'Applied Optoelectronics Inc', 10, 30, 1, 'USD', '20250101', stocks_data, k4_data, self.currency_rates, statistics_data)
        self.assertIn('USD', k4_data)
        # Since the transaction includes both a covering of a short position and the opening of a long position, and only one commission applies,
        # the commission needs to be allocated proportionally to the covering and the long position.
        self.assertEqual(k4_data['USD']['antal'], 200)
        self.assertEqual(k4_data['USD']['forsaljningspris'], 2000) # 200 * 10 = 2000
        self.assertEqual(k4_data['USD']['omkostnadsbelopp'], 1800) # 200 * 9 = 1800
        self.assertIn('AAOI', k4_data)
        self.assertEqual(k4_data['AAOI']['antal'], 5)
        self.assertEqual(k4_data['AAOI']['forsaljningspris'], 1125) # 5 * 225 = 1125
        self.assertEqual(k4_data['AAOI']['omkostnadsbelopp'], 1505) # 5 * (30+0.1)* 10 = 1505

        self.assertIn('AAOI', stocks_data)
        self.assertEqual(stocks_data['AAOI']['quantity'], 5)
        self.assertEqual(stocks_data['AAOI']['totalprice'], 1505) # 5 * (30+0.1) * 10
        self.assertEqual(stocks_data['AAOI']['avgprice'], 301) # 1505 / 5 = 301
        self.assertIn('USD', stocks_data)
        self.assertEqual(stocks_data['USD']['quantity'], -101) # 200 - (10 * 30 + 1) = -101
        self.assertEqual(stocks_data['USD']['totalprice'], -1010) # -101 * 10 = -1010
        self.assertEqual(stocks_data['USD']['avgprice'], 10.0)

    def test_process_buy_entry_034(self):
        """UC-3. Buy stock in foreign currency e.g. buy AAOI for USD
                 Transactions: Buy AAOI, Sell USD
                 USD long, stock short, stock cover partial, new USD short
        """
        stocks_data = { 'USD': {'quantity': 200, 'totalprice': 1800, 'avgprice': 9.0},
                        'AAOI': {'quantity': -15, 'totalprice': -3375, 'avgprice': 225}}
        k4_data = {}
        statistics_data = []
        # Commission is changed to positive value when processing buy entry called from process_input_data
        process_buy_entry('AAOI', 'Applied Optoelectronics Inc', 10, 30, 1, 'USD', '20250101', stocks_data, k4_data, self.currency_rates, statistics_data)
        self.assertIn('USD', k4_data)
        # Since the transaction includes both a covering of a short position and the opening of a long position, and only one commission applies,
        # the commission needs to be allocated proportionally to the covering and the long position.
        self.assertEqual(k4_data['USD']['antal'], 200)
        self.assertEqual(k4_data['USD']['forsaljningspris'], 2000) # 200 * 10 = 2000
        self.assertEqual(k4_data['USD']['omkostnadsbelopp'], 1800) # 200 * 9 = 1800
        self.assertIn('AAOI', k4_data)
        self.assertEqual(k4_data['AAOI']['antal'], 10)
        self.assertEqual(k4_data['AAOI']['forsaljningspris'], 2250) # 10 * 225 = 2250
        self.assertEqual(k4_data['AAOI']['omkostnadsbelopp'], 3010) # 10 * (30+0.1)* 10 = 3010

        self.assertIn('AAOI', stocks_data)
        self.assertEqual(stocks_data['AAOI']['quantity'], -5)
        self.assertEqual(stocks_data['AAOI']['totalprice'], -1125) # -3375 + 10 * 225 = -1125
        self.assertEqual(stocks_data['AAOI']['avgprice'], 225) # 1505 / 5 = 301
        self.assertIn('USD', stocks_data)
        self.assertEqual(stocks_data['USD']['quantity'], -101) # 200 - (10 * 30 + 1) = -101
        self.assertEqual(stocks_data['USD']['totalprice'], -1010) # -101 * 10 = -1010
        self.assertEqual(stocks_data['USD']['avgprice'], 10.0)

    def test_process_buy_entry_035(self):
        """UC-3. Buy stock in foreign currency e.g. buy AAOI for USD
                 Transactions: Buy AAOI, Sell USD
                 USD short, stock short, stock cover, USD short add
        """
        stocks_data = { 'USD': {'quantity': -200, 'totalprice': -1800, 'avgprice': 9.0},
                        'AAOI': {'quantity': -10, 'totalprice': -2250, 'avgprice': 225}}
        k4_data = {}
        statistics_data = []
        # Commission is changed to positive value when processing buy entry called from process_input_data
        process_buy_entry('AAOI', 'Applied Optoelectronics Inc', 10, 30, 1, 'USD', '20250101', stocks_data, k4_data, self.currency_rates, statistics_data)
        self.assertNotIn('USD', k4_data)
        self.assertIn('AAOI', k4_data)
        self.assertEqual(k4_data['AAOI']['antal'], 10)
        self.assertEqual(k4_data['AAOI']['forsaljningspris'], 2250) # 10 * 225 = 2250
        self.assertEqual(k4_data['AAOI']['omkostnadsbelopp'], 3010) # 10 * (30+0.1)* 10 = 3010

        self.assertIn('AAOI', stocks_data)
        self.assertEqual(stocks_data['AAOI']['quantity'], 0)
        self.assertEqual(stocks_data['AAOI']['totalprice'], 0)
        self.assertEqual(stocks_data['AAOI']['avgprice'], 0)
        self.assertIn('USD', stocks_data)
        self.assertEqual(stocks_data['USD']['quantity'], -501) # -200 - (10 * 30 + 1) = -501
        self.assertEqual(stocks_data['USD']['totalprice'], -4810) # -1800 - (301 * 10) = -4810
        self.assertEqual(stocks_data['USD']['avgprice'], 4810 / 501) # 4810 / 501 = 9.60



    def test_process_buy_entry_040(self):
        """UC-4. Buy currency pair where quote currency in not SEK e.g. EUR/USD for USD
                 Transactions: Buy EUR, Sell USD
        """
        stocks_data = { 'USD': {'quantity': 500, 'totalprice': 4500, 'avgprice': 9.0} }
        k4_data = {}
        statistics_data = []
        # Commission is changed to positive value when processing buy entry called from process_input_data
        process_buy_entry('EUR.USD', '', 100, 1.05, 1, 'USD', '20250101', stocks_data, k4_data, self.currency_rates, statistics_data)
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
        statistics_data = []
        # Commission is changed to positive value when processing buy entry called from process_input_data
        process_buy_entry('EUR.USD', '', 100, 1.05, 1, 'USD', '20250101', stocks_data, k4_data, self.currency_rates, statistics_data)
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
        statistics_data = []
        stocks_data['ERIC-B'] = {'quantity': 10, 'totalprice': 1005, 'avgprice': 100.5}
        process_sell_entry('ERIC-B', 'Ericsson', -5, 110, 5, 'SEK', '2025-01-01', stocks_data, k4_data, self.currency_rates, statistics_data)
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
        statistics_data = []
        # Short selling
        process_sell_entry('ERIC-B', 'Ericsson', -5, 110, 5, 'SEK', '2025-01-01', stocks_data, k4_data, self.currency_rates, statistics_data)
        self.assertIn('ERIC-B', stocks_data)
        self.assertEqual(stocks_data['ERIC-B']['quantity'], -5)
        self.assertEqual(stocks_data['ERIC-B']['totalprice'], (-5*110+5)) # -545
        self.assertEqual(stocks_data['ERIC-B']['avgprice'], -545 / -5) # 109.0
        # K4 event should be created when position is covered
        self.assertNotIn('ERIC-B', k4_data)

    def test_process_sell_entry_012(self):
        """UC-5. Sell stock in base currency e.g. sell ERIC-B for SEK
                 Transactions: Sell ERIC-B
        """
        stocks_data = {}
        k4_data = {}
        statistics_data = []
        stocks_data['ERIC-B'] = {'quantity': 5, 'totalprice': 502.5, 'avgprice': 100.5}
        process_sell_entry('ERIC-B', 'Ericsson', -10, 110, 5, 'SEK', '2025-01-01', stocks_data, k4_data, self.currency_rates, statistics_data)
        self.assertIn('ERIC-B', k4_data)
        self.assertEqual(k4_data['ERIC-B']['antal'], 5)
        # Since the transaction includes both a realized sale and the opening of a short position, and only one commission applies,
        # the commission needs to be allocated proportionally to the sale and the short position.
        self.assertEqual(k4_data['ERIC-B']['forsaljningspris'], 5*(110-0.5)) # 547.5
        self.assertEqual(k4_data['ERIC-B']['omkostnadsbelopp'], 5*100.5) # 502.5

        self.assertEqual(stocks_data['ERIC-B']['quantity'], -5)
        self.assertEqual(stocks_data['ERIC-B']['totalprice'], -5*(110-0.5)) # -547.5
        self.assertEqual(stocks_data['ERIC-B']['avgprice'], -547.5 / -5) # 109.5

    def test_process_sell_entry_013(self):
        """UC-5. Sell stock in base currency e.g. sell ERIC-B for SEK
                 Transactions: Sell ERIC-B
        """
        stocks_data = {}
        k4_data = {}
        statistics_data = []
        stocks_data['ERIC-B'] = {'quantity': 5, 'totalprice': 502.5, 'avgprice': 100.5}
        process_sell_entry('ERIC-B', 'Ericsson', -20, 110, 5, 'SEK', '2025-01-01', stocks_data, k4_data, self.currency_rates, statistics_data)
        self.assertIn('ERIC-B', k4_data)
        self.assertEqual(k4_data['ERIC-B']['antal'], 5)
        self.assertEqual(k4_data['ERIC-B']['forsaljningspris'], 5*(110-0.25)) # 548.75
        self.assertEqual(k4_data['ERIC-B']['omkostnadsbelopp'], 5*100.5) # 502.5

        self.assertEqual(stocks_data['ERIC-B']['quantity'], -15)
        self.assertEqual(stocks_data['ERIC-B']['totalprice'], -15*(110-0.25)) # -1646.25
        self.assertEqual(stocks_data['ERIC-B']['avgprice'], -1646.25 / -15) # 109.75

    def test_process_sell_entry_014(self):
        """UC-5. Sell stock in base currency e.g. sell ERIC-B for SEK
                 Transactions: Sell ERIC-B
        """
        stocks_data = {}
        k4_data = {}
        statistics_data = []
        stocks_data['ERIC-B'] = {'quantity': -5, 'totalprice': -502.5, 'avgprice': 100.5}
        # Short selling
        process_sell_entry('ERIC-B', 'Ericsson', -5, 110, 5, 'SEK', '2025-01-01', stocks_data, k4_data, self.currency_rates, statistics_data)
        self.assertIn('ERIC-B', stocks_data)
        self.assertEqual(stocks_data['ERIC-B']['quantity'], -10)
        self.assertEqual(stocks_data['ERIC-B']['totalprice'], -502.5 + (-5*110+5)) # -1047.5
        self.assertEqual(stocks_data['ERIC-B']['avgprice'], -1047.5 / -10) # 104.75
        # K4 event should be created when position is covered
        self.assertNotIn('ERIC-B', k4_data)

    def test_process_sell_entry_020(self):
        """UC-6. Sell currency pair where quote currency is SEK e.g. USD/SEK
                 Transactions: Sell USD
        """
        stocks_data = {'USD': {'quantity': 100, 'totalprice': 900, 'avgprice': 9.0} }
        k4_data = {}
        statistics_data = []
        # Commission is changed to positive value when processing buy entry called from process_input_data
        process_sell_entry('USD.SEK', '', -100, 10.0, 1, 'SEK', '20250101', stocks_data, k4_data, self.currency_rates, statistics_data)
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
        statistics_data = []
        process_sell_entry('USD', '', -100, 10.0, 1, 'SEK', '20250101', stocks_data, k4_data, self.currency_rates, statistics_data)
        self.assertIn('USD', stocks_data)
        self.assertEqual(stocks_data['USD']['quantity'], -100)
        self.assertEqual(stocks_data['USD']['totalprice'], -100 * 10.0 + 1) # -999
        self.assertEqual(stocks_data['USD']['avgprice'], 9.99)
        # K4 event should be created when position is covered
        self.assertNotIn('USD', k4_data)

    def test_process_sell_entry_022(self):
        """UC-6. Sell currency pair where quote currency is SEK e.g. USD/SEK
                 Transactions: Sell USD
        """
        stocks_data = {'USD': {'quantity': 100, 'totalprice': 900, 'avgprice': 9.0} }
        k4_data = {}
        statistics_data = []
        process_sell_entry('USD', '', -200, 10.0, 2, 'SEK', '20250101', stocks_data, k4_data, self.currency_rates, statistics_data)
        self.assertIn('USD', k4_data)
        self.assertEqual(k4_data['USD']['antal'], 100)
        self.assertEqual(k4_data['USD']['forsaljningspris'], 100*(10.0-0.01)) # 999
        self.assertEqual(k4_data['USD']['omkostnadsbelopp'], 100*9.0)
        self.assertEqual(stocks_data['USD']['quantity'], -100)
        self.assertEqual(stocks_data['USD']['totalprice'], -100*(10.0-0.01)) # -999
        self.assertEqual(stocks_data['USD']['avgprice'], -999 / -100)

    def test_process_sell_entry_023(self):
        """UC-6. Sell currency pair where quote currency is SEK e.g. USD/SEK
                 Transactions: Sell USD
        """
        stocks_data = {'USD': {'quantity': -100, 'totalprice': -900, 'avgprice': 9.0} }
        k4_data = {}
        statistics_data = []
        process_sell_entry('USD', '', -200, 10.0, 2, 'SEK', '20250101', stocks_data, k4_data, self.currency_rates, statistics_data)
        self.assertNotIn('USD', k4_data)
        self.assertEqual(stocks_data['USD']['quantity'], -300)
        self.assertEqual(stocks_data['USD']['totalprice'], -900 - (200*10.0-2)) # -2898
        self.assertEqual(stocks_data['USD']['avgprice'], -2898 / -300) # 9.66

    def test_process_sell_entry_030(self):
        """UC-7. Sell stock in foreign currency e.g. sell AAOI for USD
                 Transactions: Sell AAOI, Buy USD
        """
        stocks_data = {'AAOI': {'quantity': 10, 'totalprice': 3010, 'avgprice': 301} }
        k4_data = {}
        statistics_data = []
        process_sell_entry('AAOI', 'Applied Optoelectronics Inc', -5, 31, 1, 'USD', '20250101', stocks_data, k4_data, self.currency_rates, statistics_data)
        self.assertEqual(stocks_data['AAOI']['quantity'], 5)
        self.assertEqual(stocks_data['AAOI']['totalprice'], 1505)
        self.assertEqual(stocks_data['AAOI']['avgprice'], 301)
        self.assertEqual(stocks_data['USD']['quantity'], 5*31-1) # 154
        self.assertEqual(stocks_data['USD']['totalprice'], 154*10) # 1540
        self.assertEqual(stocks_data['USD']['avgprice'], 1540/154) # 10.0
        self.assertIn('AAOI', k4_data)
        self.assertEqual(k4_data['AAOI']['antal'], 5)
        self.assertEqual(k4_data['AAOI']['forsaljningspris'], (5*31-1)*10) # 154
        self.assertEqual(k4_data['AAOI']['omkostnadsbelopp'], 5*301) # 502.5


    def test_process_sell_entry_031(self):
        """UC-7. Sell stock in foreign currency e.g. sell AAOI for USD
                 Transactions: Sell AAOI, Buy USD
        """
        stocks_data = {'USD': {'quantity': 100, 'totalprice': 900, 'avgprice': 9.0},
                       'AAOI': {'quantity': 10, 'totalprice': 3010, 'avgprice': 301} }
        k4_data = {}
        statistics_data = []
        process_sell_entry('AAOI', 'Applied Optoelectronics Inc', -5, 31, 1, 'USD', '20250101', stocks_data, k4_data, self.currency_rates, statistics_data)
        self.assertEqual(stocks_data['AAOI']['quantity'], 5)
        self.assertEqual(stocks_data['AAOI']['totalprice'], 1505)
        self.assertEqual(stocks_data['AAOI']['avgprice'], 301)
        self.assertEqual(stocks_data['USD']['quantity'], 100+5*31-1) # 254
        self.assertEqual(stocks_data['USD']['totalprice'], 100*9+154*10) # 2440
        self.assertEqual(stocks_data['USD']['avgprice'], 2440/254) # 9.606299212598426
        self.assertIn('AAOI', k4_data)
        self.assertEqual(k4_data['AAOI']['antal'], 5)
        self.assertEqual(k4_data['AAOI']['forsaljningspris'], (5*31-1)*10) # 154
        self.assertEqual(k4_data['AAOI']['omkostnadsbelopp'], 5*301) # 502.5

    def test_process_sell_entry_032(self):
        """UC-7. Sell stock in foreign currency e.g. sell AAOI for USD
                 Transactions: Sell AAOI, Buy USD
        """
        stocks_data = {'USD': {'quantity': -100, 'totalprice': -900, 'avgprice': 9.0},
                       'AAOI': {'quantity': 10, 'totalprice': 3010, 'avgprice': 301} }
        k4_data = {}
        statistics_data = []
        process_sell_entry('AAOI', 'Applied Optoelectronics Inc', -5, 31, 1, 'USD', '20250101', stocks_data, k4_data, self.currency_rates, statistics_data)
        self.assertEqual(stocks_data['AAOI']['quantity'], 5)
        self.assertEqual(stocks_data['AAOI']['totalprice'], 1505) # 3010 - 5 * 301 = 1505
        self.assertEqual(stocks_data['AAOI']['avgprice'], 301)
        self.assertEqual(stocks_data['USD']['quantity'], -100+5*31-1) # -100 + (5 * 31 - 1) = 54
        self.assertEqual(stocks_data['USD']['totalprice'], 540) # 54 * 10 = 540
        self.assertEqual(stocks_data['USD']['avgprice'], 10.0) # 540 / 54 = 10.0
        self.assertIn('AAOI', k4_data)
        self.assertEqual(k4_data['AAOI']['antal'], 5)
        self.assertEqual(k4_data['AAOI']['forsaljningspris'], (5*31-1)*10) # 154
        self.assertEqual(k4_data['AAOI']['omkostnadsbelopp'], 5*301) # 502.5
        self.assertIn('USD', k4_data)
        self.assertEqual(k4_data['USD']['antal'], 100)
        # USD short position was opened at 9.0 USD/SEK exchange rate. So we got 900 SEK for 100 USD.
        # When covering the short position, the dollar gets stronger, and at a rate of 10.0 USD/SEK,
        # we need to pay 1000 SEK to cover the short position. Thus, we realize a loss of 100 SEK.
        self.assertEqual(k4_data['USD']['forsaljningspris'], 900) # 100 * 9.0
        self.assertEqual(k4_data['USD']['omkostnadsbelopp'], 1000) # 100 * 10.0

    def test_process_sell_entry_033(self):
        """UC-7. Sell stock in foreign currency e.g. sell AAOI for USD
                 Transactions: Sell AAOI, Buy USD
        """
        # Partial covering of a USD short position
        stocks_data = {'USD': {'quantity': -200, 'totalprice': -1800, 'avgprice': 9.0},
                       'AAOI': {'quantity': 10, 'totalprice': 3010, 'avgprice': 301} }
        k4_data = {}
        statistics_data = []
        process_sell_entry('AAOI', 'Applied Optoelectronics Inc', -5, 31, 1, 'USD', '20250101', stocks_data, k4_data, self.currency_rates, statistics_data)
        self.assertEqual(stocks_data['AAOI']['quantity'], 5)
        self.assertEqual(stocks_data['AAOI']['totalprice'], 1505) # 3010 - 5 * 301 = 1505
        self.assertEqual(stocks_data['AAOI']['avgprice'], 301)
        self.assertEqual(stocks_data['USD']['quantity'], -46) # -200 + (5 * 31 - 1) = -46
        self.assertEqual(stocks_data['USD']['totalprice'], -414) # -46 * 9 = -414
        self.assertEqual(stocks_data['USD']['avgprice'], 9.0) # -414 / -46 = 9.0
        self.assertIn('AAOI', k4_data)
        self.assertEqual(k4_data['AAOI']['antal'], 5)
        self.assertEqual(k4_data['AAOI']['forsaljningspris'], 1540) # (5 * 31 - 1)* 10 = 1540
        self.assertEqual(k4_data['AAOI']['omkostnadsbelopp'], 1505) # 301 * 5 = 1505
        self.assertIn('USD', k4_data)
        self.assertEqual(k4_data['USD']['antal'], 154) # 5 * 31 - 1 = 154
        # USD short position was opened at 9.0 USD/SEK exchange rate. So we got 900 SEK for 100 USD.
        # When covering the short position, the dollar gets stronger, and at a rate of 10.0 USD/SEK,
        # we need to pay 1000 SEK to cover the short position. Thus, we realize a loss of 154 SEK.
        self.assertEqual(k4_data['USD']['forsaljningspris'], 1386) # 154 * 9.0 = 1386
        self.assertEqual(k4_data['USD']['omkostnadsbelopp'], 1540) # 154 * 10.0 = 1540

    def test_process_sell_entry_034(self):
        """UC-7. Sell stock in foreign currency e.g. sell AAOI for USD
                 Transactions: Sell AAOI, Buy USD
        """
        # Covering of a USD short position
        # Opening a short position in AAOI
        stocks_data = {'USD': {'quantity': -200, 'totalprice': -1800, 'avgprice': 9.0},
                       'AAOI': {'quantity': 5, 'totalprice': 1505, 'avgprice': 301} }
        k4_data = {}
        statistics_data = []
        process_sell_entry('AAOI', 'Applied Optoelectronics Inc', -10, 31, 1, 'USD', '20250101', stocks_data, k4_data, self.currency_rates, statistics_data)
        # Since the transaction includes both a realized sale and the opening of a short position, and only one commission applies,
        # the commission needs to be allocated proportionally to the sale and the short position.
        self.assertEqual(stocks_data['AAOI']['quantity'], -5)
        self.assertEqual(stocks_data['AAOI']['totalprice'], -1545) # -5 * (31-0.1) * 10.0 = -1545
        self.assertEqual(stocks_data['AAOI']['avgprice'], 309) # 1545 / 5 = 309
        self.assertEqual(stocks_data['USD']['quantity'], 109) # -200 + (10 * 31 - 1) = 109
        self.assertEqual(stocks_data['USD']['totalprice'], 1090) # 109 * 10.0 = 1090
        self.assertEqual(stocks_data['USD']['avgprice'], 10.0) # 1090 / 109 = 10.0
        self.assertIn('AAOI', k4_data)
        self.assertEqual(k4_data['AAOI']['antal'], 5)
        self.assertEqual(k4_data['AAOI']['forsaljningspris'], 1545) # 5 * (31 - 0.1) * 10 = 1545
        self.assertEqual(k4_data['AAOI']['omkostnadsbelopp'], 1505) # 301 * 5 = 1505
        self.assertIn('USD', k4_data)
        self.assertEqual(k4_data['USD']['antal'], 200)
        # USD short position was opened at 9.0 USD/SEK exchange rate. So we got 900 SEK for 100 USD.
        # When covering the short position, the dollar gets stronger, and at a rate of 10.0 USD/SEK,
        # we need to pay 1000 SEK to cover the short position. Thus, we realize a loss of 154 SEK.
        self.assertEqual(k4_data['USD']['forsaljningspris'], 1800) # 200 * 9.0 = 1800
        self.assertEqual(k4_data['USD']['omkostnadsbelopp'], 2000) # 200 * 10.0 = 2000

    def test_process_sell_entry_035(self):
        """UC-7. Sell stock in foreign currency e.g. sell AAOI for USD
                 Transactions: Sell AAOI, Buy USD
        """
        # Covering of a USD short position
        # Adding to short position in AAOI
        stocks_data = {'USD': {'quantity': -200, 'totalprice': -1800, 'avgprice': 9.0},
                       'AAOI': {'quantity': -5, 'totalprice': -1505, 'avgprice': 301} }
        k4_data = {}
        statistics_data = []
        process_sell_entry('AAOI', 'Applied Optoelectronics Inc', -15, 31, 1, 'USD', '20250101', stocks_data, k4_data, self.currency_rates, statistics_data)
        self.assertEqual(stocks_data['AAOI']['quantity'], -20)
        self.assertEqual(stocks_data['AAOI']['totalprice'], -6145) # -1505 - (15 * 31 - 1) * 10.0) = 6145
        self.assertEqual(stocks_data['AAOI']['avgprice'], 307.25) # 6145 / 20 = 307.25
        self.assertEqual(stocks_data['USD']['quantity'], 264) # -200 + (15 * 31 - 1) = 264
        self.assertEqual(stocks_data['USD']['totalprice'], 2640) # 264 * 10.0 = 2640
        self.assertEqual(stocks_data['USD']['avgprice'], 10.0) # 2640 / 264 = 10.0
        self.assertNotIn('AAOI', k4_data)
        self.assertIn('USD', k4_data)
        self.assertEqual(k4_data['USD']['antal'], 200)
        # USD short position was opened at 9.0 USD/SEK exchange rate. So we got 900 SEK for 100 USD.
        # When covering the short position, the dollar gets stronger, and at a rate of 10.0 USD/SEK,
        # we need to pay 1000 SEK to cover the short position. Thus, we realize a loss of 154 SEK.
        self.assertEqual(k4_data['USD']['forsaljningspris'], 1800) # 200 * 9.0 = 1800
        self.assertEqual(k4_data['USD']['omkostnadsbelopp'], 2000) # 200 * 10.0 = 2000

    def test_process_sell_entry_040(self):
        """UC-8. Sell currency pair where quote currency in not SEK e.g. EUR/USD for USD
                 Transactions: Sell EUR, Buy USD
        """
        stocks_data = { 'USD': {'quantity': 500, 'totalprice': 4500, 'avgprice': 9.0},
                        'EUR': {'quantity': 100, 'totalprice': 950, 'avgprice': 9.5} }
        k4_data = {}
        statistics_data = []
        process_sell_entry('EUR.USD', '', -100, 1.05, 1, 'USD', '20250101', stocks_data, k4_data, self.currency_rates, statistics_data)
        self.assertIn('USD', stocks_data)
        self.assertEqual(stocks_data['USD']['quantity'], 500+105-1) # 604
        self.assertEqual(stocks_data['USD']['totalprice'], 4500+104*10) # 5540
        self.assertEqual(stocks_data['USD']['avgprice'], 5540/604) # 9.17
        self.assertIn('EUR', stocks_data)
        self.assertEqual(stocks_data['EUR']['quantity'], 0)
        self.assertEqual(stocks_data['EUR']['totalprice'], 0)
        self.assertEqual(stocks_data['EUR']['avgprice'], 0)
        self.assertIn('EUR', k4_data)
        self.assertEqual(k4_data['EUR']['antal'], 100)
        self.assertEqual(k4_data['EUR']['forsaljningspris'], 104*10) # 1040
        self.assertEqual(k4_data['EUR']['omkostnadsbelopp'], 100*9.5) # 950

    def test_process_sell_entry_041(self):
        """UC-8. Sell currency pair where quote currency in not SEK e.g. EUR/USD for USD
                 Transactions: Sell EUR, Buy USD
        """
        stocks_data = { 'USD': {'quantity': 500, 'totalprice': 4500, 'avgprice': 9.0},
                        'EUR': {'quantity': 100, 'totalprice': 950, 'avgprice': 9.5} }
        k4_data = {}
        statistics_data = []
        process_sell_entry('USD.EUR', '', -100, 0.95, 1, 'EUR', '20250101', stocks_data, k4_data, self.currency_rates, statistics_data)
        self.assertIn('USD', stocks_data)
        self.assertEqual(stocks_data['USD']['quantity'], 400) # 604
        self.assertEqual(stocks_data['USD']['totalprice'], 4500-100*9) # 3600
        self.assertEqual(stocks_data['USD']['avgprice'], 9.0)
        self.assertIn('EUR', stocks_data)
        self.assertEqual(stocks_data['EUR']['quantity'], 100+95-1) # 194
        self.assertEqual(stocks_data['EUR']['totalprice'], 950+94*10.5) # 1937
        self.assertEqual(stocks_data['EUR']['avgprice'], 1937/194) # 9.98
        self.assertIn('USD', k4_data)
        self.assertEqual(k4_data['USD']['antal'], 100)
        self.assertEqual(k4_data['USD']['forsaljningspris'], 94*10.5) # 987
        self.assertEqual(k4_data['USD']['omkostnadsbelopp'], 100*9) # 900

    def test_process_input_data_001(self):
        stocks_data = {}
        k4_data = {}
        statistics_data = []
        data = [
            {'DateTime': '20250101;120000', 'Symbol': 'ERIC-B', 'Buy/Sell': 'BUY', 'Quantity': '10', 'TradePrice': '100', 'IBCommission': '-5', 'CurrencyPrimary': 'SEK', 'Description': 'Ericsson'},
            {'DateTime': '20250102;120000', 'Symbol': 'ERIC-B', 'Buy/Sell': 'SELL', 'Quantity': '-5', 'TradePrice': '110', 'IBCommission': '-5', 'CurrencyPrimary': 'SEK', 'Description': 'Ericsson'}
        ]
        process_input_data(data, stocks_data, k4_data, self.currency_rates, statistics_data)
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
        statistics_data = []
        data = [
            {'DateTime': '20250101;120000', 'Symbol': 'ERIC-B', 'Buy/Sell': 'BUY', 'Quantity': '10', 'TradePrice': '100', 'IBCommission': '-5', 'CurrencyPrimary': 'SEK', 'Description': 'Ericsson'},
            {'DateTime': '20250102;120000', 'Symbol': 'ERIC-B', 'Buy/Sell': 'SELL', 'Quantity': '-5', 'TradePrice': '110', 'IBCommission': '-5', 'CurrencyPrimary': 'SEK', 'Description': 'Ericsson'}
        ]
        output = process_trading_data(data, stocks_data, k4_data, self.currency_rates, statistics_data)
        self.assertEqual(len(output), 1)
        self.assertEqual(output[0]['beteckning'], 'ERIC-B')
        self.assertEqual(output[0]['antal'], 5)
        self.assertEqual(output[0]['forsaljningspris'], 5*110-5) # 545
        self.assertEqual(output[0]['omkostnadsbelopp'], 5*100.5) # 502.5

if __name__ == '__main__':
    unittest.main()
