import rasterio
import geopandas as gpd
from shapely.geometry import Point
import numpy as np

tif_path = "static/aqhi_grid.tif"
geojson_path = "static/aqhi_grid.geojson"
stride = 5 

with rasterio.open(tif_path) as src:
    data = src.read(1)
    transform = src.transform

    rows, cols = np.meshgrid(
        np.arange(0, data.shape[0], stride),
        np.arange(0, data.shape[1], stride),
        indexing='ij'
    )

    rows = rows.flatten()
    cols = cols.flatten()

    points = []
    values = []

    for row, col in zip(rows, cols):
        x, y = rasterio.transform.xy(transform, row, col, offset='center')
        value = data[row, col]
        if not np.isnan(value):
            points.append(Point(x, y))
            values.append(value)

gdf = gpd.GeoDataFrame({'aqhi': values}, geometry=points, crs="EPSG:4326")
gdf.to_file(geojson_path, driver='GeoJSON')
print(f"Done! Exported {len(points)} points to {geojson_path}")


import geopandas as gpd

gdf = gpd.read_file("static/aqhi_grid.geojson")

gdf = gdf.set_crs(epsg=3857, allow_override=True)

gdf = gdf.to_crs(epsg=4326)

gdf.to_file("static/aqhi_grid_latlon.geojson", driver="GeoJSON")