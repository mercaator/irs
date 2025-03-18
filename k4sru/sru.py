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
from datetime import datetime
import os

OUTPUT_DIR = "output/"

# A. Marknadsnoterade aktier, aktieindexobligationer, aktieoptioner m.m.
#       Ant. Bet. F.   Om.  V.   F.
# Rad 1 3100 3101 3102 3103 3104 3105
# Rad 2 3110 3111 3112 3113 3114 3115
# Rad 3 3120 3121 3122 3123 3124 3125
# Rad 4 3130 3131 3132 3133 3134 3135
# Rad 5 3140 3141 3142 3143 3144 3145
# Rad 6 3150 3151 3152 3153 3154 3155
# Rad 7 3160 3161 3162 3163 3164 3165
# Rad 8 3170 3171 3172 3173 3174 3175
# Rad 9 3180 3181 3182 3183 3184 3185
# Summa           3300 3301 3304 3305
K4_FIELD_CODES_A = {
    1: {'antal': '3100',
        'beteckning': '3101',
        'forsaljningspris': '3102',
        'omkostnadsbelopp': '3103',
        'vinst': '3104',
        'forlust': '3105'},
    2 : {'antal': '3110',
         'beteckning': '3111',
         'forsaljningspris': '3112',
         'omkostnadsbelopp': '3113',
         'vinst': '3114',
         'forlust': '3115'},
    3 : {'antal': '3120',
         'beteckning': '3121',
         'forsaljningspris': '3122',
         'omkostnadsbelopp': '3123',
         'vinst': '3124',
         'forlust': '3125'},
    4 : {'antal': '3130',
         'beteckning': '3131',
         'forsaljningspris': '3132',
         'omkostnadsbelopp': '3133',
         'vinst': '3134',
         'forlust': '3135'},
    5 : {'antal': '3140',
         'beteckning': '3141',
         'forsaljningspris': '3142',
         'omkostnadsbelopp': '3143',
         'vinst': '3144',
         'forlust': '3145'},
    6 : {'antal': '3150',
         'beteckning': '3151',
         'forsaljningspris': '3152',
         'omkostnadsbelopp': '3153',
         'vinst': '3154',
         'forlust': '3155'},
    7 : {'antal': '3160',
         'beteckning': '3161',
         'forsaljningspris': '3162',
         'omkostnadsbelopp': '3163',
         'vinst': '3164',
         'forlust': '3165'},
    8 : {'antal': '3170',
         'beteckning': '3171',
         'forsaljningspris': '3172',
         'omkostnadsbelopp': '3173',
         'vinst': '3174',
         'forlust': '3175'},
    9 : {'antal': '3180',
         'beteckning': '3181',
         'forsaljningspris': '3182',
         'omkostnadsbelopp': '3183',
         'vinst': '3184',
         'forlust': '3185'},
    'summa_forsaljningspris': '3300',
    'summa_omkostnadsbelopp': '3301',
    'summa_vinst': '3304',
    'summa_forlust': '3305'
    }

# C. Marknadsnoterade obligationer, valuta m.m.
#       Ant. Bet. F.   Om.  V.   F.
# Rad 1 3310 3311 3312 3313 3314 3315
# Rad 2 3320 3321 3322 3323 3324 3325
# Rad 3 3330 3331 3332 3333 3334 3335
# Rad 4 3340 3341 3342 3343 3344 3345
# Rad 5 3350 3351 3352 3353 3354 3355
# Rad 6 3360 3361 3362 3363 3364 3365
# Rad 7 3370 3371 3372 3373 3374 3375
# Summa           3400 3401 3403 3404
K4_FIELD_CODES_C = {
    1 : {'antal': '3310',
         'beteckning': '3311',
         'forsaljningspris': '3312',
         'omkostnadsbelopp': '3313',
         'vinst': '3314',
         'forlust': '3315'},
    2 : {'antal': '3320',
         'beteckning': '3321',
         'forsaljningspris': '3322',
         'omkostnadsbelopp': '3323',
         'vinst': '3324',
         'forlust': '3325'},
    3 : {'antal': '3330',
         'beteckning': '3331',
         'forsaljningspris': '3332',
         'omkostnadsbelopp': '3333',
         'vinst': '3334',
         'forlust': '3335'},
    4 : {'antal': '3340',
         'beteckning': '3341',
         'forsaljningspris': '3342',
         'omkostnadsbelopp': '3343',
         'vinst': '3344',
         'forlust': '3345'},
    5 : {'antal': '3350',
         'beteckning': '3351',
         'forsaljningspris': '3352',
         'omkostnadsbelopp': '3353',
         'vinst': '3354',
         'forlust': '3355'},
    6 : {'antal': '3360',
         'beteckning': '3361',
         'forsaljningspris': '3362',
         'omkostnadsbelopp': '3363',
         'vinst': '3364',
         'forlust': '3365'},
    7 : {'antal': '3370',
         'beteckning': '3371',
         'forsaljningspris': '3372',
         'omkostnadsbelopp': '3373',
         'vinst': '3374',
         'forlust': '3375'},
    'summa_forsaljningspris': '3400',
    'summa_omkostnadsbelopp': '3401',
    'summa_vinst': '3403',
    'summa_forlust': '3404'
}

