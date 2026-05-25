import streamlit as st
import geopandas as gpd
import numpy as np
import folium
from streamlit_folium import folium_static
import libpysal
from esda.getis_ord import G_Local

# Page configuration
st.set_page_config(
    page_title="Spatial Hotspot Analyzer",
    page_icon="🌍",
    layout="wide"
)

st.title("🌍 Geospatial Hotspot Analysis Tool")
st.markdown("""
This application calculates the **Getis-Ord $Gi^*$ statistic** to identify statistically significant spatial clusters 
of high values (**hotspots**) and low values (**coldspots**).
""")

# 1. Sidebar for Data Upload and Parameters
st.sidebar.header("1. Input Configuration")
uploaded_file = st.sidebar.file_uploader(
    "Upload Spatial Layer (GeoJSON or GPKG)", 
    type=["geojson", "gpkg"]
)

# Sidebar configurations for spatial weights
st.sidebar.header("2. Analysis Parameters")
weight_type = st.sidebar.selectbox(
    "Spatial Weight Matrix Type",
    options=["Queen Contiguity", "Rook Contiguity", "Distance Band"]
)

if weight_type == "Distance Band":
    distance_threshold = st.sidebar.number_input(
        "Distance Threshold (meters/degrees)", 
        min_value=1.0, 
        value=1000.0, 
        step=100.0
    )

# 2. Main Logic Execution
if uploaded_file is not None:
    try:
        # Load data using GeoPandas
        @st.cache_data
        def load_spatial_data(file):
            gdf = gpd.read_file(file)
            return gdf

        gdf = load_spatial_data(uploaded_file)
        
        st.subheader("📊 Data Preview & Schema Inspection")
        st.write(f"Total Features Loaded: **{len(gdf)}**")
        st.dataframe(gdf.head(5), use_container_width=True)
        
        # Select target numerical column for evaluation
        numerical_cols = gdf.select_dtypes(include=[np.number]).columns.tolist()
        
        if not numerical_cols:
            st.error("The uploaded dataset does not contain any numerical columns to evaluate clustering.")
        else:
            target_col = st.selectbox(
                "Select Numerical Variable to Analyze (e.g., Incident Count, Value):", 
                options=numerical_cols
            )
            
            # Run Analysis Trigger Button
            if st.button("🚀 Run Hotspot Analysis"):
                with st.spinner("Constructing spatial weights matrix and calculating Z-scores..."):
                    
                    # Target array of values
                    y = gdf[target_col].values
                    
                    # Define Spatial Weights
                    if weight_type == "Queen Contiguity":
                        w = libpysal.weights.Queen.from_dataframe(gdf, use_index=False)
                    elif weight_type == "Rook Contiguity":
                        w = libpysal.weights.Rook.from_dataframe(gdf, use_index=False)
                    else:
                        w = libpysal.weights.DistanceBand.from_dataframe(gdf, threshold=distance_threshold, binary=True)
                    
                    # Handle isolated islands/islands with 0 neighbors safely
                    w.transform = 'R' # Row-standardize weights matrix
                    
                    # Compute Local Getis-Ord Gi*
                    # star=True includes the focal cell 'i' in its own local neighborhood calculation
                    go = G_Local(y, w, transform='R', star=True)
                    
                    # Append calculations back to the GeoDataFrame
                    gdf['z_score'] = go.Zs
                    gdf['p_value'] = go.p_sim
                    
                    # Classify outputs into Hot/Cold Confidence categories based on standard Z-scores
                    def classify_hotspot(row):
                        z = row['z_score']
                        if z >= 2.58: return "Hotspot - 99% Confidence"
                        elif z >= 1.96: return "Hotspot - 95% Confidence"
                        elif z >= 1.65: return "Hotspot - 90% Confidence"
                        elif z <= -2.58: return "Coldspot - 99% Confidence"
                        elif z <= -1.96: return "Coldspot - 95% Confidence"
                        elif z <= -1.65: return "Coldspot - 90% Confidence"
                        else: return "Not Significant"
                        
                    gdf['hotspot_category'] = gdf.apply(classify_hotspot, axis=1)
                    
                st.success("Analysis Complete!")
                
                # Layout for Map and Summary Metrics
                col1, col2 = st.columns([3, 1])
                
                with col2:
                    st.markdown("### Summary Metrics")
                    category_counts = gdf['hotspot_category'].value_counts()
                    st.write(category_counts)
                    
                with col1:
                    st.markdown("### 🗺️ Statistical Cluster Map")
                    
                    # Reproject to WGS84 for leaflet map compatibility
                    gdf_wgs84 = gdf.to_crs(epsg=4326)
                    
                    # Color Mapping Dictionary matching standard spatial mapping palettes
                    color_map = {
                        "Hotspot - 99% Confidence": "#d73027",  # Dark Red
                        "Hotspot - 95% Confidence": "#f46d43",  # Orange Red
                        "Hotspot - 90% Confidence": "#fdae61",  # Light Orange
                        "Not Significant": "#e0e0e0",           # Soft Grey
                        "Coldspot - 90% Confidence": "#abd9e9", # Light Blue
                        "Coldspot - 95% Confidence": "#74add1", # Mid Blue
                        "Coldspot - 99% Confidence": "#4575b4"  # Dark Blue
                    }
                    
                    # Determine map center point
                    centroid = gdf_wgs84.unary_union.centroid
                    m = folium.Map(location=[centroid.y, centroid.x], zoom_start=11, tiles="cartodbpositron")
                    
                    # Style function for GeoJSON layer
                    def style_fn(feature):
                        cat = feature['properties']['hotspot_category']
                        return {
                            'fillColor': color_map.get(cat, '#ffffff'),
                            'color': '#666666',
                            'weight': 0.8,
                            'fillOpacity': 0.75
                        }
                    
                    # Add interactive GeoJSON Layer with tooltips
                    folium.GeoJson(
                        gdf_wgs84,
                        style_function=style_fn,
                        tooltip=folium.GeoJsonTooltip(
                            fields=[target_col, 'z_score', 'hotspot_category'],
                            aliases=['Value:', 'Z-Score:', 'Status:'],
                            localize=True
                        )
                    ).add_to(m)
                    
                    # Render map inside Streamlit
                    folium_static(m, width=900, height=550)
                    
                    # Export Data capability
                    st.download_button(
                        label="📥 Download Analyzed GeoJSON",
                        data=gdf.to_json(),
                        file_name="hotspot_analysis_results.geojson",
                        mime="application/json"
                    )
                    
    except Exception as e:
        st.error(f"An error occurred while processing the spatial data: {e}")
        st.info("Ensure your file has a valid geometry column and features share topological boundaries.")

else:
    st.info("💡 Please upload a GeoJSON or GeoPackage file in the sidebar to begin processing.")
