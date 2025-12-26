import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from shapely import wkt

# License: MIT License — see LICENSE file in repository
# Copyright (c) 2025 Tanay Pant

# 1. PAGE CONFIGURATION
st.set_page_config(
    page_title="Bay Area Opportunity Mapper",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. LOAD DATA (Cached for performance)
@st.cache_data
def load_data():
    # read final_df
    # ======== IMPORTANT: ADJUST PATH AS NEEDED!! (Depending on where you clone the repo to) ========
    df = pd.read_csv('final_df_with_norms.csv')

    # now convert geometry to shapely objects for map
    df['geometry'] = df['geometry'].apply(wkt.loads)
    
    # make the gdf
    gdf = gpd.GeoDataFrame(df, geometry='geometry')
    
    # set Coordinate Reference System (CRS)
    # we use 4326 (standard GPS lat/lon) like before in GeoDatasets1.ipynb.
    gdf.set_crs(epsg=4326, inplace=True) 

    # 4. keep zip a string for consistency
    gdf['ZIP'] = gdf['ZIP'].astype(str)
    
    return gdf

# Helper to create county boundaries from existing ZIP data
def get_county_boundaries(gdf):
    # Dissolve (merge) ZIPs by County Name
    if 'COUNTY' in gdf.columns:
        county_gdf = gdf.dissolve(by='COUNTY').reset_index()
        return county_gdf
    return None

# 3. SCORING FUNCTION
def calculate_final_score(gdf, max_rent, bedroom_col, weights):
    """
    Calculates a score (0-100) for each zip code based on user weights and filters.
    """
    # A. FILTER: Budget
    # Keep only rows where rent is within budget, obviously this should be strict
    # Since we're looking at median rents though, we can budge it by 1.2x
    filtered_gdf = gdf[gdf[bedroom_col] <= max_rent * 1.2].copy()
    
    if filtered_gdf.empty: # base check but definitely not the case
        return filtered_gdf

    # B. SELECT: Get the correct normalized rent column
    # e.g. 'RENT_1BD' -> 'norm_rent_1bd'
    norm_rent_col = 'norm_' + bedroom_col.lower()

    # C. SCORE: Weighted Average
    # Extract weights dictionary

    # The sliders use different maxima (most are 0-10, transit is 0-3), so we divide by slider max to normalize.
    # Now, transit has as much of an impact as the others without needing a weirdly big integer range.
    slider_max = {
        'rent': 10,
        'safety_viol': 10,
        'safety_prop': 10,
        'transit': 3,
        'income': 10
    }

    # Normalize weights to 0-1 range based on slider maxima
    w_rent = weights['rent'] / slider_max['rent'] if slider_max['rent'] else 0
    w_safety_viol = weights['safety_viol'] / slider_max['safety_viol'] if slider_max['safety_viol'] else 0
    w_safety_prop = weights['safety_prop'] / slider_max['safety_prop'] if slider_max['safety_prop'] else 0
    w_transit = weights['transit'] / slider_max['transit'] if slider_max['transit'] else 0
    w_income = weights['income'] / slider_max['income'] if slider_max['income'] else 0

    total_weight = w_rent + w_safety_viol + w_safety_prop + w_transit + w_income
    if total_weight == 0:
        total_weight = 1

    # Calculate weighted average using normalized slider weights
    filtered_gdf['final_score'] = (
        (w_rent * filtered_gdf[norm_rent_col]) +
        (w_safety_viol * filtered_gdf['norm_crime_rate_viol']) +
        (w_safety_prop * filtered_gdf['norm_crime_rate_prop']) +
        (w_transit * filtered_gdf['norm_transit']) +
        (w_income * filtered_gdf['norm_income'])
    ) / total_weight

    # Scale to 100
    filtered_gdf['final_score'] = (filtered_gdf['final_score'] * 100).round(1)

    return filtered_gdf.sort_values('final_score', ascending=False)

# 4. MAIN APP INTERFACE
def main():
    st.title("Bay Area Opportunity Mapper")
    st.markdown("Find the perfect ZIP code in the San Francisco Bay for your career, budget, and lifestyle.")
    st.markdown("Click on a ZIP code for more information, and scroll down for details about this project.")

    # Load Data
    try:
        gdf = load_data()
    except FileNotFoundError:
        st.error("Error: file not found. Please check your PATH.")
        return

    # --- SIDEBAR CONTROLS ---
    with st.sidebar.form(key='search_form'):

        show_county = st.checkbox("Display County Borders?")

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

        budget = st.slider("Max Monthly Budget ($)", 800, 10000, 3500, step=100)

        st.header("2. Priorities (0-10)")
        w_rent = st.slider("Low Cost", 0, 10, 5)
        w_safety_viol = st.slider("Safety — VIOLENCE (2024 Rate)", 0, 10, 8)
        w_safety_prop = st.slider("Safety — PROPERTY (2024 Rate)", 0, 10, 7) 
        w_transit = st.slider("Public Transit Access (BART, CalTrain)", 0, 3, 2)
        w_income = st.slider("Local Wealth / Human Capital", 0, 10, 3)

        show_income = st.checkbox("Display Median Income?", value=True)
        show_crime_stats = st.checkbox("Display Crime Data?", value=True)
        show_transit = st.checkbox("Display Public Transit Data?")
        show_households = st.checkbox("Display Total Households?",)

        st.form_submit_button(label='Update Map')

    # --- APP LOGIC FROM HERE ON OUT ---
    
    # 1. Calculate Scores
    weights = {
        'rent': w_rent, 'safety_viol': w_safety_viol, 'safety_prop': w_safety_prop,
        'transit': w_transit, 'income': w_income
    }
    
    results = calculate_final_score(gdf, budget, selected_bed_col, weights)

    # 2. Display Results
    if results.empty:
        st.warning(f"No ZIP codes found with a {bedroom_option} under ${budget}.")
    else:
        st.success(f"Found {len(results)} matching ZIP codes.")

        # keep some bounds so that map stays in Bay Area zone

        min_lon, max_lon = -123.5, -120.3
        min_lat, max_lat = 36.5, 39.6

        # center map on Bay area
        m = folium.Map(location=[37.85, -121.89], zoom_start=9, max_bounds=True,
                min_lat=min_lat, max_lat=max_lat, min_lon=min_lon, max_lon=max_lon,)

        bounds = results.total_bounds
        # Folium requires bounds in [[lat_min, lon_min], [lat_max, lon_max]] format
        m.fit_bounds([
            [bounds[1], bounds[0]], # southwest corner (lat, lon)
            [bounds[3], bounds[2]]  # northeast corner (lat, lon)
        ])

        # create a user-friendly string for final score (e.g. "85.3/100") (gonna use for tooltip display later on)
        results['final_score_str'] = results['final_score'].apply(lambda x: f"{str(x)}/100")

        # Pass the 'results' GeoDataFrame as BOTH the geo_data and the data
        cp = folium.Choropleth(
            geo_data=results,                # geometry
            data=results,                    # The data (scores)
            columns=['ZIP', 'final_score'],  # [Key, Value]
            key_on='feature.properties.ZIP', # Use properties.ZIP to link geometry to data
            fill_color='RdYlGn',             # get that distinctive red/green heatmap color scheme
            fill_opacity=0.7,
            line_opacity=0.2,
            legend_name='Opportunity Score (0-100)',
            highlight=True
        ).add_to(m)

        county_boundaries = get_county_boundaries(gdf)
        
        if county_boundaries is not None and show_county:
            folium.GeoJson(
                county_boundaries,
                name="County Borders",
                style_function=lambda x: {
                    'color': 'purple',      # Color border
                    'weight': 2.5,           # Thick line
                    'opacity': 1.0,      # Transparent fill (only show the border)
                },
                tooltip=None,
                interactive=False
            ).add_to(m)

        # ADD TOOLTIPS (Hover info)
        # Using GeoJsonTooltip on the choropleth's geojson layer

        ttfields_ = ['ZIP', 'COUNTY', 'final_score_str', f'DISPLAY_{selected_bed_col}']
        ttaliases_ = ['ZIP:', 'County:', 'Opportunity Score:', 'Median Rent:', ]

        # form display options get updated here, DEFINITELY not the most efficient way but it works lmao
        if show_crime_stats: ttfields_.extend(['DISPLAY_CHANGE_IN_CRIME_VIOL%', 'DISPLAY_CHANGE_IN_CRIME_PROP%']); ttaliases_.extend(['Violent crime since 2020:', 'Property Crime since 2020:']) # repeated line 225 for clarity (for popups)
        if show_income: ttfields_.append('DISPLAY_MEDIAN_INCOME_HOUSEHOLD_EST'); ttaliases_.append('Median Household Income:')
        
        # what shows up in the tooltips (user HOVERS over zip code)
        folium.GeoJsonTooltip(
            fields=ttfields_,
            aliases=ttaliases_,
            localize=True
        ).add_to(cp.geojson)

        pufields_ = ['ZPOP', f'DISPLAY_{selected_bed_col}_RANGE']
        pualiases_ = ['Population:', 'Average Rent Range:']

        # form display options get updated here same as before
        if show_households: pufields_.append('TOTAL_HOUSEHOLDS_EST'); pualiases_.append('Total Households:')
        if show_transit: pufields_.extend(['BART_COUNT', 'CalTrain_COUNT']); pualiases_.extend(['BART Stations:', 'CalTrain Stations:'])
        if show_crime_stats: pufields_.extend(['DISPLAY_2024_CRIMERATE_VIOL', 'DISPLAY_2024_CRIMERATE_PROP']); pualiases_.extend(['2024 Violent Crime:', '2024 Property Crime:'])

        # what shows up in the popups (user CLICKS on zip code)
        folium.GeoJsonPopup(
            fields=pufields_,
            aliases=pualiases_,
            localize=True
        ).add_to(cp.geojson)

        # RENDER MAP
        st_folium(m, use_container_width=True, height=450, returned_objects=[])
        
        # Top 10 Table
        with st.expander("See Top 10 Details"):
            # Drop geometry for cleaner table display
            display_cols = ['final_score_str', 'ZIP', 'COUNTY', 'ZPOP', f'DISPLAY_{selected_bed_col}', 'DISPLAY_2024_CRIMERATE_VIOL', 'TOTAL_HOUSEHOLDS_EST', 'DISPLAY_MEDIAN_INCOME_HOUSEHOLD_EST']
            st.dataframe(results[display_cols].rename(columns={'final_score_str': 'Opportunity Score'}).head(10), use_container_width=True)

    # Polished footer: two columns, badges/links, short overview, data sources expander, and disclaimer
    st.markdown("---")
    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.markdown(
            """
            **Made by**
            **Tanay Pant**  
            DS/Econ '27 — UC Berkeley

            [View on GitHub](https://github.com/tanay-pant/bay-area-opportunity-mapper)
            """
        )
        # small badges (static image shields)
        st.markdown(
            "![license](https://img.shields.io/badge/license-MIT-green) " \
            "![python](https://img.shields.io/badge/python-3.10-blue)")

    with col_right:
        st.markdown("""
        ### About this app

        This interactive map helps you compare Bay Area ZIP codes by combining normalized measures of **rent**, **crime**, **transit access**, and **income** into a single *Opportunity Score* (0–100).

        - Use the sidebar to adjust your budget and priorities.
        - Hover to see quick stats; click a ZIP for a detailed popup.
        - Scores are normalized so each category can reach equal maximum influence unless you change weights.
        """)

        with st.expander("Data sources & notes"):
            st.markdown(
                """
                **Data sources:** see the repository README for the full list of sources (rent, crime, transit, income, and shapefiles).

                **Method notes:** Datasets were sourced from government agencies and publicly available datasets, cleaned, merged on ZIP Code, and geometries prepared using GeoPandas. Final scores are a normalized weighted average of component metrics, then scaled to 0–100.
                """
            )

        st.markdown("*Disclaimer: Do not use a single composite score as the deciding factor in choosing where to live.*")

if __name__ == "__main__":
    main()
