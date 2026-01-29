# Government Procurement Bidding Scraper & Analysis Platform

A comprehensive platform for scraping, analyzing, and managing government procurement announcements and business card information.

## Features
- **Scraping**: Automated scraping of bidding announcements from various government portals.
- **Analysis**: Full-text search and filtering of announcements.
- **Business Card Library**: Extraction and management of contact information (Business Cards) from announcements.
- **Licensing**: Hardware-locked licensing system for secure deployment.
- **Export**: Export data to Excel/Zip formats.

## Architecture
- **Backend**: Python (FastAPI, SQLite, Selenium/Playwright)
- **Frontend**: HTML/JS/CSS (No build step required)
- **Database**: SQLite (`data/gp.db`)

## Installation
1.  **Environment**: Ensure Python 3.9+ is installed.
2.  **Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Browser Drivers**:
    Ensure Chrome/Chromium is installed for the scraper.

## Usage

### starting the Server
```bash
python server.py
```
Access the web interface at: `http://localhost:8000`

### Licensing
The application is hardware-locked. On first startup:
1.  The web interface will show a **Lock Screen**.
2.  Copy the **Machine Code**.
3.  Generate a license key using the included tool:
    ```bash
    python keygen.py "YOUR_MACHINE_CODE"
    ```
4.  Enter the generated key in the web interface to unlock.

## Directory Structure
- `server.py`: Main backend entry point.
- `main.py`: Scraper command-line interface.
- `keygen.py`: License key generation tool.
- `license_utils.py`: Licensing logic.
- `web/`: Frontend assets.
- `scraper/`: Scraping logic and spiders.
- `extractor/`: Data parsing and extraction logic.
- `storage/`: Database interaction layer.

## Support
For technical support or license inquiries, please contact the administrator.
