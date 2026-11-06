AQI_BINS = [0, 50, 100, 200, 300, 400, 500]
AQI_LABELS = ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"]


def build_cpcb_urls(reqd_date: str) -> tuple[str, str]:
    """reqd_date format: YYYY_MM_DD. Returns (primary_url, fallback_url).

    cpcb.nic.in now 301-redirects to cpcb.gov.in, so we go straight to the
    redirect target (the old HEAD-without-redirect check treated the 301 as
    "missing" and always fell through to the 15-page national bulletin)."""
    primary = f"https://cpcb.gov.in/upload/Downloads/Delhi-NCR/NCR_AQI_Bulletin_{reqd_date}.pdf"
    fallback = f"https://cpcb.gov.in/upload/Downloads/AQI_Bulletin_{reqd_date.replace('_', '')}.pdf"
    return primary, fallback


def aqi_category(aqi) -> str | None:
    """CPCB National AQI category for a numeric index value."""
    try:
        value = float(aqi)
    except (TypeError, ValueError):
        return None
    for upper, label in zip(AQI_BINS[1:], AQI_LABELS):
        if value <= upper:
            return label
    return AQI_LABELS[-1]
