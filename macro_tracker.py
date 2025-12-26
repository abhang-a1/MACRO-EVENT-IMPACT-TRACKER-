# Requirements:
# pip install pandas matplotlib requests yfinance tkcalendar pytz seaborn

import requests
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta, time
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from tkcalendar import DateEntry
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.dates as mdates
import numpy as np
import pytz
import seaborn as sns

# ==================== GLOBAL STYLING ====================

# Bloomberg-like dark terminal look
plt.style.use('dark_background')
plt.rcParams.update({
    'axes.facecolor': '#000000',
    'figure.facecolor': '#000000',
    'axes.edgecolor': '#444444',
    'axes.labelcolor': '#E0E0E0',
    'xtick.color': '#B0B0B0',
    'ytick.color': '#B0B0B0',
    'grid.color': '#333333',
    'grid.linestyle': '--',
    'grid.alpha': 0.4,
    'text.color': '#E0E0E0',
    'legend.edgecolor': '#333333',
    'axes.titleweight': 'bold',
    'axes.titlesize': 11
})
sns.set_palette("husl")

# ==================== CONFIGURATION ====================
FRED_API_KEY = '725661d97c523a1e1f0214b7b51051c6'

fred_series = {
    'CPI (Inflation)': 'CPALTT01USM657N',
    'NFP (Jobs)': 'PAYEMS',
    'PMI (Manufacturing)': 'NAPM',
    'FOMC Rate Decision': 'FEDFUNDS',
    'Retail Sales': 'RSXFS',
    'GDP Growth': 'A191RL1Q225SBEA'
}

asset_symbols = {
    # Equities
    'S&P 500': '^GSPC',
    'Nasdaq': '^IXIC',
    'Dow Jones': '^DJI',
    'Russell 2000': '^RUT',

    # Fixed Income
    '10Y Treasury': '^TNX',
    '2Y Treasury': '^IRX',
    '30Y Treasury': '^TYX',

    # Commodities
    'Gold (XAU/USD)': 'GC=F',
    'Silver': 'SI=F',
    'Crude Oil': 'CL=F',
    'Natural Gas': 'NG=F',

    # Volatility
    'VIX': '^VIX',

    # Crypto
    'Bitcoin': 'BTC-USD',
    'Ethereum': 'ETH-USD',

    # FX Majors
    'EUR/USD': 'EURUSD=X',
    'GBP/USD': 'GBPUSD=X',
    'USD/JPY': 'JPY=X',
    'USD/CHF': 'CHF=X',
    'AUD/USD': 'AUDUSD=X'
}

asset_categories = {
    'Equities': ['S&P 500', 'Nasdaq', 'Dow Jones', 'Russell 2000'],
    'Fixed Income': ['10Y Treasury', '2Y Treasury', '30Y Treasury'],
    'Commodities': ['Gold (XAU/USD)', 'Silver', 'Crude Oil', 'Natural Gas'],
    'Volatility': ['VIX'],
    'Crypto': ['Bitcoin', 'Ethereum'],
    'FX': ['EUR/USD', 'GBP/USD', 'USD/JPY', 'USD/CHF', 'AUD/USD']
}

# ==================== HELPER FUNCTIONS ====================

def is_trading_day(date):
    """Check if date is a weekday."""
    return date.weekday() < 5


def fetch_fred_latest(series_id, date, key):
    """Fetch latest FRED data (monthly/quarterly series)."""
    try:
        obs_date = date.replace(day=1)
        url = (
            f"https://api.stlouisfed.org/fred/series/observations"
            f"?series_id={series_id}&api_key={key}&file_type=json"
            f"&observation_start={obs_date.strftime('%Y-%m-%d')}"
            f"&sort_order=desc&limit=1"
        )
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        dat = response.json()
        obs = dat.get('observations', [])

        if len(obs) == 0:
            return None, "No data available"

        last_val = obs[-1]['value']
        if last_val == '.':
            return None, "Data not available"

        return float(last_val), None

    except Exception as e:
        return None, f"Error: {str(e)}"


