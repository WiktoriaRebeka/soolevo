# backend/app/core/net_billing.py
"""
Net-billing simulation utilities.

Funkcje:
- load_hourly_prices(csv_path)
- generate_synthetic_hourly_prices(years=3)
- build_hourly_scenarios(prices_df)
- hourly_balance_row(...)
- aggregate_monthly(...)
- rolling_deposit(...)
- simulate_year(...)

Zależności: pandas, numpy
"""
from __future__ import annotations
import os
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# -----------------------
# Konfiguracja domyślna
# -----------------------
NET_BILLING_MULTIPLIER_DEFAULT = 1.23
DEPOSIT_VALID_MONTHS_DEFAULT = 12
REFUND_LIMIT_DEFAULT = 0.20  # ustawialne: 0.20 lub 0.30
BOOTSTRAP_BLOCK_DAYS = 7  # do bootstrapu blokowego (opcjonalnie)

# -----------------------
# Loader cen godzinowych
# -----------------------
def load_hourly_prices(csv_path: str) -> pd.DataFrame:
    """
    Wczytuje CSV z godzinowymi cenami giełdowymi.
    Oczekiwany schemat:
      - timestamp (ISO)  lub date + hour
      - price_pln_kwh (float)
    Zwraca DataFrame z indeksem DatetimeIndex i kolumną 'price_pln_kwh'.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)
    # Obsługa różnych schematów
    if 'timestamp' in df.columns:
        df['ts'] = pd.to_datetime(df['timestamp'])
    elif 'date' in df.columns and 'hour' in df.columns:
        df['ts'] = pd.to_datetime(df['date']) + pd.to_timedelta(df['hour'], unit='h')
    else:
        # Spróbuj wykryć pierwszą kolumnę jako datę
        df['ts'] = pd.to_datetime(df.iloc[:, 0])

    if 'price_pln_kwh' not in df.columns:
        # spróbuj znaleźć kolumnę z 'price' w nazwie
        price_cols = [c for c in df.columns if 'price' in c.lower()]
        if not price_cols:
            raise ValueError("CSV musi zawierać kolumnę 'price_pln_kwh' lub podobną.")
        df['price_pln_kwh'] = df[price_cols[0]]

    df = df[['ts', 'price_pln_kwh']].dropna()
    df = df.set_index('ts').sort_index()
    # Upewnij się, że mamy godzinowy indeks
    df = df.resample('H').mean().interpolate()
    return df

# -----------------------
# Fallback: syntetyczne ceny
# -----------------------
def generate_synthetic_hourly_prices(start: str = None, years: int = 3) -> pd.DataFrame:
    """
    Generuje syntetyczny szereg godzinowy na potrzeby testów.
    Nie zastępuje danych giełdowych, ale pozwala uruchomić symulacje.
    """
    if start is None:
        start = datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        start = pd.to_datetime(start)

    end = start + pd.DateOffset(years=years)
    idx = pd.date_range(start=start, end=end, freq='H', closed='left')
    # Prosty model: cena bazowa + dobowy i sezonowy komponent + losowy szum
    base = 0.30  # PLN/kWh baseline
    hour = idx.hour
    # dobowy: wyższe ceny wieczorem (17-21)
    daily = 0.05 + 0.15 * ((hour >= 17) & (hour <= 21)).astype(float)
    # sezonowy: zimą wyższe ceny
    month = idx.month
    seasonal = 0.05 * ((month <= 3) | (month >= 11)).astype(float)
    noise = np.random.normal(0, 0.03, size=len(idx))
    prices = base + daily + seasonal + noise
    df = pd.DataFrame({'price_pln_kwh': prices}, index=idx)
    df = df.clip(lower=0.01)
    return df

# -----------------------
# Scenariusze cenowe
# -----------------------
def build_hourly_scenarios(prices_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """
    Tworzy scenariusze: 'base', 'high', 'low' oraz zwraca oryginalny szereg.
    - base: mediana godzinowa (dla każdej godziny doby)
    - high: base + 1 sigma (godzinowo)
    - low: base - 1 sigma
    """
    # oblicz statystyki godzinowe (dla każdej godziny doby i miesiąca)
    df = prices_df.copy()
    df['hour'] = df.index.hour
    df['month'] = df.index.month

    # Mediana dla kombinacji (month, hour)
    grouped = df.groupby(['month', 'hour'])['price_pln_kwh']
    median = grouped.median().unstack(level=0).T.stack().rename('median')
    sigma = grouped.std().unstack(level=0).T.stack().rename('sigma').fillna(0.0)

    # Funkcja budująca roczny profil na podstawie mediany/sigma
    def build_profile(multiplier: float = 0.0) -> pd.DataFrame:
        # budujemy rok od pierwszego roku w danych
        start = df.index.min().replace(month=1, day=1, hour=0)
        end = start + pd.DateOffset(years=1)
        idx = pd.date_range(start=start, end=end, freq='H', closed='left')
        rows = []
        for ts in idx:
            m = ts.month
            h = ts.hour
            med = median.loc[(m, h)]
            sig = sigma.loc[(m, h)]
            val = med + multiplier * sig
            rows.append(val)
        return pd.DataFrame({'price_pln_kwh': rows}, index=idx)

    base = build_profile(0.0)
    high = build_profile(1.0)
    low = build_profile(-1.0)
    return {'base': base, 'high': high, 'low': low, 'raw': prices_df}

# -----------------------
# Godzinowy bilans
# -----------------------
def hourly_balance_row(
    price_h: float,
    tariff_h: float,
    e_prod_h: float,
    e_cons_h: float,
    net_billing_multiplier: float = NET_BILLING_MULTIPLIER_DEFAULT,
    grid_fee_h: float = 0.0
) -> Dict[str, float]:
    """
    Dla jednej godziny zwraca:
      - e_autokonsumpcja_h
      - e_export_h
      - e_import_h
      - revenue_export_h (PLN)
      - cost_import_h (PLN)
    """
    e_autokonsumpcja_h = min(e_prod_h, e_cons_h)
    e_export_h = max(0.0, e_prod_h - e_cons_h)
    e_import_h = max(0.0, e_cons_h - e_prod_h)

    revenue_export_h = price_h * e_export_h * net_billing_multiplier
    cost_import_h = tariff_h * e_import_h + grid_fee_h

    return {
        'e_autokonsumpcja_h': e_autokonsumpcja_h,
        'e_export_h': e_export_h,
        'e_import_h': e_import_h,
        'revenue_export_h': revenue_export_h,
        'cost_import_h': cost_import_h
    }

# -----------------------
# Agregacja miesięczna
# -----------------------
def aggregate_monthly(hourly_df: pd.DataFrame) -> pd.DataFrame:
    """
    hourly_df: DataFrame z kolumnami:
      ['e_autokonsumpcja_h','e_export_h','e_import_h','revenue_export_h','cost_import_h']
    Zwraca DataFrame miesięczny z sumami.
    """
    monthly = hourly_df.resample('M').sum()
    monthly.index = monthly.index.to_period('M')
    return monthly

# -----------------------
# Rolling deposit 12m
# -----------------------
def rolling_deposit(
    monthly_revenues: pd.Series,
    monthly_costs: pd.Series,
    deposit_valid_months: int = DEPOSIT_VALID_MONTHS_DEFAULT,
    refund_limit: float = REFUND_LIMIT_DEFAULT
) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Implementacja depozytu prosumenckiego z rolling window.
    Zwraca:
      - DataFrame z kolumnami: revenue, cost, balance, refunds
      - Series cumulative_balance
    Reguła zwrotu:
      Po upływie deposit_valid_months, jeśli środki z danego miesiąca nie zostały wykorzystane,
      zwracamy min(balance, refund_limit * revenue_of_that_month).
    """
    months = monthly_revenues.index
    n = len(months)
    df = pd.DataFrame({
        'revenue': monthly_revenues.values,
        'cost': monthly_costs.values
    }, index=months)
    df['net'] = df['revenue'] - df['cost']
    df['balance'] = 0.0
    df['refund'] = 0.0

    # history of revenues with their month index
    revenue_history = []

    balance = 0.0
    for i, m in enumerate(months):
        balance += df.at[m, 'net']
        revenue_history.append({'month_idx': i, 'value': df.at[m, 'revenue']})
        # check revenues that just reached age == deposit_valid_months
        for h in revenue_history:
            age = i - h['month_idx']
            if age == deposit_valid_months:
                # compute refund for that revenue chunk
                refund_amount = min(balance, refund_limit * h['value'])
                if refund_amount > 0:
                    df.at[m, 'refund'] += refund_amount
                    balance -= refund_amount
        df.at[m, 'balance'] = balance
        # prune history older than deposit_valid_months to keep it small
        revenue_history = [h for h in revenue_history if (i - h['month_idx']) < deposit_valid_months + 1]

    return df, df['balance']

