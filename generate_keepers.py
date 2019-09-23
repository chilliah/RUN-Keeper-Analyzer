import argparse
import json
import math
import time
from datetime import datetime
from pprint import pformat
from textwrap import dedent

import pytz
from yahoo_fantasy_api import game
from yahoo_oauth import OAuth2


def get_api_values(year):
    """ Get the api for the RUN league

    Args:
        year (int): Year of RUN for which we want to get keepers

    Returns:
        league_api (str): API string for the RUN league

    """
    sc = OAuth2(None, None, from_file='oauth2.json')
    gm = game.Game(sc, 'nfl')
    ids = gm.league_ids()
    print(ids)
    league_ids = gm.league_ids(year=year)
    print('league id {}'.format(league_ids))
    for league_id in league_ids:
        lg = gm.to_league(league_id)
        settings = lg.settings()
        print('settings {}'.format(settings))
        print('Name: {}'.format(settings['name']))
        if settings['name'] == 'The R.U.N. League':
            league_api = league_id
            print('RUN league API {}'.format(league_api))

    return league_api


def get_draft_results(run_api):
    """ Get the draft results from Yahoo API

    Args:
        run_api (str): API key for the RUN league

    Returns:
        drafted_players (dict): { Player Key: { Draft Cost: $$$$, Draft Team: Team Key}}
    """
    sc = OAuth2(None, None, from_file='oauth2.json')
    url = ('https://fantasysports.yahooapis.com/fantasy/v2/league/{}/draftresults'.format(run_api))
    response = sc.session.get(url, params={'format': 'json'})
    r = response.json()

    with open('data_files/draft.json', 'w') as f:
        f.write(json.dumps(r))

    print('{}'.format(pformat(r)))

    with open('data_files/draft.json') as f:
        data = json.load(f)

    drafted_players = dict()

    for key, value_dict in data['fantasy_content']['league'][1]['draft_results'].items():
        if key == 'count':
            continue

        player_key = value_dict['draft_result']['player_key']
        draft_cost = value_dict['draft_result']['cost']
        draft_team = value_dict['draft_result']['team_key']

        print('Key {}: Player Key: {} Cost: {}'.format(key, player_key, draft_cost))

        drafted_players[player_key] = dict()

        drafted_players[player_key] = {'draft cost': draft_cost, 'draft team': draft_team}

    print(drafted_players)

    return drafted_players


def get_team_names(run_api):
    """ Get the team key for every team in the league

    Args:
        run_api (str): API for the RUN league

    Returns:
        team_names (dict): Dictionary of Team Keys and Manager Names
    """
    sc = OAuth2(None, None, from_file='oauth2.json')
    url = ('https://fantasysports.yahooapis.com/fantasy/v2/league/{}/teams'.format(run_api))
    response = sc.session.get(url, params={'format': 'json'})
    r = response.json()

    with open('data_files/teams.json', 'w') as f:
        # r = r.replace("\'", "\"")
        f.write(json.dumps(r))

    print('{}'.format(pformat(r)))

    with open('data_files/teams.json') as f:
        data = json.load(f)

    # print('{}'.format(pfromat(data['fantasy_content']['league']['draft_results'][0])))
    print('{}'.format(pformat(data)))

    print('{}'.format(pformat(data['fantasy_content']['league'][1]['teams'])))

    team_names = dict()

    for key, value_dict in data['fantasy_content']['league'][1]['teams'].items():
        if key == 'count':
            continue

        team_key = value_dict['team'][0][0]['team_key']
        manager_name = value_dict['team'][0][19]['managers'][0]['manager']['nickname']
        # print('{}'.format(value_dict['team'][0][0]))
        print('Key {}: Team Key: {} Manager Name: {}'.format(key, team_key, manager_name))

        team_names[team_key] = manager_name

    print(team_names)

    for key in team_names:
        print(key)

    return team_names


