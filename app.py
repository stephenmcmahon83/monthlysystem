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
    "Execution Engine: Daily Data with Phantom Tracking, Gap Modeling & Cloud-Resilient Data Pipelines."
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
    """
    Fetches tickers with browser-grade headers, automated column discovery,
    string sanitization, and fallback sources for cloud execution.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    def clean_ticker_list(raw_list):
        cleaned = []
        for sym in raw_list:
            if pd.isna(sym):
                continue
            s = str(sym).strip().upper().replace('.', '-')
            # Keep standard equity tickers (1-5 letters or hyphenated classes like BRK-B)
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
                # Direct fallback for Russell constituents
                url = "https://en.wikipedia.org/wiki/Russell_1000_Index"
                tickers = extract_wiki_symbols(url)
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
    
    # Calculate consecutive red bar streaks
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

def run_daily_execution_backtest(daily_df, monthly_df, exit_type, hold_n, tick_size, init_cash, trade_after_loss_only=False, require_uptrend=False):
    setups = {}
    monthly_stats = {}
    
    for i in range(1, len(monthly_df) - 1):
        t1 = monthly_df.iloc[i]
        ym = t1.name.strftime('%Y-%m')
        monthly_stats[ym] = {'is_bear': t1['is_bear'], 'low': t1['Low']}
        
        prior_red_streak = monthly_df['red_streak_count'].iloc[i-1]
        setup_valid = (prior_red_streak >= 1) and (not t1['is_bear'])
        
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
            
            # 1. Intra-day Stop Loss (Evaluates gaps)
            if row['Low'] <= stop_price:
                exit_hit, reason = True, "Stop Loss"
                exit_px = min(row['Open'], stop_price)
                
            # 2. Intra-day Target Hit (Evaluates gaps)
            elif target_price and row['High'] >= target_price:
                exit_hit, reason = True, "Target Hit"
                exit_px = max(row['Open'], target_price)
                
            # 3. Intra-day Prior Month Low Breakdown
            elif exit_type == "Prior Month Low Breakdown":
                prior_ym = (date.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
                if prior_ym in monthly_stats and row['Low'] < monthly_stats[prior_ym]['low']:
                    exit_hit, reason = True, "Prior Low Break"
                    exit_px = min(row['Open'], monthly_stats[prior_ym]['low'] - 0.01)
                    
            # 4. End of Month Exits
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
                    
                    # Same-day execution check
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

    # Apply Prior-Trade Loss Regime Filter
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
        "Trades": len(trades_df), "Win Rate (%)": win_rate, "Total Return (%)": comp_ret,
        "B&H Return (%)": bh_ret, "Profit Factor": prof_factor, 
        "Avg Hold (Mo)": trades_df['Months Held'].mean(), "Max Drawdown (%)": max_dd
    }
    return trades_df, metrics, eq_series, drawdowns

# ==========================================
# USER INTERFACE LAYOUT
# ==========================================
tab_backtest, tab_scanner = st.tabs(["📊 Deep Backtester", "📡 Live Market Scanner"])

# ----------------- BACKTESTER -----------------
with tab_backtest:
    st.sidebar.header("1. Data Parameters")
    ticker = st.sidebar.text_input("Ticker Symbol", value="SPY", key="bt_ticker").upper().strip()
    
    col1, col2 = st.sidebar.columns(2)
    today = datetime.now().date()
    start_date = col1.date_input("Start", value=today - timedelta(days=25 * 365), key="bt_start")
    end_date = col2.date_input("End", value=today, key="bt_end")
    
    st.sidebar.header("2. Strategy Rules")
    exit_options = [
        "Compare All Exits", "Target: 2x Signal Width", "Target: 3x Signal Width", 
        "Target: 5x Signal Width", "Target: 10x Signal Width", "First Red Month", 
        "2 Consecutive Red Months", "Hold Fixed Months", "Prior Month Low Breakdown"
    ]
    exit_mode = st.sidebar.selectbox("Exit Rule", options=exit_options, key="bt_exit")
    hold_months_n = st.sidebar.number_input("Hold Duration (Months)", value=5, key="bt_hold") if "Hold" in exit_mode or exit_mode == "Compare All Exits" else 5
    
    with st.sidebar.expander("⚙️ Advanced Filters & Risk", expanded=True):
        tick_size = st.number_input("Breakout Tick Size ($)", min_value=0.01, value=0.01, key="bt_tick")
        init_cash = st.number_input("Starting Capital ($)", value=10000, key="bt_cash")
        require_uptrend = st.checkbox("Bull Market Filter (Close > 12-Month SMA)", value=True)
        trade_after_loss_only = st.checkbox("Regime Filter (Only trade if prior trade lost)", value=False)

    trade_col_config = {
        "Prior Red Months": st.column_config.NumberColumn(format="%d"),
        "Entry Price": st.column_config.NumberColumn(format="$%.2f"),
        "Exit Price": st.column_config.NumberColumn(format="$%.2f"),
        "Return (%)": st.column_config.NumberColumn(format="%.2f%%")
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
                with st.spinner("Simulating all variations..."):
                    for strat in variants:
                        t_df, m, eq, _ = run_daily_execution_backtest(df_daily, df_monthly, strat, hold_months_n, tick_size, init_cash, trade_after_loss_only, require_uptrend)
                        curves[strat] = eq
                        row = {"Exit Strategy": strat}
                        row.update(m)
                        comp_rows.append(row)
                
                st.dataframe(pd.DataFrame(comp_rows).set_index("Exit Strategy").style.format(precision=2), use_container_width=True)
                fig = go.Figure()
                for label, curve in curves.items():
                    fig.add_trace(go.Scatter(y=curve.values, mode='lines', name=label))
                fig.update_layout(title="Equity Compounding Across Strategies", template="plotly_dark", hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True)
            else:
                with st.spinner(f"Running exact daily execution for {ticker}..."):
                    t_df, metrics, eq, dd = run_daily_execution_backtest(df_daily, df_monthly, exit_mode, hold_months_n, tick_size, init_cash, trade_after_loss_only, require_uptrend)
                
                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("Strategy Return", f"{metrics.get('Total Return (%)', 0):,.2f}%")
                c2.metric("Buy & Hold Return", f"{metrics.get('B&H Return (%)', 0):,.2f}%")
                c3.metric("Win Rate", f"{metrics.get('Win Rate (%)', 0):.1f}%")
                c4.metric("Profit Factor", f"{metrics.get('Profit Factor', 0)}")
                c5.metric("Max Drawdown", f"{metrics.get('Max Drawdown (%)', 0):.1f}%")
                
                col_chart1, col_chart2 = st.columns(2)
                with col_chart1:
                    fig_eq = go.Figure()
                    fig_eq.add_trace(go.Scatter(x=eq.index, y=eq.values, mode='lines+markers', name='Equity', line=dict(color='#00FF66')))
                    fig_eq.update_layout(title="Account Growth", template="plotly_dark", margin=dict(l=20, r=20, t=40, b=20))
                    st.plotly_chart(fig_eq, use_container_width=True)
                with col_chart2:
                    fig_dd = go.Figure()
                    fig_dd.add_trace(go.Scatter(x=dd.index, y=dd.values * 100, fill='tozeroy', mode='lines', name='Drawdown', line=dict(color='#FF3366')))
                    fig_dd.update_layout(title="Historical Drawdown (%)", template="plotly_dark", margin=dict(l=20, r=20, t=40, b=20))
                    st.plotly_chart(fig_dd, use_container_width=True)
                
                if not t_df.empty:
                    st.subheader("📊 Performance Breakdown by Prior Red Streak")
                    streak_summary = []
                    for streak in sorted(t_df['Prior Red Months'].unique()):
                        subset = t_df[t_df['Prior Red Months'] == streak]
                        s_wins = len(subset[subset['Result'] == 'Win'])
                        s_total = len(subset)
                        s_wr = (s_wins / s_total) * 100
                        s_comp = ((1 + subset['Return (%)'] / 100).prod() - 1) * 100
                        s_g_prof = subset[subset['Result'] == 'Win']['Return (%)'].sum()
                        s_g_loss = abs(subset[subset['Result'] == 'Loss']['Return (%)'].sum())
                        s_pf = round(s_g_prof / s_g_loss, 2) if s_g_loss > 0 else np.nan
                        
                        streak_summary.append({
                            "Prior Red Streak": f"{streak} Month(s)",
                            "Trades": s_total,
                            "Win Rate (%)": s_wr,
                            "Profit Factor": s_pf,
                            "Total Return (%)": s_comp
                        })
                    
                    st.dataframe(
                        pd.DataFrame(streak_summary).set_index("Prior Red Streak").style.format({
                            "Win Rate (%)": "{:.1f}%",
                            "Profit Factor": "{:.2f}",
                            "Total Return (%)": "{:,.2f}%"
                        }),
                        use_container_width=True
                    )

                st.subheader("Trade Log")
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

# ----------------- SCANNER -----------------
with tab_scanner:
    st.header("Live Setup Scanner")
    st.write("Scans constituents for active breakouts using the exact settings from the sidebar.")
    
    col_s1, col_s2 = st.columns([1, 2])
    with col_s1:
        universe_choice = st.selectbox(
            "Market Universe", 
            options=["S&P 500", "Russell 1000", "US Broad Market (~2,500+ Stocks)", "Nasdaq 100", "Dow Jones 30", "Major ADRs", "Major ETFs"]
        )
    with col_s2:
        st.write("")
        st.write("")
        run_scan = st.button("🚀 Run Live Market Scan", type="primary", use_container_width=True)
        
    if universe_choice == "US Broad Market (~2,500+ Stocks)":
        st.warning("⚠️ **Heavy Computation:** Scanning 2,500+ stocks queries a substantial volume of data. It may take 2 to 4 minutes depending on network bandwidth.")

    if run_scan:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text(f"Phase 1: Fetching {universe_choice} roster...")
        universe = get_universe_tickers(universe_choice)
        
        # Guard Check: Prevent yf.download([]) crashes
        if not universe:
            progress_bar.empty()
            status_text.empty()
            st.error(f"❌ Could not retrieve symbols for **{universe_choice}**. The data source temporarily blocked the cloud request. Please try selecting **Major ETFs**, **Major ADRs**, or retry in a moment.")
            st.stop()
            
        progress_bar.progress(10)
        
        status_text.text(f"Phase 2: Downloading last 14 months of daily data for {len(universe)} symbols...")
        bulk_data = yf.download(universe, period="14mo", interval="1d", group_by="ticker", auto_adjust=False, progress=False, threads=True)
        progress_bar.progress(50)
        
        status_text.text("Phase 3: Running precise evaluations & liquidity filters...")
        candidates = []
        for sym in universe:
            try:
                df_daily = bulk_data[sym].dropna() if len(universe) > 1 else bulk_data.dropna()
                if len(df_daily) < 60: continue
                
                df_monthly = build_monthly_from_daily(df_daily)
                if len(df_monthly) < 3: continue
                
                avg_vol_m = df_monthly['Volume'].mean() / 1_000_000 
                if avg_vol_m < 0.5: continue
                
                bar_t1 = df_monthly.iloc[-2]
                prior_reds = df_monthly['red_streak_count'].iloc[-3]
                
                setup_valid = (prior_reds >= 1) and (not bar_t1['is_bear'])
                
                if require_uptrend and not pd.isna(bar_t1['SMA_12']):
                    if bar_t1['Close'] <= bar_t1['SMA_12']:
                        setup_valid = False
                        
                if not setup_valid: continue
                
                trig = round(bar_t1['High'] + tick_size, 2)
                stop = round(bar_t1['Low'] - tick_size, 2)
                width = round(bar_t1['High'] - bar_t1['Low'], 2)
                
                current_month_str = df_monthly.index[-1].strftime('%Y-%m')
                current_month_daily = df_daily[df_daily.index.strftime('%Y-%m') == current_month_str]
                
                curr_px = round(current_month_daily['Close'].iloc[-1], 2)
                curr_high = round(current_month_daily['High'].max(), 2)
                
                if curr_high >= trig:
                    triggered, stopped_out = False, False
                    for _, d_row in current_month_daily.iterrows():
                        if not triggered and d_row['High'] >= trig:
                            triggered = True
                            if d_row['Low'] <= stop: stopped_out = True
                        elif triggered and d_row['Low'] <= stop:
                            stopped_out = True
                            
                    status = "Stopped Out" if stopped_out else "Active Breakout"
                else:
                    dist = ((trig - curr_px) / curr_px) * 100
                    status = f"Pending ({dist:+.1f}%)"
                    
                candidates.append({
                    "Ticker": sym, "Status": status, "Prior Reds": prior_reds,
                    "Avg Vol (M)": round(avg_vol_m, 1),
                    "Current Price": curr_px, "Trigger Price": trig, 
                    "Stop Loss": stop, "Target 3x": round(trig + (3.0 * width), 2)
                })
            except Exception: pass
            
        progress_bar.progress(70)
        
        cand_df = pd.DataFrame(candidates)
        if not cand_df.empty:
            status_text.text(f"Phase 4: Running 20-Year Validations for {len(candidates)} active setups...")
            cand_tickers = cand_df['Ticker'].tolist()
            
            hist_daily_data = yf.download(cand_tickers, period="20y", interval="1d", group_by="ticker", auto_adjust=False, progress=False, threads=True)
            
            win_rates, tot_rets = [], []
            for sym in cand_tickers:
                try:
                    df_sym = hist_daily_data[sym].copy() if len(cand_tickers) > 1 else hist_daily_data.copy()
                    if isinstance(df_sym.columns, pd.MultiIndex): df_sym.columns = [c[0] for c in df_sym.columns]
                    
                    df_monthly_hist = build_monthly_from_daily(df_sym)
                    _, m, _, _ = run_daily_execution_backtest(
                        df_sym, df_monthly_hist, exit_mode, hold_months_n, 
                        tick_size, init_cash, trade_after_loss_only, require_uptrend 
                    )
                    win_rates.append(round(m.get('Win Rate (%)', 0), 1))
                    tot_rets.append(round(m.get('Total Return (%)', 0), 1))
                except Exception:
                    win_rates.append(0.0); tot_rets.append(0.0)

            cand_df['20yr Win Rate (%)'] = win_rates
            cand_df['20yr Return (%)'] = tot_rets
            
            progress_bar.progress(100); status_text.empty()
            
            active = cand_df[cand_df['Status'] == "Active Breakout"].copy()
            pending = cand_df[cand_df['Status'].str.startswith("Pending")].copy()
            
            if not active.empty:
                active = active.sort_values(by=['Prior Reds', '20yr Win Rate (%)'], ascending=[False, False])
                
            if not pending.empty:
                pending['Dist'] = pending['Status'].str.extract(r'\((.*)%\)').astype(float)
                pending = pending.sort_values(by=['Prior Reds', 'Dist'], ascending=[False, True]).drop(columns=['Dist'])
            
            st.download_button(
                label="📥 Download Scan Results as CSV",
                data=convert_df_to_csv(cand_df),
                file_name=f"{universe_choice}_scan_{datetime.now().strftime('%Y%m%d')}.csv",
                mime='text/csv'
            )
            
            scanner_config = {
                "Prior Reds": st.column_config.NumberColumn(format="%d"),
                "Avg Vol (M)": st.column_config.NumberColumn(format="%.1fM"),
                "Current Price": st.column_config.NumberColumn(format="$%.2f"),
                "Trigger Price": st.column_config.NumberColumn(format="$%.2f"),
                "Stop Loss": st.column_config.NumberColumn(format="$%.2f"),
                "Target 3x": st.column_config.NumberColumn(format="$%.2f"),
                "20yr Return (%)": st.column_config.NumberColumn(format="%.2f%%"),
                "20yr Win Rate (%)": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100)
            }
            
            st.subheader(f"🟢 Active Breakouts ({len(active)})")
            st.dataframe(active, column_config=scanner_config, use_container_width=True)
            
            st.subheader(f"🟡 Pending Setups Waiting for Breakout ({len(pending)})")
            st.dataframe(pending, column_config=scanner_config, use_container_width=True)
        else:
            progress_bar.progress(100); status_text.empty()
            st.info(f"No valid setups found in {universe_choice} matching current filters.")
