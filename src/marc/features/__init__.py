"""Feature engineering — pure, causal, versioned.

Every feature is a function of a price/volume history truncated at t. No window
may reference a future bar. MUST NOT import ``marc.targets`` (enforced by
``tests/test_layering.py``).
"""

from marc.features.registry import (
    FEATURE_NAMES,
    FEATURE_SET_VERSION,
    FEATURES,
    compute_feature_frame,
)

__all__ = ["FEATURE_NAMES", "FEATURE_SET_VERSION", "FEATURES", "compute_feature_frame"]
