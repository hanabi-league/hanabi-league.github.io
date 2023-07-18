import pandas as pd
from jinja2 import Environment, FileSystemLoader

def build_leaderboard(player_data, player_game_data):
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
                'hunted_scores',
                'number_of_games',
                'number_of_max_scores'
            ]]
    )
    leaderboard['player_rating'] = leaderboard['player_rating'].astype(int)
    leaderboard['top_streak'] = leaderboard['top_streak'].astype(int)
    leaderboard['hunted_scores'] = leaderboard['hunted_scores'].fillna(0)
    leaderboard['hunted_scores'] = leaderboard['hunted_scores'].astype(int)
    leaderboard = leaderboard.sort_values('player_rating', ascending=False)
    
    def get_leaderboard_category(data, category, score_col):
        if category == 'Player Rating':
            tie_breakers = ['top_streak', 'hunted_scores', 'number_of_games', 'number_of_max_scores']
        elif category == 'Top Streak':
            tie_breakers = ['player_rating', 'hunted_scores', 'number_of_games', 'number_of_max_scores']
        else: # 'Hunted Scores'
            tie_breakers = ['player_rating', 'top_streak', 'number_of_games', 'number_of_max_scores']
        leaderboard = data.sort_values([score_col] + tie_breakers, ascending=[False]*len([score_col] + tie_breakers))
        # leaderboard = leaderboard.sample(frac=1)  # Ensure randomness for final tie-breaker
        return leaderboard[['player_name_og', 'player_name', score_col]].rename(columns={score_col: 'score'}).to_dict('records')

    categories = {
        'Player Rating': 'player_rating',
        'Top Streak': 'top_streak',
        'Hunted Scores': 'hunted_scores'
    }
    titles = {
        'Player Rating': 'Highest Rating',
        'Top Streak': 'Longest Win Streak',
        'Hunted Scores': 'Most Hunted Scores'
    }
    
    leaderboards = {cat: get_leaderboard_category(leaderboard, cat, col) for cat, col in categories.items()}
    
    leaders = {cat: {'title': titles[cat], 'leader': leader[0]} for cat, leader in leaderboards.items()}

    return leaderboards, leaders

def main():
    player_data = pd.read_csv('data/player_data.csv')
    player_game_data = pd.read_csv('data/player_game_data.csv')
    if len(player_game_data) == 0:
        return

    player_data = player_data[player_data['number_of_games'] > 0]

    leaderboards, leaders = build_leaderboard(player_data, player_game_data)
    
    # Jinja things
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('content.html')
    rendered_html = template.render(leaders=leaders, leaderboards=leaderboards)
    with open('index.html', 'w') as f:
        f.write(rendered_html)

if __name__ == "__main__":
    main()
