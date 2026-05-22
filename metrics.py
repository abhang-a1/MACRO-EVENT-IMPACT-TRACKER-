# metrics.py - Analytics engine: returns, risk ratios, correlations, impact scores
import pandas as pd
import numpy as np
from config import BENCHMARK_ASSET, RISK_FREE_RATE_ANNUAL, ASSET_CATEGORIES


# ==================== PER-ASSET METRICS ====================
def compute_metrics(assets_data: dict, window_min: int) -> pd.DataFrame:
    """
    Compute comprehensive intraday metrics for each asset.

    Returns a DataFrame with columns:
        asset, category, return_pct, vol_pct, max_drawdown_pct,
        sharpe, sortino, beta, vwap_return_pct,
        high, low, price_change, annualized_vol,
        per_min_return, impact_score
    """
    rows = []
    # Build benchmark returns first (for beta)
    bench_returns = None
    if BENCHMARK_ASSET in assets_data and assets_data[BENCHMARK_ASSET] is not None:
        bench_df = assets_data[BENCHMARK_ASSET]
        prices = bench_df[bench_df.columns[0]]
        bench_returns = prices.pct_change().dropna()

    # Category lookup
    asset_to_cat = {}
    for cat, names in ASSET_CATEGORIES.items():
        for n in names:
            asset_to_cat[n] = cat

    for asset, df in assets_data.items():
        if df is None or df.empty:
            continue
        prices = df[df.columns[0]]
        returns = prices.pct_change().dropna()
        if len(returns) < 2:
            continue

        total_return = (prices.iloc[-1] / prices.iloc[0] - 1) * 100
        vol = returns.std() * 100
        annualized_vol = returns.std() * np.sqrt(252 * 390) * 100  # 390 min/day
        max_dd = ((prices / prices.cummax()) - 1).min() * 100

        # Per-minute and annualized returns
        per_min_ret = total_return / max(window_min, 1)

        # Risk-free rate per minute
        rf_per_bar = RISK_FREE_RATE_ANNUAL / (252 * 390)

        # Sharpe (per-bar)
        sharpe = (
            (returns.mean() - rf_per_bar) / returns.std() * np.sqrt(252 * 390)
            if returns.std() > 0 else 0.0
        )

        # Sortino (downside deviation only)
        neg_returns = returns[returns < rf_per_bar]
        downside_std = neg_returns.std() if len(neg_returns) > 1 else 0.0
        sortino = (
            (returns.mean() - rf_per_bar) / downside_std * np.sqrt(252 * 390)
            if downside_std > 0 else 0.0
        )

        # Beta vs benchmark
        beta = 0.0
        if bench_returns is not None and asset != BENCHMARK_ASSET:
            aligned = pd.concat([returns, bench_returns], axis=1).dropna()
            if len(aligned) > 2 and aligned.iloc[:, 1].std() > 0:
                cov = aligned.cov().iloc[0, 1]
                var = aligned.iloc[:, 1].var()
                beta = cov / var if var != 0 else 0.0

        rows.append({
            "asset": asset,
            "category": asset_to_cat.get(asset, "Other"),
            "return_pct": round(total_return, 4),
            "vol_pct": round(vol, 4),
            "max_drawdown_pct": round(max_dd, 4),
            "sharpe": round(sharpe, 3),
            "sortino": round(sortino, 3),
            "beta": round(beta, 3),
            "annualized_vol": round(annualized_vol, 2),
            "per_min_return": round(per_min_ret, 5),
            "high": round(float(prices.max()), 4),
            "low": round(float(prices.min()), 4),
            "price_change": round(float(prices.iloc[-1] - prices.iloc[0]), 4),
        })

    df_out = pd.DataFrame(rows)
    if not df_out.empty:
        df_out["impact_score"] = _compute_impact_scores(df_out)
    return df_out


# ==================== IMPACT SCORE ====================
def _compute_impact_scores(df: pd.DataFrame) -> pd.Series:
    """
    Blend |return|, volatility, and |max_drawdown| into a 0-100 impact score.
    Uses z-score normalization across assets.
    """
    factors = df[["return_pct", "vol_pct", "max_drawdown_pct"]].copy()
    factors["return_pct"] = factors["return_pct"].abs()
    factors["max_drawdown_pct"] = factors["max_drawdown_pct"].abs()

    # Z-score each column
    for col in factors.columns:
        std = factors[col].std()
        mean = factors[col].mean()
        factors[col] = (factors[col] - mean) / std if std > 0 else 0.0

    # Weighted blend: return 50%, vol 30%, drawdown 20%
    score_raw = 0.5 * factors["return_pct"] + 0.3 * factors["vol_pct"] + 0.2 * factors["max_drawdown_pct"]

    # Rescale to 0-100
    mn, mx = score_raw.min(), score_raw.max()
    if mx > mn:
        score_scaled = (score_raw - mn) / (mx - mn) * 100
    else:
        score_scaled = pd.Series([50.0] * len(score_raw), index=score_raw.index)

    return score_scaled.round(1)


def global_event_impact_index(metrics_df: pd.DataFrame) -> float:
    """
    Single number (0-100) summarizing how disruptive the event is across all assets.
    Uses the mean of the top-5 impact scores.
    """
    if metrics_df.empty or "impact_score" not in metrics_df.columns:
        return 0.0
    top5 = metrics_df["impact_score"].nlargest(5)
    return round(top5.mean(), 1)


# ==================== CORRELATION ====================
def compute_corr_matrix(assets_data: dict, price_level: bool = False) -> pd.DataFrame:
    """
    Compute return-based (default) or price-level correlation matrix.

    Returns a DataFrame of shape (n_assets, n_assets).
    """
    series = {}
    for name, df in assets_data.items():
        if df is None or df.empty:
            continue
        prices = df[df.columns[0]]
        series[name] = prices if price_level else prices.pct_change().dropna()

    if len(series) < 2:
        return pd.DataFrame()

    combined = pd.DataFrame(series).dropna()
    return combined.corr()


# ==================== CATEGORY SUMMARY ====================
def category_summary(metrics_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate metrics by asset category.
    Returns mean return, mean vol, mean impact per category.
    """
    if metrics_df.empty:
        return pd.DataFrame()
    return (
        metrics_df.groupby("category")[["return_pct", "vol_pct", "impact_score"]]
        .mean()
        .round(3)
        .reset_index()
    )
