def build_cpcb_urls(reqd_date: str) -> tuple[str, str]:
    """reqd_date format: YYYY_MM_DD. Returns (primary_url, fallback_url)."""
    primary = f"https://cpcb.nic.in//upload/Downloads/Delhi-NCR/NCR_AQI_Bulletin_{reqd_date}.pdf"
    fallback = f"https://cpcb.gov.in//upload/Downloads/AQI_Bulletin_{reqd_date.replace('_', '')}.pdf"
    return primary, fallback
