import nfl_data_py as nfl

# Specify the years and columns you want to pull data for
years = [2024]  # Replace with the years you need
columns = ['player_display_name', 'passing_yards', 'rushing_yards']  # Replace with your desired columns

# Import the weekly data
weekly_data = nfl.import_weekly_data(years=years, columns=columns, downcast=True)

# Print the data
print(weekly_data)
