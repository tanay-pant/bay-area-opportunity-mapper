import pandas as pd
import os

# --- Configuration ---
# The subfolder where you saved your 9 downloaded CSV files.
# Make sure this folder exists in the same directory as your script.
DATA_FOLDER = "/Users/tanaypant/Downloads/opportunity mapper/CountyCrimeStats"

# The name for your final, combined CSV file.
OUTPUT_FILE = "/Users/tanaypant/Downloads/opportunity mapper/raw datasets/ba_crime_combined.csv"

# --- Main Script ---
def consolidate_county_data():
    """
    Reads all individual county crime CSVs from a specified folder,
    combines them into a single DataFrame, and saves the result.
    """
    print(f"Looking for data in the '{DATA_FOLDER}' subfolder...")

    # Check if the data folder exists
    if not os.path.exists(DATA_FOLDER):
        print(f"Error: The folder '{DATA_FOLDER}' was not found.")
        print("Please create it and place your 9 downloaded CSV files inside.")
        return

    # Get a list of all CSV files in the data folder
    all_files = [f for f in os.listdir(DATA_FOLDER) if f.endswith('.csv')]
    
    if len(all_files) < 9:
        print(f"Warning: Found only {len(all_files)} CSV files. Expected 9.")
    
    if not all_files:
        print("No CSV files found in the folder. Halting script.")
        return

    # Create a list to hold each county's DataFrame
    list_of_dfs = []

    print("Reading and collecting data from each county file...")
    for filename in all_files:
        filepath = os.path.join(DATA_FOLDER, filename)
        try:
            df = pd.read_csv(filepath)
            # add new county_name column
            COUNTY_NAME = filename.replace('crime_', '').replace('.csv', '').replace('_', ' ').title()
            df['COUNTY'] = COUNTY_NAME
            df['COUNTY'] = df['COUNTY'].str.split().str[1]
            list_of_dfs.append(df)
            print(f"  - Successfully loaded {filename}")
        except Exception as e:
            print(f"  - Error loading {filename}: {e}")

    if not list_of_dfs:
        print("Could not load any data. Halting script.")
        return

    # --- Combine all DataFrames into one ---
    print("\nConsolidating all data into a single DataFrame...")
    combined_df = pd.concat(list_of_dfs, ignore_index=True)

    unnamed_col = combined_df.columns[0]
    combined_df.rename(columns={unnamed_col: 'CRIME_CATEGORY'}, inplace=True)
    print("  - Renamed the first column to 'CRIME_CATEGORY'.")

    print(f"Success! The combined dataset has {combined_df.shape[0]} rows and {combined_df.shape[1]} columns.")
    print("Here is a preview of the combined data:")
    print(combined_df.head())

    # --- Save the Final Dataset ---
    combined_df.to_csv(OUTPUT_FILE, index=False)
    print(f"\nFinal combined data has been saved to '{OUTPUT_FILE}'")

# --- Run the script ---
if __name__ == "__main__":
    consolidate_county_data()
