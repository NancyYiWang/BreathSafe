from flask import Flask, request, jsonify, render_template
import xarray as xr
from geopy.geocoders import Nominatim
import certifi
import numpy as np
import papermill as pm
import os

import ssl
ssl._create_default_https_context = ssl._create_unverified_context

app = Flask(__name__)

aqhi_grid = xr.open_dataset("data/aqhi_grid.nc")["aqhi"]
nomi = Nominatim(user_agent="breathe_safe_app", ssl_context=ssl.create_default_context(cafile=certifi.where()))

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/aqhi", methods=["GET"])
def get_aqhi_from_postal_code():
    postal_code = request.args.get("postal_code", "").strip()
    if not postal_code:
        return jsonify({"error": "Missing postal code"}), 400

    notebook_path = os.path.join(os.getcwd(), "AQHI_DATA.ipynb")
    output_path = os.path.join(os.getcwd(), "AQHI_DATA_output.ipynb")
    try:
        pm.execute_notebook(notebook_path, output_path)
    except Exception as e:
        return jsonify({'error': f'Notebook execution failed: {str(e)}'}), 500
    
    location = nomi.geocode(f"{postal_code}, Canada")
    if location is None:
        return jsonify({"error": "Invalid postal code"}), 404

    lat, lon = location.latitude, location.longitude

    try:
        aqhi_value = aqhi_grid.sel(x=lon, y=lat, method="nearest").item()
        return jsonify({"aqhi": aqhi_value, "lat": lat, "lon": lon})
    except Exception as e:
        return jsonify({"error": f"Failed to read AQHI data: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True)