# D. Övriga värdepapper, andra tillgångar (kapitalplaceringar t.ex. råvaror, kryptovalutor) m.m.
#       Ant. Bet. F.   Om.  V.   F.
# Rad 1 3410 3411 3412 3413 3414 3415
# Rad 2 3420 3421 3422 3423 3424 3425
# Rad 3 3430 3431 3432 3433 3434 3435
# Rad 4 3440 3441 3442 3443 3444 3445
# Rad 5 3450 3451 3452 3453 3454 3455
# Rad 6 3460 3461 3462 3463 3464 3465
# Rad 7 3470 3471 3472 3473 3474 3475
# Summa           3500 3501 3503 3504
K4_FIELD_CODES_D = {
    1 : {'antal': '3410',
         'beteckning': '3411',
         'forsaljningspris': '3412',
         'omkostnadsbelopp': '3413',
         'vinst': '3414',
         'forlust': '3415'},
    2 : {'antal': '3420',
         'beteckning': '3421',
         'forsaljningspris': '3422',
         'omkostnadsbelopp': '3423',
         'vinst': '3424',
         'forlust': '3425'},
    3 : {'antal': '3430',
         'beteckning': '3431',
         'forsaljningspris': '3432',
         'omkostnadsbelopp': '3433',
         'vinst': '3434',
         'forlust': '3435'},
    4 : {'antal': '3440',
         'beteckning': '3441',
         'forsaljningspris': '3442',
         'omkostnadsbelopp': '3443',
         'vinst': '3444',
         'forlust': '3445'},
    5 : {'antal': '3450',
         'beteckning': '3451',
         'forsaljningspris': '3452',
         'omkostnadsbelopp': '3453',
         'vinst': '3454',
         'forlust': '3455'},
    6 : {'antal': '3460',
         'beteckning': '3461',
         'forsaljningspris': '3462',
         'omkostnadsbelopp': '3463',
         'vinst': '3464',
         'forlust': '3465'},
    7 : {'antal': '3470',
         'beteckning': '3471',
         'forsaljningspris': '3472',
         'omkostnadsbelopp': '3473',
         'vinst': '3474',
         'forlust': '3475'},
    'summa_forsaljningspris': '3500',
    'summa_omkostnadsbelopp': '3501',
    'summa_vinst': '3503',
    'summa_forlust': '3504'
}

CURRENCY_CODES = ['USD', 'EUR', 'GBP', 'CHF', 'SEK', 'NOK', 'DKK', 'CAD', 'AUD', 'NZD', 'JPY', 'CNY', 'HKD', 'MXN', 'BRL', 'ARS', 'CLP', 'COP', 'PEN', 'UYU', 'PYG']

def generate_info_sru(data):
    """Generate INFO.SRU file from provided data.

    Args:
        data: Dictionary containing orgnr, namn, adress, postnr, postort, and email
    """
    file_content = (f"#DATABESKRIVNING_START\n"
                   f"#PRODUKT SRU\n"
                   f"#FILNAMN BLANKETTER.SRU\n"
                   f"#DATABESKRIVNING_SLUT\n"
                   f"#MEDIELEV_START\n"
                   f"#ORGNR {data.get('orgnr', '')}\n"
                   f"#NAMN {data.get('namn', '')}\n"
                   f"#ADRESS {data.get('adress', '')}\n"
                   f"#POSTNR {data.get('postnr', '')}\n"
                   f"#POSTORT {data.get('postort', '')}\n"
                   f"#EMAIL {data.get('email', '')}\n"
                   f"#MEDIELEV_SLUT\n")

    # Create output directory if it doesn't exist
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    with open(OUTPUT_DIR + "/INFO.SRU", "w") as file:
        file.write(file_content)

    logging.info("INFO.SRU file generated successfully.")

def generate_sru_header(config):
    """Generate SRU header.

    Args:
        config: Dictionary containing configuration
    """
    file_header = (f"#BLANKETT K4-2024P4\n"
                   f"#IDENTITET {config.get('orgnr', '')} {datetime.now().strftime('%Y%m%d %H%M%S')}\n"
                   f"#NAMN {config.get('namn', '')}\n"
                   )
    return file_header

