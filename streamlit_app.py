import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# 1. PAGE CONFIGURATION
st.set_page_config(
    page_title="Bay Area Opportunity Mapper",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. LOAD DATA (Cached for performance)
@st.cache_data
def load_data():
    # Make sure this matches the filename from your normalization script
    # It should be the file containing 'norm_' columns
    df = pd.read_csv('bay_area_full_scored_data.csv') #CHANGE UP
    return df

# 3. SCORING FUNCTION (The Engine)
def calculate_final_score(df, max_rent, bedroom_col, weights):
    """
    Calculates a score (0-100) based on user weights and filters.
    """
    # A. FILTER: Budget
    # Keep only rows where rent is within budget, obviously this should be strict
    filtered_df = df[df[bedroom_col] <= max_rent].copy()
    
    if filtered_df.empty:
        return filtered_df

    # B. SELECT: Get the correct normalized rent column
    # e.g. 'RENT_1BD' -> 'norm_rent_1bd'
    norm_rent_col = 'norm_' + bedroom_col.lower()

    # C. SCORE: Weighted Average
    # Extract weights dictionary
    w_rent = weights['rent']
    w_safety = weights['safety']
    w_transit = weights['transit']
    w_income = weights['income']
    w_trend = weights['crime_trend']
    
    total_weight = w_rent + w_safety + w_transit + w_income + w_trend
    if total_weight == 0: total_weight = 1

    # Calculate Score
    filtered_df['final_score'] = (
        (w_rent    * filtered_df[norm_rent_col]) +
        (w_safety  * filtered_df['norm_crime_rate']) +
        (w_transit * filtered_df['norm_transit']) +
        (w_income  * filtered_df['norm_income']) + 
        (w_trend   * filtered_df['norm_crime_trend'])
    ) / total_weight

    # Scale to 100
    filtered_df['final_score'] = (filtered_df['final_score'] * 100).round(1)
    
    return filtered_df.sort_values('final_score', ascending=False)

# 4. MAIN APP INTERFACE
def main():
    st.title("🌉 Bay Area Opportunity Mapper")
    st.markdown("Find the perfect ZIP code for your career, budget, and lifestyle.")

    # Load Data
    try:
        df = load_data()
    except FileNotFoundError:
        st.error("Error: 'bay_area_full_scored_data.csv' not found. Please run your normalization script first.")
        return

    # --- SIDEBAR CONTROLS ---
    with st.sidebar:
        st.header("1. Housing Needs")
        bedroom_option = st.selectbox(
            "Apartment Size", 
            ["Studio", "1 Bedroom", "2 Bedrooms", "3 Bedrooms", "4 Bedrooms"],
            index=1
        )
        # Map selection to column name
        bedroom_map = {
            "Studio": "RENT_STUDIO",
            "1 Bedroom": "RENT_1BD", 
            "2 Bedrooms": "RENT_2BD",
            "3 Bedrooms": "RENT_3BD",
            "4 Bedrooms": "RENT_4BD"
        }
        selected_bed_col = bedroom_map[bedroom_option]

        budget = st.slider("Max Monthly Budget ($)", 1000, 10000, 3500, step=100)

        st.header("2. Priorities (0-10)")
        w_rent = st.slider("💰 Low Cost", 0, 10, 5)
        w_safety = st.slider("🛡️ Safety (Current Rate)", 0, 10, 8)
        w_trend = st.slider("📉 Safety (Improving Trend)", 0, 10, 5)
        w_transit = st.slider("🚆 Transit Access", 0, 10, 5)
        w_income = st.slider("💼 Career / Human Capital", 0, 10, 2)

    # --- APP LOGIC ---
    
    # 1. Calculate Scores
    weights = {
        'rent': w_rent, 'safety': w_safety, 'crime_trend': w_trend, 
        'transit': w_transit, 'income': w_income
    }
    
    results = calculate_final_score(df, budget, selected_bed_col, weights)

    # 2. Display Results
    if results.empty:
        st.warning(f"No ZIP codes found with a {bedroom_option} under ${budget}.")
    else:
        st.success(f"Found {len(results)} matching ZIP codes.")
        
        # Display Top 10 Table
        display_cols = ['ZIP', 'PO_NAME', 'final_score', selected_bed_col, '2024_CRIMERATE_VIOL', 'TOTAL_TRANSIT']
        st.dataframe(results[display_cols].head(10), use_container_width=True)

        # (Phase 4.5 will be adding the map here!)

if __name__ == "__main__":
    main()

#instructions on running the app
### Step 2: How to Run It

#This is the cool part. Go to your terminal (make sure your `project_env` is active) and type:

#```bash
#streamlit run streamlit_app.py