def get_all_rosters(team_names):
    """ Get the roster at week 15 for each team.

    Loop through team_names. For each manager, get the roster at the end of the season. Insert the player, the
    player_key, the draft cost, and the draft team into the player_names dictionary

    player_names dictionary has the following structure:
    {Manager Name: { Player Name: {Player Key: Key, draft cost: cost, draft team: team key}}}

    Args:
        team_names (dict): Dictionary of a Team Key and manager name.

    Returns:
        player_names (dict): Dictionary of all the players rostered by a team at the end of the season
    """
    sc = OAuth2(None, None, from_file='oauth2.json')

    # This is where we will store the manager and player data. This dictionary will be:
    player_names = dict()

    # Loop through the teams.
    for team in team_names:
        manager_name = team_names[team]
        print(manager_name)

        url = 'https://fantasysports.yahooapis.com/fantasy/v2/team/{}/roster;week=16'.format(team)
        response = sc.session.get(url, params={'format': 'json'})
        r = response.json()

        # Write the data to the rosters.json in case we need it in the future.
        with open('data_files/rosters.json', 'w') as f:
            f.write(json.dumps(r))

        with open('data_files/rosters.json') as f:
            data = json.load(f)

        player_names[team_names[team]] = dict()

        # The player data for a team roster is stored as a list of dictionaries in the Yahoo API. We need to loop list
        # and get each dictionary so we can get the player name and key of each player rostered.
        for key, value_dict in data['fantasy_content']['team'][1]['roster']['0']['players'].items():
            if key == 'count':
                continue
            print('Key {}: Player Key: {} Player Name: {}'.format(key, value_dict['player'][0][0]['player_key'],
                                                                  value_dict['player'][0][2]['name']['full']))

            player_key = value_dict['player'][0][0]['player_key']
            player_name = value_dict['player'][0][2]['name']['full']

            player_names[manager_name][player_name] = dict()
            player_names[manager_name][player_name]['key'] = player_key

        time.sleep(1)

    print('{}'.format(pformat(player_names)))

    return player_names


def determine_drafted_players(drafted_dict, rostered_dict):
    """ Check if a rostered player was drafted

    Loop through teams in rostered_players dictionary. For each team, check if the player was drafted. If the player
    was drafted then add the draft cost player entry in rostered_players. If the player was not drafted, remove
    the player from the rostered_players dictionary.

    Args:
        drafted_dict (dict): Dictionary representing the Player Key and Draft cost.
        rostered_dict (dict): Dictionary for all players owned by a team.

    Returns:
        rostered_dict (dict): Dictionary of players organized by team that were drafted.
    """
    print('{}'.format(pformat(drafted_dict)))
    print('{}'.format(pformat(rostered_dict)))

    # Loop through
    for team in list(rostered_dict):
        print(team)
        for player in list(rostered_dict[team]):
            print(player)
            print(rostered_dict[team][player])
            player_key = rostered_dict[team][player]['key']
            # for player_key in list(rostered_players[team][player]):
            if player_key in drafted_dict:
                print('{} was drafted'.format(player))
                rostered_dict[team][player]['draft cost'] = drafted_dict[player_key]['draft cost']
                rostered_dict[team][player]['draft team'] = drafted_dict[player_key]['draft team']
            else:
                print('{} was not drafted. Removing from Dictionary'.format(player))
                del (rostered_dict[team][player])

    print('{}'.format(pformat(rostered_dict)))

    return rostered_dict


