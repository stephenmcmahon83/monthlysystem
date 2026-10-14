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
    "Universal Monthly Engine: Parametric Sequences (Red Reversals & Green Momentum) | "
    "Decoupled Stops (T-1, T-2, Streak Base, ATR) | Daily Precision with Gap Modeling."
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
            if pd.isna(sym): continue
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
    if daily.empty: return None
    if isinstance(daily.columns, pd.MultiIndex):
        daily.columns = [col[0] for col in daily.columns]
    return daily

def extract_symbol_daily(bulk_data, sym, universe_size):
    try:
        if universe_size == 1:
            df = bulk_data.copy()
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] for c in df.columns]
            return df.dropna(how='all')
        if not isinstance(bulk_data.columns, pd.MultiIndex):
            return pd.DataFrame()
        if sym in bulk_data.columns.levels[0]:
            return bulk_data[sym].copy().dropna(how='all')
        elif sym in bulk_data.columns.levels[1]:
            return bulk_data.xs(sym, axis=1, level=1).copy().dropna(how='all')
    except Exception:
        pass
    return pd.DataFrame()

def build_monthly_from_daily(daily_df):
    monthly = daily_df.resample('ME').agg({
        'Open': 'first', 'High': 'max', 'Low': 'min',
        'Close': 'last', 'Adj Close': 'last', 'Volume': 'sum'
    }).dropna()
    
    monthly['SMA_12'] = monthly['Close'].rolling(window=12).mean()
    monthly['Close_Min_12'] = monthly['Close'].rolling(window=12).min()
    monthly['Close_Min_6'] = monthly['Close'].rolling(window=6).min()
    
    monthly['prev_close'] = monthly['Close'].shift(1)
    tr1 = monthly['High'] - monthly['Low']
    tr2 = (monthly['High'] - monthly['prev_close']).abs()
    tr3 = (monthly['Low'] - monthly['prev_close']).abs()
    monthly['TR'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    monthly['ATR_12'] = monthly['TR'].rolling(window=12).mean()
    
    monthly['is_bear'] = monthly['Close'] < monthly['Open']
    monthly['is_bull'] = monthly['Close'] > monthly['Open']
    
    red_streaks, green_streaks = [], []
    r_curr, g_curr = 0, 0
    for _, row in monthly.iterrows():
        if row['is_bear']:
            r_curr += 1
            g_curr = 0
        elif row['is_bull']:
            g_curr += 1
            r_curr = 0
        else:
            r_curr = 0
            g_curr = 0
        red_streaks.append(r_curr)
        green_streaks.append(g_curr)
        
    monthly['red_streak_count'] = red_streaks
    monthly['green_streak_count'] = green_streaks
    return monthly

@st.cache_data(show_spinner=False)
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# ==========================================
# UNIFIED BACKTEST EXECUTION ENGINE
# ==========================================

def run_daily_execution_backtest(daily_df, monthly_df, seq_type, min_streak, signal_color,
                                stop_rule, exit_type, hold_n, tick_size, init_cash,
                                trade_after_loss_only=False, require_uptrend=False,
                                capitulation_filter="None", require_lower_high=False):
    setups = {}
    monthly_stats = {}
    
    for i in range(2, len(monthly_df) - 1):
        t1 = monthly_df.iloc[i]       # Signal month (T-1)
        t2 = monthly_df.iloc[i-1]     # Prior month (T-2)
        ym = t1.name.strftime('%Y-%m')
        monthly_stats[ym] = {'is_bear': t1['is_bear'], 'low': t1['Low'], 'high': t1['High']}
        
        # 1. Preceding Streak Check (T-2 backwards)
        prior_streak = monthly_df['red_streak_count'].iloc[i-1] if "Red" in seq_type else monthly_df['green_streak_count'].iloc[i-1]
        if prior_streak < min_streak:
            continue
            
        # 2. Signal Bar Color
        if signal_color == "Green Only" and not t1['is_bull']:
            continue
        elif signal_color == "Red Only" and not t1['is_bear']:
            continue
            
        # 3. Lower High Constraint (T-1 High < T-2 High)
        if require_lower_high and (t1['High'] >= t2['High']):
            continue

        # 4. Capitulation Tag / Filter on Prior Month (T-2)
        is_12m = False
        is_6m = False
        if not pd.isna(monthly_df['Close_Min_12'].iloc[i-1]):
            is_12m = t2['Close'] <= (monthly_df['Close_Min_12'].iloc[i-1] + 1e-4)
        if not pd.isna(monthly_df['Close_Min_6'].iloc[i-1]):
            is_6m = t2['Close'] <= (monthly_df['Close_Min_6'].iloc[i-1] + 1e-4)

        cap_tag = "12-Month" if is_12m else ("6-Month" if is_6m else "None")
        if capitulation_filter == "12-Month Low" and not is_12m:
            continue
        elif capitulation_filter == "6-Month Low" and not is_6m:
            continue

        # 5. Bull Market SMA12 Trend Filter
        if require_uptrend and not pd.isna(t1['SMA_12']) and t1['Close'] <= t1['SMA_12']:
            continue

        trigger_price = round(t1['High'] + tick_size, 2)
        atr_12 = monthly_df['ATR_12'].iloc[i] if not pd.isna(monthly_df['ATR_12'].iloc[i]) else (t1['High'] - t1['Low'])

        # 6. Stop-Loss Selection
        if stop_rule == "Signal Month Low (T-1 Low)":
            stop_price = round(t1['Low'] - tick_size, 2)
        elif stop_rule == "Prior Month Low (T-2 Low)":
            stop_price = round(t2['Low'] - tick_size, 2)
        elif stop_rule == "Lowest Low of Streak":
            lookback = min(i, prior_streak + 1)
            stop_price = round(monthly_df['Low'].iloc[i-lookback:i].min() - tick_size, 2)
        elif stop_rule == "1x 12M ATR Stop":
            stop_price = max(0.01, round(trigger_price - (1.0 * atr_12), 2))
        else:
            stop_price = round(t1['Low'] - tick_size, 2)

        risk_unit = trigger_price - stop_price
        if risk_unit <= 0:
            continue

        exec_ym = (t1.name + pd.DateOffset(days=15)).strftime('%Y-%m')
        setups[exec_ym] = {
            'streak': prior_streak,
            'capitulation': cap_tag,
            'trigger': trigger_price,
            'stop': stop_price,
            'risk_unit': risk_unit,
            'width': t1['High'] - t1['Low'],
            'atr': atr_12
        }

    final_ym = monthly_df.index[-1].strftime('%Y-%m')
    monthly_stats[final_ym] = {'is_bear': monthly_df.iloc[-1]['is_bear'], 'low': monthly_df.iloc[-1]['Low'], 'high': monthly_df.iloc[-1]['High']}

    daily_df = daily_df.copy()
    daily_df['ym'] = daily_df.index.strftime('%Y-%m')
    last_trading_days = {ym: grp.index.max() for ym, grp in daily_df.groupby('ym')}

    all_phantom_trades = []
    in_trade = False
    handled_setups_for_month = set()

    current_ym = None
    months_held = 0
    active_streak = 0
    active_cap_tag = "None"
    entry_date = None
    entry_price = 0.0
    entry_raw_close = 1.0
    entry_adj_close = 1.0
    stop_price = 0.0
    target_price = None
    active_risk_unit = 1.0

    # Parse target multiple
    is_atr_exit = "ATR Target" in exit_type
    target_mult = None
    if "1x" in exit_type: target_mult = 1.0
    elif "2x" in exit_type: target_mult = 2.0
    elif "3x" in exit_type: target_mult = 3.0
    elif "5x" in exit_type: target_mult = 5.0
    elif "10x" in exit_type: target_mult = 10.0

    for date, row in daily_df.iterrows():
        ym = row['ym']
        
        if in_trade:
            if ym != current_ym:
                months_held += 1
                current_ym = ym
                
            exit_hit, exit_px, reason = False, 0.0, ""
            
            # Intraday Stop Loss
            if row['Low'] <= stop_price:
                exit_hit, reason = True, "Stop Loss"
                exit_px = min(row['Open'], stop_price)
                
            # Intraday Target Multiple
            elif target_price and row['High'] >= target_price:
                exit_hit, reason = True, f"Target {target_mult}R"
                exit_px = max(row['Open'], target_price)
                
            # Prior Month Low Breakdown
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
                r_realized = (exit_px - entry_price) / active_risk_unit if active_risk_unit > 0 else 0
                
                all_phantom_trades.append({
                    "Streak": active_streak,
                    "Capitulation": active_cap_tag,
                    "Entry Date": entry_date.strftime('%Y-%m-%d'),
                    "Entry Price": round(entry_price, 2),
                    "Stop Price": round(stop_price, 2),
                    "Exit Date": date.strftime('%Y-%m-%d'),
                    "Exit Price": round(exit_px, 2),
                    "Exit Reason": reason,
                    "Return (%)": round(trade_ret * 100, 2),
                    "Realized R": round(r_realized, 2),
                    "Months Held": months_held,
                    "Result": "Win" if trade_ret > 0 else "Loss"
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
                    
                    active_streak = setup['streak']
                    active_cap_tag = setup['capitulation']
                    entry_price = max(row['Open'], setup['trigger'])
                    entry_raw_close = row['Close']
                    entry_adj_close = row['Adj Close']
                    stop_price = setup['stop']
                    active_risk_unit = setup['risk_unit']
                    
                    # Target Calculation
                    if is_atr_exit:
                        target_price = round(entry_price + (target_mult * setup['atr']), 2) if target_mult else None
                    elif target_mult:
                        target_price = round(entry_price + (target_mult * active_risk_unit), 2)
                    else:
                        target_price = None
                    
                    # Same-day intra-day checks
                    if row['Low'] <= stop_price:
                        exit_px = min(row['Open'], stop_price)
                        adj_ratio_entry = entry_adj_close / entry_raw_close
                        adj_ratio_exit = row['Adj Close'] / row['Close']
                        trade_ret = ((exit_px * adj_ratio_exit) - (entry_price * adj_ratio_entry)) / (entry_price * adj_ratio_entry)
                        
                        all_phantom_trades.append({
                            "Streak": active_streak,
                            "Capitulation": active_cap_tag,
                            "Entry Date": entry_date.strftime('%Y-%m-%d'),
                            "Entry Price": round(entry_price, 2),
                            "Stop Price": round(stop_price, 2),
                            "Exit Date": date.strftime('%Y-%m-%d'),
                            "Exit Price": round(exit_px, 2),
                            "Exit Reason": "Stop Loss (Same Day)",
                            "Return (%)": round(trade_ret * 100, 2),
                            "Realized R": -1.0,
                            "Months Held": 0,
                            "Result": "Loss"
                        })
                        in_trade = False
                    elif target_price and row['High'] >= target_price:
                        exit_px = max(row['Open'], target_price)
                        adj_ratio_entry = entry_adj_close / entry_raw_close
                        adj_ratio_exit = row['Adj Close'] / row['Close']
                        trade_ret = ((exit_px * adj_ratio_exit) - (entry_price * adj_ratio_entry)) / (entry_price * adj_ratio_entry)
                        
                        all_phantom_trades.append({
                            "Streak": active_streak,
                            "Capitulation": active_cap_tag,
                            "Entry Date": entry_date.strftime('%Y-%m-%d'),
                            "Entry Price": round(entry_price, 2),
                            "Stop Price": round(stop_price, 2),
                            "Exit Date": date.strftime('%Y-%m-%d'),
                            "Exit Price": round(exit_px, 2),
                            "Exit Reason": "Target Hit (Same Day)",
                            "Return (%)": round(trade_ret * 100, 2),
                            "Realized R": target_mult if target_mult else 1.0,
                            "Months Held": 0,
                            "Result": "Win" if trade_ret > 0 else "Loss"
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
        return trades_df, {"Trades": 0, "Win Rate (%)": 0, "Total Return (%)": 0, "B&H Return (%)": bh_ret, "Profit Factor": np.nan, "Max Drawdown (%)": 0, "Avg R Realized": 0}, eq, eq
    
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
        "Trades": len(trades_df),
        "Win Rate (%)": round(win_rate, 1),
        "Total Return (%)": round(comp_ret, 1),
        "B&H Return (%)": round(bh_ret, 1),
        "Profit Factor": prof_factor,
        "Avg Hold (Mo)": round(trades_df['Months Held'].mean(), 1),
        "Max Drawdown (%)": round(max_dd, 1),
        "Avg R Realized": round(trades_df['Realized R'].mean(), 2)
    }
    return trades_df, metrics, eq_series, drawdowns

# ==========================================
# USER INTERFACE LAYOUT
# ==========================================
tab_backtest, tab_scanner = st.tabs(["📊 Deep Backtester", "📡 Live Market Scanner"])

# --- SIDEBAR CONFIGURATION ---
st.sidebar.header("1. Asset & Historical Scope")
ticker = st.sidebar.text_input("Ticker Symbol", value="SPY", key="bt_ticker").upper().strip()
col1, col2 = st.sidebar.columns(2)
today = datetime.now().date()
start_date = col1.date_input("Start", value=today - timedelta(days=25 * 365), key="bt_start")
end_date = col2.date_input("End", value=today, key="bt_end")

st.sidebar.header("2. Preceding Sequence Setup")
seq_type = st.sidebar.selectbox(
    "Sequence Type", 
    ["Red Months (Mean-Reversion)", "Green Months (Trend-Continuation)"], 
    key="sb_seq_type"
)
min_streak = st.sidebar.number_input("Min Preceding Months (X)", min_value=1, max_value=12, value=2, key="sb_min_streak")
signal_color = st.sidebar.selectbox("Signal Bar (T-1) Color", ["Green Only", "Any Color", "Red Only"], index=0, key="sb_sig_col")

st.sidebar.header("3. Risk & Stop-Loss Architecture")
stop_rule = st.sidebar.selectbox(
    "Stop-Loss Definition",
    [
        "Prior Month Low (T-2 Low)", 
        "Signal Month Low (T-1 Low)", 
        "Lowest Low of Streak", 
        "1x 12M ATR Stop"
    ],
    index=0,
    key="sb_stop_rule",
    help="Sets the initial protective stop-loss and establishes the unit of risk (1R = Trigger - Stop)."
)

st.sidebar.header("4. Strategy Exit Rules")
exit_options = [
    "Compare All Exits",
    "Target: 1x Risk Unit (1R)",
    "Target: 2x Risk Unit (2R)",
    "Target: 3x Risk Unit (3R)",
    "Target: 5x Risk Unit (5R)",
    "Target: 10x Risk Unit (10R)",
    "ATR Target: 2x ATR",
    "ATR Target: 3x ATR",
    "ATR Target: 5x ATR",
    "First Red Month",
    "2 Consecutive Red Months",
    "Hold Fixed Months",
    "Prior Month Low Breakdown"
]
exit_mode = st.sidebar.selectbox("Exit Rule", options=exit_options, index=3, key="bt_exit") # Default to 3R
hold_months_n = st.sidebar.number_input("Hold Duration (Months)", value=5, key="bt_hold") if "Hold" in exit_mode or exit_mode == "Compare All Exits" else 5

with st.sidebar.expander("⚙️ Advanced Regime Filters & Sizing", expanded=False):
    tick_size = st.number_input("Breakout Tick Size ($)", min_value=0.01, value=0.01, key="bt_tick")
    init_cash = st.number_input("Starting Capital ($)", value=10000, key="bt_cash")
    require_lower_high = st.checkbox(
        "Contained Setup: Signal High < Prior Month High", 
        value=False, 
        help="Ensures the green signal month hasn't already broken out over the prior month's high."
    )
    capitulation_filter = st.selectbox(
        "Capitulation Filter (Prior Red Close)", 
        options=["None", "6-Month Low", "12-Month Low"],
        index=0,
        help="Filters for trades where the last red bar closed at a 6-month or 12-month low."
    )
    require_uptrend = st.checkbox(
        "Bull Market Filter (Close > 12-Month SMA)", 
        value=False, 
        help="Avoids taking breakouts during secular bear markets."
    )
    trade_after_loss_only = st.checkbox(
        "Regime Filter (Only trade if prior trade lost)", 
        value=False
    )

# ----------------- BACKTESTER TAB -----------------
with tab_backtest:
    trade_col_config = {
        "Streak": st.column_config.NumberColumn(help="Preceding sequence streak count.", format="%d"),
        "Capitulation": st.column_config.TextColumn(help="Capitulation depth: 12-Month, 6-Month, or None."),
        "Entry Date": st.column_config.TextColumn(help="Date filled during regular market hours."),
        "Entry Price": st.column_config.NumberColumn(help="Fill price (Trigger price or open gap).", format="$%.2f"),
        "Stop Price": st.column_config.NumberColumn(help="Assigned protective stop-loss.", format="$%.2f"),
        "Exit Date": st.column_config.TextColumn(help="Date closed by system rule."),
        "Exit Price": st.column_config.NumberColumn(help="Exit fill price.", format="$%.2f"),
        "Exit Reason": st.column_config.TextColumn(help="Order condition that closed trade."),
        "Return (%)": st.column_config.NumberColumn(help="Split & dividend adjusted return.", format="%.2f%%"),
        "Realized R": st.column_config.NumberColumn(help="Realized return divided by initial 1R risk.", format="%+.2fR"),
        "Months Held": st.column_config.NumberColumn(help="Duration in calendar months.", format="%d"),
        "Result": st.column_config.TextColumn(help="Trade outcome: Win or Loss.")
    }

    if st.sidebar.button("Run Backtest", type="primary", use_container_width=True):
        df_daily = fetch_daily_data(ticker, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
        if df_daily is None:
            st.error("No data found. Check ticker and date range.")
        else:
            df_monthly = build_monthly_from_daily(df_daily)
            
            if exit_mode == "Compare All Exits":
                variants = exit_options[1:]
                comp_rows, curves = [], {}
                with st.spinner("Simulating all strategy variations..."):
                    for strat in variants:
                        t_df, m, eq, _ = run_daily_execution_backtest(
                            df_daily, df_monthly, seq_type, min_streak, signal_color,
                            stop_rule, strat, hold_months_n, tick_size, init_cash,
                            trade_after_loss_only, require_uptrend, capitulation_filter, require_lower_high
                        )
                        curves[strat] = eq
                        row = {"Exit Strategy": strat}
                        row.update(m)
                        comp_rows.append(row)
                
                st.subheader(f"📊 Strategy Comparison Across Exits for {ticker}")
                st.dataframe(pd.DataFrame(comp_rows).set_index("Exit Strategy"), use_container_width=True)
                
                fig = go.Figure()
                for label, curve in curves.items():
                    fig.add_trace(go.Scatter(y=curve.values, mode='lines', name=label))
                fig.update_layout(title="Equity Compounding Across Strategies", template="plotly_dark", hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True)
            else:
                with st.spinner(f"Running daily execution backtest for {ticker}..."):
                    t_df, metrics, eq, dd = run_daily_execution_backtest(
                        df_daily, df_monthly, seq_type, min_streak, signal_color,
                        stop_rule, exit_mode, hold_months_n, tick_size, init_cash,
                        trade_after_loss_only, require_uptrend, capitulation_filter, require_lower_high
                    )
                
                c1, c2, c3, c4, c5, c6 = st.columns(6)
                c1.metric("Strategy Return", f"{metrics.get('Total Return (%)', 0):,.2f}%")
                c2.metric("Buy & Hold Return", f"{metrics.get('B&H Return (%)', 0):,.2f}%")
                c3.metric("Win Rate", f"{metrics.get('Win Rate (%)', 0):.1f}%")
                c4.metric("Profit Factor", f"{metrics.get('Profit Factor', 0)}")
                c5.metric("Avg Realized R", f"{metrics.get('Avg R Realized', 0):+.2f}R")
                c6.metric("Max Drawdown", f"{metrics.get('Max Drawdown (%)', 0):.1f}%")
                
                col_chart1, col_chart2 = st.columns(2)
                with col_chart1:
                    fig_eq = go.Figure()
                    fig_eq.add_trace(go.Scatter(x=eq.index, y=eq.values, mode='lines+markers', name='Equity', line=dict(color='#00FF66')))
                    fig_eq.update_layout(title="Account Equity ($)", template="plotly_dark", margin=dict(l=20, r=20, t=40, b=20))
                    st.plotly_chart(fig_eq, use_container_width=True)
                with col_chart2:
                    fig_dd = go.Figure()
                    fig_dd.add_trace(go.Scatter(x=dd.index, y=dd.values * 100, fill='tozeroy', mode='lines', name='Drawdown', line=dict(color='#FF3366')))
                    fig_dd.update_layout(title="Historical Drawdown (%)", template="plotly_dark", margin=dict(l=20, r=20, t=40, b=20))
                    st.plotly_chart(fig_dd, use_container_width=True)
                
                if not t_df.empty:
                    st.subheader("📊 Performance Breakdown by Preceding Streak Length")
                    streak_summary = []
                    for s_val in sorted(t_df['Streak'].unique()):
                        subset = t_df[t_df['Streak'] == s_val]
                        s_wins = len(subset[subset['Result'] == 'Win'])
                        s_total = len(subset)
                        s_wr = (s_wins / s_total) * 100
                        s_comp = ((1 + subset['Return (%)'] / 100).prod() - 1) * 100
                        s_g_prof = subset[subset['Result'] == 'Win']['Return (%)'].sum()
                        s_g_loss = abs(subset[subset['Result'] == 'Loss']['Return (%)'].sum())
                        s_pf = round(s_g_prof / s_g_loss, 2) if s_g_loss > 0 else np.nan
                        
                        streak_summary.append({
                            "Preceding Streak": f"{s_val} Month(s)",
                            "Trades": s_total,
                            "Win Rate (%)": s_wr,
                            "Profit Factor": s_pf,
                            "Total Return (%)": s_comp,
                            "Avg Realized R": subset['Realized R'].mean()
                        })
                    
                    st.dataframe(
                        pd.DataFrame(streak_summary).set_index("Preceding Streak").style.format({
                            "Win Rate (%)": "{:.1f}%",
                            "Profit Factor": "{:.2f}",
                            "Total Return (%)": "{:,.2f}%",
                            "Avg Realized R": "{:+.2f}R"
                        }),
                        use_container_width=True
                    )

                st.subheader("Trade Audit Log")
                if not t_df.empty:
                    st.download_button(
                        label="📥 Download Trade Log as CSV",
                        data=convert_df_to_csv(t_df),
                        file_name=f"{ticker}_trades_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime='text/csv'
                    )
                st.dataframe(
                    t_df.sort_values(by="Entry Date", ascending=False), 
                    column_config=trade_col_config, 
                    use_container_width=True
                )

# ----------------- SCANNER TAB -----------------
with tab_scanner:
    st.header("Live Setup Scanner")
    st.write("Scans constituents for active breakouts using the exact parameters and stop-loss logic defined in the sidebar.")
    
    scan_exit_options = [opt for opt in exit_options if opt != "Compare All Exits"]
    col_s1, col_s2, col_s3, col_s4 = st.columns([1.2, 1.2, 1.1, 1])
    with col_s1:
        universe_choice = st.selectbox(
            "Market Universe", 
            options=["S&P 500", "Russell 1000", "US Broad Market (~2,500+ Stocks)", "Nasdaq 100", "Dow Jones 30", "Major ADRs", "Major ETFs"]
        )
    with col_s2:
        scan_exit_mode = st.selectbox("20yr Historical Exit Rule", options=scan_exit_options, index=2)
    with col_s3:
        run_hist_val = st.checkbox(
            "Run 20yr Historical Backtest", 
            value=False, 
            help="Unchecked = Instant Setup Scan (<8s). Checked = Also runs deep 20-year backtests on active breakouts."
        )
    with col_s4:
        st.write("")
        st.write("")
        run_scan = st.button("🚀 Run Live Scan", type="primary", use_container_width=True)
        
    if universe_choice == "US Broad Market (~2,500+ Stocks)":
        st.warning("⚠️ Scanning 2,500+ stocks queries a substantial volume of data. It may take 1 to 2 minutes depending on network bandwidth.")

    if run_scan:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text(f"Phase 1: Fetching {universe_choice} roster...")
        universe = get_universe_tickers(universe_choice)
        
        if not universe:
            progress_bar.empty()
            status_text.empty()
            st.error(f"❌ Could not retrieve symbols for **{universe_choice}**. Temporary data provider block. Please select **Major ETFs** or retry.")
            st.stop()
            
        progress_bar.progress(15)
        
        status_text.text(f"Phase 2: Downloading last 24 months of daily data for {len(universe)} symbols...")
        bulk_data = yf.download(universe, period="24mo", interval="1d", group_by="ticker", auto_adjust=False, progress=False, threads=True)
        progress_bar.progress(60)
        
        status_text.text("Phase 3: Detecting breakouts and calculating trigger metrics...")
        candidates = []
        for sym in universe:
            try:
                df_daily = extract_symbol_daily(bulk_data, sym, len(universe))
                if len(df_daily) < 60: continue
                
                df_monthly = build_monthly_from_daily(df_daily)
                if len(df_monthly) < 3: continue
                
                avg_vol_m = df_monthly['Volume'].mean() / 1_000_000 
                if avg_vol_m < 0.5: continue
                
                bar_t1 = df_monthly.iloc[-2]
                bar_t2 = df_monthly.iloc[-3]
                
                prior_streak = df_monthly['red_streak_count'].iloc[-3] if "Red" in seq_type else df_monthly['green_streak_count'].iloc[-3]
                if prior_streak < min_streak: continue
                
                if signal_color == "Green Only" and not bar_t1['is_bull']: continue
                elif signal_color == "Red Only" and not bar_t1['is_bear']: continue
                
                if require_lower_high and (bar_t1['High'] >= bar_t2['High']): continue
                
                is_12m = False
                is_6m = False
                if not pd.isna(df_monthly['Close_Min_12'].iloc[-3]):
                    is_12m = bar_t2['Close'] <= (df_monthly['Close_Min_12'].iloc[-3] + 1e-4)
                if not pd.isna(df_monthly['Close_Min_6'].iloc[-3]):
                    is_6m = bar_t2['Close'] <= (df_monthly['Close_Min_6'].iloc[-3] + 1e-4)

                cap_tag = "12-Month" if is_12m else ("6-Month" if is_6m else "None")
                if capitulation_filter == "12-Month Low" and not is_12m: continue
                elif capitulation_filter == "6-Month Low" and not is_6m: continue

                if require_uptrend and not pd.isna(bar_t1['SMA_12']) and bar_t1['Close'] <= bar_t1['SMA_12']:
                    continue
                
                trig = round(bar_t1['High'] + tick_size, 2)
                atr_12 = df_monthly['ATR_12'].iloc[-2] if not pd.isna(df_monthly['ATR_12'].iloc[-2]) else (bar_t1['High'] - bar_t1['Low'])

                # Stop calculation according to selected rule
                if stop_rule == "Signal Month Low (T-1 Low)":
                    stop_px = round(bar_t1['Low'] - tick_size, 2)
                elif stop_rule == "Prior Month Low (T-2 Low)":
                    stop_px = round(bar_t2['Low'] - tick_size, 2)
                elif stop_rule == "Lowest Low of Streak":
                    lookback = min(len(df_monthly)-1, prior_streak + 1)
                    stop_px = round(df_monthly['Low'].iloc[-lookback-1:-1].min() - tick_size, 2)
                elif stop_rule == "1x 12M ATR Stop":
                    stop_px = max(0.01, round(trig - (1.0 * atr_12), 2))
                else:
                    stop_px = round(bar_t1['Low'] - tick_size, 2)

                r_unit = trig - stop_px
                if r_unit <= 0: continue
                
                target_3r = round(trig + (3.0 * r_unit), 2)
                target_3x_atr = round(trig + (3.0 * atr_12), 2)
                
                current_month_str = df_monthly.index[-1].strftime('%Y-%m')
                current_month_daily = df_daily[df_daily.index.strftime('%Y-%m') == current_month_str]
                
                curr_px = round(df_daily['Close'].iloc[-1], 2)
                curr_high = round(current_month_daily['High'].max(), 2) if not current_month_daily.empty else curr_px
                
                if curr_high >= trig:
                    triggered, stopped_out = False, False
                    for _, d_row in current_month_daily.iterrows():
                        if not triggered and d_row['High'] >= trig:
                            triggered = True
                            if d_row['Low'] <= stop_px: stopped_out = True
                        elif triggered and d_row['Low'] <= stop_px:
                            stopped_out = True
                            
                    status = "Stopped Out" if stopped_out else "Active Breakout"
                    dist_to_trig = ((curr_px - trig) / trig) * 100
                else:
                    dist_to_trig = ((trig - curr_px) / curr_px) * 100
                    status = "Pending"
                    
                candidates.append({
                    "Ticker": sym, 
                    "Status": status, 
                    "Streak": prior_streak,
                    "Capitulation": cap_tag,
                    "Avg Vol (M)": round(avg_vol_m, 1),
                    "Current Price": curr_px, 
                    "Trigger Price": trig, 
                    "Dist to Trigger (%)": round(dist_to_trig, 2),
                    f"Stop ({stop_rule.split(' ')[0]})": stop_px,
                    "Target 3R": target_3r,
                    "Target 3x ATR": target_3x_atr
                })
            except Exception: pass
            
        progress_bar.progress(85)
        
        cand_df = pd.DataFrame(candidates)
        if not cand_df.empty:
            active = cand_df[cand_df['Status'] == "Active Breakout"].copy()
            pending = cand_df[cand_df['Status'] == "Pending"].copy()
            
            if run_hist_val and not active.empty:
                status_text.text(f"Phase 4: Running 20-Year Validations for {len(active)} active breakouts...")
                active_tickers = active['Ticker'].tolist()
                
                hist_daily_data = yf.download(active_tickers, period="20y", interval="1d", group_by="ticker", auto_adjust=False, progress=False, threads=True)
                
                win_rates, tot_rets, bh_rets, sys_dds, bh_dds = [], [], [], [], []
                for sym in active_tickers:
                    try:
                        df_sym = extract_symbol_daily(hist_daily_data, sym, len(active_tickers))
                        if len(df_sym) < 60: raise ValueError("Insufficient data")
                        
                        bh_ret = ((df_sym['Adj Close'].iloc[-1] / df_sym['Adj Close'].iloc[0]) - 1) * 100
                        bh_cummax = df_sym['Adj Close'].cummax()
                        bh_dd = ((df_sym['Adj Close'] - bh_cummax) / bh_cummax).min() * 100

                        df_monthly_hist = build_monthly_from_daily(df_sym)
                        _, m, _, _ = run_daily_execution_backtest(
                            df_sym, df_monthly_hist, seq_type, min_streak, signal_color,
                            stop_rule, scan_exit_mode, hold_months_n, tick_size, init_cash,
                            trade_after_loss_only, require_uptrend, capitulation_filter, require_lower_high 
                        )
                        
                        win_rates.append(round(m.get('Win Rate (%)', 0), 1))
                        tot_rets.append(round(m.get('Total Return (%)', 0), 1))
                        bh_rets.append(round(bh_ret, 1))
                        sys_dds.append(round(m.get('Max Drawdown (%)', 0), 1))
                        bh_dds.append(round(bh_dd, 1))
                    except Exception:
                        win_rates.append(0.0); tot_rets.append(0.0); bh_rets.append(0.0); sys_dds.append(0.0); bh_dds.append(0.0)

                active['20yr Return (%)'] = tot_rets
                active['20yr B&H Return (%)'] = bh_rets
                active['System Max DD (%)'] = sys_dds
                active['B&H Max DD (%)'] = bh_dds
                active['20yr Win Rate (%)'] = win_rates
            else:
                active['20yr Return (%)'] = np.nan
                active['20yr B&H Return (%)'] = np.nan
                active['System Max DD (%)'] = np.nan
                active['B&H Max DD (%)'] = np.nan
                active['20yr Win Rate (%)'] = np.nan

            pending['20yr Return (%)'] = np.nan
            pending['20yr B&H Return (%)'] = np.nan
            pending['System Max DD (%)'] = np.nan
            pending['B&H Max DD (%)'] = np.nan
            pending['20yr Win Rate (%)'] = np.nan

            progress_bar.progress(100)
            status_text.empty()
            
            if not active.empty:
                sort_cols = ['Streak', '20yr Win Rate (%)'] if run_hist_val else ['Streak', 'Current Price']
                active = active.sort_values(by=sort_cols, ascending=[False, False])
                
            if not pending.empty:
                pending = pending.sort_values(by=['Streak', 'Dist to Trigger (%)'], ascending=[False, True])
            
            st.download_button(
                label="📥 Download Scan Results as CSV",
                data=convert_df_to_csv(pd.concat([active, pending], ignore_index=True)),
                file_name=f"{universe_choice}_scan_{datetime.now().strftime('%Y%m%d')}.csv",
                mime='text/csv'
            )
            
            stop_col_name = f"Stop ({stop_rule.split(' ')[0]})"
            scanner_config = {
                "Ticker": st.column_config.TextColumn(help="Ticker symbol."),
                "Status": st.column_config.TextColumn(help="Active Breakout vs Pending setup."),
                "Streak": st.column_config.NumberColumn(help=f"Preceding {seq_type.split(' ')[0]} month streak count.", format="%d"),
                "Capitulation": st.column_config.TextColumn(help="Capitulation depth: 12M, 6M, or None."),
                "Avg Vol (M)": st.column_config.NumberColumn(help="6-month average monthly volume.", format="%.1fM"),
                "Current Price": st.column_config.NumberColumn(help="Latest closing or trading price.", format="$%.2f"),
                "Trigger Price": st.column_config.NumberColumn(help="Buy Trigger: Signal High + tick size.", format="$%.2f"),
                "Dist to Trigger (%)": st.column_config.NumberColumn(help="Proximity Indicator.", format="%+.2f%%"),
                stop_col_name: st.column_config.NumberColumn(help=f"Active Stop-Loss calculated via {stop_rule}.", format="$%.2f"),
                "Target 3R": st.column_config.NumberColumn(help="Profit Target: Trigger + 3x Risk Unit (1R).", format="$%.2f"),
                "Target 3x ATR": st.column_config.NumberColumn(help="Profit Target: Trigger + 3x 12M ATR.", format="$%.2f"),
                "20yr Return (%)": st.column_config.NumberColumn(help="Compounded 20-year strategy return.", format="%.2f%%"),
                "20yr B&H Return (%)": st.column_config.NumberColumn(help="Baseline 20-year Buy & Hold return.", format="%.2f%%"),
                "System Max DD (%)": st.column_config.NumberColumn(help="Maximum historical strategy drawdown.", format="%.1f%%"),
                "B&H Max DD (%)": st.column_config.NumberColumn(help="Maximum Buy & Hold drawdown.", format="%.1f%%"),
                "20yr Win Rate (%)": st.column_config.ProgressColumn(help="Historical win rate over 20 years.", format="%.1f%%", min_value=0, max_value=100)
            }
            
            def highlight_vs_bh(row):
                styles = [''] * len(row)
                if '20yr Return (%)' in row.index and '20yr B&H Return (%)' in row.index:
                    col_idx = row.index.get_loc('20yr Return (%)')
                    sys_ret = row['20yr Return (%)']
                    bh_ret = row['20yr B&H Return (%)']
                    if pd.notna(sys_ret) and pd.notna(bh_ret):
                        if sys_ret >= bh_ret:
                            styles[col_idx] = 'background-color: rgba(0, 200, 83, 0.25); color: #00FF66; font-weight: bold;'
                        else:
                            styles[col_idx] = 'background-color: rgba(255, 51, 85, 0.25); color: #FF4B4B; font-weight: bold;'
                return styles

            st.subheader(f"🟢 Active Breakouts ({len(active)})")
            if not active.empty:
                styled_active = active.style.apply(highlight_vs_bh, axis=1) if run_hist_val else active
                st.dataframe(styled_active, column_config=scanner_config, use_container_width=True)
            else:
                st.info("No active breakouts currently found matching these criteria.")
            
            st.subheader(f"🟡 Pending Setups Waiting for Breakout ({len(pending)})")
            if not pending.empty:
                st.dataframe(pending, column_config=scanner_config, use_container_width=True)
            else:
                st.info("No pending setups currently found matching these criteria.")
        else:
            progress_bar.progress(100)
            status_text.empty()
            st.info(f"No setups found in {universe_choice} matching current parameters.")
