"""Reference data — the identity and universe layer.

- securities.py        : seed list loader; security + security_xref (ISIN-keyed,
                         ticker/MIC history with validity ranges).
- corporate_actions.py : splits, dividends, ticker changes, M&A, delisting,
                         bankruptcy; listing_status_history + delisting_return.
- universe.py          : time-varying universe_membership. "The universe on date
                         t" is an as-of query, never SELECT * FROM security.

The seed list deliberately includes delisted / acquired / bankrupt names so
survivorship handling is exercised from day one. Not implemented yet.
"""
