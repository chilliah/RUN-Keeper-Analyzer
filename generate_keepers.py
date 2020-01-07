import argparse
import json
import math
import sys
import time
from datetime import datetime
from pprint import pformat
from textwrap import dedent

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

    with open('data_files/raw/draft.json', 'w') as f:
        f.write(json.dumps(r))

    print('{}'.format(pformat(r)))

    with open('data_files/raw/draft.json') as f:
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

    with open('data_files/raw/teams.json', 'w') as f:
        # r = r.replace("\'", "\"")
        f.write(json.dumps(r))

    print('{}'.format(pformat(r)))

    with open('data_files/raw/teams.json') as f:
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
    {Manager Name: { Player Name: {Player Key: Key, draft cost: cost, draft team: team key, position: position}}}

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
        with open('data_files/raw/rosters.json', 'w') as f:
            f.write(json.dumps(r))

        with open('data_files/raw/rosters.json') as f:
            data = json.load(f)

        player_names[team_names[team]] = dict()

        # The player data for a team roster is stored as a list of dictionaries in the Yahoo API. We need to loop list
        # and get each dictionary so we can get the player name, player key, and position of each player rostered.
        for player_data_key, players_data_list in data['fantasy_content']['team'][1]['roster']['0']['players'].items():
            if player_data_key == 'count':
                continue
            print('Key {}: Player Key: {} Player Name: {}'.format(player_data_key, players_data_list['player'][0][0]['player_key'],
                                                                  players_data_list['player'][0][2]['name']['full']))

            player_data_list = players_data_list['player'][0]

            for player_data in player_data_list:
                if type(player_data) == dict:
                    for key in player_data.keys():
                        if key == 'player_key':
                            player_key = player_data['player_key']
                        if key == 'name':
                            player_name = player_data['name']['full']
                        if key == 'primary_position':
                            position = player_data['primary_position']

            player_names[manager_name][player_name] = dict()
            player_names[manager_name][player_name]['key'] = player_key
            player_names[manager_name][player_name]['position'] = position

        time.sleep(1)

    print('{}'.format(pformat(player_names)))

    return player_names


def get_player_position(drafted_dict):
    """ For every drafted player, get the position they play via the Yahoo API

    Args:
        drafted_dict (dict): Dictionary of draft results

    Returns:
        drafted_dict (dict): Dictionary of draft results with player position added
    """
    sc = OAuth2(None, None, from_file='oauth2.json')

    # Use a list so that we can make a player collection call instead of calling the Yahoo API for each individual
    # player, which takes forever.
    player_key_list = list()
    # Loop through all the drafter players so we can get their position
    for player_key in drafted_dict:
        player_key_list.append(player_key)

        # Once we have 20 players, make a call to the API. Since RUN is 12 people with 15 man rosters we will have a 
        # total of 180 players drafted. If we ever change the roster size, this will need to change. This would need
        # to change because we could get into a situation where we never hit the 20 player list size for the last few
        # players and then never get their information from the API.
        if len(player_key_list) == 20:
            # The API call to get a players collection is /players/player_keys=player_key1,player_key2, etc...
            # Join the players list in the way the API expects the call, which is key1,key2,key3
            printable_key_list = ','.join(player_key_list)
            url = ('https://fantasysports.yahooapis.com/fantasy/v2/players;player_keys={}'.format(printable_key_list))
            response = sc.session.get(url, params={'format': 'json'})
            r = response.json()

            print('{}'.format(pformat(r)))

            with open('data_files/raw/player.json', 'w') as f:
                # r = r.replace("\'", "\"")
                f.write(json.dumps(r))

            print('{}'.format(pformat(r)))

            with open('data_files/raw/player.json') as f:
                data = json.load(f)

            # Debug
            # with open('pretty_player.json', 'w') as f:
            #     f.write('{}'.format(pformat(data)))

            # Get the count of players returned.
            count = int(data['fantasy_content']['players']['count'])

            i = 0

            # Because the glorious Yahoo API can't do anything in a why that makes sense to a normal person, this
            # is a stupid and over complicated loop. First off in a player collection the list of players is actually
            # stored as a dictionary, not a list. This means that to access each element like it's a dictionary, not
            # like it's a list. For example the first player in the player collection is not player_collection[0],
            # you know how a normal person accesses a list. Instead it's player_collection['0'], yes that's right
            # it's a string. This is why we have to use a while loop and convert the iterator in the loop to a string.
            while i < count:
                players_data_list = data['fantasy_content']['players'][str(i)]['player'][0]
                # Here's the other oddity of the Yahoo API player collection. For each player in the collection there
                # is a list of attributes. Each individual attribute is a dictionary. It would make more sense to have
                # this as just a dictionary. If that was the case, then we could access each element of the dictionary
                # like it was a dictionary. However, since this is a list of dictionaries. We need to iterate through
                # the list, check if the element is a dict (cause some elements of the list are not dictionaries), then
                # check if the key is player_key and eligible_positions.
                for player_data in players_data_list:
                    if type(player_data) == dict:
                        for key in player_data.keys():
                            if key == 'player_key':
                                player_player_key = player_data['player_key']
                            if key == 'eligible_positions':
                                for position in player_data[key]:
                                    eligible_position = position['position']
                                    print('Eligible positions: {}'.format(pformat(eligible_position)))
                                    drafted_dict[player_player_key]['position'] = eligible_position
                i = i + 1

            player_key_list.clear()
            time.sleep(1)

    print('{}'.format(pformat(drafted_dict)))

    return drafted_dict


