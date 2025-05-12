import logging

logger = logging.getLogger("download")

# download a dataset into a file using a post request given a param value
def download_dataset(data_dir, id):
    import requests

    url = "https://centrodedescargas.cnig.es/CentroDescargas/descargaDir"
    params = {
        "secDescDirLA": id
    }
    response = requests.post(url, params=params)
    logger.debug(f"Response status code: {response.status_code}")
    if response.status_code == 200:
        # Save the content (a zip file) into a temporary location
        # and then extract it
        import tempfile
        import zipfile
        import os

        # Create a temporary directory
        with tempfile.TemporaryDirectory() as tmpdirname:
            # Save the zip file
            zip_path = os.path.join(tmpdirname, f"cartociudad-{id}.zip")
            logger.debug(f"Saving zip file to {zip_path}")
            with open(zip_path, "wb") as file:
                file.write(response.content)

            # Extract the zip file
            logger.debug(f"Extracting zip file {zip_path}...")
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(tmpdirname)

            # Find the GPKG file in the extracted files and its subdirectories
            logger.debug(f"Searching for GPKG file in {tmpdirname}...")
            gpkg_path = None
            gpkg_filename = None
            for root, _, files in os.walk(tmpdirname):
                for file in files:
                    if file.endswith(".gpkg"):
                        logger.debug(f"Found file: {file}")
                        gpkg_path = os.path.join(root, file)
                        gpkg_filename = file
                        break
                if gpkg_path:
                    break

            if 'gpkg_path' not in locals():
                logger.error("No GPKG file found in the zip archive for dataset {id}.")
                return

            # Move the GPKG file to the data directory
            os.makedirs(data_dir, exist_ok=True)
            os.rename(gpkg_path, os.path.join(data_dir, gpkg_filename))
            logger.info(f"Dataset {id} downloaded and extracted successfully into data/{gpkg_filename}.")
    else:
        logger.error(f"Failed to download dataset {id}.")
