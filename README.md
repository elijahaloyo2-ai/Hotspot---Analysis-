# 🌍 Spatial Hotspot Analyzer

An interactive web application developed in Python using **Streamlit** and **PySAL** to perform local spatial autocorrelation using the **Getis-Ord $Gi^*$ statistic**. This engine evaluates clustering patterns to distinguish statistically significant hotspots and coldspots from random distributions.

## 🚀 Features
* **Spatial File Ingestion:** Supports upload of complex polygon frameworks via `.geojson` and `.gpkg` file structures.
* **Dynamic Weight Control:** Toggle between Queen Contiguity, Rook Contiguity, or specified Distance Band spatial relationships.
* **Interactive Cartography:** Displays outcomes mapped dynamically by confidence boundaries (90%, 95%, 99%) utilizing an optimized Leaflet canvas via `streamlit-folium`.
* **Data Portability:** Downstream export options to download calculation vectors directly back into client environments as evaluated GeoJSON files.

## 🛠️ Local Installation & Development

To spin up this application on your local workstation machine:

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git](https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git)
   cd YOUR_REPO_NAME
   python -m venv venv
   
2. Create and activate a virtual isolation environment:
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

3. install spatial packages
pip install -r requirements.txt

4. boost the streamlit runtime application
streamlit run app.py