def get_trade_deadline(run_api):
    """ Get the trade deadline from the Yahoo API

    Args:
        run_api (str): API for the RUN league

    Returns:
        trade_deadline_str (str): The trade deadline from Yahoo league settings as a string
    """
    sc = OAuth2(None, None, from_file='oauth2.json')
    url = ('https://fantasysports.yahooapis.com/fantasy/v2/league/{}/settings'.format(run_api))
    response = sc.session.get(url, params={'format': 'json'})
    r = response.json()

    with open('data_files/raw/league_settings.json', 'w') as f:
        # r = r.replace("\'", "\"")
        f.write(json.dumps(r))

    print('{}'.format(pformat(r)))

    with open('data_files/raw/league_settings.json') as f:
        data = json.load(f)

    trade_deadline_str = data['fantasy_content']['league'][1]['settings'][0]['trade_end_date']

    return trade_deadline_str


def calculate_draft_average(drafted_players):
    """ Calculate the draft average for each position. Round up.

    Args:
        drafted_players (dict): Dictionary of drafted players

    Returns:
        draft_averages (dict): Dictionary of the average draft cost for each position
    """
    def average_ceil(position_list):
        """ Calculate the average of the items in position_list. Round up.

        Args:
            position_list (list): List of cost for draft position

        Returns: Average of items in position_list rounded up
        """
        return math.ceil(sum(position_list) / len(position_list))

    rb_cost_list = list()
    wr_cost_list = list()
    qb_cost_list = list()
    te_cost_list = list()
    def_cost_list = list()

    for player_key in drafted_players:
        position = drafted_players[player_key]['position']
        draft_cost = int(drafted_players[player_key]['draft cost'])

        if position == 'RB':
            rb_cost_list.append(draft_cost)
        elif position == 'WR':
            wr_cost_list.append(draft_cost)
        elif position == 'QB':
            qb_cost_list.append(draft_cost)
        elif position == 'TE':
            te_cost_list.append(draft_cost)
        elif position == 'DEF':
            def_cost_list.append(draft_cost)

    rb_average = average_ceil(rb_cost_list)
    wr_average = average_ceil(wr_cost_list)
    qb_average = average_ceil(qb_cost_list)
    te_average = average_ceil(te_cost_list)
    def_average = average_ceil(def_cost_list)

    print('RB cost list: {}. Average: {}'.format(rb_cost_list, rb_average))
    print('WR cost list: {}. Average: {}'.format(wr_cost_list, wr_average))
    print('QB cost list: {}. Average: {}'.format(qb_cost_list, qb_average))
    print('TE cost list: {}. Average: {}'.format(te_cost_list, te_average))
    print('DEF cost list: {}. Average: {}'.format(def_cost_list, def_average))

    draft_averages = {'RB': rb_average, 'WR': wr_average, 'QB': qb_average, 'TE': te_average, 'DEF': def_average}

    print('Draft Averages: {}'.format(pformat(draft_averages)))

    return draft_averages


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


def parse_transaction_data(run_api):
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
    url = ('https://fantasysports.yahooapis.com/fantasy/v2/league/{}/transactions'.format(run_api))
    response = sc.session.get(url, params={'format': 'json'})
    r = response.json()

    print('{}'.format(pformat(r)))

    with open('data_files/raw/transactions.json', 'w') as f:
        # r = r.replace("\'", "\"")
        f.write(json.dumps(r))

    print('{}'.format(pformat(r)))

    with open('data_files/raw/transactions.json') as f:
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


