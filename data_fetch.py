# data_fetch.py - Data fetching layer: FRED + yfinance with caching
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta, time
from concurrent.futures import ThreadPoolExecutor, as_completed
import pytz
import threading

from config import (
    FRED_API_KEY, MAX_DAYS_BACK, FRED_SERIES, ASSET_SYMBOLS
)

# ==================== IN-MEMORY CACHE ====================
_cache_lock = threading.Lock()
_yf_cache: dict = {}   # key: (ticker, date_str, window_min)
_fred_cache: dict = {}  # key: (series_id, obs_date_str)


# ==================== HELPERS ====================
def is_trading_day(date) -> bool:
    """Return True if date is Mon-Fri."""
    return date.weekday() < 5


def _is_crypto_or_fx(ticker: str) -> bool:
    return any(x in ticker for x in ["BTC", "ETH", "=X"])


# ==================== FRED ====================
def get_macro_snapshot(event_type: str, event_date) -> dict:
    """
    Fetch FRED data for a given macro event type and date.

    Returns a dict with keys:
        actual, prior, surprise, error, series_id, direction, desc
    """
    if event_type not in FRED_SERIES:
        return {"actual": None, "prior": None, "surprise": None,
                "error": f"Unknown event type: {event_type}"}

    meta = FRED_SERIES[event_type]
    series_id = meta["id"]

    obs_date = event_date.replace(day=1)
    prior_date = (obs_date - timedelta(days=1)).replace(day=1)

    actual, actual_err = _fetch_fred_obs(series_id, obs_date)
    prior, _ = _fetch_fred_obs(series_id, prior_date)

    surprise = None
    if isinstance(actual, float) and isinstance(prior, float):
        surprise = round(actual - prior, 4)

    return {
        "actual": actual,
        "prior": prior,
        "surprise": surprise,
        "error": actual_err,
        "series_id": series_id,
        "direction": meta.get("direction", "unknown"),
        "desc": meta.get("desc", ""),
    }


def _fetch_fred_obs(series_id: str, obs_date) -> tuple:
    """Fetch a single FRED observation (cached)."""
    cache_key = (series_id, obs_date.strftime("%Y-%m-%d"))
    with _cache_lock:
        if cache_key in _fred_cache:
            return _fred_cache[cache_key]

    try:
        url = (
            f"https://api.stlouisfed.org/fred/series/observations"
            f"?series_id={series_id}&api_key={FRED_API_KEY}&file_type=json"
            f"&observation_start={obs_date.strftime('%Y-%m-%d')}"
            f"&sort_order=desc&limit=1"
        )
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        obs = data.get("observations", [])
        if not obs or obs[-1]["value"] == ".":
            result = (None, "Data not available")
        else:
            result = (float(obs[-1]["value"]), None)
    except Exception as e:
        result = (None, f"FRED error: {e}")

    with _cache_lock:
        _fred_cache[cache_key] = result
    return result


# ==================== YFINANCE ====================
def get_intraday_assets(
    event_date,
    window_min: int,
    assets: dict = None,
) -> dict:
    """
    Fetch 1-minute intraday data for all assets in parallel.

    Returns dict: {asset_name -> DataFrame | None}
    Also returns a log list of strings.
    """
    if assets is None:
        assets = ASSET_SYMBOLS

    # Validate date range
    days_ago = (datetime.now().date() - event_date).days
    if days_ago > MAX_DAYS_BACK:
        return {}, [f"ERROR: Date is {days_ago} days ago (max {MAX_DAYS_BACK})"]

    results = {}
    log = []

    def _fetch_one(asset_name, ticker):
        df, err = _fetch_ticker(ticker, event_date, window_min)
        return asset_name, ticker, df, err

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(_fetch_one, name, ticker): name
            for name, ticker in assets.items()
        }
        for future in as_completed(futures):
            asset_name, ticker, df, err = future.result()
            if df is not None and not df.empty:
                results[asset_name] = df
                log.append(f"[OK]   {asset_name} ({ticker}): {len(df)} pts")
            else:
                results[asset_name] = None
                log.append(f"[FAIL] {asset_name} ({ticker}): {err}")

    return results, log


def _fetch_ticker(ticker: str, event_date, window_min: int) -> tuple:
    """Download 1-min data for one ticker (in-session cached)."""
    cache_key = (ticker, str(event_date), window_min)
    with _cache_lock:
        if cache_key in _yf_cache:
            return _yf_cache[cache_key]

    try:
        et = pytz.timezone("US/Eastern")

        if _is_crypto_or_fx(ticker):
            start_time = et.localize(datetime.combine(event_date, time(0, 0)))
        else:
            if not is_trading_day(event_date):
                result = (None, "Not a trading day")
                with _cache_lock:
                    _yf_cache[cache_key] = result
                return result
            start_time = et.localize(datetime.combine(event_date, time(9, 30)))

        end_time = start_time + timedelta(minutes=window_min)

        df = yf.download(
            ticker,
            start=start_time.date(),
            end=(end_time.date() + timedelta(days=1)),
            interval="1m",
            progress=False,
            auto_adjust=True,
            prepost=False,
        )

        if df.empty:
            result = (None, "No data returned by yfinance")
        else:
            # Flatten multi-index columns if present
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            if df.index.tz is None:
                df.index = df.index.tz_localize("US/Eastern")
            else:
                df.index = df.index.tz_convert("US/Eastern")

            df = df[(df.index >= start_time) & (df.index <= end_time)]

            if df.empty:
                result = (None, "No data in requested time window")
            else:
                df = df[["Close"]].rename(columns={"Close": ticker})
                result = (df, None)

    except Exception as e:
        result = (None, f"yfinance error: {e}")

    with _cache_lock:
        _yf_cache[cache_key] = result
    return result


def clear_cache():
    """Clear all in-session caches (call before a fresh analysis run)."""
    with _cache_lock:
        _yf_cache.clear()
        _fred_cache.clear()
