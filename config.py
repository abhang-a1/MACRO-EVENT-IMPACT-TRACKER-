# config.py - Central configuration for Macro Event Impact Tracker
import os

# ==================== API CONFIG ====================
FRED_API_KEY = os.getenv("FRED_API_KEY", "725661d97c523a1e1f0214b7b51051c6")
DEFAULT_WINDOW_MIN = 60
MAX_DAYS_BACK = 7
DEFAULT_EVENT_TYPE = "CPI (Inflation)"
APP_TITLE = "Macro Event Impact Tracker - Terminal View"
APP_GEOMETRY = "1700x1000"

# ==================== THEME ====================
THEME = {
    "bg": "#000000",
    "panel_bg": "#111111",
    "primary": "#F4F725",
    "secondary": "#00FF6A",
    "accent": "#33A1FF",
    "success": "#00FF6A",
    "danger": "#FF4D4D",
    "warning": "#FFA500",
    "text": "#E0E0E0",
    "font_mono": "Consolas",
    "font_size_sm": 9,
    "font_size_md": 10,
    "font_size_lg": 11,
    "font_size_title": 14,
    "pad_sm": 4,
    "pad_md": 8,
    "pad_lg": 10,
}

# ==================== FRED MACRO SERIES ====================
# Each entry: display_name -> {series_id, direction, description}
FRED_SERIES = {
    "CPI (Inflation)": {
        "id": "CPALTT01USM657N",
        "direction": "higher_is_hawkish",
        "desc": "Consumer Price Index - All Items",
    },
    "Core CPI": {
        "id": "CPILFESL",
        "direction": "higher_is_hawkish",
        "desc": "CPI excluding Food and Energy (MoM)",
    },
    "NFP (Jobs)": {
        "id": "PAYEMS",
        "direction": "higher_is_hawkish",
        "desc": "Nonfarm Payrolls (thousands)",
    },
    "Unemployment Rate": {
        "id": "UNRATE",
        "direction": "higher_is_dovish",
        "desc": "Unemployment Rate (%)",
    },
    "FOMC Rate Decision": {
        "id": "FEDFUNDS",
        "direction": "higher_is_hawkish",
        "desc": "Federal Funds Effective Rate (%)",
    },
    "PMI (Manufacturing)": {
        "id": "NAPM",
        "direction": "higher_is_bullish",
        "desc": "ISM Manufacturing PMI",
    },
    "Retail Sales": {
        "id": "RSXFS",
        "direction": "higher_is_bullish",
        "desc": "Advance Retail Sales (MoM %)",
    },
    "GDP Growth": {
        "id": "A191RL1Q225SBEA",
        "direction": "higher_is_bullish",
        "desc": "Real GDP Growth Rate (QoQ %)",
    },
    "PPI (Producer Prices)": {
        "id": "PPIACO",
        "direction": "higher_is_hawkish",
        "desc": "Producer Price Index - All Commodities",
    },
    "Consumer Sentiment": {
        "id": "UMCSENT",
        "direction": "higher_is_bullish",
        "desc": "University of Michigan Consumer Sentiment",
    },
}

# For backward-compatibility: flat dict of series IDs
FRED_SERIES_IDS = {k: v["id"] for k, v in FRED_SERIES.items()}

# ==================== ASSET UNIVERSE ====================
ASSET_SYMBOLS = {
    # Equities
    "S&P 500": "^GSPC",
    "Nasdaq": "^IXIC",
    "Dow Jones": "^DJI",
    "Russell 2000": "^RUT",
    # Fixed Income
    "10Y Treasury": "^TNX",
    "2Y Treasury": "^IRX",
    "30Y Treasury": "^TYX",
    # Commodities
    "Gold (XAU/USD)": "GC=F",
    "Silver": "SI=F",
    "Crude Oil": "CL=F",
    "Natural Gas": "NG=F",
    # Volatility
    "VIX": "^VIX",
    # Crypto
    "Bitcoin": "BTC-USD",
    "Ethereum": "ETH-USD",
    # FX Majors
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "JPY=X",
    "USD/CHF": "CHF=X",
    "AUD/USD": "AUDUSD=X",
}

ASSET_CATEGORIES = {
    "Equities": ["S&P 500", "Nasdaq", "Dow Jones", "Russell 2000"],
    "Fixed Income": ["10Y Treasury", "2Y Treasury", "30Y Treasury"],
    "Commodities": ["Gold (XAU/USD)", "Silver", "Crude Oil", "Natural Gas"],
    "Volatility": ["VIX"],
    "Crypto": ["Bitcoin", "Ethereum"],
    "FX": ["EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD"],
}

# Display order for categories
CATEGORY_ORDER = ["Equities", "Fixed Income", "FX", "Commodities", "Volatility", "Crypto"]

# Category accent colors for UI
CATEGORY_COLORS = {
    "Equities": "#33A1FF",
    "Fixed Income": "#FFA500",
    "FX": "#00FF6A",
    "Commodities": "#F4F725",
    "Volatility": "#FF4D4D",
    "Crypto": "#BF5FFF",
}

# Benchmark asset for beta calculation
BENCHMARK_ASSET = "S&P 500"

# Window size options (minutes)
WINDOW_OPTIONS = ["15 min", "30 min", "60 min", "120 min"]

# Assumed annualized risk-free rate for Sharpe/Sortino
RISK_FREE_RATE_ANNUAL = 0.05