def new_eligible_keepers(drafted_dict, rostered_dict, transaction_dict, draft_cost_dict, trade_deadline_str):
    """ Get a list of the eligible keepers using the MKGA rules purposed in 2019

    Loop through all the rostered players. Check if a transaction happened involving that player after the trade
    deadline. Remove that player from the keeper list. Check if an eligible keeper was drafted, store the draft price
    this price will be used as the base price. Finally, determine the price of the player using the base price.

    Args:
        drafted_dict (dict): Dictionary of drafted players
        rostered_dict (dict): Dictionary of rostered players as of week 15
        transaction_dict (dict): Dictionary of all the transactions
        draft_cost_dict (dict): Dictionary of the average draft cost for each position
        trade_deadline_str (str): Trade dead from Yahoo API

    Returns:
        rostered_dict (dict): Dictionary of rostered players with keeper cost
    """
    trade_deadline = datetime.strptime(trade_deadline_str, '%Y-%m-%d')

    for team in list(rostered_dict):
        for player in list(rostered_dict[team]):
            print('Player: {}'.format(pformat(player)))
            player_key = rostered_dict[team][player]['key']
            print('Player Key = {}'.format(player_key))

            # Look through all the transactions. If the player is in the transaction data, check if the transaction
            # took place after the trade deadline. If so, then remove the player from the keeper list. Per the new
            # keeper rules, only players added before the trade deadline are eligible to be kept.
            for transaction in transaction_dict:
                if player_key in transaction_dict[transaction]:
                    timestamp = datetime.strptime(transaction_dict[transaction]['timestamp'], '%Y-%m-%d %H:%M:%S')

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
            # If the player was drafted, use the drafted price as the keeper base price.
            if rostered_dict[team][player]['drafted']:
                base_price = int(rostered_dict[team][player]['base price'])
                keeper_cost = (base_price + 5)*1.10
                keeper_cost = math.ceil(keeper_cost)

                if player in rostered_dict[team]:
                    rostered_dict[team][player]["keeper price"] = keeper_cost
            # If the player was not drafted, use the average draft price for the players position
            else:
                position = rostered_dict[team][player]['position']
                draft_average_cost = draft_cost_dict[position]
                base_price = draft_average_cost

                # We will now be adding interest to the keeper cost for UDFAs
                keeper_cost = (base_price + 5) * 1.10
                keeper_cost = math.ceil(keeper_cost)

                rostered_dict[team][player]["keeper price"] = keeper_cost

    print('{}'.format(pformat(rostered_dict)))

    with open('final_keepers.json', 'w') as f:
        f.write('{}'.format(pformat(rostered_dict)))

    return rostered_dict


def pretty_print_keepers(year, keeper_dict):
    """ Print the final keeper information to a file in a human-readible format

    Args:
        year (int): Year of RUN league
        keeper_dict (dict): Dictionary of final keeper information
    """
    with open('final_keepers.txt', 'w') as f:
        print('The R.U.N. League Keepers for {}\n'.format(year))
        f.write('The R.U.N. League Keepers for {}\n'.format(year))
        for team in keeper_dict:
            print('Manager: {}\n'.format(team))
            f.write('Manager: {}\n'.format(team))

            for player in keeper_dict[team]:
                keeper_cost = keeper_dict[team][player]['keeper price']
                drafted_flag = keeper_dict[team][player]['drafted']
                if drafted_flag:
                    print('\t{} - Keeper Cost: ${}\n'.format(player, keeper_cost))
                    f.write('\t{} - Keeper Cost: ${}\n'.format(player, keeper_cost))
                else:
                    print('\t{} - Keeper Cost: ${} **Waiver Keeper**\n'.format(player, keeper_cost))
                    f.write('\t{} - Keeper Cost: ${}  **Waiver Keeper**\n'.format(player, keeper_cost))


