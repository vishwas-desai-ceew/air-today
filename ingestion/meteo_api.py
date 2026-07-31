import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry
from pathlib import Path

# run cron at 5:30 pm

PARENT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PARENT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def fetch_meteo_api_data():
    
    # Setup the Open-Meteo API client with cache and retry on error
    cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
    retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
    openmeteo = openmeteo_requests.Client(session = retry_session)

    # The order of variables in hourly or daily is important to assign them correctly below
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 28.6448,
        "longitude": 77.216721,
        "hourly": ["temperature_2m", "boundary_layer_height", "wind_speed_10m", "rain"],
        "models": "best_match",
        "timezone": "GMT",
        "forecast_days": 3,
        "wind_speed_unit": "ms"
    }
    responses = openmeteo.weather_api(url, params=params)

    # Process first location. Add a for-loop for multiple locations or weather models
    response = responses[0]
    print(f"Coordinates: {response.Latitude()}°N {response.Longitude()}°E")
    print(f"Elevation: {response.Elevation()} m asl")
    print(f"Timezone: {response.Timezone()}{response.TimezoneAbbreviation()}")
    print(f"Timezone difference to GMT+0: {response.UtcOffsetSeconds()}s")

    # Process hourly data. The order of variables needs to be the same as requested.
    hourly = response.Hourly()
    hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
    hourly_boundary_layer_height = hourly.Variables(1).ValuesAsNumpy()
    hourly_wind_speed_10m = hourly.Variables(2).ValuesAsNumpy()
    hourly_rain = hourly.Variables(3).ValuesAsNumpy()

    hourly_data = {"date": pd.date_range(
        start = pd.to_datetime(hourly.Time(), unit = "s", utc = True),
        end = pd.to_datetime(hourly.TimeEnd(), unit = "s", utc = True),
        freq = pd.Timedelta(seconds = hourly.Interval()),
        inclusive = "left"
    )}

    hourly_data["temperature_2m"] = hourly_temperature_2m
    hourly_data["boundary_layer_height"] = hourly_boundary_layer_height
    hourly_data["wind_speed_10m"] = hourly_wind_speed_10m
    hourly_data["rain"] = hourly_rain

    hourly_dataframe = pd.DataFrame(data = hourly_data)
    return hourly_dataframe


def save_hourly_data_to_csv(df):
    df['date'] = pd.to_datetime(df['date'], utc=True)
    df['date'] = df['date'].dt.tz_convert("Asia/Kolkata")
    df.to_csv(DATA_DIR / "meteo_api_hourly.csv", index = False)
    print(f"Hourly data written to {DATA_DIR / 'meteo_api_hourly.csv'}")



if __name__ == "__main__":
    df = fetch_meteo_api_data()  
    save_hourly_data_to_csv(df)