def fetch_yfinance_intraday(ticker, event_date, window_min, max_days=7):
    """Fetch intraday data from yfinance around the event date."""
    try:
        days_ago = (datetime.now().date() - event_date).days
        if days_ago > max_days:
            return None, f"Data only available for last {max_days} days"

        if not is_trading_day(event_date):
            # For FX/Crypto intraday we still allow, but the function already
            # special-cases them by start/end times below.
            if not any(x in ticker for x in ['BTC', 'ETH', '=X']):
                return None, "Not a trading day (weekend)"

        et = pytz.timezone('US/Eastern')
        start_time = datetime.combine(event_date, time(9, 30))
        start_time = et.localize(start_time)
        end_time = start_time + timedelta(minutes=window_min)

        # Crypto/FX trade 24/7
        if any(x in ticker for x in ['BTC', 'ETH', '=X']):
            start_time = et.localize(datetime.combine(event_date, time(0, 0)))
            end_time = start_time + timedelta(minutes=window_min)

        df = yf.download(
            ticker,
            start=start_time.date(),
            end=(end_time.date() + timedelta(days=1)),
            interval='1m',
            progress=False,
            auto_adjust=True,
            prepost=False
        )

        if df.empty:
            return None, "No data returned"

        if df.index.tz is None:
            df.index = df.index.tz_localize('US/Eastern')

        df = df[(df.index >= start_time) & (df.index <= end_time)]

        if df.empty:
            return None, "No data in time window"

        df = df[['Close']].rename(columns={'Close': ticker})
        return df, None

    except Exception as e:
        return None, f"Error: {str(e)}"


