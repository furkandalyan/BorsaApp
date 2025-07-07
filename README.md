# BorsaApp

BorsaApp is a modern Django web application for analyzing Turkish stocks with technical indicators and interactive charts.

## Features
- **Stock Analysis:** Enter a stock code and (optionally) a start date to view technical analysis and comments.
- **Autocomplete:** Fast, smart autocomplete for stock codes and company names.
- **Modern UI:** Responsive design with Bootstrap, clean navigation, and user-friendly error messages.
- **Technical Indicators:** Analysis includes RSI, MACD, Bollinger Bands, CCI, ADX, ATR, OBV, ROC, and more.
- **Interactive Charts:** Visualize stock data with Plotly.
- **No User Login:** Designed for private/internal use, no registration or authentication required.

## Setup

### 1. Clone the Repository
```bash
# Clone your project (replace with your repo URL if needed)
git clone <your-repo-url>
cd BorsaApp
```

### 2. Create a Virtual Environment
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

If you don't have a `requirements.txt`, install these main packages:
```bash
pip install django yfinance plotly pandas ta
```

### 4. Run Migrations
```bash
python manage.py migrate
```

### 5. Run the Development Server
```bash
python manage.py runserver
```

Visit [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your browser.

## Usage
- Start typing a stock code or company name in the input box. Autocomplete will suggest matches.
- Select a stock and (optionally) a start date, then click **Analiz Et**.
- View interactive charts and detailed technical analysis comments.
- Click **Yeni analiz** to return to the main page and analyze another stock.

## Project Structure
```
BorsaApp/
  analiz/
    templates/analiz/
      analiz.html
      anasayfa.html
    utils/
      hisseler.json
      update_hisse_listesi.py
    views.py
    urls.py
    ...
  BorsaApp/
    settings.py
    urls.py
  manage.py
  db.sqlite3
```

## Notes
- The app uses `hisseler.json` for stock code/company data and `yfinance` for live stock prices.
- No user authentication or registration is required.
- For best results, use a modern browser (Chrome, Firefox, Edge).

## License
This project is for private/internal use. Add a license if you plan to share or publish it.