def parse_transaction_data():
    """ Go through all the transactions and get the relevant data.

    transaction_data dictionary structure:
    { Transaction Key: { Player 1: { Type: 'add', 'drop', 'trade',
                                     Destination: 'team key', 'waiver', 'FA'
                                     Source Type: 'waiver', 'team', 'FA'
                                     }
                        }
                       { Player 2: { Type: 'add', 'drop', 'trade',
                                     Destination: 'team key', 'waiver', 'FA'
                                     Source Type: 'waiver', 'team', 'FA'
                                     }
                        }

                       {timestamp: 'timestamp stored as a datetime object in the dictionary.'}
                        }
    }

    Returns:
        transaction_data (dict): Dictionary of transaction data

    """
    sc = OAuth2(None, None, from_file='oauth2.json')
    url = 'https://fantasysports.yahooapis.com/fantasy/v2/league/380.l.841493/transactions'
    response = sc.session.get(url, params={'format': 'json'})
    r = response.json()

    print('{}'.format(pformat(r)))

    with open('data_files/transactions.json', 'w') as f:
        # r = r.replace("\'", "\"")
        f.write(json.dumps(r))

    print('{}'.format(pformat(r)))

    with open('data_files/transactions.json') as f:
        data = json.load(f)

    transactions = data['fantasy_content']['league'][1]['transactions']

    print('{}'.format(pformat(transactions)))

    # Dictionary to hold transaction data
    transaction_data = dict()

    for transaction in transactions:
        if transaction == 'count':
            continue
        if transactions[transaction]['transaction'][0]['type'] == 'commish':
            continue
        print('Transaction Number {}'.format(transaction))
        transaction_key = transactions[transaction]['transaction'][0]['transaction_key']
        timestamp = transactions[transaction]['transaction'][0]['timestamp']

        # Timestamp in the JSON is UNIX time. Convert this to a UTC datetime object.
        # This will need to be converted back to a str using
        # datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')), if we want to store this as a json anywhere.
        utc_timestamp = datetime.utcfromtimestamp(int(timestamp))

        utc_timestamp_str = utc_timestamp.strftime('%Y-%m-%d %H:%M:%S')

        # Set high level dictionary before we insert the player dictionary for each transaction
        transaction_data[transaction_key] = dict()
        # transaction_data[transaction_key]['timestamp'] = utc_timestamp
        transaction_data[transaction_key]['timestamp'] = utc_timestamp_str

        players = transactions[transaction]['transaction'][1]['players']

        # The players in a transaction is stored as a dictionary. That dictionary looks like this:
        # {'players': {'0': {'player': [[{'player_key': '380.p.30994'},
        # This means we need to loop through all the players in the transaction to get the player key and status
        # for each transaction
        for player in players:
            if player == 'count':
                continue
            print('Player: {}'.format(player))

            player_key = players[player]['player'][0][0]['player_key']

            transaction_data[transaction_key][player_key] = dict()
            transaction_data_from_json = players[player]['player'][1]['transaction_data']

            # The transaction data can either be a list or a dict. If it is a list, we need to iterate through the list
            # to make sure we get every player that is part of the transaction. If the transaction is a dict, then
            # we can access the information directly.
            if type(transaction_data_from_json) is list:
                # For reasons that I can not figure out, the 'add' of a waiver claim transaction is a list while the
                # drop is a dictionary. From the years worth of transaction data in our league, I can never see a
                # situation where this list has more than 1 element in it. However, since it is a list it is
                # technically possible.
                for list_transaction in transaction_data_from_json:
                    if list_transaction == 'count':
                        continue

                    destination_team = list_transaction['destination_team_key']
                    transaction_type = list_transaction['type']
                    source_type = list_transaction['source_type']

                    transaction_data[transaction_key][player_key]['type'] = transaction_type
                    transaction_data[transaction_key][player_key]['source'] = source_type
                    transaction_data[transaction_key][player_key]['destination'] = destination_team

            elif type(transaction_data_from_json) is dict:
                destination_type = transaction_data_from_json['destination_type']
                transaction_type = transaction_data_from_json['type']
                source_type = transaction_data_from_json['source_type']

                transaction_data[transaction_key][player_key]['type'] = transaction_type
                transaction_data[transaction_key][player_key]['source'] = source_type
                transaction_data[transaction_key][player_key]['destination'] = destination_type

    print('{}'.format(pformat(transaction_data)))

    return transaction_data


