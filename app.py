import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import re

st.set_page_config(page_title="Pro Monthly Breakout Platform", layout="wide")

st.title("🕯️ Pro Monthly Breakout Platform")
st.caption(
    "Setup: Consecutive Red Months -> 1 Green Month -> Buy Breakout. "
    "Execution Engine: Daily Data with Gap Modeling, Regime Tracking & 12-Month Low Capitulation Filtering."
)

# ==========================================
# ROBUST UNIVERSE SCRAPERS & DATA LOADERS
# ==========================================

DJIA_STATIC_FALLBACK = [
    "AAPL", "AMZN", "AXP", "BA", "CAT", "CRM", "CSCO", "CVX", "DIS", "GS",
    "HD", "HON", "IBM", "INTC", "JNJ", "JPM", "KO", "MCD", "MMM", "MRK",
    "MSFT", "NKE", "NVDA", "PG", "SHW", "TRV", "UNH", "V", "VZ", "WMT"
]

NASDAQ100_STATIC_FALLBACK = [
    "AAPL", "ABNB", "ADBE", "ADI", "ADP", "ADSK", "AEP", "AMAT", "AMD", "AMGN",
    "AMZN", "ANSS", "ASML", "AVGO", "AZN", "BIIB", "BKNG", "BKR", "CDNS", "CEG",
    "CHTR", "CMCSA", "COST", "CPRT", "CRWD", "CSCO", "CSGP", "CSX", "CTAS", "CTSH",
    "DASH", "DDOG", "DLTR", "DXCM", "EA", "EXC", "FANG", "FAST", "FTNT", "GEHC",
    "GFS", "GILD", "GOOG", "GOOGL", "HON", "IDXX", "ILMN", "INTC", "INTU", "ISRG",
    "KDP", "KHC", "KLAC", "LRCX", "LULU", "MAR", "MCHP", "MDLZ", "MELI", "META",
    "MNDZ", "MNST", "MRNA", "MRVL", "MSFT", "MU", "NFLX", "NVDA", "NXPI", "ODFL",
    "ON", "ORLY", "PANW", "PAYX", "PCAR", "PDD", "PEP", "PYPL", "QCOM", "REGN",
    "ROP", "ROST", "SBUX", "SNPS", "SPLK", "TEAM", "TMUS", "TSLA", "TTD", "TTWO",
    "TXN", "VRSK", "VRTX", "WBA", "WBD", "WDAY", "XEL", "ZS"
]

