from __future__ import annotations

import pytest
from datetime import datetime, timezone

from backend.connectors import (
    ERA5Connector,
    GFSConnector,
    IMDConnector,
    MOSDACConnector,
    get_all_connectors,
    get_connector,
)


def test_connector_factory():
    imd = get_connector("IMD")
    assert isinstance(imd, IMDConnector)
    assert imd.source_name == "IMD"

    mosdac = get_connector("ISRO-MOSDAC")
    assert isinstance(mosdac, MOSDACConnector)
    assert mosdac.source_name == "ISRO-MOSDAC"

    gfs = get_connector("GFS/WRF")
    assert isinstance(gfs, GFSConnector)
    assert gfs.source_name == "GFS/WRF"

    era5 = get_connector("ERA5")
    assert isinstance(era5, ERA5Connector)
    assert era5.source_name == "ERA5"

    with pytest.raises(ValueError):
        get_connector("UNKNOWN_SOURCE")


def test_get_all_connectors():
    all_conns = get_all_connectors()
    assert len(all_conns) == 4
    sources = {c.source_name for c in all_conns}
    assert sources == {"IMD", "ISRO-MOSDAC", "GFS/WRF", "ERA5"}


def test_imd_parser_with_sample_station():
    connector = IMDConnector()
    payload = {
        "stations": [
            {
                "station_id": "DELHI_SAF",
                "latitude": 28.585,
                "longitude": 77.206,
                "temperature": 34.5,
                "humidity": 60.0,
                "rainfall": 15.2,
                "wind_speed": 18.0,
                "pressure": 1008.5,
                "timestamp": "2026-09-11T12:00:00+00:00",
            }
        ]
    }
    records = connector.parse_station_payload(payload)
    assert len(records) == 1
    rec = records[0]
    assert rec["source"] == "IMD"
    assert rec["station_id"] == "DELHI_SAF"
    assert rec["latitude"] == 28.585
    assert rec["longitude"] == 77.206
    assert rec["parameters"]["temperature"] == 34.5
    assert rec["parameters"]["rainfall"] == 15.2


def test_mosdac_parser_with_satellite_properties():
    connector = MOSDACConnector()
    payload = {
        "products": [
            {
                "properties": {
                    "grid_id": "INSAT3D-BOB-01",
                    "latitude": 16.5,
                    "longitude": 86.0,
                    "rain_rate": 28.4,
                    "cloud_fraction": 0.85,
                    "sst": 29.2,
                    "observation_time": "2026-09-11T12:00:00+00:00",
                }
            }
        ]
    }
    records = connector.parse_satellite_payload(payload)
    assert len(records) == 1
    rec = records[0]
    assert rec["source"] == "ISRO-MOSDAC"
    assert rec["station_id"] == "INSAT3D-BOB-01"
    assert rec["parameters"]["rainfall"] == 28.4
    assert rec["parameters"]["cloud_cover"] == 85.0
    assert rec["parameters"]["sea_surface_temp"] == 29.2


def test_gfs_parser_with_current_fields():
    connector = GFSConnector()
    payload = {
        "current": {
            "temperature_2m": 31.0,
            "relative_humidity_2m": 72.0,
            "precipitation": 12.0,
            "wind_speed_10m": 22.0,
            "surface_pressure": 1004.0,
            "time": "2026-09-11T12:00:00Z",
        }
    }
    record = connector.parse_gfs_api_response(payload, "GFS-TEST", 21.0, 79.0)
    assert record is not None
    assert record["source"] == "GFS/WRF"
    assert record["station_id"] == "GFS-TEST"
    assert record["parameters"]["temperature"] == 31.0
    assert record["parameters"]["humidity"] == 72.0
    assert record["parameters"]["rainfall"] == 12.0


def test_era5_parser_with_hourly_fields():
    connector = ERA5Connector()
    payload = {
        "hourly": {
            "time": ["2026-09-06T12:00:00Z"],
            "temperature_2m": [28.2],
            "relative_humidity_2m": [65.0],
            "precipitation": [5.5],
            "surface_pressure": [1012.0],
            "wind_speed_10m": [11.0],
        }
    }
    record = connector.parse_era5_json(payload, "ERA5-DELHI", 28.61, 77.23)
    assert record is not None
    assert record["source"] == "ERA5"
    assert record["station_id"] == "ERA5-DELHI"
    assert record["parameters"]["temperature"] == 28.2
    assert record["parameters"]["rainfall"] == 5.5


def test_connectors_telemetry_fallbacks():
    imd = IMDConnector()
    imd_records = imd._generate_telemetry_records()
    assert len(imd_records) > 0
    assert imd_records[0]["source"] == "IMD"

    mosdac = MOSDACConnector()
    mosdac_records = mosdac._generate_swath_telemetry()
    assert len(mosdac_records) > 0
    assert mosdac_records[0]["source"] == "ISRO-MOSDAC"

    gfs = GFSConnector()
    gfs_records = gfs._generate_model_telemetry()
    assert len(gfs_records) > 0
    assert gfs_records[0]["source"] == "GFS/WRF"

    era5 = ERA5Connector()
    era5_records = era5._generate_climatological_records()
    assert len(era5_records) > 0
    assert era5_records[0]["source"] == "ERA5"
