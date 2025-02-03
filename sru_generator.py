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
# Summa           3301 3302 3303 3304
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
    'summa_vinst': '3303',
    'summa_forlust': '3304'
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
# Summa           3400 3401 3402 3403
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

    with open("INFO.SRU", "w") as file:
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

def generate_row(number, symbol, data):
    """Generate a row of data for the SRU file.

    Args:
        symbol: Symbol of the stock
        data: Dictionary containing data for the stock
    """
    row = (f"#UPPGIFT {K4_FIELD_CODES_A[number]['antal']} {data['antal']}\n"
                  f"#UPPGIFT {K4_FIELD_CODES_A[number]['beteckning']} {symbol}\n"
                  f"#UPPGIFT {K4_FIELD_CODES_A[number]['forsaljningspris']} {data['forsaljningspris']}\n"
                  f"#UPPGIFT {K4_FIELD_CODES_A[number]['omkostnadsbelopp']} {data['omkostnadsbelopp']}\n")
    if data['vinst'] < 0:
        row += (f"#UPPGIFT {K4_FIELD_CODES_A[number]['vinst']} 0\n"
                      f"#UPPGIFT {K4_FIELD_CODES_A[number]['forlust']} {abs(data['vinst'])}\n")
    else:
        row += (f"#UPPGIFT {K4_FIELD_CODES_A[number]['vinst']} {data['vinst']}\n"
                     f"#UPPGIFT {K4_FIELD_CODES_A[number]['forlust']} 0\n")
    return row

def generate_footer(blankett):
    footer = (f"#UPPGIFT 7014 {blankett}\n"
              f"#BLANKETTSLUT\n")
    return footer

def generate_summary(summa_forsaljningspris, summa_omkostnadsbelopp, summa_vinst, summa_forlust):
    summary = (f"#UPPGIFT {K4_FIELD_CODES_C['summa_forsaljningspris']} {summa_forsaljningspris}\n"
               f"#UPPGIFT {K4_FIELD_CODES_C['summa_omkostnadsbelopp']} {summa_omkostnadsbelopp}\n"
               f"#UPPGIFT {K4_FIELD_CODES_C['summa_vinst']} {summa_vinst}\n"
               f"#UPPGIFT {K4_FIELD_CODES_C['summa_forlust']} {summa_forlust}\n")
    return summary


def generate_body(config, k4_combined_transactions):
    """Process K4 transactions into SRU file format.

    Args:
        k4_combined_transactions: Dictionary of combined K4 transactions

    Returns:
        str: Formatted K4 data for SRU file
    """
    file_body = ""
    MAX_ROWS = 9
    processed_rows = 0
    blankett = 0

    summa_forsaljningspris = 0
    summa_omkostnadsbelopp = 0
    summa_vinst = 0
    summa_forlust = 0

    for i, (symbol, data) in enumerate(k4_combined_transactions.items(), 1):
        if processed_rows == 0:
            file_body += generate_sru_header(config)
        file_body += generate_row(processed_rows + 1, symbol, data) # row number starts from 1
        summa_forsaljningspris += data['forsaljningspris']
        summa_omkostnadsbelopp += data['omkostnadsbelopp']
        if data['vinst'] < 0:
            summa_forlust += abs(data['vinst'])
        else:
            summa_vinst += data['vinst']
        processed_rows += 1
        if processed_rows == MAX_ROWS:
            file_body += generate_summary(summa_forsaljningspris, summa_omkostnadsbelopp, summa_vinst, summa_forlust)
            file_body += generate_footer(blankett)
            processed_rows = 0
            blankett += 1
            summa_forsaljningspris = 0
            summa_omkostnadsbelopp = 0
            summa_vinst = 0
            summa_forlust = 0

    if processed_rows < MAX_ROWS:
        file_body += generate_summary(summa_forsaljningspris, summa_omkostnadsbelopp, summa_vinst, summa_forlust)
        file_body += generate_footer(blankett)

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

    with open("BLANKETTER.SRU", "w") as file:
        file.write(file_content)

    logging.info("BLANKETTER.SRU file generated successfully.")