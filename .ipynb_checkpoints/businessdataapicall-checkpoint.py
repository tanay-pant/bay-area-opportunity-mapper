import requests
import pandas as pd

# This is the API call to get ZBP from census.gov. It asks for the number of establishments
# and industry labels for all ZIP codes within the state of California (state code 06).
# This uses the 2022 CBP API, as it's the most recent complete dataset available.
API_URL = "https://api.census.gov/data/2023/cbp?get=ESTAB,NAICS2017_LABEL,GEO_ID,COUNTY&for=ZIPCODE:*&in=state:06"

# The name for your new CSV file containing the business data.
OUTPUT_FILE = "bay_area_business_data.csv"

# --- Main Script ---
def fetch_and_process_business_data():
    """
    Makes an API call to the Census Bureau to get business pattern data
    for all ZIP codes in California, then processes and saves it.
    """
    print(f"Making API call to Census Bureau:\n{API_URL}")

    try:
        # Make the GET request to the API
        response = requests.get(API_URL)
        # Raise an exception if the call was unsuccessful (e.g., 404, 500)
        response.raise_for_status() 
        print("Successfully received data from the API.")
        
        # The API returns data in JSON format
        data = response.json()
        
        # The first row of the data is the header, the rest is the content
        header = data[0]
        rows = data[1:]
        
        # Convert the JSON data to a Pandas DataFrame
        df = pd.DataFrame(rows, columns=header)
        print(f"Created a DataFrame with {len(df)} rows.")

        # --- Data Cleaning ---
        # Rename columns for clarity
        df = df.rename(columns={'ZIPCODE': 'ZIP_CODE', 'ESTAB': 'ESTAB_COUNT'})
        
        # The API returns establishment_count as a string, convert it to a number
        # errors='coerce' will turn any non-numeric values into NaN (Not a Number)
        df['ESTAB_COUNT'] = pd.to_numeric(df['ESTAB_COUNT'], errors='coerce')

        # Drop rows where the count is not a valid number
        df.dropna(subset=['ESTAB_COUNT'], inplace=True)

        # Convert the count to an integer
        df['ESTAB_COUNT'] = df['ESTAB_COUNT'].astype(int)

        print("\nCleaned and processed the data. Here's a preview:")
        print(df.head())
        
        # --- Save the Data ---
        df.to_csv(OUTPUT_FILE, index=False)
        print(f"\nSuccessfully saved the data to '{OUTPUT_FILE}'")

    except requests.exceptions.RequestException as e:
        print(f"\nAn error occurred while making the API call: {e}")
        print("Please check your internet connection and the API URL.")
    except Exception as e:
        print(f"\nAn error occurred during data processing: {e}")

# --- Run the script ---
if __name__ == "__main__":
    fetch_and_process_business_data()