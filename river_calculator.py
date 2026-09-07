import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple

def calculate_river_bands(
    df_input: pd.DataFrame,
    ma_period: int = 60,
    time_horizon_months: float = 36.0
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Calculate valuation river bands and indicators for Allianz Taiwan Tech Fund.
    
    ma_period: Moving Average Period in trading days (5, 10, 20, 60, 120, 240)
    time_horizon_months: Time range in months (1, 3, 6, 12, 36, 60, 0 for All)
    """
    df = df_input.copy()
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').reset_index(drop=True)
    
    # Calculate rolling MA and Std on full dataset first to prevent lookback NaNs
    df['MA'] = df['NAV'].rolling(window=ma_period, min_periods=1).mean()
    df['Std'] = df['NAV'].rolling(window=ma_period, min_periods=1).std().fillna(0.0)
    
    # Calculate 5 River Boundaries (2.0σ, 1.0σ, MA, -1.0σ, -2.0σ)
    df['Upper_2'] = df['MA'] + 2.0 * df['Std']
    df['Upper_1'] = df['MA'] + 1.0 * df['Std']
    df['Center']  = df['MA']
    df['Lower_1'] = df['MA'] - 1.0 * df['Std']
    df['Lower_2'] = df['MA'] - 2.0 * df['Std']
    
    # Filter by time horizon
    if time_horizon_months > 0:
        max_dt = df['Date'].max()
        cutoff_dt = max_dt - pd.DateOffset(months=int(time_horizon_months))
        df_sub = df[df['Date'] >= cutoff_dt].copy().reset_index(drop=True)
    else:
        df_sub = df.copy().reset_index(drop=True)
        
    if df_sub.empty or len(df_sub) < 2:
        df_sub = df.tail(min(len(df), max(ma_period, 20))).copy().reset_index(drop=True)
        
    # Latest Day Indicators Summary
    last_row = df_sub.iloc[-1]
    latest_nav = float(last_row['NAV'])
    latest_ma = float(last_row['MA'])
    latest_upper2 = float(last_row['Upper_2'])
    latest_upper1 = float(last_row['Upper_1'])
    latest_lower1 = float(last_row['Lower_1'])
    latest_lower2 = float(last_row['Lower_2'])
    
    bias_pct = ((latest_nav - latest_ma) / latest_ma * 100.0) if latest_ma > 0 else 0.0
    
    # Determine valuation level status
    if latest_nav > latest_upper2:
        status_str = "🔴 昂貴區 (高於 +2.0σ)"
        status_color = "#ef4444"
    elif latest_nav > latest_upper1:
        status_str = "🟠 偏高區 (+1.0σ ~ +2.0σ)"
        status_color = "#f59e0b"
    elif latest_nav >= latest_lower1:
        status_str = "⚪ 合理區 (-1.0σ ~ +1.0σ)"
        status_color = "#e2e8f0"
    elif latest_nav >= latest_lower2:
        status_str = "🟢 偏低區 (-2.0σ ~ -1.0σ)"
        status_color = "#22c55e"
    else:
        status_str = "🔵 便宜區 (低於 -2.0σ)"
        status_color = "#3b82f6"
        
    now_year = datetime.now().year
    last_dt = last_row['Date']
    latest_date_str = f"{last_dt.year}/{last_dt.month}/{last_dt.day}" if last_dt.year != now_year else f"{last_dt.month}/{last_dt.day}"

    summary = {
        "latest_date": latest_date_str,
        "latest_nav": latest_nav,
        "latest_ma": latest_ma,
        "bias_pct": bias_pct,
        "upper_2": latest_upper2,
        "upper_1": latest_upper1,
        "lower_1": latest_lower1,
        "lower_2": latest_lower2,
        "status_str": status_str,
        "status_color": status_color,
        "ma_period": ma_period,
        "total_records": len(df_sub),
        "start_date": df_sub['Date'].min().strftime("%Y/%m/%d"),
        "end_date": df_sub['Date'].max().strftime("%Y/%m/%d")
    }
    
    return df_sub, summary
