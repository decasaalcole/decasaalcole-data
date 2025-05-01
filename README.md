# School Data Scraper

A Python-based web scraper for collecting school information from the Valencian Community's education portal.

## Features

- Scrapes comprehensive school data including basic information, contact details, facilities, and schedules
- Supports both local file mode and live web scraping
- Configurable output formats (CSV/JSON)
- Rate limiting to prevent server overload
- Graceful error handling for missing or malformed data
- Docker support for easy deployment

## Project Structure

```
.
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env
├── data/           # Output directory for scraped data
├── logs/           # Log files directory
├── tmp/            # Directory for local HTML files
└── src/
    ├── main.py
    └── scraper.py
```

## Prerequisites

- Docker and Docker Compose installed
- Python 3.9+ (if running without Docker)
- Required Python packages (if running without Docker):
  - requests
  - beautifulsoup4
  - pandas

## Environment Variables

Create a `.env` file with the following variables:

```env
CONSULTABASE_URL=https://ceice.gva.es/abc/i_guiadecentros/es/consulta01.asp
CONSULTA_CENTRO_URL=https://ceice.gva.es/abc/i_guiadecentros/es/centro.asp
REQUEST_TIMEOUT=30
MAX_RETRIES=3
OUTPUT_DIR=./data
OUTPUT_FORMAT=CSV  # or JSON
ENCODING=utf-8
REQUEST_DELAY=1.0  # Delay between requests in seconds
```

## Usage with Docker

1. **Build the Docker image**:
   ```bash
   docker-compose build
   ```

2. **Run the scraper in normal mode**:
   ```bash
   docker-compose up scraper
   ```

3. **Run in local mode** (using local HTML files, for dev purposes):
   ```bash
   Add 
   
   LOCAL_MODE=1

   to the .env file and then
   
   docker-compose up scraper
   ```

4. **View the output**:
   The scraped data will be saved in the `data` directory in your chosen format (CSV or JSON).

## How It Works

### Scraping Process

1. **Initial Data Collection**:
   - The scraper first makes a POST request to the main search page
   - It submits a form with parameters to get all schools
   - The response contains a list of schools with basic information

2. **Detail Extraction**:
   - For each school, the scraper makes a GET request to its detail page
   - It extracts comprehensive information including:
     - Basic information (name, code, type)
     - Contact details (address, phone, email)
     - Facilities (from icon titles)
     - Authorized levels (with detailed breakdown)
     - Schedule information (filtered to exclude headers)
     - Additional information
     - Adscriptions

3. **Data Processing**:
   - The scraper handles missing fields gracefully
   - It filters out header text from schedule information
   - It structures complex data (like levels and adscriptions) into nested objects
   - Rate limiting is implemented to prevent server overload

4. **Output Generation**:
   - Data is saved in either CSV or JSON format
   - The output directory and format are configurable
   - File encoding is customizable

### Error Handling

- The scraper implements comprehensive error handling:
  - Network errors are caught and logged
  - Missing fields are handled gracefully
  - Invalid HTML structures are detected
  - Rate limiting prevents server overload
  - Each school's detail extraction is independent, so one failure doesn't affect others

### Local Mode

- The scraper can run in local mode using pre-downloaded HTML files
- This is useful for testing and development
- Files should be placed in the `tmp` directory:
  - `tmp/consulta01.html` for the main list
  - `tmp/centro_03012591.html` for school details

## Output Format

The scraper generates data in the following structure:

```json
{
  "nombre": "School Name",
  "codigo": "School Code",
  "regimen": "School Type",
  "direccion": "Full Address",
  "telefono": "Phone Number",
  "email": "Email Address",
  "localidad": "City",
  "comarca": "Region",
  "titular": "Owner",
  "latitud": "Latitude",
  "longitud": "Longitude",
  "instalaciones": ["Facility 1", "Facility 2"],
  "niveles_autorizados": [
    {
      "nivel": "Level Name",
      "unidades_autorizadas": "Authorized Units",
      "puestos_autorizados": "Authorized Positions",
      "unidades_activas": "Active Units",
      "puestos_activos": "Active Positions"
    }
  ],
  "horario": [
    "Schedule Item 1",
    "Schedule Item 2"
  ],
  "informacion_adicional": ["Additional Info 1", "Additional Info 2"],
  "adscripciones": [
    {
      "tipo": "Adscription Type",
      "centro": "Adscribed Center"
    }
  ]
}
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
