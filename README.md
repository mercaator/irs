# IRS

IRS is a Python-based tool designed to process trading data and generate Swedish tax reports (K4 SRU files).

## Flex Query Configuration

The input data shall be in a specific file format used by Interactive Brokers. You should create a flex query with the following parameters:

#### Delivery Configuration
- From Trades->Execution section select:

  ```Date/Time, Symbol, Buy/Sell, Quantity, TradePrice, IB Commission, Currency, Description, ISIN, Exchange```

- Models: ```Optional```
- Format: ```CSV```
- Include header and trailer records: ```No```
- Include column Headers: ```Yes```
- Display single column header row: ```No```
- Include section code and line descriptor: ```No```
- Period: ```Year to Date```

#### General Configuration
- Date Format: ```yyyyMMdd```
- Time Format: ```HHmmss```
- Date/Time Separator: ```; (semi-colon)```
- Profit and Loss: ```Default```
- Include Cancelled Trades: ```No```
- Include Currency Rates: ```Yes```
- Include Audit Trail Fields: ```No```
- Display Account Alias in Place of Account ID: ```No```
- Breakout by Day: ```No```

#### Sample file format

```
"DateTime","Symbol","Buy/Sell","Quantity","TradePrice","IBCommission","CurrencyPrimary","Description","ISIN","Exchange"
"20250225;030616","RHMd","BUY","2","985.4","-3","EUR","RHEINMETALL AG","DE0007030009","IBIS"
...
"Date/Time","FromCurrency","ToCurrency","Rate"
"20250225","EUR","USD","1.0515"
```

## List of generated files

- INFO.SRU         - tax payer information
- BLANKETTER.SRU   - transaction data for each stock sold during the tax year
- output_portfolio_\<```year```\>.json - portfolio data at the end of the tax year
- output_statistics_\<```year```\>.csv - profit/loss statistics for post-processing e.g. pandas

## Features

- **Generate SRU Files**: Generate `INFO.SRU` and `BLANKETTER.SRU` files for Swedish tax reporting.
- **Input Data**: IBKR is the only supported input format.
- **Supported Assets**: stocks, FX currency pairs, ETFs and a single option (IBIT).
- **Customizable Configuration**: Use a `config.json` file to provide organization details and other settings.
- **Detailed Logging**: Logs all operations for easy debugging and auditing.
- **Test Coverage**: Includes unittests for key functions with coverage reporting.

## Installation

Clone the repository:
   ```bash
   git clone <repository-url>
   cd irs
   ```

## Usage

### Command-Line Interface

Run the main script with the desired commands:
```bash
python irs.py <command> [options]
```

#### Available Commands

- `k4sru`: Generate K4 SRU files (```INFO.SRU``` and ```BLANKETTER.SRU```) from trading data.step.

#### Common Options

