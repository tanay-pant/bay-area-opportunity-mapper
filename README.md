# bay-area-opportunity-mapper

![license](https://img.shields.io/badge/license-MIT-green)

> **An interactive heatmap built with GeoPandas and Folium to help explore promising Bay Area ZIP codes based on rent, crime, transit access, and income.**

![App Screenshot](/OppMapSS1.png)

## Overview:
The **Bay Area Opportunity Mapper** is an interactive web application that helps users identify promising neighborhoods by synthesizing disparate datasets. Unlike standard apartment finders that only look at rent, this tool calculates a holistic **"Opportunity Score"** for every ZIP code based on:
-   **Affordability:** Median apartment rent per # of bedrooms.
-   **Safety:** Violence and property crime rates (and trends).
-   **Connectivity:** Access to BART and Caltrain transit systems.
-   **Human Capital:** Local median income and economic vibrancy.

## Methodology/How It Works
The scoring engine uses a Weighted Decision Matrix:
1.  **Data Integration:** Merges HUD rent data, DOJ crime stats, and Census demographics using geospatial joins (GeoPandas). Drop useless zip codes and ensure proper data joins. The initial cleanup happens in _BaseDatasets1.ipnyb_, and the geospatial properties are merged in _GeoDatasets1.ipynb_.
2.  **Normalization:** Scales all metrics from 0 to 1 using MinMax scaling (inverting "bad" metrics like crime/rent). This takes place in _Metrics1.ipynb_, which is also where the 'DISPLAY' columns are made for the front-end
3.  **Dynamic Scoring:**
    $$\text{Score} = \frac{\sum (Weight_i \times Metric_i)}{\sum Weights}$$
    The user controls the weights via the UI, allowing the map to instantly re-rank ZIP codes based on individual priorities (e.g., optimizing for "Safety" vs. "Budget").

## Project Structure
* `streamlit_app.py`: The main application and front-end logic.
* `The IPNYB files`: Notebooks that merge and clean dataframes into usable state. Base -> Geo -> Metrics.
* `final_df_with_norms.csv`: The processed dataset powering the app.
* `raw_datasets/`: Contains raw CSVs and Shapefiles.

## Requirements:
- Language: Python
- Data Analysis: Pandas, NumPy, Scikit-learn
- Geospatial Analysis: GeoPandas
- Web App Framework: Streamlit
- Mapping Library: Folium

## Next Steps:

This is an early demo (2-week project of mine). Next steps could include using live APIs (Zillow/Transit/Jobs) for present-day accurate data rather than relying on static CSV files supplied by the government. Additionally, improving data pipelines, adding richer streamlit interactivity, getting a dataset of crime by ZIP CODE as opposed to County, and introducing more metrics would help make the model more comprehensive.

## Sources:

-   Median Rent: [huduser.gov](https://www.huduser.gov/portal/datasets/fmr.html#documents_2026)
-   GeoSpatial Zip Code Bay Area: [geodata](https://geodata.lib.berkeley.edu/catalog/ark28722-s7888q)
-   BART: [bart.gov](https://www.bart.gov/schedules/developers/geo) / CalTrain: [arcgis](https://gisdata-caltrans.opendata.arcgis.com/datasets/7ad7157d33384076ae3363bffb3ce2be_0/explore?showTable=true)
-   Median income: [census.gov](https://data.census.gov/table/ACSST1Y2024.S1901?q=S1901:+Income+in+the+Past+12+Months+(in+2024+Inflation-Adjusted+Dollars)&g=040XX00US06,06$8600000) (S1901)
-   Crime Statistics: [OpenJustice DOJ](https://openjustice.doj.ca.gov/exploration/crime-statistics/crimes-clearances)
-   Zip-Code, County, City crosswalk: [Census](https://www2.census.gov/geo/docs/maps-data/data/rel/zcta_county_rel_10.txt)

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