def old_eligible_keepers(player_dict, transaction_dict):
    """ Get the eligible keepers

    Go through the dictionary of drafted players that were rostered week 15. If they are not eligible to be kept remove
    them from the dictionary.

    Args:
        player_dict (dict): Dictionary of players there were rostered in week 15 and drafted
        transaction_dict (dict): Dictionary of parsed transaction data.

    Returns:
        final_keeper_dict (dict): The final dictionary of players that are eligible to be kept.
    """

    dropped_players = dict()
    free_agent_players = dict()

    for team in list(player_dict):
        # For every player that was drafted and is on a roster at the end of the season
        for player in list(player_dict[team]):
            print('Player: {}'.format(pformat(player)))
            player_key = player_dict[team][player]['key']

            print('Player Key = {}'.format(player_key))

            # Look through all the transactions. If the player is in the transaction, then check what type of
            # transaction. If the player was added off of freeagents, they are not eligible to be kept. Remove them
            # from the player_dict. If the player was dropped, add them to a dropped player list.
            for transaction in transaction_dict:
                # If the player is in the transaction data, check how that player was added.
                if player_key in transaction_dict[transaction]:
                    # If the player was added off of free agents, that player is not eligible to be kept. Add them to
                    # a free_agent_player dictionary.
                    if transaction_dict[transaction][player_key]['type'] == 'add' and\
                            transaction_dict[transaction][player_key]['source'] == 'freeagents':
                        print('Transaction ID: {}'.format(transaction))
                        print('{} {} was added off of freeagents. Remove from keeper list'.format(player, player_key))
                        free_agent_players[player_key] = player

                        print('{}'.format(pformat(player_dict[team])))
                        print('{}'.format(pformat(team)))

                    # If the player was dropped, add that player to the dropped_players dictionary.
                    if transaction_dict[transaction][player_key]['type'] == 'drop':
                        print('transaction: {}'.format(transaction))
                        print('{} {} was added off of freeagents. Remove from keeper list'.format(player, player_key))
                        dropped_players[player_key] = player

    print('{}'.format(pformat(player_dict)))

    print(dropped_players)
    print(len(dropped_players))
    print(free_agent_players)
    print(len(free_agent_players))

    # Loop through the dropped_players dictionary. If a player is also in the free_agent dictionary, then that player
    # is not eligible. Remove them from the dropped_player list.
    for player in list(dropped_players):
        if player in list(free_agent_players):
            del(dropped_players[player])
            # print('{} is not in both lists'.format(dropped_players[player]))

    print(dropped_players)
    print(len(dropped_players))

    # For every dropped player left, go through the transaction data to get the drop time.
    for player_key in dropped_players:
        player = dropped_players[player_key]
        print(player_key)
        # Initialize lists of times a player was dropped and added.
        list_drop_times = []
        list_add_times = []
        for transaction in transaction_dict:
            # print(transaction)
            if player_key in transaction_dict[transaction]:
                if transaction_dict[transaction][player_key]['type'] == 'drop':
                    # print('Drop time for {} is {}'.format(player, transaction_dict[transaction]['timestamp']))
                    timestamp = datetime.strptime(transaction_dict[transaction]['timestamp'], '%Y-%m-%d %H:%M:%S')
                    list_drop_times.append(timestamp)
                if transaction_dict[transaction][player_key]['type'] == 'add':
                    # print('Add time for {} is {}'.format(player, transaction_dict[transaction]['timestamp']))
                    timestamp = datetime.strptime(transaction_dict[transaction]['timestamp'], '%Y-%m-%d %H:%M:%S')
                    list_add_times.append(timestamp)

        sorted_drop_times = sorted(list_drop_times)
        sorted_add_times = sorted(list_add_times)

        print('Drop times for player {}: {}, count {}'.format(player, sorted_drop_times, len(sorted_drop_times)))
        print('Add times for player {}: {}, count {}'.format(player, sorted_add_times, len(sorted_add_times)))

        # Go through the list of drop times. If the difference between the add time and drop time is greater than
        # 3 days, then that player was not picked up off of waivers. Remove them from keeper list.
        for drop_time in sorted_drop_times:
            for add_time in sorted_add_times:
                difference = add_time-drop_time
                print('Time between drops and adds: {}'.format(difference))
                if difference.days >= 3:
                    print('Difference is greater than 3 days. Remove it from the keeper list')
                    for team in player_dict:
                        if player in player_dict[team]:
                            del (player_dict[team][player])

    print('Keeper list: {}'.format(pformat(player_dict)))


def new_eligible_keepers(drafted_dict, rostered_dict, transaction_dict):
    """ Get a list of the eligible keepers using the MKGA rules purposed in 2019

    Loop through all the rostered players. Check if a transaction happened involving that player after the trade
    deadline. Remove that player from the keeper list. Check if an eligible keeper was drafted, store the draft price
    this price will be used as the base price. Finally, determine the price of the player using the base price.

    Args:
        drafted_dict (dict): Dictionary of drafted players
        rostered_dict (dict): Dictionary of rostered players as of week 15
        transaction_dict (dict): Dictionary of all the transactions

    Returns:
    """
    # Create UTC trade deadline, cause we are using UTC in our timestamps
    est = pytz.timezone('US/Eastern')
    utc = pytz.timezone('utc')
    trade_deadline = datetime(2018, 10, 30, 16, 0, 0)
    trade_deadline = est.localize(trade_deadline, is_dst=True)
    trade_deadline = trade_deadline.astimezone(pytz.utc)

    for team in list(rostered_dict):
        for player in list(rostered_dict[team]):
            print('Player: {}'.format(pformat(player)))
            player_key = rostered_dict[team][player]['key']
            print('Player Key = {}'.format(player_key))

            # Look through all the transactions. If the player is in the transaction data, check if the transaction
            # took place after the trade deadline. If so, then remove the player from the keeper list. Per the new
            # keeper rules, only players added before the trade deadline are eligible to be kept.
            for transaction in transaction_data:
                if player_key in transaction_dict[transaction]:

                    # Convert timestamp to UTC. Need to do this because you can't compare a naive timestamp with an
                    # aware timestamp.
                    timestamp = datetime.strptime(transaction_dict[transaction]['timestamp'], '%Y-%m-%d %H:%M:%S')
                    timestamp = utc.localize(timestamp)

                    # If there was a transaction after the trade deadline, then the player is not eligible. Remove
                    # them from the keeper list
                    if timestamp > trade_deadline:
                        print('Transaction {} is {} after {}'.format(transaction, timestamp, trade_deadline))
                        if player in rostered_dict[team]:
                            del(rostered_dict[team][player])

            # Check if rostered player was also drafted. If so, set the drafted flag and set base price to drafted
            # price. If not, set the drafted flag to false and set base price to determined price.
            if player_key in drafted_dict:
                print('{} is in drafted list'.format(player_key))
                draft_price = drafted_dict[player_key]['draft cost']
                print('{} was drafted for {}'.format(player, draft_price))

                if player in rostered_dict[team]:
                    rostered_dict[team][player]["base price"] = draft_price
                    rostered_dict[team][player]["drafted"] = True
            else:
                print('Player was not drafted {}'.format(player))
                if player in rostered_dict[team]:
                    rostered_dict[team][player]["base price"] = 'Player not drafted.'
                    rostered_dict[team][player]["drafted"] = False

    # Determine final keeper value
    for team in rostered_dict:
        for player in rostered_dict[team]:
            if rostered_dict[team][player]['drafted']:
                base_price = int(rostered_dict[team][player]['base price'])
                keeper_cost = (base_price + 5)*1.10
                keeper_cost = math.ceil(keeper_cost)

                if player in rostered_dict[team]:
                    rostered_dict[team][player]["keeper price"] = keeper_cost
            else:
                keeper_cost = 'Market value'
                rostered_dict[team][player]["keeper price"] = keeper_cost

    print('{}'.format(pformat(rostered_dict)))

    with open('final_keepers.json', 'w') as f:
        f.write('{}'.format(pformat(rostered_dict)))

    return


