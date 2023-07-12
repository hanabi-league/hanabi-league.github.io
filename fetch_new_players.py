import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Define the scope
scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']

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

# View the data
print(records_data)
