import math
import requests
import streamlit as st
from astral.sun import azimuth, elevation

def search_city(city_name):
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json&limit=1"
        headers = {'User-Agent': 'SolarPathVisualizer_v1'}
        resp = requests.get(url, headers=headers).json()
        if resp: return [float(resp[0]['lat']), float(resp[0]['lon'])]
    except: return None
    return None

@st.cache_data(ttl=600)
def get_environmental_data(lat, lon):
    api_key = "d4b056a2-a4bc-48d0-9a38-3f5a2c675ea7"
    url = f"http://api.airvisual.com/v2/nearest_city?lat={lat}&lon={lon}&key={api_key}"
    # Default values to prevent dashboard errors
    env = {"aqi": "N/A", "temp": "N/A", "hum": "N/A", "wind": "N/A", "color": "#444", "label": "Unknown"}
    try:
        r = requests.get(url, timeout=5).json()
        if r.get("status") == "success":
            data = r["data"]["current"]
            env.update({"aqi": data["pollution"]["aqius"], "temp": data["weather"]["tp"], "hum": data["weather"]["hu"], "wind": data["weather"]["ws"]})
            aqi = env["aqi"]
            if aqi <= 50: env["label"], env["color"] = "Good", "#00e400"
            elif aqi <= 100: env["label"], env["color"] = "Moderate", "#ffff00"
            elif aqi <= 150: env["label"], env["color"] = "Unhealthy(S)", "#ff7e00"
            else: env["label"], env["color"] = "Unhealthy", "#ff0000"
    except: pass
    return env

def get_solar_pos(city_info, t, r, clat, clon):
    az_val = azimuth(city_info.observer, t)
    el_val = elevation(city_info.observer, t)
    sc = math.cos(math.radians(max(0, el_val)))
    slat = clat + (r * sc / 111111) * math.cos(math.radians(az_val))
    slon = clon + (r * sc / (111111 * math.cos(math.radians(clat)))) * math.sin(math.radians(az_val))
    shlat = clat + (r * 0.7 / 111111) * math.cos(math.radians(az_val + 180))
    shlon = clon + (r * 0.7 / (111111 * math.cos(math.radians(clat)))) * math.sin(math.radians(az_val + 180))
    return slat, slon, shlat, shlon, az_val, el_val

def get_edge(lat, lon, az_input, radius):
    rad = math.radians(az_input)
    return [lat + (radius/111111)*math.cos(rad), lon + (radius/(111111*math.cos(math.radians(lat))))*math.sin(rad)]




def calculate_solar_radiation(elevation_deg):
    """
    Calculates estimated Global Horizontal Irradiance (W/m2).
    """
    if elevation_deg <= 0:
        return 0
    
    # Convert elevation to radians
    el_rad = math.radians(elevation_deg)
    
    # Air Mass calculation
    air_mass = 1 / (math.sin(el_rad) + 0.001)
    
    # Solar Constant
    I0 = 1367 
    
    # Clear sky transmission
    transmission = 0.7 ** (air_mass ** 0.678)
    radiation = I0 * math.sin(el_rad) * transmission
    
    return round(radiation, 2)

import math

def normalize_inputs(ghi, temp, humidity, et):
    # Recalibrated denominators to make the score more dynamic
    Sn = min(max(ghi / 800, 0), 1)         # 800 W/m² is a more realistic high average
    Tn = min(max((temp - 10) / 30, 0), 1)   # Heat impact starts at 10°C
    Hn = min(max(humidity / 100, 0), 1)
    ETn = min(max(et / 8, 0), 1)           # 8mm/day is significant ET
    return Sn, Tn, Hn, ETn

def calculate_wss_breakdown(ghi, temp, humidity):
    try:
        temp, ghi, humidity = float(temp), float(ghi), float(humidity)
    except:
        temp, ghi, humidity = 25.0, 0.0, 50.0

    et = (0.0023 * ghi * (temp + 17.8)) / 50
    Sn, Tn, Hn, ETn = normalize_inputs(ghi, temp, humidity, et)
    
    # Calculate weighted contributions for the bar chart
    solar_impact = 0.35 * Sn * 100
    temp_impact = 0.25 * Tn * 100
    et_impact = 0.25 * ETn * 100
    hum_impact = 0.15 * (1 - Hn) * 100
    
    total_wss = round(solar_impact + temp_impact + et_impact + hum_impact, 2)
    
    return total_wss, [solar_impact, temp_impact, et_impact, hum_impact]

def classify_wss(wss):
    if wss < 40:
        return {
            "color": "#2ecc71", 
            "status": "Low", 
            "actions": ["✅ Maintain standard schedule", "✅ Monitor soil moisture", "✅ Check for pipe leaks"],
            "savings": {"water": "5%", "cost": "AED 150", "evap": "5%"}
        }
    elif wss < 70:
        return {
            "color": "#f39c12", 
            "status": "Moderate", 
            "actions": ["⚠️ Shift watering to 6:30 PM", "⚠️ Reduce non-essential use", "⚠️ Check mulch layers"],
            "savings": {"water": "15%", "cost": "AED 450", "evap": "12%"}
        }
    else:
        return {
            "color": "#e74c3c", 
            "status": "Extreme", 
            "actions": ["🚨 Reduce irrigation by 40%", "🚨 Activate drip-only mode", "🚨 Use recycled water only"],
            "savings": {"water": "28%", "cost": "AED 1,250", "evap": "22%"}
        }
      
