import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests

# Configure page layout and ensure sidebar is visible
st.set_page_config(
    page_title="Monthly Reversal Backtester",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📈 Monthly Reversal Strategy Backtester")
st.caption(
    "Rules: $N$ Consecutive Red Months → Green Inside/Lower-High Signal Month → "
    "Buy 1 Tick Above Green High → Stop Loss 1 Tick Below First Red Month's Low."
)

# --- SIDEBAR CONTROLS ---
st.sidebar.header("Configuration")
ticker = st.sidebar.text_input("Stock Ticker", value="SPY").upper().strip()
start_year = st.sidebar.selectbox("Start Year", options=[1995, 2000, 2005, 2010, 2015, 2020], index=1)
consec_red_target = st.sidebar.slider("Min Consecutive Red Months", min_value=2, max_value=8, value=3)
hold_months = st.sidebar.slider("Hold Duration (Months)", min_value=1, max_value=12, value=3)


# --- DATA FETCHING WITH CACHE & CUSTOM USER-AGENT ---
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_stock_data(ticker_sym, start_yr):
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })

    ticker_obj = yf.Ticker(ticker_sym, session=session)
    monthly_df = ticker_obj.history(start=f"{start_yr}-01-01", interval="1mo")
    daily_df = ticker_obj.history(start=f"{start_yr}-01-01", interval="1d")

    # Fallback to download if history yields an empty frame
    if monthly_df.empty or daily_df.empty:
        monthly_df = yf.download(ticker_sym, start=f"{start_yr}-01-01", interval="1mo", progress=False)
        daily_df = yf.download(ticker_sym, start=f"{start_yr}-01-01", interval="1d", progress=False)

    return monthly_df, daily_df


