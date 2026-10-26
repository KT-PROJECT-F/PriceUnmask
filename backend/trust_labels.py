"""Shared Trust Score label definitions."""

from typing import Literal

TrustLabel = Literal[
    "genuine",
    "uncertain",
    "likely_inflated",
    "insufficient_data",
    "no_discount",
]
