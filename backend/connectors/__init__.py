"""WeatherGPT Data Connectors Package.

Exposes real HTTP/API connectors for IMD, ISRO MOSDAC, NOAA GFS, and ECMWF ERA5.
"""

from .base import BaseConnector, ConnectorError
from .era5 import ERA5Connector
from .gfs import GFSConnector
from .imd import IMDConnector
from .mosdac import MOSDACConnector

__all__ = [
    "BaseConnector",
    "ConnectorError",
    "IMDConnector",
    "MOSDACConnector",
    "GFSConnector",
    "ERA5Connector",
    "get_connector",
    "get_all_connectors",
]


def get_connector(source_name: str) -> BaseConnector:
    """Retrieve an instantiated connector by its source key."""
    normalized = source_name.strip().upper()
    if "IMD" in normalized:
        return IMDConnector()
    if "MOSDAC" in normalized or "ISRO" in normalized:
        return MOSDACConnector()
    if "GFS" in normalized or "WRF" in normalized or "NOAA" in normalized:
        return GFSConnector()
    if "ERA5" in normalized or "ECMWF" in normalized or "CDS" in normalized:
        return ERA5Connector()
    raise ValueError(f"Unknown data source connector: {source_name}")


def get_all_connectors() -> list[BaseConnector]:
    """Retrieve instances of all active connectors."""
    return [
        IMDConnector(),
        MOSDACConnector(),
        GFSConnector(),
        ERA5Connector(),
    ]
