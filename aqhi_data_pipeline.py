import requests
import json
import geopandas as gpd
import pandas as pd
import numpy as np
import rasterio
import xarray as xr
from geojson import Feature, FeatureCollection, Point
from datetime import datetime
from shapely.geometry import Point
from scipy.spatial import cKDTree

def fetch_and_process_aqhi_data(output_nc_path="data/aqhi_grid.nc", grid_res=2000):

    url = "https://api.weather.gc.ca/collections/aqhi-forecasts-realtime/items?f=json&limit=100000"
    response = requests.get(url)
    data = response.json()

    features = []

    for item in data.get("features", []):
        props = item["properties"]
        geom = item["geometry"]

        feature = Feature(
            geometry=Point((geom["coordinates"][0], geom["coordinates"][1])),
            properties={
               "location": props.get("location_name_en", "Unknown"),
                "location_id": props.get("location_id", "N/A"),
                "aqhi": props.get("aqhi", -1),
                "forecast_time": props.get("forecast_datetime", "Unknown"),
                "forecast_issue": props.get("publication_datetime", "Unknown")
            })
        features.append(feature)
    

    geojson_data = FeatureCollection(features)
    
    gdf = gpd.GeoDataFrame(features, geometry=[f["geometry"] for f in features], crs="EPSG:4326")
    properties_df = pd.json_normalize(gdf["properties"])
    gdf = pd.concat([properties_df, gdf.drop(columns="properties")], axis=1)
    gdf = gpd.GeoDataFrame(gdf, geometry="geometry", crs="EPSG:4326")

    gdf = gdf[gdf.geometry.notnull() & gdf["aqhi"].notnull()]

    gdf = gdf.to_crs(epsg=3978)

    coords = np.array([[pt.x, pt.y] for pt in gdf.geometry])
    values = gdf["aqhi"].astype(float).values

    valid_mask = np.isfinite(coords).all(axis=1) & np.isfinite(values)
    coords = coords[valid_mask]
    values = values[valid_mask]

    xmin, ymin, xmax, ymax = gdf.total_bounds
    xmin1 = int(xmin)
    ymin1 = int(ymin)
    xmax1 = int(xmax)
    ymax1 = int(ymax)

    x_steps = int((xmax1 - xmin1) // grid_res)
    y_steps = int((ymax1 - ymin1) // grid_res)

    x_coords = np.linspace(xmin, xmax, x_steps)
    y_coords = np.linspace(ymin, ymax, y_steps)

    xx, yy = np.meshgrid(x_coords, y_coords)
    grid_points = np.c_[xx.ravel(), yy.ravel()]

    def idw_interpolation(xy_known, values_known, xy_grid, k=10, power=2):
        tree = cKDTree(xy_known)
        dists, idxs = tree.query(xy_grid, k=k)
        weights = 1 / np.power(dists + 1e-10, power)
        return np.sum(weights * values_known[idxs], axis=1) / np.sum(weights, axis=1)


    interpolated_vals = idw_interpolation(coords, values, grid_points)
    grid_array = interpolated_vals.reshape((len(y_coords), len(x_coords)))

    da = xr.DataArray(
        grid_array,
        coords={"y": yy[:, 0], "x": xx[0, :]},
        dims=["y", "x"],
        name="aqhi"
    )
    

    import os
    if os.path.exists(output_nc_path):
        os.remove(output_nc_path)

    xr.Dataset({"aqhi": da}).to_netcdf(output_nc_path)
    


import xarray as xr
if __name__ == "__main__":
    fetch_and_process_aqhi_data()
    ds = xr.open_dataset("data/aqhi_grid.nc")
    print(ds)