def compute_advanced_metrics(assets_data, window_min):
    """Calculate intraday performance metrics per asset."""
    metrics = {}

    for asset, df in assets_data.items():
        if df is None or df.empty:
            continue

        prices = df[df.columns[0]]
        returns = prices.pct_change().dropna()

        if len(returns) < 2:
            continue

        metrics[asset] = {
            'return': ((prices.iloc[-1] / prices.iloc[0]) - 1) * 100,
            'volatility': returns.std() * 100,
            'max_drawdown': ((prices / prices.cummax()) - 1).min() * 100,
            'sharpe': (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0,
            'price_change': prices.iloc[-1] - prices.iloc[0],
            'high': prices.max(),
            'low': prices.min(),
            'volume_weighted_return': returns.mean() * 100  # placeholder, no volume used
        }

    return metrics

# ==================== BLOOMBERG-STYLE GUI ====================

class ProfessionalMacroTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Macro Event Impact Tracker - Terminal View")
        self.root.geometry("1700x1000")
        self.root.resizable(True, True)

        # Bloomberg-like terminal colors
        self.colors = {
            'bg': '#000000',
            'panel_bg': '#111111',
            'primary': '#F4F725',    # yellow
            'secondary': '#00FF6A',  # neon green
            'accent': '#33A1FF',     # blue
            'success': '#00FF6A',
            'danger': '#FF4D4D',
            'warning': '#FFA500',
            'text': '#E0E0E0'
        }

        self.root.configure(bg=self.colors['bg'])

        self.configure_style()
        self.setup_ui()

    def configure_style(self):
        style = ttk.Style()
        style.theme_use('clam')

        # Global
        style.configure('.',
                        background=self.colors['bg'],
                        foreground=self.colors['text'],
                        fieldbackground=self.colors['bg'])

        # Frames
        style.configure('TLabelframe',
                        background=self.colors['panel_bg'],
                        foreground=self.colors['primary'],
                        bordercolor='#333333',
                        borderwidth=1)
        style.configure('TLabelframe.Label',
                        background=self.colors['panel_bg'],
                        foreground=self.colors['primary'],
                        font=('Consolas', 10, 'bold'))

        # Notebook
        style.configure('TNotebook',
                        background=self.colors['bg'],
                        borderwidth=0)
        style.configure('TNotebook.Tab',
                        background=self.colors['panel_bg'],
                        foreground=self.colors['text'],
                        padding=(10, 4),
                        borderwidth=0,
                        font=('Consolas', 9, 'bold'))
        style.map('TNotebook.Tab',
                  background=[('selected', '#1E1E1E')],
                  foreground=[('selected', self.colors['primary'])])

        # Labels
        style.configure('Title.TLabel',
                        font=('Consolas', 14, 'bold'),
                        foreground=self.colors['primary'],
                        background=self.colors['panel_bg'])
        style.configure('Header.TLabel',
                        font=('Consolas', 11, 'bold'),
                        foreground=self.colors['secondary'],
                        background=self.colors['panel_bg'])
        style.configure('Info.TLabel',
                        font=('Consolas', 9),
                        foreground=self.colors['text'],
                        background=self.colors['panel_bg'])

        # Buttons
        style.configure('Accent.TButton',
                        font=('Consolas', 10, 'bold'),
                        background='#1E1E1E',
                        foreground=self.colors['primary'],
                        borderwidth=0,
                        focuscolor=self.colors['accent'],
                        padding=(10, 4))
        style.map('Accent.TButton',
                  background=[('active', '#333333')],
                  foreground=[('active', self.colors['primary'])])

        # Treeview
        style.configure('Treeview',
                        background=self.colors['bg'],
                        foreground=self.colors['text'],
                        fieldbackground=self.colors['bg'],
                        rowheight=22,
                        bordercolor='#333333',
                        borderwidth=1,
                        font=('Consolas', 9))
        style.configure('Treeview.Heading',
                        background='#1E1E1E',
                        foreground=self.colors['primary'],
                        bordercolor='#333333',
                        borderwidth=1,
                        font=('Consolas', 9, 'bold'))
        style.map('Treeview',
                  background=[('selected', '#003366')],
                  foreground=[('selected', '#FFFFFF')])

        # Scrollbar
        style.configure('Vertical.TScrollbar',
                        background='#1E1E1E',
                        troughcolor='#000000',
                        arrowcolor=self.colors['primary'],
                        bordercolor='#1E1E1E')

        # Status bar
        style.configure('Status.TLabel',
                        background=self.colors['bg'],
                        foreground=self.colors['secondary'],
                        font=('Consolas', 9))

    def setup_ui(self):
        main_container = ttk.Frame(self.root, padding=10, style='TLabelframe')
        main_container.pack(fill='both', expand=True)

        # ========== CONTROL PANEL ==========
        control_frame = ttk.LabelFrame(main_container, text=" CONFIGURATION ", padding=10)
        control_frame.pack(fill='x', pady=(0, 8))

        controls_grid = ttk.Frame(control_frame)
        controls_grid.pack(fill='x')

        # Macro Event
        ttk.Label(controls_grid, text="Macro Event", style='Header.TLabel').grid(
            row=0, column=0, sticky='w', padx=10, pady=5
        )
        self.event = tk.StringVar()
        self.event_cb = ttk.Combobox(
            controls_grid,
            textvariable=self.event,
            state='readonly',
            width=25,
            font=('Consolas', 10)
        )
        self.event_cb['values'] = list(fred_series.keys())
        self.event_cb.current(0)
        self.event_cb.grid(row=0, column=1, padx=10, pady=5)

        # Date
        ttk.Label(controls_grid, text="Event Date", style='Header.TLabel').grid(
            row=0, column=2, sticky='w', padx=10, pady=5
        )
        self.date_picker = DateEntry(
            controls_grid,
            width=20,
            date_pattern='yyyy-mm-dd',
            font=('Consolas', 10),
            background='#000000',
            foreground=self.colors['text'],
            borderwidth=1
        )
        self.date_picker.grid(row=0, column=3, padx=10, pady=5)

        # Window
        ttk.Label(controls_grid, text="Window", style='Header.TLabel').grid(
            row=0, column=4, sticky='w', padx=10, pady=5
        )
        self.window = tk.StringVar(value='60')
        self.win_cb = ttk.Combobox(
            controls_grid,
            textvariable=self.window,
            state='readonly',
            width=12,
            font=('Consolas', 10)
        )
        self.win_cb['values'] = ['15 min', '30 min', '60 min', '120 min']
        self.win_cb.current(2)
        self.win_cb.grid(row=0, column=5, padx=10, pady=5)

        # Analyze button
        self.analyze_btn = ttk.Button(
            controls_grid,
            text="▶ RUN",
            command=self.run_analysis,
            style='Accent.TButton',
            width=12
        )
        self.analyze_btn.grid(row=0, column=6, padx=20, pady=5)

        # ========== TABS ==========
        self.results_notebook = ttk.Notebook(main_container)
        self.results_notebook.pack(fill='both', expand=True)

        self.overview_tab = ttk.Frame(self.results_notebook)
        self.charts_tab = ttk.Frame(self.results_notebook)
        self.metrics_tab = ttk.Frame(self.results_notebook)
        self.data_tab = ttk.Frame(self.results_notebook)

        self.results_notebook.add(self.overview_tab, text=" OVERVIEW ")
        self.results_notebook.add(self.charts_tab, text=" CHARTS ")
        self.results_notebook.add(self.metrics_tab, text=" METRICS ")
        self.results_notebook.add(self.data_tab, text=" RAW LOG ")

        # Status bar
        self.status_bar = ttk.Label(
            main_container,
            text="READY",
            anchor=tk.W,
            style='Status.TLabel'
        )
        self.status_bar.pack(fill='x', pady=(8, 0))

    # ==================== ANALYSIS FLOW ====================

    def run_analysis(self):
        # Clear tabs
        for tab in [self.overview_tab, self.charts_tab, self.metrics_tab, self.data_tab]:
            for widget in tab.winfo_children():
                widget.destroy()

        self.status_bar.config(text="FETCHING DATA ...")
        self.root.update()

        event_type = self.event.get()
        event_date = self.date_picker.get_date()
        window_str = self.window.get()
        window_min = int(window_str.split()[0])

        # Validation
        days_ago = (datetime.now().date() - event_date).days
        if days_ago > 7:
            messagebox.showwarning(
                "DATE LIMIT",
                f"Selected date is {days_ago} days ago.\n\n"
                "Yahoo Finance provides 1-minute data for last 7 days only.\n"
                "Select a more recent date."
            )
            self.status_bar.config(text="ERROR: DATE TOO OLD")
            return

        if not is_trading_day(event_date):
            messagebox.showwarning(
                "NON-TRADING DAY",
                "Selected date is a weekend.\n\nSelect a weekday for equities/bonds."
            )
            self.status_bar.config(text="ERROR: WEEKEND SELECTED")
            return

        # Fetch FRED data
        self.status_bar.config(text="FETCHING MACRO DATA ...")
        self.root.update()

        actual, actual_err = fetch_fred_latest(fred_series[event_type], event_date, FRED_API_KEY)
        prev_date = event_date - timedelta(days=30)
        consensus, consensus_err = fetch_fred_latest(fred_series[event_type], prev_date, FRED_API_KEY)

        # Fetch markets
        self.status_bar.config(text="FETCHING MARKET DATA ...")
        self.root.update()

        assets_data = {}
        fetch_log = []

        for i, (asset_name, ticker) in enumerate(asset_symbols.items()):
            self.status_bar.config(
                text=f"FETCHING {asset_name} ({i + 1}/{len(asset_symbols)}) ..."
            )
            self.root.update()

            df, error = fetch_yfinance_intraday(ticker, event_date, window_min)

            if df is not None and not df.empty:
                assets_data[asset_name] = df
                fetch_log.append(f"OK  {asset_name}: {len(df)} pts")
            else:
                fetch_log.append(f"FAIL {asset_name}: {error}")

        if not assets_data:
            messagebox.showerror("NO DATA", "No intraday asset data returned.\nTry another date/window.")
            self.status_bar.config(text="ERROR: NO DATA")
            return

        # Build UI tabs
        self.create_overview_tab(event_type, event_date, actual, consensus, assets_data, window_min)
        self.create_charts_tab(assets_data, window_min, event_date)
        self.create_metrics_tab(assets_data, window_min)
        self.create_data_tab(assets_data, fetch_log)

        self.status_bar.config(text=f"COMPLETE | {len(assets_data)} ASSETS")

    # ==================== TAB BUILDERS ====================

    def create_overview_tab(self, event_type, event_date, actual, consensus, assets_data, window_min):
        import math

        container = ttk.Frame(self.overview_tab, padding=10, style='TLabelframe')
        container.pack(fill='both', expand=True)

        # Macro summary
        macro_frame = ttk.LabelFrame(container, text=" MACRO EVENT ", padding=10)
        macro_frame.pack(fill='x', pady=(0, 10))

        summary_grid = ttk.Frame(macro_frame)
        summary_grid.pack()

        ttk.Label(summary_grid, text="Event", font=('Consolas', 10, 'bold'),
                  background=self.colors['panel_bg'],
                  foreground=self.colors['secondary']).grid(row=0, column=0, sticky='w', padx=8, pady=2)
        ttk.Label(summary_grid, text=event_type, font=('Consolas', 10),
                  background=self.colors['panel_bg']).grid(row=0, column=1, sticky='w', padx=8, pady=2)

        ttk.Label(summary_grid, text="Date", font=('Consolas', 10, 'bold'),
                  background=self.colors['panel_bg'],
                  foreground=self.colors['secondary']).grid(row=0, column=2, sticky='w', padx=8, pady=2)
        ttk.Label(summary_grid, text=event_date.strftime('%Y-%m-%d'),
                  font=('Consolas', 10),
                  background=self.colors['panel_bg']).grid(row=0, column=3, sticky='w', padx=8, pady=2)

        ttk.Label(summary_grid, text="Actual", font=('Consolas', 10, 'bold'),
                  background=self.colors['panel_bg'],
                  foreground=self.colors['secondary']).grid(row=1, column=0, sticky='w', padx=8, pady=2)
        actual_valid = isinstance(actual, float) and not math.isnan(actual)
        ttk.Label(summary_grid, text=f"{actual:.2f}" if actual_valid else "N/A",
                  font=('Consolas', 10),
                  background=self.colors['panel_bg']).grid(row=1, column=1, sticky='w', padx=8, pady=2)

        ttk.Label(summary_grid, text="Consensus", font=('Consolas', 10, 'bold'),
                  background=self.colors['panel_bg'],
                  foreground=self.colors['secondary']).grid(row=1, column=2, sticky='w', padx=8, pady=2)
        consensus_valid = isinstance(consensus, float) and not math.isnan(consensus)
        ttk.Label(summary_grid, text=f"{consensus:.2f}" if consensus_valid else "N/A",
                  font=('Consolas', 10),
                  background=self.colors['panel_bg']).grid(row=1, column=3, sticky='w', padx=8, pady=2)

        ttk.Label(summary_grid, text="Surprise", font=('Consolas', 10, 'bold'),
                  background=self.colors['panel_bg'],
                  foreground=self.colors['secondary']).grid(row=1, column=4, sticky='w', padx=8, pady=2)

        if actual_valid and consensus_valid:
            surprise = actual - consensus
            surprise_color = self.colors['success'] if surprise > 0 else self.colors['danger']
            surprise_label = ttk.Label(summary_grid, text=f"{surprise:+.2f}",
                                       font=('Consolas', 10, 'bold'),
                                       foreground=surprise_color,
                                       background=self.colors['panel_bg'])
        else:
            surprise_label = ttk.Label(summary_grid, text="N/A",
                                       font=('Consolas', 10),
                                       background=self.colors['panel_bg'])
        surprise_label.grid(row=1, column=5, sticky='w', padx=8, pady=2)

        # Market overview
        stats_frame = ttk.LabelFrame(container, text=" MARKET SNAPSHOT ", padding=10)
        stats_frame.pack(fill='both', expand=True)

        metrics = compute_advanced_metrics(assets_data, window_min)

        tree = ttk.Treeview(
            stats_frame,
            columns=('Asset', 'Return %', 'Volatility %', 'Max DD %'),
            show='headings',
            height=18
        )
        tree.heading('Asset', text='Asset')
        tree.heading('Return %', text='Return %')
        tree.heading('Volatility %', text='Volatility %')
        tree.heading('Max DD %', text='Max Drawdown %')

        tree.column('Asset', width=220, anchor='w')
        tree.column('Return %', width=120, anchor='center')
        tree.column('Volatility %', width=120, anchor='center')
        tree.column('Max DD %', width=140, anchor='center')

        for asset, m in sorted(metrics.items(), key=lambda x: abs(x[1]['return']), reverse=True):
            tag = 'pos' if m['return'] > 0 else 'neg'
            tree.insert(
                '',
                'end',
                values=(
                    asset,
                    f"{m['return']:.2f}",
                    f"{m['volatility']:.2f}",
                    f"{m['max_drawdown']:.2f}"
                ),
                tags=(tag,)
            )

        tree.tag_configure('pos', foreground=self.colors['success'])
        tree.tag_configure('neg', foreground=self.colors['danger'])

        scrollbar = ttk.Scrollbar(stats_frame, orient='vertical', command=tree.yview, style='Vertical.TScrollbar')
        tree.configure(yscroll=scrollbar.set)

        tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

    def create_charts_tab(self, assets_data, window_min, event_date):
        container = ttk.Frame(self.charts_tab, style='TLabelframe')
        container.pack(fill='both', expand=True)

        metrics = compute_advanced_metrics(assets_data, window_min)
        sorted_vols = sorted(metrics.items(), key=lambda x: x[1]['volatility'], reverse=True)
        sorted_rets = sorted(metrics.items(), key=lambda x: x[1]['return'], reverse=True)

        price_data = pd.DataFrame({name: df[df.columns[0]] for name, df in list(assets_data.items())[:10]})
        corr = price_data.corr() if not price_data.empty else pd.DataFrame()

        fig, axs = plt.subplots(2, 2, figsize=(14, 9), dpi=100)
        fig.subplots_adjust(hspace=0.4, wspace=0.3, top=0.93, bottom=0.08, left=0.06, right=0.97)
        fig.patch.set_facecolor('#000000')
        for ax in axs.flat:
            ax.set_facecolor('#000000')

        # 1) % change first 4 assets
        ax1 = axs[0, 0]
        assets_to_plot = list(assets_data.keys())[:4]
        colors_price = ['#F4F725', '#00FF6A', '#33A1FF', '#FF4D4D']
        for asset, color in zip(assets_to_plot, colors_price):
            df = assets_data[asset]
            normalized = (df[df.columns[0]] / df[df.columns[0]].iloc[0] - 1) * 100
            ax1.plot(df.index, normalized, label=asset, linewidth=2, color=color)
        ax1.set_title('Top 4 Assets: % Change', fontweight='bold')
        ax1.set_ylabel('% from Start')
        ax1.legend(fontsize=8, loc='best', frameon=True, framealpha=0.2)
        ax1.grid(True, alpha=0.4, linestyle='--')
        ax1.axhline(y=0, color='#666666', linestyle='-', linewidth=0.5)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

        # 2) Volatility ranking
        ax2 = axs[0, 1]
        vol_assets = [x[0] for x in sorted_vols[:6]]
        vols = [x[1]['volatility'] for x in sorted_vols[:6]]
        colors_vol = ['#F4F725'] * len(vols)
        bars = ax2.barh(vol_assets, vols, color=colors_vol)
        ax2.set_xlabel('Volatility (%)')
        ax2.set_title('Top 6 Volatility', fontweight='bold')
        ax2.grid(True, axis='x', alpha=0.4, linestyle='--')
        for bar in bars:
            width = bar.get_width()
            ax2.text(width + 0.1, bar.get_y() + bar.get_height() / 2,
                     f'{width:.2f}', va='center', ha='left', fontsize=8, color='#E0E0E0')

        # 3) Return ranking
        ax3 = axs[1, 0]
        ret_assets = [x[0] for x in sorted_rets[:6]]
        rets = [x[1]['return'] for x in sorted_rets[:6]]
        colors_ret = ['#00FF6A' if r > 0 else '#FF4D4D' for r in rets]
        bars_ret = ax3.barh(ret_assets, rets, color=colors_ret, alpha=0.8)
        ax3.set_xlabel('Return (%)')
        ax3.set_title('Top 6 Returns', fontweight='bold')
        ax3.grid(True, axis='x', alpha=0.4, linestyle='--')
        ax3.axvline(x=0, color='#666666', linestyle='-', linewidth=0.5)
        for bar, ret in zip(bars_ret, rets):
            width = bar.get_width()
            ha = 'left' if ret > 0 else 'right'
            dx = 0.3 if ret > 0 else -0.3
            ax3.text(width + dx, bar.get_y() + bar.get_height() / 2,
                     f'{ret:.2f}', va='center', ha=ha, fontsize=8, color='#E0E0E0')

        # 4) Correlation heatmap
        ax4 = axs[1, 1]
        if not corr.empty:
            im = ax4.imshow(corr, cmap='coolwarm', vmin=-1, vmax=1, aspect='auto')
            ax4.set_xticks(range(len(corr)))
            ax4.set_yticks(range(len(corr)))
            ax4.set_xticklabels(corr.columns, rotation=45, ha='right', fontsize=7, color='#E0E0E0')
            ax4.set_yticklabels(corr.index, fontsize=7, color='#E0E0E0')
            ax4.set_title('Correlation Matrix', fontweight='bold')
            fig.colorbar(im, ax=ax4, fraction=0.05, pad=0.05)
        else:
            ax4.axis('off')
            ax4.set_title('No Data for Correlation', fontweight='bold')

        canvas = FigureCanvasTkAgg(fig, master=container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True, pady=5)

    def create_metrics_tab(self, assets_data, window_min):
        container = ttk.Frame(self.metrics_tab, padding=10, style='TLabelframe')
        container.pack(fill='both', expand=True)

        metrics = compute_advanced_metrics(assets_data, window_min)

        tree = ttk.Treeview(
            container,
            columns=('Asset', 'Return', 'Vol', 'Sharpe', 'Max DD', 'High', 'Low', 'Change'),
            show='headings',
            height=24
        )

        headers = ['Asset', 'Return %', 'Volatility %', 'Sharpe', 'Max DD %', 'High', 'Low', 'Price Δ']
        for i, header in enumerate(headers):
            tree.heading(f'#{i + 1}', text=header)
            tree.column(f'#{i + 1}', width=120, anchor='center')

        tree.column('#1', width=200, anchor='w')

        for asset, m in sorted(metrics.items(), key=lambda x: x[0]):
            tree.insert('', 'end', values=(
                asset,
                f"{m['return']:.2f}",
                f"{m['volatility']:.3f}",
                f"{m['sharpe']:.2f}",
                f"{m['max_drawdown']:.2f}",
                f"{m['high']:.2f}",
                f"{m['low']:.2f}",
                f"{m['price_change']:.2f}"
            ))

        scrollbar = ttk.Scrollbar(container, orient='vertical', command=tree.yview, style='Vertical.TScrollbar')
        tree.configure(yscroll=scrollbar.set)

        tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

    def create_data_tab(self, assets_data, fetch_log):
        container = ttk.Frame(self.data_tab, padding=10, style='TLabelframe')
        container.pack(fill='both', expand=True)

        log_frame = ttk.LabelFrame(container, text=" DATA FETCH LOG ", padding=8)
        log_frame.pack(fill='both', expand=True)

        log_text = scrolledtext.ScrolledText(
            log_frame,
            height=30,
            width=130,
            font=('Consolas', 9),
            background=self.colors['bg'],
            foreground=self.colors['text'],
            insertbackground=self.colors['primary'],
            borderwidth=1
        )
        log_text.pack(fill='both', expand=True)

        for line in fetch_log:
            log_text.insert(tk.END, line + '\n')


# ==================== MAIN ====================

if __name__ == "__main__":
    root = tk.Tk()
    app = ProfessionalMacroTrackerApp(root)
    root.mainloop()
