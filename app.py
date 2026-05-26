import streamlit as st
import geopandas as gpd
import numpy as np
import folium
from streamlit_folium import folium_static

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

# 1. Sidebar for Data Upload
st.sidebar.header("1. Input Configuration")
uploaded_file = st.sidebar.file_uploader(
    "Upload Spatial Layer (GeoJSON or GPKG)", 
    type=["geojson", "gpkg"]
)

st.sidebar.header("2. Analysis Parameters")
st.sidebar.info("Using Contiguity Matrix engine (Focal feature included: Gi*)")

# 2. Main Logic Execution
if uploaded_file is not None:
    try:
        @st.cache_data
        def load_spatial_data(file):
            return gpd.read_file(file)

        gdf = load_spatial_data(uploaded_file)
        
        st.subheader("📊 Data Preview")
        st.write(f"Total Features Loaded: **{len(gdf)}**")
        st.dataframe(gdf.head(5), use_container_width=True)
        
        # Select target numerical column for evaluation
        numerical_cols = gdf.select_dtypes(include=[np.number]).columns.tolist()
        
        if not numerical_cols:
            st.error("The uploaded dataset does not contain any numerical columns.")
        else:
            target_col = st.selectbox(
                "Select Numerical Variable to Analyze:", 
                options=numerical_cols
            )
            
            if st.button("🚀 Run Hotspot Analysis"):
                with st.spinner("Calculating spatial statistics matrix..."):
                    
                    n = len(gdf)
                    y = gdf[target_col].values.astype(float)
                    
                    # Calculate global parameters
                    y_mean = np.mean(y)
                    y_std = np.std(y)
                    
                    if y_std == 0:
                        st.error("The selected variable has zero variance. Cannot compute statistics.")
                        st.stop()
                    
                    # Generate spatial weights matrix (Fixed topology search)
                    # Touching boundaries define spatial neighbors
                    centroids = gdf.geometry.centroid
                    z_scores = np.zeros(n)
                    
                    # Pure math implementation of local Getis-Ord Gi*
                    for i in range(n):
                        # Find indices of intersecting features (Queen contiguity)
                        neighbors_idx = gdf.index[gdf.geometry.touches(gdf.geometry.iloc[i])].tolist()
                        neighbors_idx.append(i) # Include star component (self)
                        
                        # Spatial weights vector for location i
                        w_i = np.ones(len(neighbors_idx))
                        sum_w = float(len(neighbors_idx))
                        sum_w_sq = float(len(neighbors_idx))
                        
                        # Local sum calculation
                        local_sum = np.sum(y[neighbors_idx])
                        
                        # Getis-Ord Gi* standard formula calculation
                        numerator = local_sum - (y_mean * sum_w)
                        denominator_term = np.sqrt((n * sum_w_sq - (sum_w ** 2)) / (n - 1))
                        denominator = y_std * denominator_term
                        
                        if denominator != 0:
                            z_scores[i] = numerator / denominator
                        else:
                            z_scores[i] = 0.0

                    # Append calculations back safely
                    gdf['z_score'] = z_scores
                    
                    # Classify categories using standard critical value thresholds
                    def classify_hotspot(z):
                        if z >= 2.58: return "Hotspot - 99% Confidence"
                        elif z >= 1.96: return "Hotspot - 95% Confidence"
                        elif z >= 1.65: return "Hotspot - 90% Confidence"
                        elif z <= -2.58: return "Coldspot - 99% Confidence"
                        elif z <= -1.96: return "Coldspot - 95% Confidence"
                        elif z <= -1.65: return "Coldspot - 90% Confidence"
                        else: return "Not Significant"
                        
                    gdf['hotspot_category'] = gdf['z_score'].apply(classify_hotspot)
                    
                st.success("Analysis Complete!")
                
                col1, col2 = st.columns([3, 1])
                
                with col2:
                    st.markdown("### Summary Metrics")
                    st.write(gdf['hotspot_category'].value_counts())
                    
                with col1:
                    st.markdown("### 🗺️ Statistical Cluster Map")
                    
                    gdf_wgs84 = gdf.to_crs(epsg=4326)
                    
                    color_map = {
                        "Hotspot - 99% Confidence": "#d73027",
                        "Hotspot - 95% Confidence": "#f46d43",
                        "Hotspot - 90% Confidence": "#fdae61",
                        "Not Significant": "#e0e0e0",
                        "Coldspot - 90% Confidence": "#abd9e9",
                        "Coldspot - 95% Confidence": "#74add1",
                        "Coldspot - 99% Confidence": "#4575b4"
                    }
                    
                    centroid = gdf_wgs84.unary_union.centroid
                    m = folium.Map(location=[centroid.y, centroid.x], zoom_start=11, tiles="cartodbpositron")
                    
                    def style_fn(feature):
                        cat = feature['properties']['hotspot_category']
                        return {
                            'fillColor': color_map.get(cat, '#ffffff'),
                            'color': '#666666',
                            'weight': 0.8,
                            'fillOpacity': 0.75
                        }
                    
                    folium.GeoJson(
                        gdf_wgs84,
                        style_function=style_fn,
                        tooltip=folium.GeoJsonTooltip(
                            fields=[target_col, 'z_score', 'hotspot_category'],
                            aliases=['Value:', 'Z-Score:', 'Status:'],
                            localize=True
                        )
                    ).add_to(m)
                    
                    folium_static(m, width=900, height=550)
                    
                    st.download_button(
                        label="📥 Download Analyzed GeoJSON",
                        data=gdf.to_json(),
                        file_name="hotspot_analysis_results.geojson",
                        mime="application/json"
                    )
                    
    except Exception as e:
        st.error(f"Processing Error: {e}")

else:
    st.info("💡 Please upload a GeoJSON or GeoPackage file in the sidebar to begin processing.")