@st.cache_data(show_spinner=False, ttl=86400)
def get_universe_tickers(universe_name):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    def clean_ticker_list(raw_list):
        cleaned = []
        for sym in raw_list:
            if pd.isna(sym):
                continue
            s = str(sym).strip().upper().replace('.', '-')
            if re.match(r'^[A-Z]{1,5}(-[A-Z]{1,2})?$', s):
                cleaned.append(s)
        return list(dict.fromkeys(cleaned))

    def extract_wiki_symbols(url):
        try:
            resp = requests.get(url, headers=headers, timeout=12)
            if resp.status_code == 200:
                tables = pd.read_html(resp.text)
                for df in tables:
                    for col in ['Symbol', 'Ticker', 'Ticker symbol']:
                        if col in df.columns:
                            return clean_ticker_list(df[col].dropna().tolist())
        except Exception:
            pass
        return []

    if universe_name == "S&P 500":
        tickers = extract_wiki_symbols("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
        if not tickers:
            try:
                fallback_url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
                df_fallback = pd.read_csv(fallback_url)
                tickers = clean_ticker_list(df_fallback['Symbol'].tolist())
            except Exception:
                pass
        return tickers

    elif universe_name == "Russell 1000":
        tickers = extract_wiki_symbols("https://en.wikipedia.org/wiki/List_of_Russell_1000_companies")
        if not tickers:
            try:
                tickers = extract_wiki_symbols("https://en.wikipedia.org/wiki/Russell_1000_Index")
            except Exception:
                pass
        return tickers

    elif universe_name == "Nasdaq 100":
        tickers = extract_wiki_symbols("https://en.wikipedia.org/wiki/Nasdaq-100")
        if not tickers:
            tickers = extract_wiki_symbols("https://en.wikipedia.org/wiki/List_of_NASDAQ-100_companies")
        return tickers if tickers else NASDAQ100_STATIC_FALLBACK

    elif universe_name == "Dow Jones 30":
        tickers = extract_wiki_symbols("https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average")
        return tickers if tickers else DJIA_STATIC_FALLBACK

    elif universe_name == "US Broad Market (~2,500+ Stocks)":
        sp500 = get_universe_tickers("S&P 500")
        sp400 = extract_wiki_symbols("https://en.wikipedia.org/wiki/List_of_S%26P_400_companies")
        sp600 = extract_wiki_symbols("https://en.wikipedia.org/wiki/List_of_S%26P_600_companies")
        r1000 = get_universe_tickers("Russell 1000")
        combined = list(dict.fromkeys(sp500 + sp400 + sp600 + r1000))
        return clean_ticker_list(combined)

    elif universe_name == "Major ADRs":
        return [
            "TSM", "NVO", "ASML", "BABA", "TM", "AZN", "BHP", "SAP", "SHEL", "NVS",
            "SONY", "HDB", "TTE", "SNY", "BTI", "RY", "TD", "UBS", "RIO", "IBN",
            "MUFG", "INFY", "BP", "RELX", "CP", "MFG", "ITUB", "CNI", "GSK", "PBR",
            "VALE", "SAN", "ERIC", "NOK", "BIDU", "JD", "PDD", "MELI", "SHOP", "SE"
        ]

    elif universe_name == "Major ETFs":
        return [
            "SPY", "QQQ", "DIA", "IWM", "VTI", "VOO", "VEA", "VWO", 
            "GLD", "SLV", "USO", "UNG", "TLT", "IEF", "SHY",
            "XLF", "XLE", "XLK", "XLV", "XLY", "XLI", "XLP", "XLU", "XLB", "XLRE",
            "ARKK", "SMH", "KRE", "XBI", "ITB"
        ]

    return []

@st.cache_data(show_spinner=False)
def fetch_daily_data(symbol, start=None, end=None, period=None):
    if period:
        daily = yf.download(symbol, period=period, auto_adjust=False, progress=False)
    else:
        daily = yf.download(symbol, start=start, end=end, auto_adjust=False, progress=False)
        
    if daily.empty:
        return None
    if isinstance(daily.columns, pd.MultiIndex):
        daily.columns = [col[0] for col in daily.columns]
    return daily

def build_monthly_from_daily(daily_df):
    monthly = daily_df.resample('ME').agg({
        'Open': 'first', 'High': 'max', 'Low': 'min',
        'Close': 'last', 'Adj Close': 'last', 'Volume': 'sum'
    }).dropna()
    
    monthly['SMA_12'] = monthly['Close'].rolling(window=12).mean()
    monthly['Close_Min_12'] = monthly['Close'].rolling(window=12).min()
    
    monthly['is_bear'] = monthly['Close'] < monthly['Open']
    red_streaks = []
    current_streak = 0
    for is_bear in monthly['is_bear']:
        if is_bear:
            current_streak += 1
        else:
            current_streak = 0
        red_streaks.append(current_streak)
    monthly['red_streak_count'] = red_streaks
    
    return monthly

@st.cache_data(show_spinner=False)
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# ==========================================
# BACKTEST EXECUTION ENGINE
# ==========================================

def run_daily_execution_backtest(daily_df, monthly_df, exit_type, hold_n, tick_size, init_cash, trade_after_loss_only=False, require_uptrend=False, require_12m_low_red=False):
    setups = {}
    monthly_stats = {}
    
    for i in range(1, len(monthly_df) - 1):
        t1 = monthly_df.iloc[i]       # Signal month (Green)
        t2 = monthly_df.iloc[i-1]     # Prior month (Red)
        ym = t1.name.strftime('%Y-%m')
        monthly_stats[ym] = {'is_bear': t1['is_bear'], 'low': t1['Low']}
        
        prior_red_streak = monthly_df['red_streak_count'].iloc[i-1]
        setup_valid = (prior_red_streak >= 1) and (not t1['is_bear'])
        
        # 1. 12-Month Low Capitulation Filter on preceding red bar
        if require_12m_low_red:
            if pd.isna(monthly_df['Close_Min_12'].iloc[i-1]):
                setup_valid = False
            elif t2['Close'] > (monthly_df['Close_Min_12'].iloc[i-1] + 1e-4):
                setup_valid = False

        # 2. Long-Term Trend Filter
        if require_uptrend and not pd.isna(t1['SMA_12']):
            if t1['Close'] <= t1['SMA_12']:
                setup_valid = False
                
        if setup_valid:
            exec_ym = (t1.name + pd.DateOffset(days=15)).strftime('%Y-%m') 
            setups[exec_ym] = {
                'prior_reds': prior_red_streak,
                'trigger': t1['High'] + tick_size,
                'stop': t1['Low'] - tick_size,
                'width': t1['High'] - t1['Low']
            }
            
    final_ym = monthly_df.index[-1].strftime('%Y-%m')
    monthly_stats[final_ym] = {'is_bear': monthly_df.iloc[-1]['is_bear'], 'low': monthly_df.iloc[-1]['Low']}

    daily_df = daily_df.copy()
    daily_df['ym'] = daily_df.index.strftime('%Y-%m')
    last_trading_days = {ym: grp.index.max() for ym, grp in daily_df.groupby('ym')}

    all_phantom_trades = []
    in_trade = False
    handled_setups_for_month = set()

    target_mult = None
    if "Target: 2x" in exit_type: target_mult = 2.0
    elif "Target: 3x" in exit_type: target_mult = 3.0
    elif "Target: 5x" in exit_type: target_mult = 5.0
    elif "Target: 10x" in exit_type: target_mult = 10.0

    for date, row in daily_df.iterrows():
        ym = row['ym']
        
        if in_trade:
            if ym != current_ym:
                months_held += 1
                current_ym = ym
                
            exit_hit, exit_px, reason = False, 0.0, ""
            
            # Stop Loss Check
            if row['Low'] <= stop_price:
                exit_hit, reason = True, "Stop Loss"
                exit_px = min(row['Open'], stop_price)
                
            # Target Check
            elif target_price and row['High'] >= target_price:
                exit_hit, reason = True, "Target Hit"
                exit_px = max(row['Open'], target_price)
                
            # Breakdown of Prior Month Low
            elif exit_type == "Prior Month Low Breakdown":
                prior_ym = (date.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
                if prior_ym in monthly_stats and row['Low'] < monthly_stats[prior_ym]['low']:
                    exit_hit, reason = True, "Prior Low Break"
                    exit_px = min(row['Open'], monthly_stats[prior_ym]['low'] - 0.01)
                    
            # End of Month Exits
            elif date == last_trading_days.get(ym):
                if exit_type == "First Red Month" and monthly_stats[ym]['is_bear']:
                    exit_hit, exit_px, reason = True, row['Close'], "1st Red Month"
                elif exit_type == "2 Consecutive Red Months":
                    prior_ym = (date.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
                    if monthly_stats[ym]['is_bear'] and monthly_stats.get(prior_ym, {}).get('is_bear', False):
                        exit_hit, exit_px, reason = True, row['Close'], "2 Cons Red"
                elif exit_type == "Hold Fixed Months" and months_held >= hold_n:
                    exit_hit, exit_px, reason = True, row['Close'], f"Held {hold_n} Mos"

            if exit_hit:
                adj_ratio_entry = entry_adj_close / entry_raw_close
                adj_ratio_exit = row['Adj Close'] / row['Close']
                trade_ret = ((exit_px * adj_ratio_exit) - (entry_price * adj_ratio_entry)) / (entry_price * adj_ratio_entry)
                
                all_phantom_trades.append({
                    "Prior Red Months": active_prior_reds,
                    "Entry Date": entry_date.strftime('%Y-%m-%d'), "Entry Price": round(entry_price, 2),
                    "Exit Date": date.strftime('%Y-%m-%d'), "Exit Price": round(exit_px, 2),
                    "Exit Reason": reason, "Return (%)": round(trade_ret * 100, 2),
                    "Months Held": months_held, "Result": "Win" if trade_ret > 0 else "Loss"
                })
                in_trade = False

        if not in_trade:
            if ym in setups and ym not in handled_setups_for_month:
                setup = setups[ym]
                if row['High'] >= setup['trigger']:
                    in_trade = True
                    handled_setups_for_month.add(ym)
                    
                    entry_date = date
                    current_ym = ym
                    months_held = 0
                    
                    active_prior_reds = setup['prior_reds']
                    stop_price = setup['stop']
                    entry_price = max(row['Open'], setup['trigger'])
                    entry_raw_close = row['Close']
                    entry_adj_close = row['Adj Close']
                    target_price = entry_price + (target_mult * setup['width']) if target_mult else None
                    
                    # Same-day intra-day checks
                    if row['Low'] <= stop_price:
                        exit_px = min(row['Open'], stop_price)
                        adj_ratio_entry = entry_adj_close / entry_raw_close
                        adj_ratio_exit = row['Adj Close'] / row['Close']
                        trade_ret = ((exit_px * adj_ratio_exit) - (entry_price * adj_ratio_entry)) / (entry_price * adj_ratio_entry)
                        
                        all_phantom_trades.append({
                            "Prior Red Months": active_prior_reds,
                            "Entry Date": entry_date.strftime('%Y-%m-%d'), "Entry Price": round(entry_price, 2),
                            "Exit Date": date.strftime('%Y-%m-%d'), "Exit Price": round(exit_px, 2),
                            "Exit Reason": "Stop Loss (Same Day)", "Return (%)": round(trade_ret * 100, 2),
                            "Months Held": 0, "Result": "Win" if trade_ret > 0 else "Loss"
                        })
                        in_trade = False
                    elif target_price and row['High'] >= target_price:
                        exit_px = max(row['Open'], target_price)
                        adj_ratio_entry = entry_adj_close / entry_raw_close
                        adj_ratio_exit = row['Adj Close'] / row['Close']
                        trade_ret = ((exit_px * adj_ratio_exit) - (entry_price * adj_ratio_entry)) / (entry_price * adj_ratio_entry)
                        
                        all_phantom_trades.append({
                            "Prior Red Months": active_prior_reds,
                            "Entry Date": entry_date.strftime('%Y-%m-%d'), "Entry Price": round(entry_price, 2),
                            "Exit Date": date.strftime('%Y-%m-%d'), "Exit Price": round(exit_px, 2),
                            "Exit Reason": "Target Hit (Same Day)", "Return (%)": round(trade_ret * 100, 2),
                            "Months Held": 0, "Result": "Win" if trade_ret > 0 else "Loss"
                        })
                        in_trade = False

    final_account_trades = []
    if trade_after_loss_only and len(all_phantom_trades) > 0:
        for i in range(1, len(all_phantom_trades)):
            if all_phantom_trades[i-1]['Result'] == 'Loss':
                final_account_trades.append(all_phantom_trades[i])
    else:
        final_account_trades = all_phantom_trades

    trades_df = pd.DataFrame(final_account_trades)
    bh_ret = ((daily_df['Adj Close'].iloc[-1] / daily_df['Adj Close'].iloc[0]) - 1) * 100

    if trades_df.empty:
        eq = pd.Series([init_cash], index=[daily_df.index[0]])
        return trades_df, {"Win Rate (%)": 0, "Total Return (%)": 0, "B&H Return (%)": bh_ret, "Max Drawdown (%)": 0}, eq, eq
    
    win_rate = (len(trades_df[trades_df['Result'] == 'Win']) / len(trades_df)) * 100
    comp_ret = ((1 + trades_df['Return (%)'] / 100).prod() - 1) * 100
    
    eq_series = init_cash * (1 + trades_df['Return (%)'] / 100).cumprod()
    eq_series.index = pd.to_datetime(trades_df['Exit Date'])
    drawdowns = (eq_series - eq_series.cummax()) / eq_series.cummax()
    max_dd = drawdowns.min() * 100
    
    gross_prof = trades_df[trades_df['Result'] == 'Win']['Return (%)'].sum()
    gross_loss = abs(trades_df[trades_df['Result'] == 'Loss']['Return (%)'].sum())
    prof_factor = round(gross_prof / gross_loss, 2) if gross_loss > 0 else np.nan

    metrics = {
        "Trades":
