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
from k4sru.sru import generate_info_sru, generate_sru_header, clean_symbol, generate_row, generate_footer, generate_summary, generate_k4_blocks, assemble_blocks
from k4sru.sru import K4_FIELD_CODES_A, K4_FIELD_CODES_C, OUTPUT_DIR

class TestSRUFunctions(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

    def test_generate_info_sru_001(self):
        data = {
            'orgnr': '1234567890',
            'namn': 'Test Company',
            'adress': 'Test Street 1',
            'postnr': '12345',
            'postort': 'Test City',
            'email': 'test@example.com'
        }
        generate_info_sru(data)
        with open(f"{OUTPUT_DIR}INFO.SRU", "r") as file:
            content = file.read()
        expected_content = (
            "#DATABESKRIVNING_START\n"
            "#PRODUKT SRU\n"
            "#FILNAMN BLANKETTER.SRU\n"
            "#DATABESKRIVNING_SLUT\n"
            "#MEDIELEV_START\n"
            "#ORGNR 1234567890\n"
            "#NAMN Test Company\n"
            "#ADRESS Test Street 1\n"
            "#POSTNR 12345\n"
            "#POSTORT Test City\n"
            "#EMAIL test@example.com\n"
            "#MEDIELEV_SLUT\n"
        )
        self.assertEqual(content, expected_content)

    def test_generate_sru_header_001(self):
        config = {
            'orgnr': '1234567890',
            'namn': 'Test Company'
        }
        header = generate_sru_header(config)
        self.assertIn("#BLANKETT K4-2024P4\n", header)
        self.assertIn("#IDENTITET 1234567890", header)
        self.assertIn("#NAMN Test Company\n", header)

    def test_clean_symbo_001(self):
        self.assertEqual(clean_symbol("AAPL.SEK"), "AAPL")
        self.assertEqual(clean_symbol("GOOGL"), "GOOGL")

    def test_generate_row_001(self):
        data = {
            'antal': 10,
            'forsaljningspris': 1000,
            'omkostnadsbelopp': 800
        }
        row = generate_row(1, K4_FIELD_CODES_A, "AAPL", data)
        self.assertIn("#UPPGIFT 3100 10\n", row)
        self.assertIn("#UPPGIFT 3101 AAPL\n", row)
        self.assertIn("#UPPGIFT 3102 1000\n", row)
        self.assertIn("#UPPGIFT 3103 800\n", row)
        self.assertIn("#UPPGIFT 3104 200\n", row)
        self.assertIn("#UPPGIFT 3105 0\n", row)

    def test_generate_footer_001(self):
        footer = generate_footer(1)
        self.assertEqual(footer, "#UPPGIFT 7014 1\n#BLANKETTSLUT\n")

    def test_generate_summary_001(self):
        summary = generate_summary(K4_FIELD_CODES_A, 1000, 800)
        self.assertIn("#UPPGIFT 3300 1000\n", summary)
        self.assertIn("#UPPGIFT 3301 800\n", summary)
        self.assertIn("#UPPGIFT 3304 200\n", summary)
        self.assertIn("#UPPGIFT 3305 0\n", summary)

    def test_generate_k4_blocks_001(self):
        k4_combined_transactions = [
            {'beteckning': 'AAPL', 'antal': 10, 'forsaljningspris': 1000, 'omkostnadsbelopp': 800},
            {'beteckning': 'USD', 'antal': 100, 'forsaljningspris': 1000, 'omkostnadsbelopp': 900}
        ]
        blocks_a, blocks_c, blocks_d = generate_k4_blocks(k4_combined_transactions)
        self.assertEqual(len(blocks_a), 1)
        self.assertEqual(len(blocks_c), 1)
        self.assertEqual(len(blocks_d), 0)

    def test_assemble_blocks_001(self):
        config = {
            'orgnr': '1234567890',
            'namn': 'Test Company'
        }
        blocks_a = ["#UPPGIFT 3100 10\n#UPPGIFT 3101 AAPL\n#UPPGIFT 3102 1000\n#UPPGIFT 3103 800\n#UPPGIFT 3104 200\n#UPPGIFT 3105 0\n"]
        blocks_c = ["#UPPGIFT 3310 100\n#UPPGIFT 3311 USD\n#UPPGIFT 3312 1000\n#UPPGIFT 3313 900\n#UPPGIFT 3314 100\n#UPPGIFT 3315 0\n"]
        blocks_d = []
        file_content = assemble_blocks(config, blocks_a, blocks_c, blocks_d)
        self.assertIn("#UPPGIFT 3100 10\n", file_content)
        self.assertIn("#UPPGIFT 3310 100\n", file_content)
        self.assertIn("#BLANKETTSLUT\n", file_content)

if __name__ == '__main__':
    unittest.main()
