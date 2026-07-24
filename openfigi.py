import json
import logging
import re
import time
from typing import TypedDict

import pandas as pd
import requests

from models import OpenFigiPayloadByCountry
from utilities import normalise_key, load_exchange_map, build_openfigi_payload_by_country

API_URL = "https://api.openfigi.com/v3/mapping"

EXCHANGE_MAP = load_exchange_map("exchange_mapping.json")


def fetch_openfigi_batch(
    tickers: list[str], 
    target_security_type: str, 
    country_exch_code: str, 
    api_key: str
) -> list[dict]:
    """Fetches OpenFIGI data for a batch of tickers, filtering for a specific
    security type and country exchange code. Returns a list of dictionaries with
    the results, including status and relevant OpenFIGI fields.
    """
    headers = {"Content-Type": "application/json"}

    if api_key and api_key != "YOUR_OPENFIGI_API_KEY":
        headers["X-OPENFIGI-APIKEY"] = api_key
    else:
        logging.warning("Continuing without API key. Rate limits will be lower.")

    payload = build_openfigi_payload_by_country(tickers, country_exch_code)
    results = []

    try:
        response = requests.post(API_URL, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

        for idx, item in enumerate(data):
            original_ticker = tickers[idx]

            if "error" in item:
                results.append(
                    {
                        "Ticker": original_ticker,
                        "OpenFIGI_Status": "Not Found / Delisted",
                        "OpenFIGI_CompanyName": None,
                        "OpenFIGI_SecurityType": None,
                        "OpenFIGI_Exchange_Code": None,
                    }
                )
            else:
                matches = item.get("data", [])
                
                # 1. Filter for requested security type
                stock_matches = [
                    m for m in matches 
                    if m.get("securityType2") == target_security_type
                ]

                # 2. Grab the primary stock match
                valid_match = stock_matches[0] if stock_matches else None

                if valid_match:
                    results.append(
                        {
                            "Ticker": original_ticker,
                            "OpenFIGI_Status": "Verified Active",
                            "OpenFIGI_CompanyName": valid_match.get("name"),
                            "OpenFIGI_SecurityType": valid_match.get("securityType2"),
                            "OpenFIGI_Exchange_Code": valid_match.get("exchCode"),
                        }
                    )
                else:
                    results.append(
                        {
                            "Ticker": original_ticker,
                            "OpenFIGI_Status": "No Common Stock Match",
                            "OpenFIGI_CompanyName": None,
                            "OpenFIGI_SecurityType": None,
                            "OpenFIGI_Exchange_Code": country_exch_code,
                        }
                    )

    except requests.exceptions.RequestException as e:
        print(f"API Request Failed: {e}")
        for ticker in tickers:
            results.append(
                {
                    "Ticker": ticker,
                    "OpenFIGI_Status": "API Error",
                    "OpenFIGI_CompanyName": None,
                    "OpenFIGI_SecurityType": None,
                    "OpenFIGI_Exchange_Code": country_exch_code,
                }
            )

    return results


if __name__ == "__main__":
    main()