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
            'player_name_og',
            'player_rating', 
            'top_streak', 
            'hunted_scores'
        ]]
)
leaderboard['player_rating'] = leaderboard['player_rating'].astype(int)

players = player_data.sort_values('player_rating', ascending=False).to_dict('records')


# # Create three separate DataFrames, each sorted by one of the metrics
# top_rating = leaderboard[['player_name', 'player_name_og', 'player_rating']].sort_values('player_rating', ascending=False)
# top_streak = leaderboard[['player_name', 'player_name_og', 'top_streak']].sort_values('top_streak', ascending=False)
# top_hunted_scores = leaderboard[['player_name', 'player_name_og', 'hunted_scores']].sort_values('hunted_scores', ascending=False)

# # Add a column to each DataFrame that contains the name of the metric
# top_rating['metric_name'] = 'player_rating'
# top_streak['metric_name'] = 'top_streak'
# top_hunted_scores['metric_name'] = 'hunted_scores'

# # Select the top player for each metric
# top_rating = top_rating.head(1)
# top_streak = top_streak.head(1)
# top_hunted_scores = top_hunted_scores.head(1)

# # Rename the metric column to 'metric_value'
# top_rating.rename(columns={'player_rating': 'metric_value'}, inplace=True)
# top_streak.rename(columns={'top_streak': 'metric_value'}, inplace=True)
# top_hunted_scores.rename(columns={'hunted_scores': 'metric_value'}, inplace=True)

# # Concatenate these three DataFrames to create the top_players DataFrame
# top_players = pd.concat([top_rating, top_streak, top_hunted_scores])

# # Sort the DataFrame by metric name (you can customize the sort order)
# sort_order = ['player_rating', 'top_streak', 'hunted_scores']  # update this list to your desired sort order
# top_players['metric_name'] = top_players['metric_name'].astype('category')
# top_players['metric_name'].cat.set_categories(sort_order, inplace=True)
# top_players.sort_values(['metric_name', 'metric_value'], ascending=[True, False], inplace=True)

# env = Environment(loader=FileSystemLoader('.'))
# template = env.get_template('index.html')
# html = template.render(players=players, top_players=top_players.to_dict('records'))
# with open('index.html', 'w') as f:
    # f.write(html)

with open('index.html', 'w') as f:
    f.write(leaderboard.to_html())
