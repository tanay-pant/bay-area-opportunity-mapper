import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from shapely import wkt

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
    df = pd.read_csv('~/Downloads/opportunity mapper/final_df_with_norms.csv')

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
    w_rent = weights['rent']
    w_safety_viol = weights['safety_viol']
    w_safety_prop = weights['safety_prop']
    w_transit = weights['transit']
    w_income = weights['income']

    total_weight = w_rent + w_safety_viol + w_safety_prop + w_transit + w_income
    # In case all weights are zero, set total_weight to 1 to avoid / 0
    if total_weight == 0: 
        total_weight = 1

    # Calculate Score
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
    st.markdown("Find the perfect ZIP code in the Bay for your career, budget, and lifestyle.")

    # Load Data
    try:
        gdf = load_data()
    except FileNotFoundError:
        st.error("Error: file not found. Please run your normalization script first.")
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
        selected_bed_col_display = f"${selected_bed_col}.00"

        budget = st.slider("Max Monthly Budget ($)", 800, 10000, 3500, step=100)

        st.header("2. Priorities (0-10)")
        w_rent = st.slider("Low Cost", 0, 10, 5)
        w_safety_viol = st.slider("Safety — VIOLENCE (2024 Rate)", 0, 10, 8)
        w_safety_prop = st.slider("Safety — PROPERTY (2024 Rate)", 0, 10, 7) 
        w_transit = st.slider("Public Transit Access (BART, CalTrain)", 0, 3, 2)
        w_income = st.slider("Local Wealth / Human Capital", 0, 10, 3)

        show_income = st.checkbox("Display Median Income?", value=True)
        show_viol_crime = st.checkbox("Display Violent Crime Data?", value=True)
        show_prop_crime = st.checkbox("Display Property Crime Data?", value=True)
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
        
        # ------ UNUSED, DISPLAY DATAFRAME WITH THE TOP TEN RESULTS -----------
        #
        #st.subheader("Top 10 ZIP Codes")
        ##display_cols = ['ZIP', 'CITY', 'final_score', selected_bed_col, '2024_CRIMERATE_VIOL', 'CHANGE_IN_CRIME_VIOL%', '2024_CRIMERATE_PROP', 'CHANGE_IN_CRIME_PROP%', 'BART_COUNT', 'CalTrain_COUNT', 'DISPLAY_MEDIAN_INCOME_HOUSEHOLD_EST']
        #st.dataframe(results[display_cols].head(10), use_container_width=True)
        #
        # ------ UNUSED, DISPLAY DATAFRAME WITH THE TOP TEN RESULTS -----------

        # keep some bounds so that map stays in Bay Area zone

        min_lon, max_lon = -123.5, -120.3
        min_lat, max_lat = 36.5, 39.6

        # center map on Bay area
        m = folium.Map(location=[37.85, -121.89], zoom_start=9,
                min_lat=min_lat, max_lat=max_lat, min_lon=min_lon, max_lon=max_lon,)

        bounds = results.total_bounds
        # Folium requires bounds in [[lat_min, lon_min], [lat_max, lon_max]] format
        m.fit_bounds([
            [bounds[1], bounds[0]], # southwest corner (lat, lon)
            [bounds[3], bounds[2]]  # northeast corner (lat, lon)
        ])

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
        fields_ = ['ZIP', 'final_score', selected_bed_col, selected_bed_col + '_90', selected_bed_col + '_110']
        aliases_ = ['ZIP:', 'Score:', 'Rent:', 'Rent (90th Percentile):', 'Rent (110th Percentile):']

        # form display options get updated here, DEFINITELY not the most efficient way but it works lmao
        if show_viol_crime: fields_.extend(['2024_CRIMERATE_VIOL', 'CHANGE_IN_CRIME_VIOL%']); aliases_.extend(['Violent Crime Rate (2024):', 'Violent Crime Rate Percent since 2020:'])
        if show_prop_crime: fields_.extend(['2024_CRIMERATE_PROP', 'CHANGE_IN_CRIME_PROP%']); aliases_.extend(['Property Crime Rate (2024):', 'Property Crime Rate Percent since 2020:'])
        if show_income: fields_.append('DISPLAY_MEDIAN_INCOME_HOUSEHOLD_EST'); aliases_.append('Median Household Income:')
        if show_households: fields_.append('TOTAL_HOUSEHOLDS_EST'); aliases_.append('Total Households:')
        if show_transit: fields_.extend(['BART_COUNT', 'CalTrain_COUNT']); aliases_.extend(['BART:', 'CalTrain:'])

        folium.GeoJsonTooltip(
            fields=fields_,
            aliases=aliases_,
            localize=True
        ).add_to(cp.geojson)

        # FIX THESE POPUPS LATER TO DISPLAY MORE DATA AND HAVE TOOLTIPS DISPLAY LESS DATA (or at least more concise)
        folium.GeoJsonPopup(
            fields=fields_,
            aliases=aliases_,
            localize=True
        ).add_to(cp.geojson)

        # RENDER MAP
        st_folium(m, use_container_width=True, height=450, returned_objects=[])
        
        # Top 10 Table
        with st.expander("See Top 10 Details"):
            # Drop geometry for cleaner table display
            display_cols = ['ZIP', 'final_score', selected_bed_col, '2024_CRIMERATE_VIOL', 'BART_COUNT']
            st.dataframe(results[display_cols].drop(columns='geometry', errors='ignore').head(10), use_container_width=True)

if __name__ == "__main__":
    main()

    ##### THINGS TO COMPLETE BEFORE THE PROJECT IS DONE #######:

    # - adding $ signs and making rent columns look better might need to be done in jupyter
    # - make crime more readable, maybe in jupyter. USE POPUPS INSTEAD OF TOOLTIPS FOR COMPLEX DATA!!
    # - dress up tooltips and popups in general, emojis based on crime going up or down, etc.
    # - Look at weights: what's up with them not being normalized ints? Public transit matters less than the others, why?
    # - make the sidebars look better
    # - Give details about construction of the dataframe and how the scores are calculated
