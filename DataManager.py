import requests
import json

from dateutil.parser import parse
import pytz

import pandas as pd
import numpy as np

from itertools import combinations

import datetime

class DataManager:
    def __init__(self):
        self.constants = self._fetch_constants()
        self.player_data = self._fetch_player_data()
        self.player_game_data = self._fetch_player_game_data()
        self.variant_data = self._fetch_variant_data()
        self.variants = self._build_variant_list()
        
    def _fetch_constants(self):
        with open('data/constants.json', 'r') as file:
            constants = json.load(file)
        return constants

    def _fetch_player_data(self):
        player_data = pd.read_csv('data/player_data.csv')
        return player_data

    def _fetch_player_game_data(self):
        player_game_data = pd.read_csv('data/player_game_data.csv')
        return player_game_data

    def _fetch_variant_data(self):
        variant_data = pd.read_csv('data/variant_data.csv')
        return variant_data

    # Define function for determining number of suits in a given variant
    def _get_number_of_suits(self, variant_name):
        # Special cases
        if variant_name == 'No Variant':
            return 5
        elif variant_name in ['Ambiguous & Dual-Color', 'Ambiguous Mix', 'Dual-Color Mix']:
            return 6
        
        # General case
        for num in range(3, 7):
            if f'{num} Suits' in variant_name:
                return num
        
        # If no number of suits was found
        raise ValueError(f'Cannot determine number of suits for variant "{variant_name}"')
    
    # Define function for determining which suits are in a given variant
    def _find_variants(self, variant_name):
        suits = sorted(self.variant_data['variant_name'].unique(), key=len, reverse=True)
        
        variant_suits = []
        
        # Check for each suit if it is in the variant name
        for suit in suits:
            # If the suit is in the variant name, add it to the list and remove it from the variant name
            if suit in variant_name:
                variant_suits.append(suit)
                variant_name = variant_name.replace(suit, "")
        
        if not variant_suits:
            variant_suits.append('No Variant')
        
        return variant_suits
    
    def _build_variant_list(self):
        variants_raw = requests.get('https://hanab.live/api/v1/variants').json()
    
        # Variants with any of these words in the name will be excluded for the league
        filter_terms = [
            'ambiguous',
            'mix',
            'evens',
            'dark',
            'cocoa',
            'fives',
            'ones',
            'black',
            'gray',
            'matryoshka',
            'dual',
            'critical',
            'blind',
            'mute',
            'alternating',
            'duck',
            'cow',
            'synesthesia',
            'reversed',
            'down',
            'throw',
            'funnels',
            'chimneys'
        ]
    
        variants_raw = list(variants_raw.items())
        
        variants = pd.DataFrame(variants_raw, columns=['variant_id', 'variant_name'])
        variants['variant_id'] = variants['variant_id'].astype(int)
        variants = variants.drop('variant_id', axis=1)
        
        # Filter out the rows with specific terms in 'variant_name'
        pattern = '|'.join(filter_terms)
        variants = variants[~variants['variant_name'].str.lower().str.contains(pattern)]
        
        variants['number_of_suits'] = variants['variant_name'].apply(self._get_number_of_suits)
        variants = variants[variants['number_of_suits'].between(self.constants['min_suits'], self.constants['max_suits'])]
        variants['variants'] = variants['variant_name'].apply(self._find_variants)
        
        return variants
    
    #  Fetch game data from hanab.live
    def _fetch_game_data(self):
        # Fetch game data
        def fetch_data(player):
            url = f'https://hanab.live/api/v1/history-full/{player}?start={self.constants["starting_game_id"]}&end={self.constants["ending_game_id"]}'
            response = requests.get(url)
            try:
                data = response.json()
            except ValueError:  # includes simplejson.decoder.JSONDecodeError
                data = []
            return data

    
        players = self.player_data['player_name'].unique()
    
        rows = []
        for player_name in players:
            data = fetch_data(player_name)
    
            for game in data:
                # Calculate game length in minutes
                start = parse(game["datetimeStarted"])
                end = parse(game["datetimeFinished"])
                length = (end - start).total_seconds() / 60

                datetime_started = start.astimezone(pytz.timezone('US/Eastern'))
    
                if (
                    not game["options"]["deckPlays"]
                    and not game["options"]["emptyClues"]
                    and not game["options"]["oneExtraCard"]
                    and not game["options"]["oneLessCard"]
                    and not game["options"]["allOrNothing"]
                    and not game["options"]["detrimentalCharacters"]
                    and datetime_started >= parse(self.constants['starting_time'], tzinfos={'EST': 'US/Eastern'})
                ):
                    row = {
                        "game_id": game["id"],
                        "player_name": player_name,
                        "number_of_players": game["options"]["numPlayers"],
                        "datetime": start,
                        "game_length": length,
                        "score": game["score"],
                        "variant_id": game["options"]["variantID"],
                        "variant_name": game["options"]["variantName"],
                        "seed": game["seed"],
                        "number_of_turns": game["numTurns"],
                        "end_condition": game["endCondition"],
                        "player_names": game['playerNames']
                    }
                    rows.append(row)
    
        if len(rows) > 0:
            print(rows)
            game_data = pd.DataFrame(rows)
            
            # Just new games
            latest_game_id = self.player_game_data['game_id'].max()
            if not pd.isna(latest_game_id):
                game_data = game_data[game_data['game_id'] > latest_game_id]
            game_data = game_data[game_data['game_id'] >= self.constants['starting_game_id']]
            game_data = game_data[game_data['game_id'] <= self.constants['ending_game_id']]
        
            game_data = game_data[game_data['number_of_players'].between(self.constants['min_player_count'], self.constants['max_player_count'])]
            game_data = game_data[game_data['player_names'].apply(lambda x: set(x).issubset(players))]

            if len(game_data):
                game_data = pd.merge(game_data, self.variants, on='variant_name')
    
                game_data = game_data.sort_values(by=['game_id', 'player_name'])
    
                return game_data

        return []
    
    # Define functions for development coefficients
    def _calculate_development_coefficient(self, number_of_games, player_rating):
        if number_of_games <= 30:
            return 40
        elif player_rating <= 1600:
            return 30
        else:
            return 15
    
    def _calculate_league_development_coefficient(self, number_of_games_variant, variant_rating):
        if number_of_games_variant <= 30:
            return 20
        elif variant_rating <= 1600:
            return 10
        else:
            return 5
    
    # Calculate player/variant ratings
    def calculate_ratings(self):
        game_data = self._fetch_game_data()

        if len(game_data) == 0:
            print("No games to parse. Exiting...")
            return
        
        game_ids = game_data['game_id'].unique()
        game_ids.sort()
    
        print(len(game_ids), "games to parse")

        game_id = self.constants['starting_game_id']
        for i, game_id in enumerate(game_ids):
            noVar_rating = self.variant_data.loc[self.variant_data['variant_name'] == 'No Variant', 'variant_rating'].values[0]
    
            current_game = game_data.loc[game_data['game_id'] == game_id].copy()
    
            # Just storing this for score-hunting
            true_variant_name = current_game['variant_name'].values[0]
    
            # Calculate difficulty modifier
            difficulty_modifiers = [1]
    
            if current_game['number_of_players'].values[0] == 5:
                difficulty_modifiers[0] += self.constants['difficulty_modifier_5p']
    
            variant_names = current_game['variants'].values[0]
            variant_ratings = [self.variant_data.loc[self.variant_data['variant_name'] == name, 'variant_rating'].values[0] for name in variant_names]
            if len(current_game['variants'].values[0]) == 2:
                variant_rating_calculated = variant_ratings[0] + variant_ratings[1] - noVar_rating
                difficulty_modifiers += difficulty_modifiers
                difficulty_modifiers[0] += variant_rating_calculated / variant_ratings[0] - 1
                # just used for calculating the second variant's rating change
                difficulty_modifiers[1] += variant_rating_calculated / variant_ratings[1] - 1
            else:
                variant_rating_calculated = self.variant_data.loc[self.variant_data['variant_name'] == current_game['variants'].values[0][0], 'variant_rating'].values[0]
    
            player_names = current_game['player_names'].values[0]
            player_ratings = [self.player_data.loc[self.player_data['player_name'] == name, 'player_rating'].values[0] for name in player_names]
            avg_team_rating = sum(player_ratings) / len(player_ratings)
    
            current_game['variant_name'] = current_game['variants'].str[0]
            current_game = current_game.merge(self.player_data, on='player_name')
            current_game = current_game.merge(self.variant_data, on='variant_name')
    
            current_game['player_expected_results'] = (1-self.constants['u_v']) / (1 + 10 ** ((difficulty_modifiers[0] * variant_rating_calculated - current_game['player_rating']) / 400))
    
            team_expected_results = current_game['player_expected_results'].mean()
    
            max_score = 1 if current_game['score'].values[0] == current_game['number_of_suits'].values[0] * 5 else 0
    
            current_game['development_coefficient'] = current_game.apply(lambda row: self._calculate_development_coefficient(row['number_of_games'], row['player_rating']), axis=1)
            current_game['new_player_rating'] = current_game['player_rating'] + current_game['development_coefficient'] * (max_score - team_expected_results)
    
            # Note: More efficient way of doing the subsequent operations would be using .loc but making sure we are not operating on a view
            # This might result in SettingWithCopyWarning otherwise
            self.player_data = self.player_data.merge(current_game[['player_name', 'new_player_rating']], on='player_name', how='left')
    
            self.player_data['player_rating'] = np.where(self.player_data['new_player_rating'].isna(), self.player_data['player_rating'], self.player_data['new_player_rating'])
            self.player_data['number_of_games'] = np.where(self.player_data['new_player_rating'].isna(), self.player_data['number_of_games'], self.player_data['number_of_games'] + 1)
            self.player_data['number_of_max_scores'] = np.where(self.player_data['new_player_rating'].isna(), self.player_data['number_of_max_scores'], self.player_data['number_of_max_scores'] + max_score)
            self.player_data['current_streak'] = np.where(self.player_data['new_player_rating'].isna(), self.player_data['current_streak'], np.where(max_score == 0, 0, self.player_data['current_streak'] + 1))
            self.player_data['top_streak'] = np.where(self.player_data['new_player_rating'].isna(), self.player_data['top_streak'], np.maximum(self.player_data['current_streak'], self.player_data['top_streak']))
    
            self.player_data = self.player_data.drop(columns=['new_player_rating'])
    
            for i, variant_name in enumerate(variant_names):
                league_development_coefficient = self._calculate_league_development_coefficient(self.variant_data.loc[self.variant_data['variant_name'] == variant_names[i], 'number_of_games_variant'].values[0], variant_ratings[i])
                new_variant_rating = variant_ratings[i] + (league_development_coefficient / difficulty_modifiers[i]) * (team_expected_results - max_score)
    
                self.variant_data.loc[self.variant_data['variant_name'] == variant_names[i], 'variant_rating'] = new_variant_rating
                self.variant_data.loc[self.variant_data['variant_name'] == variant_names[i], 'number_of_games_variant'] += 1
                self.variant_data.loc[self.variant_data['variant_name'] == variant_names[i], 'number_of_max_scores_variant'] += max_score
    
            # Adding the required information to the DataFrame
            current_rating_info = current_game[['game_id', 'player_name', 'variant_name', 'number_of_suits', 'number_of_players', 'score', 'new_player_rating', 'player_rating']].copy()
            current_rating_info['variant_name'] = true_variant_name
            current_rating_info['max_score'] = max_score
            current_rating_info['avg_team_rating'] = avg_team_rating
            current_rating_info['change_in_player_rating'] = current_rating_info['new_player_rating'] - current_rating_info['player_rating']
            current_rating_info.drop(columns='player_rating', inplace=True)
            current_rating_info = current_rating_info.rename(columns={'new_player_rating': 'player_rating'})
            self.player_game_data = pd.concat([self.player_game_data, current_rating_info], ignore_index=True)
            self.constants['total_games_played'] += 1
    
        self.constants['latest_game_id'] = game_id
        self.constants['latest_run'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
        self.player_game_data = self.player_game_data.sort_values(['player_name', 'game_id'])
        self.player_game_data['player_game_number'] = self.player_game_data.groupby('player_name').cumcount() + 1
    
    def update_data_files(self):
        self.variant_data.to_csv('data/variant_data.csv', index=False)
        self.player_data.to_csv('data/player_data.csv', index=False)
        self.player_game_data.to_csv('data/player_game_data.csv', index=False)

        class NpEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, np.integer):
                    return int(obj)
                if isinstance(obj, np.floating):
                    return float(obj)
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
                return super(NpEncoder, self).default(obj)
        
        with open('data/constants.json', 'w') as file:
            json.dump(self.constants, file, indent=4, cls=NpEncoder)
    
    def reset_data(self):
        self.player_game_data = pd.DataFrame(columns=self.player_game_data.columns)
        self.player_game_data.to_csv('data/player_game_data.csv', index=False)
    
        self.player_data['player_rating'] = self.constants['player_base_rating']
        self.player_data['top_streak'] = 0
        self.player_data['current_streak'] = 0
        self.player_data['number_of_games'] = 0
        self.player_data['number_of_max_scores'] = 0
        self.player_data.to_csv('data/player_data.csv', index=False)
    
        self.variant_data['variant_rating'] = self.variant_data['variant_name'].map(self.constants['variant_base_ratings'])
        self.variant_data['number_of_games_variant'] = 0
        self.variant_data['number_of_max_scores_variant'] = 0
        self.variant_data.to_csv('data/variant_data.csv', index=False)
    
        self.constants['latest_game_id'] = self.constants['starting_game_id'] - 1
        self.constants['total_games_played'] = 0
        self.constants['latest_run'] = None
        with open('data/constants.json', 'w') as file:
            json.dump(self.constants, file, indent=4)
