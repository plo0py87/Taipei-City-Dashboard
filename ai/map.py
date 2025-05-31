import pandas as pd
import requests
import time
import urllib.parse

# Your Google Maps API key
API_KEY = ''

# Load CSV file
df = pd.read_csv("1.csv")

# Function to get coordinates from address
def get_coordinates(address):
    if not isinstance(address, str) or address.strip() == "":
        return None, None

    encoded_address = urllib.parse.quote(address)
    base_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_address}&key={API_KEY}"

    try:
        response = requests.get(base_url)
        result = response.json()
        if result['status'] == 'OK':
            location = result['results'][0]['geometry']['location']
            return location['lng'], location['lat']
        else:
            print(f"Error for address '{address}': {result['status']}, message: {result.get('error_message')}")
            return None, None
    except Exception as e:
        print(f"Exception for address '{address}': {e}")
        return None, None

# Geocode each address
longitudes = []
latitudes = []

for addr in df['地址']:
    lon, lat = get_coordinates(addr)
    longitudes.append(lon)
    latitudes.append(lat)
    print(f"Geocoded: {addr} => ({lon}, {lat})")
    time.sleep(0.2)  # To avoid hitting rate limits

# Add new columns
df['longitude'] = longitudes
df['latitude'] = latitudes

# Save to new CSV
df.to_csv("hospitals_with_coords.csv", index=False)
print("Geocoding complete. Output saved to hospitals_with_coords.csv")