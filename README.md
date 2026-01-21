# Market PE*PB Analyzer

A Flask web application for analyzing NSE (National Stock Exchange of India) indices using PE*PB (Price-to-Earnings multiplied by Price-to-Book) ratios. This tool provides data-driven insights and buy/sell/hold recommendations based on historical valuation metrics.

## Features

- Real-time analysis of major NSE indices:
  - NIFTY 50
  - NIFTY NEXT 50
  - NIFTY BANK
  - NIFTY FIN SERVICE
  - NIFTY MID SELECT

- Comprehensive valuation analysis with moving averages across multiple time periods (20 to 5000 days)
- Automated buy/sell/hold recommendations based on historical PE*PB ratios
- Percentage deviation tracking from moving averages
- Historical data storage and analysis
- Clean web interface for viewing analysis reports

## Tech Stack

- **Backend**: Flask 3.1.1
- **Data Processing**: Pandas 2.3.1
- **NSE Data**: nsepython 2.97, nsetools 2.0.1
- **Production Server**: Gunicorn 23.0.0

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/marketpepb.git
cd marketpepb
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Running Locally

1. Update historical data:
```bash
python core.py
```

2. Start the Flask application:
```bash
python app.py
```

3. Open your browser and navigate to `http://localhost:5000`

### Production Deployment

The application is configured for deployment on Render. The `render.yaml` file contains the deployment configuration.

## Project Structure

```
marketpepb/
├── app.py                  # Flask application entry point
├── core.py                 # Core analysis logic and data processing
├── update.py               # Utility for updating index data
├── update_data.py          # Additional data update utilities
├── requirements.txt        # Python dependencies
├── render.yaml            # Render deployment configuration
├── data/                  # Historical data storage
│   ├── df_*.csv          # Current data files
│   └── *_Historical.csv  # Historical baseline data
└── templates/
    └── index.html         # Web interface template
```

## How It Works

1. **Data Collection**: Fetches historical PE, PB, and dividend data for NSE indices using the nsepython library
2. **Analysis**: Calculates PE*PB ratios and computes moving averages over various time periods
3. **Recommendations**: Compares current valuations against historical averages to generate buy/sell/hold signals:
   - 🟢 Strong Buy: Current PE*PB is >5% below all tracked averages
   - 🟩 Buy: Current PE*PB is below all tracked averages
   - 🔴 Overvalued: Current PE*PB is above all tracked averages
   - 🟡 Hold/Neutral: Mixed signals or insufficient data

## Data Periods Analyzed

- 20, 40, 60 days (short-term trends with percentage changes)
- 120, 250 days (medium-term trends)
- 500, 750, 1000 days (long-term trends)
- 2000, 3000, 4000, 5000 days (very long-term trends)
- All-time average

## License

This project is for educational and informational purposes only. Not financial advice.
