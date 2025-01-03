import nfl_data_py as nfl
import sqlite3
import pandas as pd

# Import the weekly data
playerIds = nfl.import_ids()

# Connect to SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect('playerIds.db')
cursor = conn.cursor()

# Create a table to store the data
playerIds.to_sql('Player_Ids', conn, if_exists='replace', index=False)

# Commit and close the connection
conn.commit()
conn.close()

# Print confirmation
print("Data imported into the database successfully.")