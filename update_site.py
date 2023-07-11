import pandas as pd
from jinja2 import Environment, FileSystemLoader

# Load the data from the CSV files
player_data = pd.read_csv('data/player_data.csv')
player_game_data = pd.read_csv('data/player_game_data.csv')

# Join player_data to player_game_data
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

# Convert the DataFrame to a list of dicts
players = player_data.sort_values('player_rating', ascending=False).to_dict('records')

# Load the template from the filesystem
env = Environment(loader=FileSystemLoader('.'))
template = env.get_template('index.html')

# Render the template with the data
html = template.render(players=players)

# Write the HTML to a file
with open('index.html', 'w') as f:
    f.write(html)
