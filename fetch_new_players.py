import base64
import json
import os

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

# Define the scope
scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']

# Try grabbing new auth token
token_b64 = os.environ.get('google_auth_token')
token_json = json.loads(base64.b64decode(token_b64))
creds_new = ServiceAccountCredentials.from_json_keyfile_dict(token_json, scope)
print(creds_new)

# Add your service account file
creds = ServiceAccountCredentials.from_json_keyfile_name('config/service_account_keyfile.json', scope)

# Authorize the clientsheet 
client = gspread.authorize(creds)

# Get the instance of the Spreadsheet
sheet = client.open_by_key('116bG8yMtG5liQPmwt4EXSCPtZmIfRTITdnTbWNPnqZ0')

# Get the first sheet of the Spreadsheet
sheet_instance = sheet.worksheet('Signup responses')

# Get all the records of the data
records_data = sheet_instance.get_all_records()

# Convert to DataFrame
new_players = pd.DataFrame.from_records(records_data)

# Rename the columns
new_players = new_players.rename(columns={
    "Timestamp": "Timestamp", 
    "What is your new League Alt Account, on hanab.live? \n(Remember this will be your dedicated alt account, where all League games will be played & tracked.)": "player_name", 
    "What recognizable name do you like to go by in the Hanabi community?\n(e.g. main h.live account, Discord tag, etc - just whatever's recognizable & preferable)": "player_name_og",
    "What's your Discord tag?\n(so I can share info & updates, via the Hanabi Central @League role or DMs if ever necessary)": "discord_tag"
})

# Drop the column you're not interested in
new_players = new_players.drop(columns=["discord_tag"])

with open('data/constants.json', 'r') as file:
    constants = json.load(file)
    
# Load existing data
player_data = pd.read_csv('data/player_data.csv')

# Check for new players and add them to the CSV
for index, row in new_players.iterrows():
    if row['player_name'] not in player_data['player_name'].values:
        new_row = pd.DataFrame({
            'player_name': [row['player_name']], 
            'player_name_og': [row['player_name_og']], 
            'player_rating': [constants['player_base_rating']], 
            'top_streak': [0], 
            'current_streak': [0], 
            'number_of_games': [0], 
            'number_of_max_scores': [0]
        })
        player_data = pd.concat([player_data, new_row], ignore_index=True)

# Save updated player data
player_data.to_csv('data/player_data.csv', index=False)
