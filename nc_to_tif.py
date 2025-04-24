import xarray as xr
import rioxarray

ds = xr.open_dataset("data/aqhi_grid.nc")

aqhi = ds["aqhi"]

aqhi.rio.write_crs("EPSG:3978", inplace=True)

aqhi.rio.to_raster("static/aqhi_grid.tif")