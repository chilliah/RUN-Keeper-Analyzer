# RUN-Keeper-Analyzer
Maybe something with the potential to make the life of our glorious commish easier.

## Description

Uses the Yahoo API to generate a list of keepers for The R.U.N League.

## Getting Started

### Dependencies

This script requires python 3.x. As with all python projects, I recommend using a virtual environment.

Required Packages: 
* docopt==0.6.2
* pandas==0.25.1
* yahoo_oauth==0.1.9
* yahoo_fantasy_api==1.2.0

### Installation

To install required packages: ```pip install -r requirements.txt```

### Executing program

```
python auth.py
python generate_keepers.py --year 2018 --File False
```

## Help

usage: generate_keepers.py [-h] --year YEAR [--file FILE] [--rules RULES]
                           [--cost COST]

Generates a list of eligible keepers for The R.U.N. League.

       You must first authenticate with Yahoo using 'python auth.py'. You only need to authenticate once.
       For first time use, the --file flag must be False. Ex: 'python generate_keepers.py --year 2018 --file False

       You must specify a year with '--year'
       To get new data from the Yahoo API, use the optional argument '--file False'
       To use the old keeper rules, use the optional argument '--rules old'
       To only print the average draft cost for each position, use the optional argument '--cost True'

optional arguments:
 * -h, --help     show this help message and exit
 * --year YEAR    Year to generate keeper list
 * --file FILE    If False, get new data from the Yahoo API
 * --rules RULES  If old, use old keeper rules.
 * --cost COST    If True, only print the draft costs.
