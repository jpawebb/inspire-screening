import json
import re
import pandas as pd

from models import OpenFigiPayloadByCountry

def normalise_key(text: str) -> str:
    """Removes underscores, spaces, and non-alphanumeric chars, converting to UPPERCASE.

    'United Kingdom', 'UNITED_KINGDOM', and 'united kingdom' all become 'UNITEDKINGDOM'.
    """
    if not text or pd.isna(text):
        return ""
    return re.sub(r"[^A-Z0-9]", "", str(text).upper())


def build_openfigi_payload_by_country(
    tickers: list[str], country_exch_code: str
) -> list[OpenFigiPayloadByCountry]:
    """Constructs the batch payload for OpenFIGI API using a country exchange prefix. e.g. LN for United kingdom"""
    return [
        {"idType": "TICKER", "idValue": ticker, "exchCode": country_exch_code}
        for ticker in tickers
    ]

def load_exchange_map(filepath: str) -> dict[str, str]:
    """Loads exchange_mapping.json and builds a normalized lookup dict."""
    with open(filepath, "r") as f:
        data = json.load(f)

    lookup = {}
    for entry in data.get("exchanges", []):
        code = entry.get("code")
        country = entry.get("country")
        if country and code:
            lookup[normalise_key(country)] = code
            lookup[normalise_key(code)] = code

    return lookup