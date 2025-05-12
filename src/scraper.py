import logging
import os
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
import pandas as pd
from pathlib import Path
import json
import time

from multiprocessing import Pool

import requests_cache
from requests_cache.backends.sqlite import SQLiteCache

logger = logging.getLogger(__name__)

# Define a requests cache backend as a SQLite database in the data folder
requests_backend = SQLiteCache('data/school_scraper_cache.sqlite')
# Store the cached session globally to prevent multiprocessing issues
requests_session = requests_cache.CachedSession('SchoolScrapper', backend=requests_backend, allowable_methods=['GET', 'POST'])
requests_session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
})

class SchoolScraper:
    """
    A web scraper for collecting school information from the Valencian Community's education portal.
    
    This class handles:
    - Fetching school data from the education portal
    - Extracting detailed information for each school
    - Processing and structuring the data
    - Saving the results in CSV or JSON format
    
    Attributes:
        use_local (bool): Whether to use local HTML files instead of making HTTP requests
        base_url (str): URL for the main search page
        detail_url_template (str): Template for school detail URLs
        request_timeout (int): Timeout for HTTP requests in seconds
        max_retries (int): Maximum number of retries for failed requests
        output_dir (str): Directory to save output files
        request_delay (float): Delay between requests in seconds
        session (requests.Session): HTTP session for making requests
    """
    
    def __init__(self, use_local: bool = False):
        """
        Initialize the SchoolScraper.
        
        Args:
            use_local (bool): Whether to use local HTML files instead of making HTTP requests
            
        Environment Variables:
            CONSULTABASE_URL: URL for the main search page
            CONSULTA_CENTRO_URL: Base URL for school detail pages
            REQUEST_TIMEOUT: Timeout for HTTP requests
            MAX_RETRIES: Maximum number of retries
            OUTPUT_DIR: Directory for output files
            REQUEST_DELAY: Delay between requests
        """
        self.use_local = use_local
        self.base_url = os.getenv('CONSULTABASE_URL', 'https://ceice.gva.es/abc/i_guiadecentros/es/consulta01.asp')
        base_detail_url = os.getenv('CONSULTA_CENTRO_URL', 'https://ceice.gva.es/abc/i_guiadecentros/es/centro.asp')
        self.detail_url_template = f"{base_detail_url}?codi={{}}"
        self.request_timeout = int(os.getenv('REQUEST_TIMEOUT', '30'))
        self.max_retries = int(os.getenv('MAX_RETRIES', '3'))
        self.output_dir = os.getenv('OUTPUT_DIR', './data')
        self.request_delay = float(os.getenv('REQUEST_DELAY', '1.0'))
    
    def _get_page_content(self) -> str:
        """
        Get the page content either from local file or URL.
        
        In local mode, reads from a local HTML file.
        In normal mode, makes a POST request to the education portal.
        
        Returns:
            str: The HTML content of the page
            
        Raises:
            FileNotFoundError: If local file doesn't exist in local mode
            requests.exceptions.RequestException: If HTTP request fails
            ValueError: If response validation fails
        """
        if self.use_local:
            logger.info("Local mode enabled, using local file")
            local_file = Path('tmp/consulta01.html')
            if not local_file.exists():
                raise FileNotFoundError(f"Local file not found: {local_file}")
            
            # Get encoding from environment variable, default to utf-8
            encoding = os.getenv('ENCODING', 'utf-8')
            logger.info(f"Using encoding: {encoding}")
            
            with open(local_file, 'r', encoding=encoding) as f:
                return f.read()
        else:
            try:
                logger.info(f"Fetching page from {self.base_url}")
                payload = {
                    "opcion": "on",
                    "cpro": "%",
                    "cregime": "%",
                    "ter1": "",
                    "tipo_consulta": "F_DENO_LOCALIDAD(A.COD_PROVINCIA, A.COD_MUNI, A.COD_ECOL, A.COD_ESIN, NULL,1)",
                    "tipo_consulta2": "F_DENO_LOCALIDAD(A.COD_PROVINCIA, A.COD_MUNI, A.COD_ECOL, A.COD_ESIN, NULL,2)",
                    "prov": "%",
                    "reg": "%",
                    "t": "3",
                    "aceptar": "Buscar"
                }
                response = requests_session.post(
                    self.base_url,
                    data=payload,
                    timeout=self.request_timeout,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'Referer': self.base_url
                    }
                )
                
                # Check if the request was successful
                response.raise_for_status()
                
                # Check if we got HTML content
                if not response.headers.get('content-type', '').startswith('text/html'):
                    raise ValueError(f"Expected HTML content, got {response.headers.get('content-type')}")
                
                # Check if the content is not empty
                if not response.text.strip():
                    raise ValueError("Received empty response")
                
                # Write the content in the tmp folder
                os.makedirs('tmp', exist_ok=True)
                with open('tmp/consulta01.html', 'w', encoding='utf-8') as f:
                    f.write(response.text)
                    logger.debug("Saved page content to tmp/consulta01.html")

                
                # Check if the content contains the expected table structure
                soup = BeautifulSoup(response.text, 'lxml')
                if not soup.find('table'):
                    raise ValueError("Page content does not contain expected table structure")
                
                logger.info("Successfully fetched and validated page content")
                return response.text
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to fetch page: {str(e)}")
                raise
            except ValueError as e:
                logger.error(f"Page content validation failed: {str(e)}")
                raise
    
    def _process_school(self, school):
        """
        Internal method to process each school in a multiprocessing pool.

        Args:
            school (Dict): Dictionary containing basic school information
        Returns:
            Dict: A new dictionary containing enriched school information

        """
        if 'código' in school:
            try:
                logger.debug(f"Fetching details for school: {school.get('centro', 'Unknown')}, code: {school['código']}")
                school_details = self._extract_school_data(school['código'])
                result = school.copy()
                result.update(school_details)

                # Remove duplicated keys
                if 'código' in result:
                    result['codigo'] = result.pop('código')
                if 'rég.' in result:
                    result['reg'] = result.pop('rég.')
                if 'dirección' in result:
                    result['dir'] = result.pop('dirección')
                if 'teléfono' in result:
                    result['tel'] = result.pop('teléfono')
                if 'localidad' in result:
                    localidad = result.pop('localidad')
                    # if a number is found in localidad, extract it
                    if any(char.isdigit() for char in localidad):
                        muni_parts = localidad.split(' - ')
                        if len(muni_parts) < 2:
                            logger.warning(f"Unexpected format for localidad: {localidad}")
                            result['muni'] = localidad
                            result['cp'] = ''
                        else:
                            result['cp'] = muni_parts[0]
                            result['muni'] = muni_parts[1]
                    else:
                        result['muni'] = localidad

                # Rename some keys
                if 'centro' in result:
                    result['denGenEs'] = result.pop('centro')
                if 'nombre' in result:
                    result['deno'] = result.pop('nombre')
                
                # Some postprocessing
                if 'deno' in result:
                    result['deno'] = result['deno'].replace('  ', ' ').strip()
                    result['deno'] = result['deno'].replace('\n', ' ').strip()
                
                # Sort the keys in the result dictionary based on the keys
                sorted_result = {k: result[k] for k in sorted(result.keys())}    

                # Add delay between requests if not in local mode
                if not self.use_local:
                    time.sleep(self.request_delay)
                
                return sorted_result 
                    
            except Exception as e:
                logger.error(f"Failed to fetch details for school {school.get('código')} - {school.get('centro', 'Unknown')}: {str(e)}")
                # Print also the stack trace
                logger.exception(e)
                return None

    def scrape_schools(self, subset: int = 0, threads: int = 1) -> List[Dict]:
        """
        Main method to scrape school data.
        
        This method:
        1. Fetches the initial page with the list of schools
        2. Extracts basic information for each school
        3. Fetches and extracts detailed information for each school
        4. Saves the collected data

        Args:
            subset (int): Number of schools to scrape (0 for all schools)
            threads (int): Number of threads to use for scraping (default: 1)
        
        Returns:
            List[Dict]: List of dictionaries containing school data
            
        Raises:
            Exception: If any error occurs during the scraping process
        """
        try:
            # Get page content
            logger.info("Fetching page content...")
            html_content = self._get_page_content()
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Find the outer table
            outer_table = soup.find('table')
            if not outer_table:
                raise ValueError("No outer table found on the page")
            
            # Find all inner tables
            inner_tables = outer_table.find_all('table')
            if not inner_tables:
                raise ValueError("No inner tables found")
            
            # Get the first inner table (the one we want)
            target_table = inner_tables[0]
            logger.info("Found target table for school data")
            
            # Extract data from the table
            schools_data = self._extract_table_data(target_table)
            
            # Extract detailed information for each school using a multiprocessing pool
            with Pool(processes=threads) as pool:
                # Retrieving only a subset of schools if specified
                if subset > 0:
                    schools_data = schools_data[:subset]
                    logger.warning(f"⚠  Only processingc {len(schools_data)} schools")
                
                # Use map to process each school in parallel
                logger.info(f"Processing {len(schools_data)} schools in parallel with {threads} threads")
                results = pool.map(self._process_school, schools_data)

            
            # Save the data
            self._save_data([r for r in results if r is not None])
            
            return schools_data
            
        except Exception as e:
            logger.error(f"Error during scraping: {str(e)}")
            raise
    
    def _extract_table_data(self, table) -> List[Dict]:
        """
        Extract data from the schools table.
        
        Args:
            table: BeautifulSoup table object containing school data
            
        Returns:
            List[Dict]: List of dictionaries containing basic school information
            
        Raises:
            ValueError: If the table structure is invalid
        """
        schools_data = []
        
        # Get all rows including header
        rows = table.find_all('tr')
        if not rows:
            raise ValueError("No rows found in the table")
        
        # Extract header row and clean field names
        header_cells = rows[0].find_all('td')
        field_names = [cell.text.strip().lower().replace(' ', '_') for cell in header_cells]
        logger.info(f"Extracted field names: {field_names}")
        
        # Process data rows (skip header)
        for row in rows[1:]:
            try:
                # Extract cells
                cells = row.find_all('td')
                if len(cells) != len(field_names):
                    logger.warning(f"Row has {len(cells)} cells, expected {len(field_names)}")
                    continue
                
                # Create school data dictionary using field names
                school_data = {}
                for field_name, cell in zip(field_names, cells):
                    school_data[field_name] = cell.text.strip()
                
                schools_data.append(school_data)
                #logger.debug(f"Extracted data for school: {school_data.get('centro', 'Unknown')}")
                
            except Exception as e:
                logger.error(f"Error extracting data from row: {str(e)}")
                continue
        
        logger.info(f"Successfully extracted data for {len(schools_data)} schools")
        return schools_data
    
    def _save_data(self, data: List[Dict]) -> None:
        """
        Save the scraped data to a file.
        
        Args:
            data (List[Dict]): List of dictionaries containing school data
            
        Environment Variables:
            OUTPUT_FORMAT: Format to save the data (CSV or JSON)
            ENCODING: File encoding to use
            
        Raises:
            ValueError: If the output format is not supported
            OSError: If file writing fails
        """
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Get output format from environment variable, default to CSV
        output_format = os.getenv('OUTPUT_FORMAT', 'CSV').upper()
        # Get encoding from environment variable, default to utf-8
        encoding = os.getenv('ENCODING', 'utf-8')
        
        logger.info(f"Using output format: {output_format}")
        logger.info(f"Using encoding: {encoding}")
        
        if output_format == 'CSV':
            output_file = os.path.join(self.output_dir, 'schools_list.csv')
            # Convert to DataFrame and save
            df = pd.DataFrame(data)
            df.to_csv(output_file, index=False, encoding=encoding)
            logger.info(f"Saved data to {output_file} in CSV format with {encoding} encoding")
        elif output_format == 'JSON':
            output_file = os.path.join(self.output_dir, 'schools_list.json')
            
            # Clean and optimize data
            optimized_data = []
            for school in data:
                # Remove empty values and detail_url
                cleaned_school = {
                    k: v for k, v in school.items() 
                    if v and k != 'detail_url' and v != [] and v != {}
                }
                
                # Optimize arrays removing empty properties
                if 'inst' in cleaned_school:
                    cleaned_school['inst'] = [i for i in cleaned_school['inst'] if i]
                if 'horario' in cleaned_school:
                    cleaned_school['horario'] = [h for h in cleaned_school['horario'] if h]
                if 'info' in cleaned_school:
                    cleaned_school['info'] = [i for i in cleaned_school['info'] if i]
                
                # Optimize nested structures
                if 'niveles' in cleaned_school:
                    cleaned_school['niveles'] = [
                        {k: v for k, v in level.items() if v}
                        for level in cleaned_school['niveles']
                    ]
                
                optimized_data.append(cleaned_school)
            
            # Save as JSON with minimal whitespace
            with open(output_file, 'w', encoding=encoding) as f:
                indent = None if len(optimized_data) > 100 else 4
                json.dump(optimized_data, f, ensure_ascii=False, separators=(',', ':'), indent=indent)
            logger.info(f"Saved optimized data to {output_file} in JSON format with {encoding} encoding")
        else:
            raise ValueError(f"Unsupported output format: {output_format}. Supported formats are CSV and JSON")

    def _extract_school_data(self, school_code: str) -> Dict:
        """
        Extract detailed data from a school's detail page.
        
        Args:
            school_code (str): The code of the school to fetch details for
            
        Returns:
            Dict: Dictionary containing detailed school information
            
        Raises:
            FileNotFoundError: If local file doesn't exist in local mode
            requests.exceptions.RequestException: If HTTP request fails
            Exception: If any error occurs during data extraction
        """
        try:
            if self.use_local:
                logger.info("Local mode enabled, using local file")

                # Check if the local file exists
                local_file = Path(f'tmp/centro_{school_code}.html')
                # If the file doesn't exist, use a default file for testing
                if not local_file.exists():
                    local_file = Path('tmp/centro_03012591.html')
                
                # Raise an error if the file doesn't exist
                if not local_file.exists():
                    raise FileNotFoundError(f"Local file not found: {local_file}")
                
                # Get encoding from environment variable, default to utf-8
                encoding = os.getenv('ENCODING', 'utf-8')
                logger.info(f"Using encoding: {encoding}")
                
                with open(local_file, 'r', encoding=encoding) as f:
                    html_content = f.read()
            else:
                # Construct the detail URL
                detail_url = self.detail_url_template.format(school_code)
                
                # Fetch the detail page
                response = requests_session.get(
                    detail_url,
                    timeout=self.request_timeout,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1'
                    }
                )
                response.raise_for_status()
                html_content = response.text

                # Write the content in the tmp folder
                os.makedirs('tmp', exist_ok=True)
                with open(f'tmp/centro_{school_code}.html', 'w', encoding='utf-8') as f:
                    f.write(html_content)
                logger.debug(f"Saved detail page to tmp/centro_{school_code}.html")
            
            # Parse the detail page
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Initialize the details dictionary
            details = {}
            
            try:
                # Extract basic information
                name_cell = soup.find('td', bgcolor="#EBEBEB", colspan="2")
                if name_cell:
                    details['nombre'] = name_cell.find('span', class_="Estilo1").text.strip()
                
                # Extract code and type
                cells = soup.find_all('td', bgcolor="#EBEBEB")
                for cell in cells:
                    text = cell.text.strip()
                    if 'Código:' in text:
                        details['código'] = text.replace('Código:', '').strip()
                    elif 'Régimen:' in text:
                        details['rég.'] = text.replace('Régimen:', '').strip().replace('\xa0', '')
                    elif 'CIF:' in text:
                        details['cif'] = text.replace('CIF:', '').strip()
                
                # Extract contact information
                # Find the third table inside a named div
                outer_div = soup.find_all('div', {'class': 'nivelCentro'})
                if outer_div:
                    # Find the tables inside the div
                    tables = outer_div[0].find_all('table')
                    if tables and len(tables) >= 3:
                        # Get the third table where the contact details are
                        table = tables[2]
                        # Get the rows and iterate them to find cells with desired labels
                        rows = table.find_all('tr')
                        for row_index, row in enumerate(rows):
                            # Find all cells in the row
                            cells = row.find_all('td')

                            for index, cell in enumerate(cells):
                                label = cell.text.strip().lower()
                                if 'dirección:' in label:
                                    details['dirección'] = cells[index + 1].text.strip()
                                elif 'teléfono:' in label:
                                    details['tel'] = cells[index + 1].text.strip()
                                elif 'e-correo:' in label:
                                    details['email'] = cells[index + 1].text.strip()
                                elif 'localidad:' in label:
                                    details['muni'] = cells[index + 1].text.strip()
                                elif 'comarca:' in label:
                                    details['com'] = cells[index + 1].text.strip()
                                elif 'titular:' in label:
                                    details['titular'] = cells[index + 1].text.strip()
                                elif 'lat:' in label:
                                    lat_row = rows[row_index + 1]
                                    # Get the cell at the same index in the next row
                                    lat_cell = lat_row.find_all('td')[index]
                                    details['lat'] = lat_cell.text.strip().replace(',', '.')
                                elif 'long:' in label:
                                    long_row = rows[row_index + 1]
                                    # Get the cell at the same index in the next row
                                    long_cell = long_row.find_all('td')[index]
                                    details['long'] = long_cell.text.strip().replace(',', '.')
                else:
                    logger.warning("No contact details div found")
                
                # Extract coordinates


                # Extract facilities
                facilities = []
                facility_icons = soup.find_all('img', title=True)
                for icon in facility_icons:
                    if icon.get('title'):
                        facilities.append(icon['title'])
                if facilities:
                    details['inst'] = facilities
                
                # Extract authorized levels
                levels = []
                levels_tables = soup.find_all('table', {'class': 'fondos'})
                if levels_tables:
                    for table in levels_tables:
                        ths_table = table.find_all('th')
                        # Look for the table with NIVELES EDUCATIVOS header
                        if any(th.text.strip().lower() == 'nivel educativo' for th in ths_table):
                            rows = table.find_all('tr')[1:]  # Skip header
                            for row in rows:
                                cells = row.find_all('td')
                                if len(cells) >= 5:
                                    level_info = {
                                        'nivel': cells[0].text.strip(),
                                        'uni_auto': cells[1].text.strip(),
                                        'pues_auto': cells[2].text.strip(),
                                        'uni_act': cells[3].text.strip(),
                                        'pues_act': cells[4].text.strip()
                                    }
                                    levels.append(level_info)
                                elif len(cells) >= 3:
                                    level_info = {
                                        'nivel': cells[0].text.strip(),
                                        'uni_auto': cells[1].text.strip(),
                                        'pues_auto': cells[2].text.strip(),
                                        'uni_act': '',
                                        'pues_act': ''
                                    }
                                    levels.append(level_info)
                                elif len(cells) >= 2:
                                    level_info = {
                                        'nivel': cells[0].text.strip(),
                                        'uni_auto': cells[1].text.strip(),
                                        'pues_auto': '',
                                        'uni_act': '',
                                        'pues_act': ''
                                    }
                                    levels.append(level_info)
                            break  # Exit the loop once we find and process the correct table
                if levels:
                    details['niveles'] = levels
                
                # Extract schedule
                schedule_section = soup.find('div', id="secc152")
                if schedule_section:
                    schedule_items = schedule_section.find_all('li')
                    if schedule_items:
                        # Filter to only keep items containing schedule-related keywords
                        schedule_keywords = {
                            "jornada",
                            "tarde",
                            "mañana",
                            "horario",
                            "entrada",
                            "salida",
                            "hora",
                            "h."
                        }
                        schedule = [
                            item.text.strip() 
                            for item in schedule_items 
                            if any(keyword in item.text.strip().lower() for keyword in schedule_keywords)
                        ]
                        if schedule:
                            details['horario'] = schedule
                
                # Extract additional information
                info_section = soup.find('div', id="secc16")
                if info_section:
                    info_items = info_section.find_all('td')
                    if info_items:
                        details['info'] = [item.text.strip() for item in info_items if item.text.strip()]
                
            except Exception as e:
                logger.warning(f"Error extracting specific field: {str(e)}")
                logger.exception(e)
                # Continue with what we have extracted so far
            
            logger.debug(f"Extracted {len(details)} details from school page")
            return details
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch school details: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error extracting school details: {str(e)}")
            raise 

    def scrape_specific_schools(self, school_codes: List[str]) -> List[Dict]:
        """
        Scrape data for specific schools by their codes.
        
        Args:
            school_codes (List[str]): List of school codes to scrape
            
        Returns:
            List[Dict]: List of dictionaries containing school data
            
        Raises:
            Exception: If any error occurs during the scraping process
        """
        try:
            schools_data = []
            
            for school_code in school_codes:
                try:
                    logger.info(f"Fetching details for school code: {school_code}")
                    school_details = self._extract_school_data(school_code)
                    
                    # Add the school code to the details
                    school_details['código'] = school_code

                    # Enrich the details
                    school_details = self._process_school(school_details)
                    
                    schools_data.append(school_details)
                    
                    # Add delay between requests if not in local mode
                    if not self.use_local:
                        time.sleep(self.request_delay)
                        
                except Exception as e:
                    logger.error(f"Failed to fetch details for school code {school_code}: {str(e)}")
                    continue
            
            # Save the data
            self._save_data(schools_data)
            
            return schools_data
            
        except Exception as e:
            logger.error(f"Error during specific schools scraping: {str(e)}")
            raise 