# --- BACKTEST ENGINE ---
def run_granular_backtest_with_data(monthly_raw, daily_raw, red_target, hold_len):
    monthly_df = monthly_raw.copy()
    daily_df = daily_raw.copy()

    # Flatten MultiIndex columns if present
    for df in [monthly_df, daily_df]:
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

    # Clean indices: ensure timezone-naive for seamless date slicing
    if monthly_df.index.tz is not None:
        monthly_df.index = monthly_df.index.tz_localize(None)
    if daily_df.index.tz is not None:
        daily_df.index = daily_df.index.tz_localize(None)

    monthly_df.dropna(subset=['Open', 'High', 'Low', 'Close'], inplace=True)
    daily_df.dropna(subset=['Open', 'High', 'Low', 'Close'], inplace=True)

    # Setup identification
    monthly_df['Is_Red'] = monthly_df['Close'] < monthly_df['Open']
    monthly_df['Is_Green'] = monthly_df['Close'] > monthly_df['Open']
    monthly_df['Consec_Red'] = monthly_df['Is_Red'].groupby((~monthly_df['Is_Red']).cumsum()).cumsum()

    trades = []

    for i in range(len(monthly_df)):
        if i < red_target + 1:
            continue

        was_green_signal = bool(monthly_df['Is_Green'].iloc[i - 1])
        actual_red_streak = int(monthly_df['Consec_Red'].iloc[i - 2])
        had_enough_reds = actual_red_streak >= red_target

        # Inside / Lower-High condition
        lower_high_filter = float(monthly_df['High'].iloc[i - 1]) < float(monthly_df['High'].iloc[i - 2])

        if was_green_signal and had_enough_reds and lower_high_filter:
            # Locate first red bar in the preceding streak
            first_red_idx = (i - 2) - actual_red_streak + 1

            tick = 0.01
            buy_trigger = float(monthly_df['High'].iloc[i - 1] + tick)
            stop_loss_level = float(monthly_df['Low'].iloc[first_red_idx] - tick)

            exec_month_start = monthly_df.index[i]
            exec_month_end = monthly_df.index[i + 1] if (i + 1 < len(monthly_df)) else daily_df.index[-1]

            execution_days = daily_df[(daily_df.index >= exec_month_start) & (daily_df.index < exec_month_end)]
            triggered_days = execution_days[execution_days['High'] >= buy_trigger]

            if triggered_days.empty:
                continue

            entry_date = triggered_days.index[0]
            entry_day_data = daily_df.loc[entry_date]
            entry_price = max(buy_trigger, float(entry_day_data['Open']))

            exit_month_idx = i + hold_len
            max_hold_date = monthly_df.index[exit_month_idx] if (exit_month_idx < len(monthly_df)) else daily_df.index[-1]

            trade_lifecycle = daily_df[(daily_df.index >= entry_date) & (daily_df.index <= max_hold_date)]

            exited = False
            for current_date, row in trade_lifecycle.iterrows():
                # Same-day execution check
                if current_date == entry_date:
                    if float(row['Low']) <= stop_loss_level:
                        exit_price = stop_loss_level
                        trades.append({
                            'Entry Date': entry_date.strftime('%Y-%m-%d'),
                            'Exit Date': current_date.strftime('%Y-%m-%d'),
                            'Entry ($)': round(entry_price, 2),
                            'Exit ($)': round(exit_price, 2),
                            'Return (%)': round(((exit_price - entry_price) / entry_price) * 100, 2),
                            'Exit Type': 'Stopped Out (Day 1)'
                        })
                        exited = True
                        break
                    continue

                # Stop loss check against first red month's low
                if float(row['Low']) <= stop_loss_level:
                    exit_price = min(stop_loss_level, float(row['Open']))
                    trades.append({
                        'Entry Date': entry_date.strftime('%Y-%m-%d'),
                        'Exit Date': current_date.strftime('%Y-%m-%d'),
                        'Entry ($)': round(entry_price, 2),
                        'Exit ($)': round(exit_price, 2),
                        'Return (%)': round(((exit_price - entry_price) / entry_price) * 100, 2),
                        'Exit Type': 'Stopped Out (First Red Low)'
                    })
                    exited = True
                    break

                # Time exit check
                if current_date == max_hold_date:
                    exit_price = float(row['Close'])
                    trades.append({
                        'Entry Date': entry_date.strftime('%Y-%m-%d'),
                        'Exit Date': current_date.strftime('%Y-%m-%d'),
                        'Entry ($)': round(entry_price, 2),
                        'Exit ($)': round(exit_price, 2),
                        'Return (%)': round(((exit_price - entry_price) / entry_price) * 100, 2),
                        'Exit Type': 'Time Exit'
                    })
                    exited = True
                    break

            if not exited and not trade_lifecycle.empty:
                last_row = trade_lifecycle.iloc[-1]
                trades.append({
                    'Entry Date': entry_date.strftime('%Y-%m-%d'),
                    'Exit Date': trade_lifecycle.index[-1].strftime('%Y-%m-%d'),
                    'Entry ($)': round(entry_price, 2),
                    'Exit ($)': round(float(last_row['Close']), 2),
                    'Return (%)': round(((float(last_row['Close']) - entry_price) / entry_price) * 100, 2),
                    'Exit Type': 'End of Data'
                })

    if len(trades) > 0:
        return pd.DataFrame(trades)
    return pd.DataFrame()


# --- DASHBOARD DISPLAY ---
with st.spinner(f"Fetching data and evaluating {ticker}..."):
    try:
        monthly_raw, daily_raw = fetch_stock_data(ticker, start_year)

        if monthly_raw.empty or daily_raw.empty:
            st.error(
                f"Could not retrieve historical data for '{ticker}'. Yahoo Finance may be temporarily throttling "
                "requests from this IP. Please wait a minute and refresh, or test another symbol."
            )
        else:
            trades_df = run_granular_backtest_with_data(monthly_raw, daily_raw, consec_red_target, hold_months)

            if not trades_df.empty:
                win_rate = (trades_df['Return (%)'] > 0).mean() * 100
                avg_return = trades_df['Return (%)'].mean()
                total_trades = len(trades_df)

                col1, col2, col3 = st.columns(3)
                col1.metric("Total Trades", total_trades)
                col2.metric("Win Rate", f"{win_rate:.1f}%")
                col3.metric("Avg Return / Trade", f"{avg_return:.2f}%")

                st.subheader("Trade Log")
                st.dataframe(trades_df, width="stretch")
            else:
                st.info(
                    f"Connected to **{ticker}** successfully, but **0 trades** matched the criteria "
                    f"(≥ {consec_red_target} Red Months followed by an Inside Green Month). "
                    "Try decreasing the required red months in the sidebar."
                )
    except Exception as e:
        st.error(f"Error during backtest calculation: {e}")
