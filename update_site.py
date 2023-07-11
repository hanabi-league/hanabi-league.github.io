import pandas as pd

# Load the data from the CSV files
player_data = pd.read_csv('/data/player_data.csv')
player_game_data = pd.read_csv('/data/player_game_data.csv')

# Join player_data to player_game_data
joined_data = pd.merge(player_data, player_game_data, on='player_name', how='left')

# Calculate hunted_scores
hunted_scores = joined_data[joined_data['max_score'] == 1].groupby('player_name')['variant_name'].nunique()
hunted_scores = hunted_scores.reset_index().rename(columns={'variant_name': 'hunted_scores'})

# Merge hunted_scores back into the player data
player_data = pd.merge(player_data, hunted_scores, on='player_name', how='left')

player_data[['player_name', 'player_rating', 'top_streak', 'hunted_scores']]

# Convert the DataFrame to an HTML table
html_table = player_data.to_html(index=False)

html_table