def clean_symbol(symbol):
    """Clean symbol by removing .SEK if present.

    Args:
        symbol: Symbol to clean
    """
    return symbol[:-4] if symbol.endswith('.SEK') else symbol

def generate_row(number, codes, symbol, data):
    """Generate a row of data for the SRU file.

    Args:
        symbol: Symbol of the stock
        data: Dictionary containing data for the stock
    """
    row = (f"#UPPGIFT {codes[number]['antal']} {data['antal']}\n"
                  f"#UPPGIFT {codes[number]['beteckning']} {clean_symbol(symbol)}\n"
                  f"#UPPGIFT {codes[number]['forsaljningspris']} {data['forsaljningspris']}\n"
                  f"#UPPGIFT {codes[number]['omkostnadsbelopp']} {data['omkostnadsbelopp']}\n")
    vinst = data['forsaljningspris'] - data['omkostnadsbelopp']
    if vinst < 0:
        row += (f"#UPPGIFT {codes[number]['vinst']} 0\n"
                f"#UPPGIFT {codes[number]['forlust']} {abs(vinst)}\n")
    else:
        row += (f"#UPPGIFT {codes[number]['vinst']} {vinst}\n"
                f"#UPPGIFT {codes[number]['forlust']} 0\n")
    return row

def generate_footer(blankett):
    footer = (f"#UPPGIFT 7014 {blankett}\n"
              f"#BLANKETTSLUT\n")
    return footer

def generate_summary(codes, summa_forsaljningspris, summa_omkostnadsbelopp):
    summary = (f"#UPPGIFT {codes['summa_forsaljningspris']} {summa_forsaljningspris}\n"
               f"#UPPGIFT {codes['summa_omkostnadsbelopp']} {summa_omkostnadsbelopp}\n")
    vinst = summa_forsaljningspris - summa_omkostnadsbelopp
    if vinst < 0:
        summary += (f"#UPPGIFT {codes['summa_vinst']} 0\n"
                    f"#UPPGIFT {codes['summa_forlust']} {abs(vinst)}\n")
    else:
        summary += (f"#UPPGIFT {codes['summa_vinst']} {vinst}\n"
                    f"#UPPGIFT {codes['summa_forlust']} 0\n")
    return summary

def generate_k4_blocks(k4_combined_transactions):
    """Process K4 transactions into SRU file format.

    Args:
        k4_combined_transactions: Dictionary of combined K4 transactions
    """
    k4_a_rows = ""
    k4_c_rows = ""
    k4_d_rows = ""
    k4_a_counter = 0
    k4_c_counter = 0
    k4_d_counter = 0

    blocks_a = []
    blocks_c = []
    blocks_d = []

    MAX_SHARE_ROWS = 9
    MAX_VALUTA_ROWS = 7
    MAX_OTHER_ROWS = 7

    summa_forsaljningspris_a = 0
    summa_omkostnadsbelopp_a = 0
    summa_forsaljningspris_c = 0
    summa_omkostnadsbelopp_c = 0
    summa_forsaljningspris_d = 0
    summa_omkostnadsbelopp_d = 0

    for data in k4_combined_transactions:
        symbol = data['beteckning']
        forsaljningspris = data['forsaljningspris']
        omkostnadsbelopp = data['omkostnadsbelopp']
        if symbol not in CURRENCY_CODES and not (' ' in symbol and any(c.isdigit() for c in symbol)): # Aktier
            k4_a_counter += 1
            logging.debug(f"Aktie: {symbol} row {k4_a_counter}")
            k4_a_rows += generate_row(k4_a_counter, K4_FIELD_CODES_A, symbol, data)
            summa_forsaljningspris_a += forsaljningspris
            summa_omkostnadsbelopp_a += omkostnadsbelopp

            if k4_a_counter == MAX_SHARE_ROWS:
                logging.debug(f"Aktie: A summary")
                k4_a_rows += generate_summary(K4_FIELD_CODES_A, summa_forsaljningspris_a, summa_omkostnadsbelopp_a)
                blocks_a.append(k4_a_rows)
                k4_a_counter = 0
                summa_forsaljningspris_a = 0
                summa_omkostnadsbelopp_a = 0
                k4_a_rows = ""
        elif symbol not in CURRENCY_CODES: # Other (options, BTC, etc.)
            k4_d_counter += 1
            logging.debug(f"Övriga värdepapper: {symbol} row {k4_d_counter}")
            k4_d_rows += generate_row(k4_d_counter, K4_FIELD_CODES_D, symbol, data)
            summa_forsaljningspris_d += forsaljningspris
            summa_omkostnadsbelopp_d += omkostnadsbelopp

            if k4_d_counter == MAX_SHARE_ROWS:
                logging.debug(f"Aktie: A summary")
                k4_d_rows += generate_summary(K4_FIELD_CODES_D, summa_forsaljningspris_d, summa_omkostnadsbelopp_d)
                blocks_d.append(k4_d_rows)
                k4_d_counter = 0
                summa_forsaljningspris_d = 0
                summa_omkostnadsbelopp_d = 0
                k4_d_rows = ""
        else: # Valuta
            k4_c_counter += 1
            logging.debug(f"Valuta: {symbol} row {k4_c_counter}")
            k4_c_rows += generate_row(k4_c_counter, K4_FIELD_CODES_C, symbol, data)
            summa_forsaljningspris_c += forsaljningspris
            summa_omkostnadsbelopp_c += omkostnadsbelopp

            if k4_c_counter == MAX_VALUTA_ROWS:
                logging.debug(f"Valuta: C summary")
                k4_c_rows += generate_summary(K4_FIELD_CODES_C, summa_forsaljningspris_c, summa_omkostnadsbelopp_c)
                blocks_c.append(k4_c_rows)
                k4_c_counter = 0
                summa_forsaljningspris_c = 0
                summa_omkostnadsbelopp_c = 0
                k4_c_rows = ""
    if k4_a_counter > 0:
        logging.debug(f"Aktie: A summary")
        k4_a_rows += generate_summary(K4_FIELD_CODES_A, summa_forsaljningspris_a, summa_omkostnadsbelopp_a)
        blocks_a.append(k4_a_rows)


    if k4_c_counter > 0:
        logging.debug(f"Valuta: C summary")
        k4_c_rows += generate_summary(K4_FIELD_CODES_C, summa_forsaljningspris_c, summa_omkostnadsbelopp_c)
        blocks_c.append(k4_c_rows)

    if k4_d_counter > 0:
        logging.debug(f"Övriga värdepapper: D summary")
        k4_d_rows += generate_summary(K4_FIELD_CODES_D, summa_forsaljningspris_d, summa_omkostnadsbelopp_d)
        blocks_d.append(k4_d_rows)

    return blocks_a, blocks_c, blocks_d

