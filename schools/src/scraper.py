import logging
import os
import json
import time
from typing import List, Dict, Optional
from base64 import b64encode
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import pandas as pd

logger = logging.getLogger(__name__)

API_BASE_URL = "https://xacen-backend.gva.es/xacen-backend/api/v1/"
API_USER = "XacenFront"
API_PASS = "APzFiPRZotdrIL4bVpBgvA=="

DETAIL_ENDPOINTS = [
    ("niveles", "centro/nivelesAutorizados"),
    ("horario", "centro/jornadas"),
    ("info", "centro/informacionAdicional"),
    ("servicios", "simbolos/servicios"),
    ("programaLinguistico", "centro/programaLinguistico"),
]


class SchoolScraper:
    """
    Scraper for school data from the Valencian Community's education portal.

    Authenticates against the xacen-backend API with a public JWT flow,
    fetches the paginated school list, then enriches each school with
    detail endpoints (levels, schedule, services, etc.).
    """

    def __init__(self):
        self.api_base = os.getenv("API_BASE_URL", API_BASE_URL)
        self.request_timeout = int(os.getenv("REQUEST_TIMEOUT", "30"))
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.output_dir = os.getenv("OUTPUT_DIR", "./data")
        self.request_delay = float(os.getenv("REQUEST_DELAY", "0"))
        self.idioma = os.getenv("IDIOMA", "es")

        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Origin": "https://ceice.gva.es",
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64; rv:132.0) "
                    "Gecko/20100101 Firefox/132.0"
                ),
            }
        )

        self._token: Optional[str] = None
        self._token_expiry: float = 0

    def _authenticate(self):
        credentials = b64encode(f"{API_USER}:{API_PASS}".encode()).decode()
        response = self.session.get(
            f"{self.api_base}user",
            headers={"Authorization": f"Basic {credentials}"},
            timeout=self.request_timeout,
        )
        response.raise_for_status()
        data = response.json()
        self._token = data["token"]
        # Refresh 1 minute before expiry
        self._token_expiry = time.time() + (data["tiempoExpiracion"] - 1) * 60
        self.session.headers["Authorization"] = self._token
        logger.info("Authenticated with xacen-backend API")

    def _ensure_auth(self):
        if self._token is None or time.time() >= self._token_expiry:
            self._authenticate()

    def _api_get(self, endpoint: str, params: Optional[dict] = None):
        """Authenticated GET request with retry and token refresh on 403."""
        self._ensure_auth()
        url = f"{self.api_base}{endpoint}"

        for attempt in range(self.max_retries):
            try:
                resp = self.session.get(
                    url, params=params, timeout=self.request_timeout
                )
                if resp.status_code == 403:
                    logger.debug("Got 403, refreshing token")
                    self._authenticate()
                    resp = self.session.get(
                        url, params=params, timeout=self.request_timeout
                    )
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    raise
                wait = 2 ** attempt
                logger.warning(
                    f"Retry {attempt + 1}/{self.max_retries} for {endpoint}: {e} "
                    f"(waiting {wait}s)"
                )
                time.sleep(wait)

    # ------------------------------------------------------------------
    # School list
    # ------------------------------------------------------------------

    def _fetch_all_schools(self, limit: int = 0) -> List[Dict]:
        all_schools: List[Dict] = []
        page = 0

        while True:
            logger.info(f"Fetching school list page {page}...")
            data = self._api_get(
                "guiadecentros/listaCentrosAulariosLibre",
                params={
                    "idioma": self.idioma,
                    "textoBusqueda": "",
                    "numLlamada": page,
                },
            )

            schools = data.get("listaCentros", [])
            all_schools.extend(schools)

            if data.get("SinDatos", True) or not schools:
                break
            if limit > 0 and len(all_schools) >= limit:
                break
            page += 1

            if self.request_delay > 0:
                time.sleep(self.request_delay)

        logger.info(f"Fetched {len(all_schools)} schools in {page + 1} pages")
        return all_schools

    # ------------------------------------------------------------------
    # School details
    # ------------------------------------------------------------------

    def _fetch_school_details(self, code: str) -> Dict:
        params = {"codCentro": code, "idioma": self.idioma}
        details = self._api_get("centro/datosGenerales", params)

        for key, endpoint in DETAIL_ENDPOINTS:
            try:
                result = self._api_get(endpoint, params)
                if not result:
                    continue

                if key == "servicios":
                    for item in result:
                        item.pop("icono", None)

                details[key] = result
            except Exception as e:
                logger.warning(f"Failed to fetch {key} for {code}: {e}")

        return details

    @staticmethod
    def _transform_to_legacy_format(details: Dict) -> Dict:
        """Map API response fields to the legacy output schema."""
        result: Dict = {}

        result["cif"] = details.get("cif", "")
        result["codigo"] = details.get("codCentro", "")
        result["com"] = details.get("denomComarca", "")
        result["cp"] = details.get("cp", "")
        result["denGenEs"] = details.get("denomCentro", "")
        result["deno"] = details.get("denomGenerica", "")
        result["dir"] = details.get("direccion", "")
        result["email"] = details.get("email", "")

        # horario: already a list of strings from the API
        result["horario"] = details.get("horario", [])

        # info: API returns [{informacion, enlace}] → flatten to list of strings
        raw_info = details.get("info", [])
        if raw_info and isinstance(raw_info[0], dict):
            result["info"] = [
                item["informacion"]
                for item in raw_info
                if item.get("informacion")
            ]
        else:
            result["info"] = raw_info

        # inst: API returns servicios [{denominacion, ...}] → list of strings
        raw_servicios = details.get("servicios", [])
        result["inst"] = [
            item["denominacion"]
            for item in raw_servicios
            if item.get("denominacion")
        ]

        result["lat"] = details.get("latitud", "")
        result["long"] = details.get("longitud", "")
        result["muni"] = details.get("localidad", "")

        # niveles: rename fields to match legacy format
        raw_niveles = details.get("niveles", [])
        result["niveles"] = [
            {
                "nivel": n.get("denomNivel", ""),
                "uni_auto": str(n.get("unidadesAutorizadas", "")),
                "pues_auto": str(n.get("puestosAutorizados", "")),
                "uni_act": str(n.get("unidadesActivas", "")),
                "pues_act": str(n.get("puestosActivos", "")),
            }
            for n in raw_niveles
        ]

        result["reg"] = details.get("regimen", "").upper()
        result["tel"] = details.get("telefono", "")
        result["titular"] = details.get("titular", "")

        return result

    def _process_school(self, school: Dict) -> Optional[Dict]:
        code = school.get("codCentro")
        if not code:
            return None
        try:
            details = self._fetch_school_details(code)
            if self.request_delay > 0:
                time.sleep(self.request_delay)
            return self._transform_to_legacy_format(details)
        except Exception as e:
            logger.error(f"Failed to process school {code}: {e}")
            logger.exception(e)
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scrape_schools(self, subset: int = 0, threads: int = 1) -> List[Dict]:
        schools = self._fetch_all_schools(limit=subset)

        if subset > 0:
            schools = schools[:subset]
            logger.warning(f"⚠  Only processing {len(schools)} schools (subset)")

        logger.info(
            f"Fetching details for {len(schools)} schools "
            f"with {threads} thread(s)..."
        )

        results: List[Dict] = []

        if threads <= 1:
            for i, school in enumerate(schools):
                result = self._process_school(school)
                if result:
                    results.append(result)
                if (i + 1) % 50 == 0:
                    logger.info(f"Progress: {i + 1}/{len(schools)}")
        else:
            with ThreadPoolExecutor(max_workers=threads) as pool:
                futures = {
                    pool.submit(self._process_school, s): s for s in schools
                }
                for i, future in enumerate(as_completed(futures)):
                    result = future.result()
                    if result:
                        results.append(result)
                    if (i + 1) % 50 == 0:
                        logger.info(f"Progress: {i + 1}/{len(schools)}")

        if not results:
            logger.warning("No valid data to save")
            return []

        logger.info(f"Saving data for {len(results)} schools")
        self._save_data(results)
        self._save_metadata(results)
        return results

    def scrape_specific_schools(self, school_codes: List[str]) -> List[Dict]:
        results: List[Dict] = []
        for code in school_codes:
            try:
                logger.info(f"Fetching details for school {code}")
                details = self._fetch_school_details(code)
                results.append(self._transform_to_legacy_format(details))
                if self.request_delay > 0:
                    time.sleep(self.request_delay)
            except Exception as e:
                logger.error(f"Failed to fetch school {code}: {e}")

        if results:
            self._save_data(results)
            self._save_metadata(results)
        return results

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save_data(self, data: List[Dict]) -> None:
        os.makedirs(self.output_dir, exist_ok=True)
        encoding = os.getenv("ENCODING", "utf-8")

        self._save_csv(data, encoding)
        self._save_json(data, encoding)

    def _save_csv(self, data: List[Dict], encoding: str) -> None:
        output_file = os.path.join(self.output_dir, "schools.csv")
        df = pd.DataFrame(data)
        df.to_csv(output_file, index=False, encoding=encoding)
        logger.info(f"Saved {len(data)} schools to {output_file} (CSV)")

    def _save_json(self, data: List[Dict], encoding: str) -> None:
        output_file = os.path.join(self.output_dir, "schools.json")
        cleaned = []
        for school in data:
            entry = {
                k: v
                for k, v in school.items()
                if v and v != [] and v != {}
            }
            if "niveles" in entry:
                entry["niveles"] = [
                    {k: v for k, v in level.items() if v}
                    for level in entry["niveles"]
                ]
            if "horario" in entry:
                entry["horario"] = [h for h in entry["horario"] if h]
            if "info" in entry:
                entry["info"] = [i for i in entry["info"] if i]
            if "inst" in entry:
                entry["inst"] = [i for i in entry["inst"] if i]
            cleaned.append(entry)

        with open(output_file, "w", encoding=encoding) as f:
            indent = None if len(cleaned) > 100 else 4
            json.dump(
                cleaned,
                f,
                ensure_ascii=False,
                separators=(",", ":"),
                indent=indent,
            )
        logger.info(f"Saved {len(data)} schools to {output_file} (JSON)")

    def _save_metadata(self, data: List[Dict]) -> None:
        metadata_file = os.path.join(self.output_dir, "schools.metadata.json")
        metadata = {
            "total_schools": len(data),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=4)
        logger.info(f"Saved metadata to {metadata_file}")
