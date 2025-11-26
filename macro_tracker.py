# Requirements: pip install pandas matplotlib requests yfinance tkcalendar pytz seaborn

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

plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

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



def is_trading_day(date):
    """Check if date is a weekday"""
    return date.weekday() < 5


def fetch_fred_latest(series_id, date, key):
    """Fetch latest FRED data"""
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
    """Fetch intraday data from yfinance"""
    try:
        days_ago = (datetime.now().date() - event_date).days
        if days_ago > max_days:
            return None, f"Data only available for last {max_days} days"

        if not is_trading_day(event_date):
            return None, "Not a trading day (weekend)"

        et = pytz.timezone('US/Eastern')
        start_time = datetime.combine(event_date, time(9, 30))
        start_time = et.localize(start_time)
        end_time = start_time + timedelta(minutes=window_min)

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
    """Calculate comprehensive metrics"""
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
            'volume_weighted_return': returns.mean() * 100
        }

    return metrics



class ProfessionalMacroTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Macro Event Impact Tracker")
        self.root.geometry("1600x1000")
        self.root.resizable(True, True)

        self.colors = {
            'bg': '#f0f0f0',
            'primary': '#2c3e50',
            'secondary': '#34495e',
            'accent': '#3498db',
            'success': '#27ae60',
            'danger': '#e74c3c',
            'warning': '#f39c12'
        }

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Title.TLabel', font=('Arial', 14, 'bold'), foreground=self.colors['primary'])
        style.configure('Header.TLabel', font=('Arial', 11, 'bold'), foreground=self.colors['secondary'])
        style.configure('Info.TLabel', font=('Arial', 9), foreground=self.colors['secondary'])
        style.configure('Accent.TButton', font=('Arial', 10, 'bold'))

        self.root.configure(bg=self.colors['bg'])

        self.setup_ui()

    def setup_ui(self):
        """Setup the user interface"""
        main_container = ttk.Frame(self.root, padding=15)
        main_container.pack(fill='both', expand=True)


        control_frame = ttk.LabelFrame(main_container, text="Analysis Configuration", padding=15)
        control_frame.pack(fill='x', pady=(0, 10))

        controls_grid = ttk.Frame(control_frame)
        controls_grid.pack(fill='x')

        ttk.Label(controls_grid, text="Macro Event:", style='Header.TLabel').grid(
            row=0, column=0, sticky='w', padx=10, pady=5
        )
        self.event = tk.StringVar()
        self.event_cb = ttk.Combobox(
            controls_grid,
            textvariable=self.event,
            state='readonly',
            width=25,
            font=('Arial', 10)
        )
        self.event_cb['values'] = list(fred_series.keys())
        self.event_cb.current(0)
        self.event_cb.grid(row=0, column=1, padx=10, pady=5)

        ttk.Label(controls_grid, text="Event Date:", style='Header.TLabel').grid(
            row=0, column=2, sticky='w', padx=10, pady=5
        )
        self.date_picker = DateEntry(
            controls_grid,
            width=20,
            date_pattern='yyyy-mm-dd',
            font=('Arial', 10)
        )
        self.date_picker.grid(row=0, column=3, padx=10, pady=5)

        ttk.Label(controls_grid, text="Analysis Window:", style='Header.TLabel').grid(
            row=0, column=4, sticky='w', padx=10, pady=5
        )
        self.window = tk.StringVar(value='60')
        self.win_cb = ttk.Combobox(
            controls_grid,
            textvariable=self.window,
            state='readonly',
            width=12,
            font=('Arial', 10)
        )
        self.win_cb['values'] = ['15 min', '30 min', '60 min', '120 min']
        self.win_cb.current(2)
        self.win_cb.grid(row=0, column=5, padx=10, pady=5)

        self.analyze_btn = ttk.Button(
            controls_grid,
            text="🔍 ANALYZE",
            command=self.run_analysis,
            style='Accent.TButton',
            width=15
        )
        self.analyze_btn.grid(row=0, column=6, padx=20, pady=5)

        self.results_notebook = ttk.Notebook(main_container)
        self.results_notebook.pack(fill='both', expand=True)

        # Create tabs
        self.overview_tab = ttk.Frame(self.results_notebook)
        self.charts_tab = ttk.Frame(self.results_notebook)
        self.metrics_tab = ttk.Frame(self.results_notebook)
        self.data_tab = ttk.Frame(self.results_notebook)

        self.results_notebook.add(self.overview_tab, text=" Overview")
        self.results_notebook.add(self.charts_tab, text=" Charts")
        self.results_notebook.add(self.metrics_tab, text=" Metrics")
        self.results_notebook.add(self.data_tab, text="Raw Data")

        # Status bar
        self.status_bar = ttk.Label(
            main_container,
            text="Ready to analyze",
            relief=tk.SUNKEN,
            anchor=tk.W,
            font=('Arial', 9)
        )
        self.status_bar.pack(fill='x', pady=(10, 0))

    def run_analysis(self):
        """Main analysis execution"""
        # Clear tabs
        for tab in [self.overview_tab, self.charts_tab, self.metrics_tab, self.data_tab]:
            for widget in tab.winfo_children():
                widget.destroy()

        self.status_bar.config(text="⏳ Fetching data...")
        self.root.update()

        # Get inputs
        event_type = self.event.get()
        event_date = self.date_picker.get_date()
        window_str = self.window.get()
        window_min = int(window_str.split()[0])

        # Validations
        days_ago = (datetime.now().date() - event_date).days
        if days_ago > 7:
            messagebox.showwarning(
                "Date Limitation",
                f"Selected date is {days_ago} days ago.\n\n"
                "Yahoo Finance provides 1-minute data for last 7 days only.\n"
                "Please select a more recent date."
            )
            self.status_bar.config(text="❌ Date too old")
            return

        if not is_trading_day(event_date):
            messagebox.showwarning(
                "Non-Trading Day",
                f"Selected date is a weekend.\n\nPlease select a weekday."
            )
            self.status_bar.config(text="❌ Weekend selected")
            return

        # Fetch FRED data
        self.status_bar.config(text="⏳ Fetching macro data...")
        self.root.update()

        actual, actual_err = fetch_fred_latest(fred_series[event_type], event_date, FRED_API_KEY)
        prev_date = event_date - timedelta(days=30)
        consensus, consensus_err = fetch_fred_latest(fred_series[event_type], prev_date, FRED_API_KEY)

        # Fetch asset data
        self.status_bar.config(text="⏳ Fetching asset prices...")
        self.root.update()

        assets_data = {}
        fetch_log = []

        for i, (asset_name, ticker) in enumerate(asset_symbols.items()):
            self.status_bar.config(text=f"⏳ Fetching {asset_name} ({i + 1}/{len(asset_symbols)})")
            self.root.update()

            df, error = fetch_yfinance_intraday(ticker, event_date, window_min)

            if df is not None and not df.empty:
                assets_data[asset_name] = df
                fetch_log.append(f"✓ {asset_name}: {len(df)} points")
            else:
                fetch_log.append(f"✗ {asset_name}: {error}")

        if not assets_data:
            messagebox.showerror("No Data", "Unable to fetch any asset data.\n\nTry a different date.")
            self.status_bar.config(text="❌ No data")
            return

        # Generate displays
        self.create_overview_tab(event_type, event_date, actual, consensus, assets_data, window_min)
        self.create_charts_tab(assets_data, window_min, event_date)
        self.create_metrics_tab(assets_data, window_min)
        self.create_data_tab(assets_data, fetch_log)

        self.status_bar.config(text=f"✅ Analysis complete | {len(assets_data)} assets loaded")

    def create_overview_tab(self, event_type, event_date, actual, consensus, assets_data, window_min):
        """Create overview tab with summary"""
        container = ttk.Frame(self.overview_tab, padding=15)
        container.pack(fill='both', expand=True)

        import math

        # Macro event summary panel (displaying with robust validation)
        macro_frame = ttk.LabelFrame(container, text="📈 Macro Event Summary", padding=10)
        macro_frame.pack(fill='x', pady=(0, 10))

        summary_grid = ttk.Frame(macro_frame)
        summary_grid.pack()

        ttk.Label(summary_grid, text="Event:", font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky='w', padx=10)
        ttk.Label(summary_grid, text=event_type, font=('Arial', 10)).grid(row=0, column=1, sticky='w', padx=10)

        ttk.Label(summary_grid, text="Date:", font=('Arial', 10, 'bold')).grid(row=0, column=2, sticky='w', padx=10)
        ttk.Label(summary_grid, text=event_date.strftime('%Y-%m-%d'), font=('Arial', 10)).grid(row=0, column=3,
                                                                                               sticky='w', padx=10)

        ttk.Label(summary_grid, text="Actual:", font=('Arial', 10, 'bold')).grid(row=1, column=0, sticky='w', padx=10)
        actual_valid = isinstance(actual, float) and not math.isnan(actual)
        ttk.Label(summary_grid, text=f"{actual:.2f}" if actual_valid else "N/A", font=('Arial', 10)).grid(row=1,
                                                                                                          column=1,
                                                                                                          sticky='w',
                                                                                                          padx=10)

        ttk.Label(summary_grid, text="Consensus:", font=('Arial', 10, 'bold')).grid(row=1, column=2, sticky='w',
                                                                                    padx=10)
        consensus_valid = isinstance(consensus, float) and not math.isnan(consensus)
        ttk.Label(summary_grid, text=f"{consensus:.2f}" if consensus_valid else "N/A", font=('Arial', 10)).grid(row=1,
                                                                                                                column=3,
                                                                                                                sticky='w',
                                                                                                                padx=10)

        ttk.Label(summary_grid, text="Surprise:", font=('Arial', 10, 'bold')).grid(row=1, column=4, sticky='w', padx=10)
        if actual_valid and consensus_valid:
            surprise = actual - consensus
            surprise_color = self.colors['success'] if surprise > 0 else self.colors['danger']
            surprise_label = ttk.Label(summary_grid, text=f"{surprise:+.2f}", font=('Arial', 10, 'bold'),
                                       foreground=surprise_color)
        else:
            surprise_label = ttk.Label(summary_grid, text="N/A", font=('Arial', 10))
        surprise_label.grid(row=1, column=5, sticky='w', padx=10)

        # Quick stats
        metrics = compute_advanced_metrics(assets_data, window_min)

        stats_frame = ttk.LabelFrame(container, text="📊 Market Overview", padding=10)
        stats_frame.pack(fill='both', expand=True)

        # Create summary table
        tree = ttk.Treeview(stats_frame, columns=('Asset', 'Return %', 'Volatility %', 'Max DD %'), show='headings',
                            height=20)
        tree.heading('Asset', text='Asset')
        tree.heading('Return %', text='Return %')
        tree.heading('Volatility %', text='Volatility %')
        tree.heading('Max DD %', text='Max Drawdown %')

        tree.column('Asset', width=200)
        tree.column('Return %', width=150, anchor='center')
        tree.column('Volatility %', width=150, anchor='center')
        tree.column('Max DD %', width=150, anchor='center')

        for asset, m in sorted(metrics.items(), key=lambda x: abs(x[1]['return']), reverse=True):
            ret_color = 'green' if m['return'] > 0 else 'red'
            tree.insert('', 'end', values=(
                asset,
                f"{m['return']:.2f}%",
                f"{m['volatility']:.2f}%",
                f"{m['max_drawdown']:.2f}%"
            ), tags=(ret_color,))

        tree.tag_configure('green', foreground='darkgreen')
        tree.tag_configure('red', foreground='darkred')

        scrollbar = ttk.Scrollbar(stats_frame, orient='vertical', command=tree.yview)
        tree.configure(yscroll=scrollbar.set)

        tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

    def create_charts_tab(self, assets_data, window_min, event_date):
        """Create professional 2x2-grid charts with spacing for clarity"""
        import math

        container = ttk.Frame(self.charts_tab)
        container.pack(fill='both', expand=True)

        # Prepare metrics and data for charts
        metrics = compute_advanced_metrics(assets_data, window_min)
        sorted_vols = sorted(metrics.items(), key=lambda x: x[1]['volatility'], reverse=True)
        sorted_rets = sorted(metrics.items(), key=lambda x: x[1]['return'], reverse=True)
        price_data = pd.DataFrame({name: df[df.columns[0]] for name, df in list(assets_data.items())[:10]})
        corr = price_data.corr() if not price_data.empty else pd.DataFrame()

        fig, axs = plt.subplots(2, 2, figsize=(14, 10), dpi=100)
        fig.subplots_adjust(hspace=0.4, wspace=0.3, top=0.93, bottom=0.07, left=0.07, right=0.97)

        # Subplot 1: Price movement for first 4 assets
        ax1 = axs[0, 0]
        assets_to_plot = list(assets_data.keys())[:4]
        for asset in assets_to_plot:
            df = assets_data[asset]
            normalized = (df[df.columns[0]] / df[df.columns[0]].iloc[0] - 1) * 100
            ax1.plot(df.index, normalized, label=asset, linewidth=2)
        ax1.set_title('Top 4 Assets: % Change from Start', fontsize=11, fontweight='bold')
        ax1.set_ylabel('% Change', fontsize=9)
        ax1.legend(fontsize=8, loc='best')
        ax1.grid(True, alpha=0.3, linestyle='--')
        ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.5, alpha=0.5)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

        # Subplot 2: Volatility ranking
        ax2 = axs[0, 1]
        vol_assets = [x[0] for x in sorted_vols[:6]]
        vols = [x[1]['volatility'] for x in sorted_vols[:6]]
        colors_vol = sns.color_palette("rocket", len(vols))
        bars = ax2.barh(vol_assets, vols, color=colors_vol)
        ax2.set_xlabel('Volatility (%)', fontsize=9)
        ax2.set_title('Top 6 Volatility', fontsize=11, fontweight='bold')
        ax2.grid(True, axis='x', alpha=0.3, linestyle='--')
        for bar in bars:
            width = bar.get_width()
            ax2.text(width, bar.get_y() + bar.get_height() / 2, f'{width:.2f}%', va='center', ha='left', fontsize=8)

        # Subplot 3: Return ranking
        ax3 = axs[1, 0]
        ret_assets = [x[0] for x in sorted_rets[:6]]
        rets = [x[1]['return'] for x in sorted_rets[:6]]
        colors = ['green' if r > 0 else 'red' for r in rets]
        bars_ret = ax3.barh(ret_assets, rets, color=colors, alpha=0.7)
        ax3.set_xlabel('Return (%)', fontsize=9)
        ax3.set_title('Top 6 Returns', fontsize=11, fontweight='bold')
        ax3.grid(True, axis='x', alpha=0.3, linestyle='--')
        ax3.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
        for bar, ret in zip(bars_ret, rets):
            width = bar.get_width()
            ha = 'left' if ret > 0 else 'right'
            ax3.text(width + (0.5 if ret > 0 else -0.5), bar.get_y() + bar.get_height() / 2,
                     f'{ret:.2f}%', va='center', ha=ha, fontsize=8)

        # Subplot 4: Correlation heatmap
        ax4 = axs[1, 1]
        if not corr.empty:
            im = ax4.imshow(corr, cmap='RdYlGn', vmin=-1, vmax=1, aspect='auto')
            ax4.set_xticks(range(len(corr)))
            ax4.set_yticks(range(len(corr)))
            ax4.set_xticklabels(corr.columns, rotation=45, ha='right', fontsize=7)
            ax4.set_yticklabels(corr.index, fontsize=7)
            ax4.set_title('Correlation Matrix', fontsize=11, fontweight='bold')
            fig.colorbar(im, ax=ax4, fraction=0.05, pad=0.05)
        else:
            ax4.axis('off')
            ax4.set_title('No Data for Correlation', fontsize=11, fontweight='bold')

        # Canvas integration for Tkinter
        canvas = FigureCanvasTkAgg(fig, master=container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True, pady=10)

    def create_metrics_tab(self, assets_data, window_min):
        """Create detailed metrics tab"""
        container = ttk.Frame(self.metrics_tab, padding=15)
        container.pack(fill='both', expand=True)

        metrics = compute_advanced_metrics(assets_data, window_min)

        # Detailed metrics table
        tree = ttk.Treeview(
            container,
            columns=('Asset', 'Return', 'Vol', 'Sharpe', 'Max DD', 'High', 'Low', 'Change'),
            show='headings',
            height=25
        )

        headers = ['Asset', 'Return %', 'Volatility %', 'Sharpe', 'Max DD %', 'High', 'Low', 'Price Δ']
        for i, header in enumerate(headers):
            tree.heading(f'#{i + 1}', text=header)
            tree.column(f'#{i + 1}', width=120, anchor='center')

        tree.column('#1', width=180, anchor='w')

        for asset, m in sorted(metrics.items(), key=lambda x: x[0]):
            tree.insert('', 'end', values=(
                asset,
                f"{m['return']:.2f}%",
                f"{m['volatility']:.3f}%",
                f"{m['sharpe']:.2f}",
                f"{m['max_drawdown']:.2f}%",
                f"{m['high']:.2f}",
                f"{m['low']:.2f}",
                f"{m['price_change']:.2f}"
            ))

        scrollbar = ttk.Scrollbar(container, orient='vertical', command=tree.yview)
        tree.configure(yscroll=scrollbar.set)

        tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

    def create_data_tab(self, assets_data, fetch_log):
        """Create raw data tab"""
        container = ttk.Frame(self.data_tab, padding=15)
        container.pack(fill='both', expand=True)

        # Fetch log
        log_frame = ttk.LabelFrame(container, text="📋 Data Fetch Log", padding=10)
        log_frame.pack(fill='both', expand=True)

        log_text = scrolledtext.ScrolledText(log_frame, height=30, width=120, font=('Courier', 9))
        log_text.pack(fill='both', expand=True)

        for line in fetch_log:
            log_text.insert(tk.END, line + '\n')



if __name__ == "__main__":
    root = tk.Tk()
    app = ProfessionalMacroTrackerApp(root)
    root.mainloop()