def assemble_blocks(config, blocks_a, blocks_c, blocks_d):
    """Assemble blocks into a single SRU file.

    Args:
        config: Dictionary containing configuration
        blocks_a: List of blocks for A
        blocks_c: List of blocks for C
        blocks_d: List of blocks for D
    """
    file_content = ""
    logging.debug(f"Blocks A: {len(blocks_a)}")
    logging.debug(f"Blocks C: {len(blocks_c)}")
    logging.debug(f"Blocks C: {blocks_c}")
    logging.debug(f"Blocks D: {len(blocks_d)}")
    logging.debug(f"Blocks D: {blocks_d}")
    for i, block in enumerate(blocks_a, 1):
        file_content += generate_sru_header(config)
        file_content += block
        if len(blocks_c) > 0:
            file_content += blocks_c[0]
            del blocks_c[0]
        if len(blocks_d) > 0:
            file_content += blocks_d[0]
            del blocks_d[0]
        file_content += generate_footer(i)

    # Improbable, but possible
    if len(blocks_c) > 0:
        for i, block in enumerate(blocks_c, 1):
            file_content += generate_sru_header(config)
            file_content += block
            if len(blocks_d) > 0:
                file_content += blocks_d[0]
                del blocks_d[0]
            file_content += generate_footer(i)

    return file_content


def generate_body(config, k4_combined_transactions):
    """Process K4 transactions into SRU file format.

    Args:
        k4_combined_transactions: Dictionary of combined K4 transactions

    Returns:
        str: Formatted K4 data for SRU file
    """
    file_body = ""
    blocks_a, blocks_c, blocks_d = generate_k4_blocks(k4_combined_transactions)
    file_body += assemble_blocks(config, blocks_a, blocks_c, blocks_d)
    return file_body

def generate_blanketter_sru(config, k4_combined_transactions):
    """Generate BLANKETTER.SRU file from K4 trading data.

    Args:
        config: Dictionary containing configuration
        k4_combined_transactions: Dictionary containing combined K4 transactions
    """
    # Initialize file_content first
    file_content = ""
    file_body = generate_body(config, k4_combined_transactions)
    file_content += file_body
    file_content += "#FIL_SLUT\n"

    with open(OUTPUT_DIR + "BLANKETTER.SRU", "w") as file:
        file.write(file_content)

    logging.info("BLANKETTER.SRU file generated successfully.")