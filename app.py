import yfinance as yf
import pandas as pd
import numpy as np

def run_granular_backtest_v3(ticker, consec_red_target=3, hold_months=1, start_year="2000"):
    monthly_df = yf.download(ticker, start=f"{start_year}-01-01", interval="1mo", progress=False)
    daily_df = yf.download(ticker, start=f"{start_year}-01-01", interval="1d", progress=False)
    
    # Flatten MultiIndex columns from yfinance if present
    for df in [monthly_df, daily_df]:
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
    monthly_df.dropna(subset=['Open', 'High', 'Low', 'Close'], inplace=True)
    daily_df.dropna(subset=['Open', 'High', 'Low', 'Close'], inplace=True)
    
    # Identify bar colors and consecutive red streaks
    monthly_df['Is_Red'] = monthly_df['Close'] < monthly_df['Open']
    monthly_df['Is_Green'] = monthly_df['Close'] > monthly_df['Open']
    monthly_df['Consec_Red'] = monthly_df['Is_Red'].groupby((~monthly_df['Is_Red']).cumsum()).cumsum()
    
    trades = []
    
    for i in range(len(monthly_df)):
        if i < consec_red_target + 1:
            continue
            
        was_green_signal = monthly_df['Is_Green'].iloc[i-1]
        actual_red_streak = int(monthly_df['Consec_Red'].iloc[i-2])
        had_enough_reds = actual_red_streak >= consec_red_target
        
        # --- NEW CONDITION ---
        # The green signal bar's High (i-1) must be lower than the preceding red bar's High (i-2)
        lower_high_filter = float(monthly_df['High'].iloc[i-1]) < float(monthly_df['High'].iloc[i-2])
        
        if was_green_signal and had_enough_reds and lower_high_filter:
            # Locate the first red bar of this streak
            first_red_idx = (i - 2) - actual_red_streak + 1
            
            tick = 0.01
            buy_trigger = float(monthly_df['High'].iloc[i-1] + tick)
            stop_loss_level = float(monthly_df['Low'].iloc[first_red_idx] - tick)
            
            exec_month_start = monthly_df.index[i]
            exec_month_end = monthly_df.index[i+1] if (i + 1 < len(monthly_df)) else daily_df.index[-1]
            
            execution_days = daily_df[(daily_df.index >= exec_month_start) & (daily_df.index < exec_month_end)]
            triggered_days = execution_days[execution_days['High'] >= buy_trigger]
            
            if triggered_days.empty:
                continue 
                
            entry_date = triggered_days.index[0]
            entry_day_data = daily_df.loc[entry_date]
            entry_price = max(buy_trigger, float(entry_day_data['Open']))
            
            # Time exit boundary
            exit_month_idx = i + hold_months
            max_hold_date = monthly_df.index[exit_month_idx] if (exit_month_idx < len(monthly_df)) else daily_df.index[-1]
            
            trade_lifecycle = daily_df[(daily_df.index >= entry_date) & (daily_df.index <= max_hold_date)]
            
            exited = False
            for current_date, row in trade_lifecycle.iterrows():
                # Same-day execution check
                if current_date == entry_date:
                    if float(row['Low']) <= stop_loss_level:
                        exit_price = stop_loss_level
                        trades.append({
                            'Entry_Date': entry_date, 'Exit_Date': current_date,
                            'Entry': entry_price, 'Exit': exit_price,
                            'Return': (exit_price - entry_price) / entry_price, 'Type': 'Stopped Out (Same Day)'
                        })
                        exited = True
                        break
                    continue
                
                # Check stop loss against first red month's low
                if float(row['Low']) <= stop_loss_level:
                    exit_price = min(stop_loss_level, float(row['Open']))
                    trades.append({
                        'Entry_Date': entry_date, 'Exit_Date': current_date,
                        'Entry': entry_price, 'Exit': exit_price,
                        'Return': (exit_price - entry_price) / entry_price, 'Type': 'Stopped Out (First Red Low)'
                    })
                    exited = True
                    break
                    
                # Check time exit
                if current_date == max_hold_date:
                    exit_price = float(row['Close'])
                    trades.append({
                        'Entry_Date': entry_date, 'Exit_Date': current_date,
                        'Entry': entry_price, 'Exit': exit_price,
                        'Return': (exit_price - entry_price) / entry_price, 'Type': 'Time Exit'
                    })
                    exited = True
                    break
                    
            if not exited and not trade_lifecycle.empty:
                last_row = trade_lifecycle.iloc[-1]
                trades.append({
                    'Entry_Date': entry_date, 'Exit_Date': trade_lifecycle.index[-1],
                    'Entry': entry_price, 'Exit': float(last_row['Close']),
                    'Return': (float(last_row['Close']) - entry_price) / entry_price, 'Type': 'End of Data'
                })

    if len(trades) > 0:
        tdf = pd.DataFrame(trades)
        win_rate = len(tdf[tdf['Return'] > 0]) / len(tdf)
        avg_ret = tdf['Return'].mean()
        return len(tdf), win_rate, avg_ret, tdf
    return 0, 0.0, 0.0, None


# =====================================================================
# ⚙️ USER CONFIGURATION BLOCK
# =====================================================================
TICKER = "SPY"
START_YEAR = "2000"

red_closes_to_test = [3, 4, 5, 6]
months_to_hold_test = [1, 2, 3, 6]
# =====================================================================

if __name__ == "__main__":
    print(f"🚀 Running Scan for {TICKER} (Filter: Signal High < Preceding Red High)")
    optimization_matrix = []
    detailed_logs = {}
    
    for red_count in red_closes_to_test:
        for hold_len in months_to_hold_test:
            count, wr, avg, detailed_df = run_granular_backtest_v3(
                ticker=TICKER, 
                consec_red_target=red_count, 
                hold_months=hold_len,
                start_year=START_YEAR
            )
            
            optimization_matrix.append({
                'Red Mnth Count': red_count,
                'Hold Mnth Duration': hold_len,
                'Total Trades': count,
                'Win Rate': f"{wr:.1%}" if count > 0 else "N/A",
                'Avg Return': f"{avg:.2%}" if count > 0 else "N/A"
            })
            
            if count > 0:
                detailed_logs[f"Red_{red_count}_Hold_{hold_len}"] = detailed_df
                
    summary_table = pd.DataFrame(optimization_matrix)
    print("\n========================= FILTERED RESULTS =========================")
    print(summary_table.to_string(index=False))
    print("====================================================================\n")
    
    # Inspect a populated run (e.g. 3 Red Months, 3 Month Hold)
    target_key = "Red_3_Hold_3"
    if target_key in detailed_logs:
        print(f"📋 Trade Breakdown ({target_key.replace('_',' ')}):")
        print(detailed_logs[target_key][['Entry_Date', 'Exit_Date', 'Return', 'Type']].to_string(index=False))