if __name__ == '__main__':
    main_help_text = dedent(
        ''' Generates a list of eligible keepers for the R.U.N. League.
        
        For first time use, you must authenticate with Yahoo using 'python auth.py'
        
        You must specify a year with --year
        To read all data from files, use --file'''
    )
    parser = argparse.ArgumentParser(description=main_help_text, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--year', required=True, type=int, help='Year to generate keeper list')
    parser.add_argument('--file',
                        type=str,
                        default='True',
                        help='If False, use local files instead of connecting to Yahoo API'
                        )
    parser.add_argument('--rules', type=str, default='new', help='If old, use old keeper rules.')

    args = parser.parse_args()
    year = args.year
    file = args.file
    rules = args.rules

    use_old_keeper_rules = False
    if rules.lower() == 'old'.lower():
        use_old_keeper_rules = True
        print(use_old_keeper_rules)

    if file.lower() == 'False'.lower():
        # Get the API Key for the specified year of RUN
        run_api = get_api_values(year)

        # Get the drafted results
        drafted_players = get_draft_results(run_api)

        # Get the teams in RUN
        team_names = get_team_names(run_api)

        # Get the roster for all teams at week 16
        rostered_players = get_all_rosters(team_names)

        if use_old_keeper_rules:
            # Get all the drafted players that were rostered by week 16. This is used for the old keeper rules.
            drafted_rostered_players = determine_drafted_players(drafted_players, rostered_players)

        # Get all the transaction information for RUN
        transaction_data = parse_transaction_data()

        # Writing everything to a file, so I can do this faster without needing to ping the API constantly.
        with open('dump_drafted.json', "w") as f:
            f.write(json.dumps(drafted_players))
        if use_old_keeper_rules:
            with open('dump_drafted_rosters.json', "w") as f:
                f.write(json.dumps(drafted_rostered_players))
        with open('dump_rosters.json', "w") as f:
            f.write(json.dumps(rostered_players))
        with open('dump_transaction.json', "w") as f:
            f.write(json.dumps(transaction_data))

    else:
        # Make this quicker for now by loading from file.
        with open('dump_drafted.json') as f:
            drafted_players = json.load(f)
        if use_old_keeper_rules:
            with open('dump_drafted_rosters.json') as f:
                drafted_rostered_players = json.load(f)
        with open('dump_rosters.json') as f:
            rostered_players = json.load(f)
        with open('dump_transaction.json') as f:
            transaction_data = json.load(f)

    if use_old_keeper_rules:
        # Get the list of keepers using the old keeper rules
        old_eligible_keepers(drafted_rostered_players, transaction_data)
    else:
        # Get the lsit of keepers using the new keeper rules
        new_eligible_keepers(drafted_players, rostered_players, transaction_data)
