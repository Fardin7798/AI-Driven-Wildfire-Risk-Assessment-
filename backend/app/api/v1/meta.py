from fastapi import APIRouter

from app.schemas.common import SHORT_DISCLAIMER
from app.schemas.meta import DisclaimerResponse, SourceAttribution, SourcesMetaResponse

router = APIRouter(prefix="/meta", tags=["Metadata & Governance"])


@router.get("/sources", response_model=SourcesMetaResponse)
async def list_data_source_attributions() -> SourcesMetaResponse:
    """Retrieve licenses, citations, and open data attributions for all ingested datasets."""
    return SourcesMetaResponse(
        sources=[
            SourceAttribution(
                name="NASA FIRMS",
                category="Active Thermal Anomalies",
                license="NASA Open Data Policy",
                attribution_text=(
                    "We acknowledge the use of data and/or imagery from NASA's Land, Atmosphere "
                    "near real-time Capability for EOS (LANCE) system operated by NASA's Earth "
                    "Science Data and Information System (ESDIS) with funding provided by NASA/HQ."
                ),
                url="https://firms.modaps.eosdis.nasa.gov/",
            ),
            SourceAttribution(
                name="Open-Meteo Weather & Air Quality",
                category="Synoptic Meteorological & Atmospheric Variables",
                license="Creative Commons Attribution 4.0 International (CC BY 4.0)",
                attribution_text=(
                    "Contains modified Copernicus Climate Change Service information (ERA5), "
                    "and Copernicus Atmosphere Monitoring Service information (CAMS)."
                ),
                url="https://open-meteo.com/",
            ),
            SourceAttribution(
                name="Central Pollution Control Board (CPCB) via data.gov.in",
                category="In-situ National Air Quality Index",
                license="Government Open Data License - India (GODL)",
                attribution_text=(
                    "Real time Air Quality Index published by CPCB and state pollution control "
                    "boards via Open Government Data (OGD) Platform India."
                ),
                url="https://data.gov.in/resource/3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69",
            ),
            SourceAttribution(
                name="GADM Database of Global Administrative Areas",
                category="Administrative Spatial Boundaries",
                license="GADM License (Free for academic and non-commercial research)",
                attribution_text="GADM database of Global Administrative Areas, version 4.1.",
                url="https://gadm.org/",
            ),
            SourceAttribution(
                name="ESA WorldCover 10 m 2021",
                category="High-Resolution Land Cover Fractions",
                license="Creative Commons Attribution 4.0 International (CC BY 4.0)",
                attribution_text=(
                    "ESA WorldCover 10 m 2021 v100 produced by European Space Agency (ESA) "
                    "consortium led by VITO Remote Sensing."
                ),
                url="https://esa-worldcover.org/",
            ),
        ]
    )


@router.get("/disclaimer", response_model=DisclaimerResponse)
async def get_statutory_disclaimer() -> DisclaimerResponse:
    """Retrieve statutory disclaimers, academic research scope, and official agency mandate."""
    return DisclaimerResponse(
        disclaimer=SHORT_DISCLAIMER,
        academic_mandate=(
            "This platform is an academic research decision-support prototype created as part of "
            "a B.Tech final-year engineering capstone project. It synthesizes satellite telemetry "
            "and predictive machine learning models to assess environmental wildfire susceptibility "
            "and ambient air quality trends. It DOES NOT constitute an official early-warning "
            "system, statutory civil defence alert, or emergency evacuation directive."
        ),
        official_authorities=[
            "India Meteorological Department (IMD)",
            "Central Pollution Control Board (CPCB)",
            "National Disaster Management Authority (NDMA)",
            "State Disaster Management Authorities (SDMAs)",
            "Ministry of Environment, Forest and Climate Change (MoEFCC)",
            "State Forest Departments and District Magistrate Emergency Operations Centres",
        ],
        guidance=(
            "In all events of active fire emergencies, hazardous air quality spikes, or natural "
            "hazards, the public and local administrations must comply strictly with official "
            "bulletins issued by statutory state and national authorities."
        ),
    )
