# 📊 MACRO EVENT IMPACT TRACKER

> **Professional-grade macroeconomic event analyzer with real-time data, advanced financial metrics, and interactive visualizations**

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## ✨ Overview

A Python Tkinter application that analyzes macroeconomic events' impact across asset classes using FRED and Yahoo Finance APIs. Track how CPI, NFP, FOMC, and other macro releases move markets in real-time with advanced analytics and Bloomberg-style terminal interface.

## 🎯 Key Features

### Data & Analytics
- **Multi-Asset Coverage**: Equities, Fixed Income, FX, Commodities, Volatility (VIX), Crypto
- **FRED Integration**: CPI, NFP, PMI, Retail Sales, GDP, PPI, Consumer Sentiment, and more
- **Advanced Metrics**: Sharpe, Sortino ratios, Beta calculation, max drawdown, impact scores
- **Parallel Fetching**: ThreadPoolExecutor for 8x faster data loading
- **Smart Caching**: In-session cache for instant repeated queries

### UI & Visualization
- **Bloomberg-Style Terminal**: Dark theme with professional color scheme
- **4-Tab Interface**: Overview, Charts, Detailed Metrics, Raw Log
- **2×2 Dashboard Charts**: Price changes, volatility spikes, returns, correlation heatmap
- **Real-time Updates**: Live status bar with progress tracking
- **Sortable Tables**: Interactive treeviews with color-coded returns

### Technical Highlights
- Clean multi-file architecture (config, data_fetch, metrics, UI modules)
- Timezone-aware processing (US/Eastern for market hours)
- Robust error handling and validation
- Customizable event windows (15/30/60/120 minutes)

## 📁 Project Structure

```
MACRO-EVENT-IMPACT-TRACKER/
├── config.py              # Central configuration (API keys, assets, theme)
├── data_fetch.py          # FRED + yfinance with caching & parallel execution
├── metrics.py             # Analytics engine (Sharpe, Sortino, beta, impact scores)
├── macro_tracker.py       # Original monolithic app (legacy)
├── ui/
│   ├── __init__.py        # UI package initializer
│   ├── app.py             # Main Tkinter application class
│   ├── overview_tab.py    # Macro summary + market snapshot
│   ├── charts_tab.py      # 2×2 dashboard with PNG export
│   ├── metrics_tab.py     # Detailed metrics table with filters
│   └── log_tab.py         # Raw log console output
├── main.py                # Entry point (CLI + GUI modes)
├── requirements.txt       # Project dependencies
└── README.md              # This file
```

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/abhang-a1/MACRO-EVENT-IMPACT-TRACKER-.git
cd MACRO-EVENT-IMPACT-TRACKER-

# Install dependencies
pip install -r requirements.txt
```

### Configuration

1. **FRED API Key** (Optional): Set environment variable
   ```bash
   export FRED_API_KEY="your_key_here"  # Linux/Mac
   set FRED_API_KEY=your_key_here       # Windows
   ```
   Or use the default key in `config.py`

### Run the Application

```bash
# Legacy monolithic version
python macro_tracker.py

# Modular version (GUI)
python main.py

# CLI mode (coming soon)
python main.py --cli --event "CPI (Inflation)" --date 2026-05-20 --window 60
```

## 📊 Supported Macroeconomic Events

| Event | FRED Series | Direction |
|-------|-------------|----------|
| CPI (Inflation) | CPALTT01USM657N | Hawkish ↑ |
| Core CPI | CPILFESL | Hawkish ↑ |
| NFP (Jobs) | PAYEMS | Hawkish ↑ |
| Unemployment Rate | UNRATE | Dovish ↑ |
| FOMC Rate Decision | FEDFUNDS | Hawkish ↑ |
| PMI (Manufacturing) | NAPM | Bullish ↑ |
| Retail Sales | RSXFS | Bullish ↑ |
| GDP Growth | A191RL1Q225SBEA | Bullish ↑ |
| PPI (Producer Prices) | PPIACO | Hawkish ↑ |
| Consumer Sentiment | UMCSENT | Bullish ↑ |

## 💡 Usage Example

### Analyzing CPI Release Impact

1. Launch the app: `python macro_tracker.py`
2. Select **"CPI (Inflation)"** from dropdown
3. Pick event date (must be within last 7 days for intraday data)
4. Choose window: **60 min** (1 hour post-release)
5. Click **"▶ RUN"**

**Results:**
- Overview tab shows: Actual vs Consensus, Surprise magnitude
- Asset snapshot: Returns, volatility, impact scores across 20+ instruments
- Charts tab: 2×2 dashboard with correlations and vol spikes
- Metrics tab: Sharpe, Sortino, beta vs S&P 500

## 📈 Metrics Explained

- **Impact Score**: 0-100 blend of |return|, volatility, and |max drawdown| (z-scored)
- **Sharpe Ratio**: Risk-adjusted return (annualized)
- **Sortino Ratio**: Like Sharpe but only penalizes downside volatility
- **Beta**: Sensitivity to S&P 500 movements
- **Global Event Impact Index**: Mean of top-5 asset impact scores

## 🛠️ Tech Stack

- **Python 3.8+**
- **Tkinter** - Native GUI framework
- **pandas** - Data manipulation
- **matplotlib** - Charting
- **yfinance** - Market data (1-min intraday)
- **requests** - FRED API integration
- **pytz** - Timezone handling
- **seaborn** - Color palettes
- **tkcalendar** - Date picker widget

## ⚙️ Configuration Options

Edit `config.py` to customize:

```python
# API Keys
FRED_API_KEY = os.getenv("FRED_API_KEY", "default_key")

# Data Limits
MAX_DAYS_BACK = 7  # yfinance 1-min data limit
DEFAULT_WINDOW_MIN = 60

# Theme Colors
THEME = {
    "bg": "#000000",
    "primary": "#F4F725",  # Yellow
    "success": "#00FF6A",  # Green
    "danger": "#FF4D4D",   # Red
    ...
}

# Asset Universe
ASSET_SYMBOLS = {
    "S&P 500": "^GSPC",
    "Bitcoin": "BTC-USD",
    ...
}
```

## 📋 Roadmap

- [x] Clean multi-file architecture
- [x] Advanced analytics (Sharpe, Sortino, beta)
- [x] Impact scoring system
- [x] Parallel data fetching
- [ ] CLI mode with argparse
- [ ] PNG dashboard export
- [ ] CSV metrics export
- [ ] Category filters
- [ ] Historical backtesting
- [ ] Multi-event comparison
- [ ] Scheduled event calendar

## 🐛 Known Limitations

- **7-day window**: Yahoo Finance provides 1-minute data for last 7 days only
- **Market hours**: Equity/bond data limited to trading hours (9:30 AM - 4:00 PM ET)
- **Weekend data**: No data for Sat/Sun (except crypto/FX)
- **FRED frequency**: Most macro series are monthly/quarterly

## 📄 License

MIT License - see [LICENSE](LICENSE) for details

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📞 Contact

**Developer**: Abhang A1  
**GitHub**: [@abhang-a1](https://github.com/abhang-a1)  

---

⭐ **Star this repo** if you find it useful!
