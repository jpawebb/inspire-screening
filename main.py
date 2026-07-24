import json
import logging
import re
import os
import time
from typing import TypedDict
from dotenv import load_dotenv
from tqdm import tqdm

import pandas as pd
import requests

from openfigi import fetch_openfigi_batch, normalise_key, EXCHANGE_MAP

load_dotenv()

OPENFIGI_API_KEY = os.getenv("OPENFIGI_API_KEY")

TARGET_COUNTRY, TARGET_COUNTRY_EXCH = "UNITED_KINGDOM", "LN"
TARGET_SECURITY_TYPE = "Common Stock"

DATA_FILE = "data/2026 Q3 Score Updates.xlsx"

def main():
    all_results = []
    batch_size = 100

    frames = pd.read_excel(DATA_FILE, sheet_name=None)
    all_scores = pd.concat(list(frames.values()), axis=0).reset_index(
        drop=True
    )

    print("========== DATA ANALYSIS ==========")
    print(f"Total companies: {len(all_scores)}")

    null_count_by_row = all_scores.isnull().sum(axis=1)
    print(f"Total NULLs: {null_count_by_row.sum()}")
    print(f"Rows with NULLs: \n{all_scores[all_scores.isnull().any(axis=1)]}")
    print(
        f"Unique 'Security Type' values: \n{list(all_scores['Security Type'].unique())}"
    )

    if TARGET_COUNTRY:
        target_norm = normalise_key(TARGET_COUNTRY)

        # Vectorized check: normalise the Excel column values to match our target
        mask = (
            all_scores["Exchange Location"]
            .astype(str)
            .apply(normalise_key)
            .isin(
                [
                    target_norm,
                    EXCHANGE_MAP.get(target_norm),
                ]
            )
        )
        all_scores = all_scores[mask].copy()
        print(
            f"Filtered for '{TARGET_COUNTRY}': {len(all_scores)} rows remaining."
        )

        if all_scores.empty:
            print(
                f"No records found matching target country: '{TARGET_COUNTRY}'"
            )
            return

    # Group DataFrame by Exchange Location
    grouped = all_scores.groupby("Exchange Location")

    for raw_location, group in grouped:
        normalised_loc = normalise_key(raw_location)
        exch_code = EXCHANGE_MAP.get(normalised_loc)

        if not exch_code:
            print(
                f"Warning: Location '{raw_location}' couldn't be mapped in JSON. Skipping."
            )
            continue

        tickers = group["Ticker"].dropna().unique().tolist()
        print(
            f"\nProcessing '{raw_location}' -> Code: '{exch_code}' ({len(tickers)} unique tickers)..."
        )

        # Chunk tickers into batches of 100
        for i in tqdm(range(0, len(tickers), batch_size)):
            chunk = tickers[i : i + batch_size]
            batch_results = fetch_openfigi_batch(chunk, TARGET_SECURITY_TYPE, exch_code, OPENFIGI_API_KEY)
            all_results.extend(batch_results)

            time.sleep(0.5)

    if all_results:
        openfigi_df = pd.DataFrame(all_results).drop_duplicates(
            subset=["Ticker"]
        )
        final_df = pd.merge(all_scores, openfigi_df, on="Ticker", how="left")

        print("\n========== VERIFICATION COMPLETE ==========")
        print(
            f"Final output shape: {final_df.shape} (All input columns preserved)"
        )
        print(
            f"New OpenFIGI Status counts:\n{final_df['OpenFIGI_Status'].value_counts()}"
        )

        final_df.to_excel(
            f"{DATA_FILE.split('.')[0]}_Verified.xlsx", index=False
        )
        print(f"\nSaved verified data to '{DATA_FILE.split('.')[0]}_Verified.xlsx'")
    else:
        print("\nNo results generated.")

if __name__ == "__main__":
    main()