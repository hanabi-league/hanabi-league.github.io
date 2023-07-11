import pandas as pd
from jinja2 import Environment, FileSystemLoader

player_data = pd.read_csv('data/player_data.csv')
player_game_data = pd.read_csv('data/player_game_data.csv')

joined_data = pd.merge(player_data, player_game_data, on='player_name', how='left')

# Calculate hunted_scores
hunted_scores = joined_data[joined_data['max_score'] == 1].groupby('player_name')['variant_name'].nunique()
hunted_scores = hunted_scores.reset_index().rename(columns={'variant_name': 'hunted_scores'})

# Merge hunted_scores back into the player data
leaderboard = (
    pd
        .merge(player_data, hunted_scores, on='player_name', how='left')
        [[
            'player_name', 
            'player_rating', 
            'top_streak', 
            'hunted_scores'
        ]]
)
leaderboard['player_rating'] = leaderboard['player_rating'].astype(int)

players = player_data.sort_values('player_rating', ascending=False).to_dict('records')

# Load the template from the filesystem
env = Environment(loader=FileSystemLoader('.'))
template = env.get_template('index.html')

html = template.render(players=players)

with open('index.html', 'w') as f:
    f.write(html)
