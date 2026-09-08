"""Data ingestion — per-source adapters behind one protocol.

Parse only, no transformation. Idempotent and re-runnable. Every run records an
ingestion_run and stamps rows with a data_vintage id. Raw payloads are also
written unmodified to data/raw/ as Parquet/JSON.

v0.1 sources: yfinance, stooq (price), openfigi (symbology), riksbank (fx).
Stubs: borsdata, eodhd — interface only, disabled until signed off.
"""