# -----------------------
# Prosta integracja baterii (heurystyka)
# -----------------------
def apply_simple_battery_strategy(
    hourly_prices: pd.Series,
    e_prod: pd.Series,
    e_cons: pd.Series,
    battery_capacity_kwh: float,
    battery_efficiency: float = 0.9,
    battery_power_kw: float = 5.0
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Prosty algorytm:
      - Ładuj baterię z PV (nadwyżka) do jej pojemności (z uwzględnieniem mocy)
      - Rozładowuj baterię w godzinach, gdy cena jest w top X% (np. top 25%)
    Zwraca zmodyfikowane serie: e_prod_after_batt, e_cons_after_batt, battery_flow (positive=discharge)
    """
    idx = hourly_prices.index
    n = len(idx)
    soc = 0.0  # state of charge (kWh)
    soc_series = np.zeros(n)
    prod_after = e_prod.copy()
    cons_after = e_cons.copy()
    battery_flow = np.zeros(n)

    # threshold: rozładowanie gdy cena >= 75 percentyl
    price_threshold = np.percentile(hourly_prices.values, 75)

    for i, ts in enumerate(idx):
        prod = e_prod.iloc[i]
        cons = e_cons.iloc[i]
        # najpierw autokonsumpcja (bez baterii) - to już będzie liczone wyżej
        # ładowanie z nadwyżki PV
        surplus = max(0.0, prod - cons)
        # limit mocy ładowania
        max_charge = min(battery_power_kw, surplus)
        charge = min(max_charge, battery_capacity_kwh - soc)
        # uwzględnij sprawność przy ładowaniu (roundtrip applied on discharge)
        soc += charge
        prod_after.iloc[i] = prod - charge  # ta energia poszła do baterii, nie do sieci
        # rozładowanie jeśli cena wysoka i jest zapotrzebowanie
        if hourly_prices.iloc[i] >= price_threshold and soc > 0:
            # ile możemy oddać (moc i soc)
            max_discharge = min(battery_power_kw, soc)
            # ile potrzeba do pokrycia konsumpcji
            needed = max(0.0, cons - prod_after.iloc[i])
            discharge = min(max_discharge, needed)
            # uwzględnij sprawność
            delivered = discharge * battery_efficiency
            soc -= discharge
            cons_after.iloc[i] = cons - delivered
            battery_flow[i] = delivered  # dodatnie = rozładowanie
        soc_series[i] = soc

    return prod_after, cons_after, pd.Series(battery_flow, index=idx)

# -----------------------
# Symulacja roku
# -----------------------
def simulate_year(
    hourly_prices: pd.DataFrame,
    production_profile_hourly: pd.Series,
    consumption_profile_hourly: pd.Series,
    tariff_hourly: pd.Series,
    params: Dict = None
) -> Dict:
    """
    Symulacja roczna:
      - hourly_prices: DataFrame index=DatetimeIndex, col 'price_pln_kwh' (rok)
      - production_profile_hourly: Series index=DatetimeIndex (rok) kWh produced each hour
      - consumption_profile_hourly: Series index=DatetimeIndex (rok) kWh consumed each hour
      - tariff_hourly: Series index=DatetimeIndex (rok) PLN/kWh retail
      - params: dict z kluczami:
          net_billing_multiplier, deposit_valid_months, refund_limit,
          grid_fee_hourly (Series or float),
          battery: dict {capacity_kwh, efficiency, power_kw} (opcjonalnie)
    Zwraca dict z:
      - hourly_df (DataFrame z kolumnami bilansu)
      - monthly_df (DataFrame)
      - deposit_df (DataFrame z rolling balance i refund)
      - annual_cashflow (dict: revenue, cost, refunds, net)
    """
    if params is None:
        params = {}
    net_mult = params.get('net_billing_multiplier', NET_BILLING_MULTIPLIER_DEFAULT)
    deposit_months = params.get('deposit_valid_months', DEPOSIT_VALID_MONTHS_DEFAULT)
    refund_limit = params.get('refund_limit', REFUND_LIMIT_DEFAULT)
    grid_fee = params.get('grid_fee_hourly', 0.0)

    # Ensure indices align
    idx = hourly_prices.index
    prod = production_profile_hourly.reindex(idx).fillna(0.0)
    cons = consumption_profile_hourly.reindex(idx).fillna(0.0)
    tariff = tariff_hourly.reindex(idx).ffill().fillna(method='ffill').fillna(0.0)

    # Battery integration (optional)
    battery_cfg = params.get('battery')
    if battery_cfg:
        prod, cons, battery_flow = apply_simple_battery_strategy(
            hourly_prices=hourly_prices['price_pln_kwh'],
            e_prod=prod,
            e_cons=cons,
            battery_capacity_kwh=battery_cfg.get('capacity_kwh', 10.0),
            battery_efficiency=battery_cfg.get('efficiency', 0.9),
            battery_power_kw=battery_cfg.get('power_kw', 5.0)
        )
    else:
        battery_flow = pd.Series(0.0, index=idx)

    # Build hourly balance
    rows = []
    for ts in idx:
        p = float(hourly_prices.at[ts, 'price_pln_kwh'])
        t = float(tariff.at[ts])
        r = hourly_balance_row(
            price_h=p,
            tariff_h=t,
            e_prod_h=float(prod.at[ts]),
            e_cons_h=float(cons.at[ts]),
            net_billing_multiplier=net_mult,
            grid_fee_h=(grid_fee.at[ts] if isinstance(grid_fee, pd.Series) else float(grid_fee))
        )
        rows.append(r)
    hourly_df = pd.DataFrame(rows, index=idx)
    # add battery_flow for diagnostics
    hourly_df['battery_flow_kwh'] = battery_flow

    # aggregate monthly
    monthly_df = aggregate_monthly(hourly_df)

    # rolling deposit
    deposit_df, balance_series = rolling_deposit(
        monthly_revenues=monthly_df['revenue'],
        monthly_costs=monthly_df['cost'],
        deposit_valid_months=deposit_months,
        refund_limit=refund_limit
    )

    annual_cashflow = {
        'total_revenue': float(monthly_df['revenue'].sum()),
        'total_cost': float(monthly_df['cost'].sum()),
        'total_refunds': float(deposit_df['refund'].sum()),
        'net': float(monthly_df['revenue'].sum() - monthly_df['cost'].sum() - deposit_df['refund'].sum())
    }

    return {
        'hourly_df': hourly_df,
        'monthly_df': monthly_df,
        'deposit_df': deposit_df,
        'annual_cashflow': annual_cashflow
    }

# -----------------------
# Helper: przygotowanie godzinowych profili z rocznych wartości
# -----------------------
def expand_annual_to_hourly(annual_kwh: float, daily_profile: Dict[str, float], year_start: Optional[str] = None) -> pd.Series:
    """
    Rozszerza roczną wartość (kWh) do serii godzinowej na rok, używając prostego profilu dziennego.
    daily_profile: {'morning':0.23,'day':0.18,'evening':0.48,'night':0.11}
    Mapowanie godzin:
      morning 6-9 (4h), day 10-15 (6h), evening 16-21 (6h), night 22-5 (8h)
    """
    if year_start is None:
        year_start = datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        year_start = pd.to_datetime(year_start)
    idx = pd.date_range(start=year_start, periods=24*365, freq='H')
    # map hours to periods
    def period_of_hour(h):
        if 6 <= h <= 9:
            return 'morning'
        if 10 <= h <= 15:
            return 'day'
        if 16 <= h <= 21:
            return 'evening'
        return 'night'
    weights = np.array([daily_profile[period_of_hour(h)] for h in idx.hour])
    # normalize to sum=1 over year
    weights = weights / weights.sum()
    hourly = pd.Series(weights * annual_kwh, index=idx)
    return hourly

# -----------------------
# Public helper: generate scenarios from CSV or synthetic
# -----------------------
def generate_price_scenarios(csv_path: Optional[str] = None, fallback_years: int = 3) -> Dict[str, pd.DataFrame]:
    """
    Jeśli csv_path istnieje -> wczytaj i zbuduj scenariusze.
    W przeciwnym razie -> wygeneruj syntetyczne ceny i zbuduj scenariusze.
    """
    if csv_path and os.path.exists(csv_path):
        prices = load_hourly_prices(csv_path)
    else:
        prices = generate_synthetic_hourly_prices(years=fallback_years)
    scenarios = build_hourly_scenarios(prices)
    return scenarios

# -----------------------
# Example usage (do testów)
# -----------------------
if __name__ == "__main__":
    # quick smoke test
    scenarios = generate_price_scenarios(None, fallback_years=1)
    base_prices = scenarios['base']
    # create synthetic production/consumption
    annual_prod = 8000.0
    annual_cons = 7000.0
    daily_profile = {'morning':0.23,'day':0.18,'evening':0.48,'night':0.11}
    prod_h = expand_annual_to_hourly(annual_prod, daily_profile, year_start=base_prices.index.min())
    cons_h = expand_annual_to_hourly(annual_cons, daily_profile, year_start=base_prices.index.min())
    # tariff: simple flat 1.09 PLN/kWh
    tariff = pd.Series(1.09, index=base_prices.index)
    res = simulate_year(base_prices, prod_h, cons_h, tariff, params={'net_billing_multiplier':1.23})
    print("Annual cashflow:", res['annual_cashflow'])