import nfl_data_py as nfl

# Specify the years and columns you want to pull data for
years = [2024]  # Replace with the years you need
s_type = 'REG'  # Replace with your desired columns

# Import the weekly data
seasonal_data = nfl.import_seasonal_data(years, s_type)

# Print the data
print(seasonal_data.columns)
