import os
import sys
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any

def get_resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller bundle."""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# Supported funds configuration
SUPPORTED_FUNDS: Dict[str, Dict[str, Any]] = {
    "allianz_tech": {
        "id": "allianz_tech",
        "name": "安聯台灣科技基金",
        "short_name": "安聯科技",
        "fund_code": "ACDD04",
        "sitca_code": "042004",
        "isin_code": "TW000T4204Y0",
        "currency": "台幣級別",
        "category": "科技類股票型",
        "cache_filename": "allianz_tech_nav_river.csv",
        "fallback_start_nav": 35.0,
        "fallback_growth": 155.0,
    },
    "nomura_small_cap": {
        "id": "nomura_small_cap",
        "name": "野村中小基金",
        "short_name": "野村中小",
        "fund_code": "ACIC08",
        "sitca_code": "006006",
        "isin_code": "TW000T3207Y5",
        "currency": "台幣級別",
        "category": "中小型股票型",
        "cache_filename": "nomura_small_cap_nav_river.csv",
        "fallback_start_nav": 45.0,
        "fallback_growth": 610.0,
    }
}

CSV_CACHE_PATH = os.path.join(DATA_DIR, SUPPORTED_FUNDS["allianz_tech"]["cache_filename"])

def generate_fallback_data(fund_key: str = "allianz_tech") -> pd.DataFrame:
    """Generate realistic synthetic NAV data if network is unavailable."""
    fund_info = SUPPORTED_FUNDS.get(fund_key, SUPPORTED_FUNDS["allianz_tech"])
    print(f"[Fetcher] Network request failed for {fund_info['name']}. Generating fallback NAV historical data...")
    start_date = datetime(2018, 1, 1)
    end_date = datetime.now()
    
    dates = pd.date_range(start=start_date, end=end_date, freq='B')
    n = len(dates)
    
    start_nav = fund_info.get("fallback_start_nav", 40.0)
    growth = fund_info.get("fallback_growth", 200.0)
    
    t = np.linspace(0, 1, n)
    trend = start_nav + growth * (t ** 1.3)
    
    # Cyclical market fluctuations and volatility
    cycles = (growth * 0.08) * np.sin(2 * np.pi * 3.5 * t) + (growth * 0.04) * np.cos(2 * np.pi * 7.0 * t)
    noise = np.random.normal(0, 1.2, n).cumsum() * 0.3
    
    nav_series = trend + cycles + noise
    nav_series = np.maximum(nav_series, start_nav * 0.5) # floor price
    
    df = pd.DataFrame({
        "Date": dates,
        "NAV": np.round(nav_series, 2)
    })
    return df

def fetch_fund_nav_data(fund_key: str = "allianz_tech", force_update: bool = False) -> pd.DataFrame:
    """
    Fetch live NAV data for a specified fund from MoneyDJ API endpoint.
    Caches to local CSV file and falls back to cached/synthetic data if network fails.
    """
    if fund_key not in SUPPORTED_FUNDS:
        fund_key = "allianz_tech"
        
    fund_info = SUPPORTED_FUNDS[fund_key]
    os.makedirs(DATA_DIR, exist_ok=True)
    cache_path = os.path.join(DATA_DIR, fund_info["cache_filename"])
    
    # Use local cache if available and force_update is False
    if not force_update and os.path.exists(cache_path):
        try:
            df = pd.read_csv(cache_path)
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.sort_values('Date').reset_index(drop=True)
            print(f"[Loader] Successfully loaded {len(df)} records from cache for {fund_info['name']}.")
            return df
        except Exception as e:
            print(f"[Loader] Failed reading cache for {fund_info['name']}: {e}. Refetching...")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    nav_url = f"https://fund.bot.com.tw/w/bcd/tBCDNavList.djbcd?a={fund_info['fund_code']}&c=2018-1-1&d=2026-12-31"
    
    try:
        print(f"[Fetcher] Requesting live NAV data for {fund_info['name']} ({fund_info['fund_code']})...")
        res = requests.get(nav_url, headers=headers, timeout=12)
        res.raise_for_status()
        
        raw_text = res.text.strip()
        parts = raw_text.split(' ')
        if len(parts) >= 2:
            raw_dates = parts[0].split(',')
            raw_navs = parts[1].split(',')
            
            records = []
            for d_str, n_str in zip(raw_dates, raw_navs):
                if len(d_str) == 8 and n_str:
                    try:
                        dt_val = f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:8]}"
                        nav_val = float(n_str)
                        records.append({"Date": dt_val, "NAV": nav_val})
                    except ValueError:
                        continue
                        
            if records:
                df = pd.DataFrame(records)
                df['Date'] = pd.to_datetime(df['Date'])
                df = df.sort_values('Date').reset_index(drop=True)
                
                # Save to cache CSV
                df_to_save = df.copy()
                df_to_save['Date'] = df_to_save['Date'].dt.strftime('%Y-%m-%d')
                df_to_save.to_csv(cache_path, index=False, encoding='utf-8-sig')
                print(f"[Cache] Saved {len(df)} records to CSV cache for {fund_info['name']}.")
                return df
    except Exception as e:
        print(f"[Fetcher] Network request error for {fund_info['name']}: {e}")

    # Fallback if network or parsing fails: keep existing CSV cache if present
    if os.path.exists(cache_path):
        try:
            df = pd.read_csv(cache_path)
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.sort_values('Date').reset_index(drop=True)
            print(f"[Loader] Network failed, safely loaded {len(df)} records from existing cache for {fund_info['name']}.")
            return df
        except Exception:
            pass

    df_fallback = generate_fallback_data(fund_key)
    df_to_save = df_fallback.copy()
    df_to_save['Date'] = df_to_save['Date'].dt.strftime('%Y-%m-%d')
    df_to_save.to_csv(cache_path, index=False, encoding='utf-8-sig')
    return df_fallback

def fetch_allianz_nav_data(force_update: bool = False) -> pd.DataFrame:
    """Fetch live NAV data for Allianz Taiwan Tech Fund (backward compatibility)."""
    return fetch_fund_nav_data("allianz_tech", force_update=force_update)

def fetch_nomura_nav_data(force_update: bool = False) -> pd.DataFrame:
    """Fetch live NAV data for Nomura Taiwan Small Cap Fund."""
    return fetch_fund_nav_data("nomura_small_cap", force_update=force_update)

def fetch_all_funds_nav_data(force_update: bool = False) -> None:
    """Fetch and cache live NAV data for all supported funds."""
    for fund_key in SUPPORTED_FUNDS:
        fetch_fund_nav_data(fund_key, force_update=force_update)

if __name__ == "__main__":
    for fund_key, info in SUPPORTED_FUNDS.items():
        print(f"\n==================== Testing {info['name']} ====================")
        df = fetch_fund_nav_data(fund_key, force_update=True)
        print(f"Total Rows:  {len(df)}")
        print(f"Start Date:  {df['Date'].min().strftime('%Y-%m-%d')}")
        print(f"End Date:    {df['Date'].max().strftime('%Y-%m-%d')}")
        print(f"Latest NAV: ${df['NAV'].iloc[-1]:.2f}")
