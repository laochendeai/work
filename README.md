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
    /home/leo-cy/work/work/bin/pip install -r requirements.txt
    ```
3.  **Browser Drivers**:
    Ensure Chrome/Chromium is installed for the scraper.

## Usage

### Starting the Server
```bash
/home/leo-cy/work/work/bin/python server.py
```
Access the web interface at: `http://localhost:8080`

### Licensing
The application is hardware-locked. On first startup:
1.  The application now provides a **7-day trial period** on first use for each machine.
2.  During the trial, the web interface opens normally.
3.  After the trial expires, the web interface will show a **Lock Screen**.
4.  Contact the administrator with the **Machine Code** to obtain a license key.
5.  Enter the provided key in the web interface to unlock.

### Trial Persistence
- Trial state is bound to the current machine code.
- The app stores trial state outside the portable folder so deleting and re-copying the release folder on the same machine does not reset the 7-day trial.
- On Windows, the trial state is stored in both `HKCU\Software\BidSystemPortable` and `%ProgramData%\BidSystemPortable\trial.json`.

## Directory Structure
- `server.py`: Main backend entry point.
- `main.py`: Scraper command-line interface.
- `license_utils.py`: Licensing logic.
- `web/`: Frontend assets.
- `scraper/`: Scraping logic and spiders.
- `extractor/`: Data parsing and extraction logic.
- `storage/`: Database interaction layer.

## Support
For technical support or license inquiries, please contact the administrator.
