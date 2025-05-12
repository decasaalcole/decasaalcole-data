# Compute postcode centroids

## Install

Three options:

* You can use `pip install -r requirements.txt` into a virtual environment,
* If you have `uv` installed, run `uv sync` to get the the environment and dependencies installed at once
* If you have `docker` and the `compose` plugin, run `docker compose build` to create a local image with the dependencies ready

## Running the script

The `main.py` script does the following:

* Downloads from CartoCiudad the geopackages for the three Valencian provinces into a `data/provinces` folder
* From each geopackage, extracts all the different street number points into CSVs per postcode into the folders `data/postcodes/[alicante|castellon|valencia]`.
* Then for each postcode CSV it computes the centroid following these steps:
  * Compute a `DBSCAN` clustering using the parameters in `dcac_postcodes/config.py`
  * From the clusters that are not considered noise, compute the center and the closest point in the original dataset
  * Return the largest along with the number of points considered and their percentage
  * Store the result in `data/postcodes.csv` 

The script is documented and running `main.py -h` will provide the settings available to change log level, force downloads, etc.

To use the `docker` recipe, just run `docker compose run postcodes` with the same options (so probably start with `--help`).