- `--config <path>`: path to configuration file (default: `input/config.json`).
- `--indata <path>`: input CSV file with trade data
- `--indata2 <path>`: optional secondary input CSV file with additional trade data (e.g., Bitstamp trades)
- `--year <YYYY>`: tax year for which to generate the K4 SRU files (default: `2025`).
- `--debug <level>`: set logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`).

#### Configuration File Fields

The configuration file (`config.json`) should include:

- `orgnr`: Organization number or personal ID.
- `namn`: Name of the organization/person.
- `adress`: Street address.
- `postnr`: Postal code.
- `postort`: City.
- `email`: Email address.

### Example

Generate SRU files for the tax year 2024:
```
python irs.py k4sru --indata input/indata_ibkr_sample.csv --longnames --year 2024
```
```
2025-06-01 13:23:09,873 - INFO - INFO.SRU file generated successfully.
2025-06-01 13:23:09,873 - INFO - Portfolio file input_portfolio_2024.json not found
2025-06-01 13:23:09,874 - INFO - 9 stock trades and 9 currency rates have been read from input/indata_ibkr_sample.csv.
2025-06-01 13:23:09,874 - INFO - Currency rates file input_currency_rates_2024.json not found
2025-06-01 13:23:09,874 - INFO -     ==> Processing k4 entry: EUR (EUR), -1973.8, 11.14349300551081, 0, 11.4833, SEK, 20250225;030616
2025-06-01 13:23:09,875 - INFO -     ==> K4 Tax event - Profit/Loss: -670.7110457227609
2025-06-01 13:23:09,875 - INFO -     ==> Processing k4 entry: EUR (EUR), -1975.8, 11.18352422433726, 0, 11.19794328937757, SEK, 20250227;040318
2025-06-01 13:23:09,875 - INFO -     ==> K4 Tax event - Profit/Loss: -28.4891887066442
2025-06-01 13:23:09,875 - INFO -     ==> Processing k4 entry: EUR (EUR), -14763.87825, 10.911423606901847, 0, 11.107300293644535, SEK, 20250324;070718
2025-06-01 13:23:09,876 - INFO -     ==> K4 Tax event - Profit/Loss: -2891.899555082433
2025-06-01 13:23:09,876 - INFO -     ==> Processing k4 entry: EUR (EUR), -6710.85375, 10.911423606901847, 0, 11.107300293644535, SEK, 20250324;070718
2025-06-01 13:23:09,876 - INFO -     ==> K4 Tax event - Profit/Loss: -1314.4997977647436
2025-06-01 13:23:09,876 - INFO -     ==> Processing k4 entry: RHMd (RHEINMETALL AG), -20.0, 1291.0, 12.91, 13920.566567670665, EUR, 20250404;071423
2025-06-01 13:23:09,876 - INFO -     ==> K4 Tax event - Profit/Loss: 4285.638740511611
2025-06-01 13:23:09,877 - INFO - ==> Total profit/loss: -619.9608467649668
2025-06-01 13:23:09,878 - INFO - Saved portfolio data for 2024
2025-06-01 13:23:09,879 - INFO - Saved statistics data for 2024
2025-06-01 13:23:09,880 - INFO - BLANKETTER.SRU file generated successfully.
```
#### Generated INFO.SRU

```
#DATABESKRIVNING_START
#PRODUKT SRU
#FILNAMN BLANKETTER.SRU
#DATABESKRIVNING_SLUT
#MEDIELEV_START
#ORGNR 123456789012
#NAMN Example Name
#ADRESS Street 123
#POSTNR 12345
#POSTORT City Name
#EMAIL example@email.com
#MEDIELEV_SLUT
```

#### Generated BLANKETTER.SRU

```
#BLANKETT K4-2024P4
#IDENTITET 123456789012 20250601 132309
#NAMN Example Name
#UPPGIFT 3100 20
#UPPGIFT 3101 RHEINMETALL AG
#UPPGIFT 3102 282697
#UPPGIFT 3103 278411
#UPPGIFT 3104 4286
#UPPGIFT 3105 0
#UPPGIFT 3300 282697
#UPPGIFT 3301 278411
#UPPGIFT 3304 4286
#UPPGIFT 3305 0
#UPPGIFT 3310 25424
#UPPGIFT 3311 EUR
#UPPGIFT 3312 278411
#UPPGIFT 3313 283317
#UPPGIFT 3314 0
#UPPGIFT 3315 4906
#UPPGIFT 3400 278411
#UPPGIFT 3401 283317
#UPPGIFT 3403 0
#UPPGIFT 3404 4906
#UPPGIFT 7014 1
#BLANKETTSLUT
#FIL_SLUT
```

## Testing

Run unittests with coverage:

### On Unix-like Systems
```bash
./run_coverage.sh
```

### On Windows
```cmd
run_coverage.bat
```

View the HTML coverage report by opening `htmlcov/index.html` in a browser.

## Directory Structure

```
irs/
├── k4sru/                 # Core logic for SRU generation
│   ├── __init__.py
│   ├── data.py
│   ├── sru.py
├── tests/                 # Unit tests
│   ├── test_data.py
│   ├── test_sru.py
├── input/                 # Input files (e.g., config.json, trading data)
├── output/                # Generated SRU files
├── run_coverage.sh        # Coverage script for Unix-like systems
├── run_coverage.bat       # Coverage script for Windows
├── .coveragerc            # Coverage configuration
├── README.md              # Project documentation
└── irs.py                 # Main script
```

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.
