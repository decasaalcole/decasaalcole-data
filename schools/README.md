# School Data Scraper

A Python scraper for collecting school information from the Valencian Community's education portal (xacen-backend API).

## Features

- Fetches school data from the official REST API (no HTML scraping)
- JWT authentication handled automatically (public credentials)
- Paginated school listing with detail enrichment
- Concurrent detail fetching with configurable thread count
- Configurable output formats (CSV/JSON)
- Docker support for easy deployment
- Ability to scrape specific schools by their codes

## Project Structure

```
.
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── pyproject.toml
├── .env
├── data/           # Output directory for scraped data
├── logs/           # Log files directory
└── src/
    ├── main.py
    └── scraper.py
```

## Prerequisites

- Docker and Docker Compose installed
- Python 3.11+ (if running without Docker)

## Environment Variables

Create a `.env` file with the following variables:

```env
API_BASE_URL=https://xacen-backend.gva.es/xacen-backend/api/v1/
REQUEST_TIMEOUT=30
MAX_RETRIES=3
REQUEST_DELAY=0
IDIOMA=es
OUTPUT_DIR=./data
OUTPUT_FORMAT=json   # csv or json
LOG_LEVEL=INFO
LOG_FILE=./logs/scraper.log
SCHOOL_SUBSET=0      # 0 for all
SCHOOL_THREADS=15
```

## Usage with Docker

1. **Build the Docker image**:
   ```bash
   docker-compose build
   ```

2. **Run the scraper** (scrapes all schools):
   ```bash
   docker-compose up scraper
   ```

3. **Scrape specific schools**:
   ```bash
   docker-compose run scraper python src/main.py --school-codes 03012591 03012592
   ```

4. **View the output**:
   The scraped data will be saved in the `data` directory in your chosen format (CSV or JSON).

## Usage without Docker

```bash
uv sync
uv run src/main.py
```

## Command Line Arguments

- `--school-codes`: List of specific school codes to scrape (e.g., `03012591 03012592`)
- `--subset N`: Only scrape the first N schools (0 = all)
- `--threads N`: Number of concurrent threads for detail fetching

Examples:

```bash
# Scrape all schools
python src/main.py

# Scrape specific schools
python src/main.py --school-codes 03012591 03012592

# Scrape first 10 schools with 4 threads
python src/main.py --subset 10 --threads 4
```

## How It Works

### API Endpoints

The scraper uses the `xacen-backend` REST API:

1. **Authentication**: `GET /user` with Basic auth returns a JWT token (10 min TTL, auto-refreshed)
2. **School list**: `GET /guiadecentros/listaCentrosAulariosLibre` — paginated (100 per page)
3. **School detail**: Multiple `GET` endpoints per school code:
   - `/centro/datosGenerales` — name, address, coordinates, contact, etc.
   - `/centro/nivelesAutorizados` — authorized education levels
   - `/centro/jornadas` — schedule
   - `/centro/informacionAdicional` — additional information
   - `/centro/programaLinguistico` — linguistic programs
   - `/simbolos/servicios` — facilities and services

### Scraping Process

1. Authenticate and obtain a JWT token
2. Fetch all schools via the paginated list endpoint
3. For each school, fetch detail data from multiple endpoints
4. Merge and save the enriched data

## Output Format

```json
{
  "codCentro": "03000047",
  "denomCentro": "CEIP LA RAMBLA",
  "regimen": "Público",
  "direccion": "Avenida DE ALCOY, S/N",
  "cp": "03698",
  "localidad": "AGOST",
  "telefono": "966908135",
  "denomGenerica": "COL·LEGI D'EDUCACIÓ INFANTIL I PRIMÀRIA LA RAMBLA",
  "titular": "GENERALITAT VALENCIANA",
  "cif": "Q5355128I",
  "latitud": "38.438389",
  "longitud": "-0.635608",
  "denomComarca": "L'ALACANTÍ",
  "email": "03000047@edu.gva.es",
  "web": "https://portal.edu.gva.es/03000047",
  "niveles": [
    {
      "denomNivel": "EDUCACIÓN PRIMARIA",
      "unidadesAutorizadas": 8,
      "puestosAutorizados": 200,
      "unidadesActivas": 11,
      "puestosActivos": 275
    }
  ],
  "horario": ["Jornada lectiva de 9 a 14 h."],
  "servicios": [
    { "denominacion": "Biblioteca", "categoria": "Instalaciones" }
  ],
  "programaLinguistico": [
    { "programa": "Programa de educación plurilingüe", "porcVal": 54, "porcCas": 30, "porcIng": 17 }
  ]
}
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