def main_program(year, file, rules, cost):
    """ Main function for program

    Args:
        year: Year of the results to get
        file: Use files flag
        rules: Use new or old rules flag
        cost: Only print cost flag
    """
    use_old_keeper_rules = False
    if rules.lower() == 'old'.lower():
        use_old_keeper_rules = True
        print(use_old_keeper_rules)

    only_print_draft_costs = False
    if cost.lower() == 'true'.lower():
        only_print_draft_costs = True

    if file.lower() == 'False'.lower():
        # Get the API Key for the specified year of RUN
        run_api = get_api_values(year)

        # Get the trade_deadline
        trade_deadline = get_trade_deadline(run_api)

        # Get the drafted results
        drafted_players = get_draft_results(run_api)

        # Get the position for each drafted player
        drafted_players = get_player_position(drafted_players)

        # Calculate draft averages
        positional_draft_costs = calculate_draft_average(drafted_players)

        if only_print_draft_costs:
            print('Only printing draft averages, because --cost flag set to True')
            return

        # Get the teams in RUN
        team_names = get_team_names(run_api)

        # Get the roster for all teams at week 16
        rostered_players = get_all_rosters(team_names)

        if use_old_keeper_rules:
            # Get all the drafted players that were rostered by week 16. This is used for the old keeper rules.
            drafted_rostered_players = determine_drafted_players(drafted_players, rostered_players)

        # Get all the transaction information for RUN
        transaction_data = parse_transaction_data(run_api)

        # Writing everything to a file, so I can do this faster without needing to ping the API constantly.
        with open('data_files/dump_drafted.json', "w") as f:
            f.write(json.dumps(drafted_players))
        if use_old_keeper_rules:
            with open('data_files/dump_drafted_rosters.json', 'w') as f:
                f.write(json.dumps(drafted_rostered_players))
        with open('data_files/dump_draft_cost.json', 'w') as f:
            f.write(json.dumps(positional_draft_costs))
        with open('data_files/dump_rosters.json', 'w') as f:
            f.write(json.dumps(rostered_players))
        with open('data_files/dump_transaction.json', 'w') as f:
            f.write(json.dumps(transaction_data))
        with open('data_files/trade_deadline.json', 'w') as f:
            f.write(trade_deadline)

    else:
        # Make this quicker for now by loading from file.
        with open('data_files/dump_drafted.json') as f:
            drafted_players = json.load(f)
        if use_old_keeper_rules:
            with open('data_files/dump_drafted_rosters.json') as f:
                drafted_rostered_players = json.load(f)
        with open('data_files/dump_draft_cost.json') as f:
            positional_draft_costs = json.load(f)
        with open('data_files/dump_rosters.json') as f:
            rostered_players = json.load(f)
        with open('data_files/dump_transaction.json') as f:
            transaction_data = json.load(f)
        with open('data_files/trade_deadline.json') as f:
            trade_deadline = f.read()

    if only_print_draft_costs:
        calculate_draft_average(drafted_players)
        print('Only printing draft averages, because --cost flag set to True')
        return

    if use_old_keeper_rules:
        # Get the list of keepers using the old keeper rules
        old_eligible_keepers(drafted_rostered_players, transaction_data)
        # pretty_print_keepers(year, final_keeper_list)
    else:
        # Get the list of keepers using the new keeper rules
        final_keeper_list = new_eligible_keepers(
            drafted_players,
            rostered_players,
            transaction_data,
            positional_draft_costs,
            trade_deadline
        )

        # Print a more user friendly version of the final keeper list to a text file.
        pretty_print_keepers(year, final_keeper_list)


if __name__ == '__main__':
    main_help_text = dedent(
        ''' Generates a list of eligible keepers for The R.U.N. League.
        
        You must first authenticate with Yahoo using 'python auth.py'. You only need to authenticate once.
        For first time use, the --file flag must be False. Ex: 'python generate_keepers.py --year 2018 --file False
        Results are saved to final_keepers.txt.
        
        You must specify a year with '--year'
        To get new data from the Yahoo API, use the optional argument '--file False'
        To use the old keeper rules, use the optional argument '--rules old' 
        To only print the average draft cost for each position, use the optional argument '--cost True' '''
    )
    parser = argparse.ArgumentParser(description=main_help_text, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--year', required=True, type=int, help='Year to generate keeper list')
    parser.add_argument('--file',
                        type=str,
                        default='True',
                        help='If False, get new data from the Yahoo API'
                        )
    parser.add_argument('--rules', type=str, default='new', help='If old, use old keeper rules.')
    parser.add_argument('--cost', type=str, default='False', help='If True, only print the draft costs.')

    args = parser.parse_args()
    year = args.year
    file = args.file
    rules = args.rules
    cost = args.cost

    main_program(year, file, rules, cost)

    sys.exit(0)
