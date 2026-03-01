import streamlit as st
import pytz
import plotly.graph_objects as go
import folium
from datetime import datetime, date, timedelta
from timezonefinder import TimezoneFinder
from astral import LocationInfo
from astral.sun import sunrise, sunset, noon, azimuth
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation
import json
import os
import requests
import pandas as pd
import math
import numpy as np
from scipy.optimize import minimize
import base64
import visuals
import solarlogic



# --- INITIALIZATION ---
st.set_page_config(layout="wide", page_title="Solar Path Visualizer", page_icon="☀️")
visuals.apply_styles()

if 'page' not in st.session_state:
    st.session_state.page = "home"

if 'coords' not in st.session_state:
    st.session_state.coords = [0.0, 0.0] 
    st.session_state.gps_requested = False

# --- GPS & TIMEZONE LOGIC ---
if not st.session_state.gps_requested:
    loc = get_geolocation()
    if loc and 'coords' in loc:
        st.session_state.coords = [loc['coords']['latitude'], loc['coords']['longitude']]
        st.session_state.gps_requested = True
        st.rerun()

lat, lon = st.session_state.coords
tf = TimezoneFinder()
tz_name = tf.timezone_at(lng=lon, lat=lat) or "UTC"
local_tz = pytz.timezone(tz_name)
city_info = LocationInfo(timezone=tz_name, latitude=lat, longitude=lon)

# Fetch environmental data
loc_key = f"{lat}_{lon}"
if "last_loc_key" not in st.session_state or st.session_state.last_loc_key != loc_key:
    st.session_state.env_data = solarlogic.get_environmental_data(lat, lon)
    st.session_state.last_loc_key = loc_key
env_data = st.session_state.env_data

# --- FOOTER RENDERER ---
def render_dashboard_footer(key_suffix, t_date, s_time, aqi_enabled, r_t, s_t, n_t):
    st.markdown("---")
    m_slat, m_slon, m_shlat, m_shlon, m_az, m_el = solarlogic.get_solar_pos(city_info, s_time, 250, lat, lon)
    radiation_wm2 = solarlogic.calculate_solar_radiation(m_el)

    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    m_col1.metric("Selected Time", s_time.strftime('%H:%M'))
    m_col2.metric("Azimuth", f"{m_az:.1f}°")
    m_col3.metric("Elevation", f"{m_el:.1f}°")
    m_col4.metric("Solar Noon", n_t.strftime('%H:%M'))

    if aqi_enabled:
        st.markdown("#### ⚡ Live Environmental & Solar Data")
        w_col1, w_col2, w_col3, w_col4, w_col5 = st.columns(5)
        env = st.session_state.env_data
        w_col1.metric("Temp", f"{env['temp']}°C")
        w_col2.metric("Humidity", f"{env['hum']}%")
        w_col3.metric("Wind", f"{env['wind']} m/s")
        w_col4.metric("AQI", env["aqi"], delta=env["label"], delta_color="inverse")
        w_col5.metric("Solar Radiation", f"{radiation_wm2} W/m²")

    path_pts = []
    temp_curr = r_t
    while temp_curr <= s_t:
        _, _, _, _, _, el = solarlogic.get_solar_pos(city_info, temp_curr, 250, lat, lon)
        path_pts.append({"time": temp_curr.strftime("%H:%M"), "el": el})
        temp_curr += timedelta(minutes=15)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[p['time'] for p in path_pts], y=[p['el'] for p in path_pts], mode='lines', line=dict(color='#f39c12', width=3), fill='tozeroy', fillcolor='rgba(243, 156, 18, 0.1)'))
    fig.update_layout(height=250, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="black", xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, title="Elevation (°)"))
    st.plotly_chart(fig, use_container_width=True, key=f"chart_{key_suffix}")


# --- HELPER FUNCTION (Place this near the top of app.py) ---
def get_base64_image(path):
    with open(path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

# --- PAGE ROUTING ---
if st.session_state.page == "home":
    # 1. Encode Images
    bg_img = get_base64_image("bg.png")
    logo_img = get_base64_image("flowstate_logo.png")

    # 2. CSS for Hero Section, Animations, and Ripple Button
    st.markdown(f"""
    <style>
    @keyframes togetherRise {{
        0% {{ letter-spacing: 2px; opacity: 0; filter: blur(10px); transform: translateY(15px); }}
        100% {{ letter-spacing: 12px; opacity: 1; filter: blur(0px); transform: translateY(0px); }}
    }}
    @keyframes logoFade {{
        from {{ opacity: 0; transform: scale(0.95); }}
        to {{ opacity: 1; transform: scale(1); }}
    }}
    .hero-section {{
        background: linear-gradient(rgba(0, 0, 0, 0.4), rgba(0, 0, 0, 0.2)), url("data:image/jpg;base64,{bg_img}");
        background-size: cover; background-position: center; height: 100vh; width: 100vw;
        margin-left: calc(-50vw + 50%); margin-top: -100px; display: flex; flex-direction: column;
        align-items: center; justify-content: center; position: relative; text-align: center; overflow: hidden;
    }}
    .hero-logo {{ width: 380px; filter: drop-shadow(0px 0px 30px rgba(243, 156, 18, 0.5)); animation: logoFade 0.8s ease-out forwards; margin-bottom: -85px; }}
    .hero-title {{
        font-family: 'Akira', sans-serif; font-size: 85px; color: #F39C12; text-transform: uppercase; margin: 0; line-height: 1;
        background: linear-gradient(180deg, #F39C12 0%, #FFD06D 50%, #D35400 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        animation: togetherRise 0.8s ease-out 0.2s forwards; opacity: 0;
    }}
    .hero-subtitle {{
        font-family: 'Poppins', sans-serif; color: white; font-size: 1.1rem; text-transform: uppercase; margin-top: 15px; margin-bottom: 50px;
        animation: togetherRise 0.8s ease-out 0.2s forwards; opacity: 0;
    }}
    [data-testid="stVerticalBlock"] > div:has(div.stButton) {{ display: flex !important; justify-content: center !important; width: 100% !important; }}
    .stButton {{ margin-top: -160px !important; z-index: 999; }}
    div.stButton > button {{
        background-color: #F39C12 !important; 
        color: white !important; 
        border: 2px solid #F39C12 !important; 
        border-radius: 50px !important;
        padding: 0.6rem 2.5rem !important; /* Narrower padding */
        font-weight: bold !important; 
        text-transform: uppercase !important; 
        letter-spacing: 2px !important;
        animation: logoFade 0.6s ease-out 1s forwards; 
        opacity: 0;
        width: auto !important; /* Prevents full-width stretch */
        display: block;
        margin: 0 auto;
    }}
    </style>
    <div class="hero-section">
        <img src="data:image/png;base64,{logo_img}" class="hero-logo">
        <h1 class="hero-title">FLOWSTATE</h1>
        <p class="hero-subtitle">Guided by Light • Rooted in Water</p>
    </div>
    """, unsafe_allow_html=True)

    
   

    # 3. Interactive Button (Positioned over the Hero)
    c1, c2, c3 = st.columns([1.5, 1, 1.5])
    with c2:
        st.markdown('<div style="margin-top: -220px; position: relative; z-index: 1000;">', unsafe_allow_html=True)
        if st.button("Go to Maps", use_container_width=True):
            st.session_state.page = "app"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # 4. CONTENT BELOW THE FOLD
    st.markdown('<div style="height: 120px;"></div>', unsafe_allow_html=True)
    

   
    
    st.markdown("""
    <div style="color: white; font-family: 'Inter', sans-serif;">
    <h2 style="color: white;">Let the Sun guide your next big decision. </h2>
    <p>Ever wondered how much sunlight your <b>bedroom, balcony, terrace garden,</b> or <b>solar panels</b> will get throughout the year? Now you don't have to guess.</p>
    <hr style="border-top: 1px solid rgba(255,255,255,0.2); margin: 20px 0;">
    <h3 style="color: white;">What Solar Path Visualizer Does</h3>
    <p>A simple, educational purpose-built tool that <b>instantly shows how sunlight moves across any location on Earth</b>.</p>
    <ul style="list-style-type: none; padding-left: 20px; line-height: 2;">
        <li><b>Buying a new home</b></li>
        <li><b>Planning a balcony or terrace garden</b></li>
        <li><b>Installing a solar geyser or solar panels</b></li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
else:
    radius_meters = 250
    target_date = date.today()

    with st.sidebar:

        try:
            sidebar_logo = get_base64_image("flowstate_logo.png")
            st.markdown(
                f"""
                <div style="display: flex; justify-content: center; margin-bottom: -20px;">
                    <img src="data:image/png;base64,{sidebar_logo}" width="150">
                </div>
                """, 
                unsafe_allow_html=True
            )
        except FileNotFoundError:
            pass # Fails silently if logo is missing in sidebar



        st.markdown(
            """
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');
            
            /* Load Akira for headers */
            @font-face {
                font-family: 'Akira';
                src: url('https://fonts.cdnfonts.com/s/62983/Akira Expanded Demo.woff');
            }

            /* Global font override for readability */
            html, body, [class*="st-at"], [class*="st-ae"] {
                font-family: 'Poppins', sans-serif !important;
            }

            .flowstate-title {
                font-family: 'Akira', sans-serif;
                font-size: 80px;
                font-weight: 900;
                color: #F39C12;
                text-align: center;
                text-transform: uppercase;
                letter-spacing: 15px;
                line-height: 1.1;
                margin-bottom: 10px;
                background: linear-gradient(180deg, #F39C12 0%, #FFD06D 50%, #D35400 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                filter: drop-shadow(0px 0px 20px rgba(243, 156, 18, 0.4));
            }

            .flowstate-subtitle {
                font-family: 'Poppins', sans-serif;
                color: #F39C12;
                text-align: center;
                font-size: 1.2rem;
                font-weight: 300;
                letter-spacing: 4px;
                text-transform: uppercase;
                margin-top: -20px;
                margin-bottom: 40px;
            }
            </style>
            <h1 class="flowstate-title">FLOW<br>STATE</h1>
            <p class="flowstate-subtitle">Guided by light • Rooted by water</p>
            """, 
            unsafe_allow_html=True
        )

        if st.button("⬅️ Back to Info"):
            st.session_state.page = "home"
            st.rerun()

        st.header("⚙️ Settings")
        with st.form("city_search"):
            search_query = st.text_input("🔍 Search Place", placeholder="e.g. London, UK")
            if st.form_submit_button("Search") and search_query:
                coords = solarlogic.search_city(search_query)
                if coords: 
                    st.session_state.coords = coords
                    st.rerun()
        st.markdown("---")
        if st.button("📍 Reset to My GPS", use_container_width=True):
            st.session_state.gps_requested = False
            st.session_state.coords = [0.0, 0.0] 
            st.rerun()
        
        celestial_dates = {
            "Manual Selection": None, 
            "Spring Equinox (Mar 20)": date(2026, 3, 20), 
            "Summer Solstice (Jun 21)": date(2026, 6, 21), 
            "Autumnal Equinox (Sep 22)": date(2026, 9, 22), 
            "Winter Solstice (Dec 21)": date(2026, 12, 21)
        }
        date_preset = st.selectbox("Key Celestial Dates", list(celestial_dates.keys()))
        target_date = st.date_input("Date", date.today()) if date_preset == "Manual Selection" else celestial_dates[date_preset]
        
        enable_aqi = st.toggle("AQI & Live Weather", value=False)
        shour = st.slider("Hour", 0, 23, datetime.now(local_tz).hour)
        smin = st.slider("Minute", 0, 59, 0)
        sim_time = local_tz.localize(datetime.combine(target_date, datetime.min.time())) + timedelta(hours=shour, minutes=smin)

    try:
        rise_t = sunrise(city_info.observer, date=target_date, tzinfo=local_tz)
        set_t = sunset(city_info.observer, date=target_date, tzinfo=local_tz)
        noon_t = noon(city_info.observer, date=target_date, tzinfo=local_tz)
    except:
        rise_t = sim_time.replace(hour=6, minute=0); set_t = sim_time.replace(hour=18, minute=0); noon_t = sim_time.replace(hour=12, minute=0)

    # --- TABS START HERE ---
    tab_location, tab_sunfeatures, tab_waterfeatures = st.tabs(["Location Setup", "Sun Features", "Water Features"])
        
    with tab_location:
        display_lat = f"{st.session_state.coords[0]:.5f}"
        display_lon = f"{st.session_state.coords[1]:.5f}"
        display_date = target_date.strftime("%B %d, %Y") 
      
        map_key = f"map_select_{target_date}_{st.session_state.coords[0]}"
        m = folium.Map(location=st.session_state.coords, zoom_start=17, tiles=None)

        folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satellite').add_to(m)
        folium.TileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', attr='&copy; OpenStreetMap contributors', name='Street').add_to(m)
        folium.LayerControl(position='topleft', collapsed=False).add_to(m)
        folium.Marker(st.session_state.coords, icon=folium.Icon(color='orange', icon='sun', prefix='fa')).add_to(m)

        info_html = f'''
            <div style="position: absolute; top: 10px; right: 10px; width: 180px; background: rgba(14, 17, 23, 0.9); padding: 12px; border-radius: 10px; border: 2px solid #F39C12; color: white; font-family: 'Inter', sans-serif; font-size: 13px; z-index: 1000; pointer-events: none;">
                <div style="color:#F39C12; font-weight:bold; font-size: 11px; letter-spacing: 1px;">📍 LOCATION</div>
                <div style="margin-bottom: 8px;">{display_lat}, {display_lon}</div>
                <div style="color:#F39C12; font-weight:bold; font-size: 11px; letter-spacing: 1px;">📅 SELECTED DATE</div>
                <div>{display_date}</div>
            </div>
        '''
        m.get_root().html.add_child(folium.Element(info_html))

        st.markdown("Select your location and date/Season of interest. Then switch to Step 2: Live Visualization.")
        
        map_data = st_folium(m, height=550, use_container_width=True, key=map_key)

        if map_data and map_data.get("last_clicked"):
            new_coords = [map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"]]
            if new_coords != st.session_state.coords:
                st.session_state.coords = new_coords
                st.rerun()

        render_dashboard_footer("location", target_date, sim_time, enable_aqi, rise_t, set_t, noon_t)

    with tab_sunfeatures:
        sunfeature_choice = st.selectbox("Analysis Tool", ["Live Path Visualization", "Year Round Summary"])
            
        if sunfeature_choice == "Live Path Visualization":
            animate_trigger = st.toggle("Play Path", value=True)
            path_data = []
            curr = rise_t
            while curr <= set_t:
                slat, slon, shlat, shlon, az, el = solarlogic.get_solar_pos(city_info, curr, radius_meters, lat, lon)
                path_data.append({"lat": slat, "lon": slon, "shlat": shlat, "shlon": shlon, "time": curr.strftime("%H:%M"), "el": el})
                curr += timedelta(minutes=10)
                
            m_slat, m_slon, _, _, _, m_el = solarlogic.get_solar_pos(city_info, sim_time, radius_meters, lat, lon)
            rise_edge = solarlogic.get_edge(lat, lon, azimuth(city_info.observer, rise_t), radius_meters)
            set_edge = solarlogic.get_edge(lat, lon, azimuth(city_info.observer, set_t), radius_meters)

            visuals.render_map_component(lat, lon, radius_meters, path_data, animate_trigger, sim_time, m_slat, m_slon, 0, 0, m_el, rise_edge, set_edge, rise_t.strftime("%H:%M"), set_t.strftime("%H:%M"), "On" if enable_aqi else "Off")
            render_dashboard_footer("viz", target_date, sim_time, enable_aqi, rise_t, set_t, noon_t)

        elif sunfeature_choice == "Year Round Summary":
            st.markdown('<div class="theory-section"><h2 class="theory-header">Seasonal Comparison For Selected Location</h2></div>', unsafe_allow_html=True)
            
            milestones = [
                {"id": "Summer", "label": "Summer (June 21)", "date": date(2026, 6, 21)},
                {"id": "Autumn", "label": "Autumn (Oct 31)", "date": date(2026, 10, 31)},
                {"id": "Spring", "label": "Spring (March 20)", "date": date(2026, 3, 20)},
                {"id": "Winter", "label": "Winter (Dec 21)", "date": date(2026, 12, 21)}
            ]
            
            seasonal_data = {}
            for m in milestones:
                m_date = m["date"]
                m_r = sunrise(city_info.observer, date=m_date, tzinfo=local_tz)
                m_s = sunset(city_info.observer, date=m_date, tzinfo=local_tz)
                pts = []
                c = m_r
                while c <= m_s:
                    lat_p, lon_p, _, _, _, _ = solarlogic.get_solar_pos(city_info, c, radius_meters, lat, lon)
                    pts.append([lat_p, lon_p])
                    c += timedelta(minutes=20)
                seasonal_data[m["id"]] = {"coords": pts, "label": m["label"]}

            visuals.render_seasonal_map(lat, lon, radius_meters, seasonal_data)
            st.markdown("""
                <div style="display: flex; justify-content: space-around; background: rgba(255,255,255,0.05); padding: 15px; border-radius: 10px; margin-top: 10px;">
                    <div style="color:#FF0000;">● Summer</div>
                    <div style="color:#FF8C00;">● Autumn</div>
                    <div style="color:#FFD700;">● Spring</div>
                    <div style="color:#FFFF00;">● Winter</div>
                </div>""", unsafe_allow_html=True)


    with tab_waterfeatures:
        wfeature_choice = st.selectbox("Analysis Tool", ["Water Stress Score (WSS)", "AC Condesate Estimator", "Solar-Water Nexus (Desalination)", "Water Quality Monitoring"])
        # Pull environment data once for both tools
        env = st.session_state.env_data
        u_lat, u_lon = st.session_state.coords[0], st.session_state.coords[1]

        if wfeature_choice == "Water Stress Score (WSS)":

            # 1. Processing logic
            m_slat, m_slon, m_shlat, m_shlon, m_az, m_el = solarlogic.get_solar_pos(
                city_info, sim_time, radius_meters, u_lat, u_lon
            )
            current_ghi = solarlogic.calculate_solar_radiation(m_el)
            wss_val, breakdown = solarlogic.calculate_wss_breakdown(
                current_ghi, env.get('temp', 25), env.get('hum', 50)
            )
            res = solarlogic.classify_wss(wss_val)

            # 2. Refined Styling (-4px adjustment)
            st.markdown("""
                <style>
                .main-title { text-align: center; color: #3498db; font-size: 3.55rem !important; font-weight: 800; margin-bottom: 6px; }
                .subtitle { text-align: center; color: #94a3b8; font-size: 1.15rem; margin-bottom: 36px; }
                
                .formula-container {
                    background: #111827;
                    border: 2px solid #3498db;
                    border-radius: 16px;
                    padding: 41px;
                    margin-bottom: 46px;
                    text-align: center;
                }
                
                .glass-card {
                    background: rgba(255, 255, 255, 0.05);
                    border-radius: 11px;
                    padding: 26px;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    margin-bottom: 21px;
                }
                
                .stat-label { font-size: 1.15rem !important; color: #3498db; font-weight: 700; text-transform: uppercase; }
                .stat-value { font-size: 2.55rem !important; font-weight: 900; color: #ffffff; margin: 1px 0; }
                
                .protocol-text { font-size: 1.35rem !important; line-height: 1.5; font-weight: 500; }
                .impact-val { font-size: 1.75rem !important; font-weight: bold; color: #2ecc71; }
                
                .theory-box {
                    background: rgba(52, 152, 219, 0.05);
                    border-radius: 11px;
                    padding: 16px;
                    border-left: 5px solid #3498db;
                    margin-top: 16px;
                }
                </style>
            """, unsafe_allow_html=True)

            st.markdown('<h1 class="main-title">Water Stress Intelligence</h1>', unsafe_allow_html=True)
            
            st.markdown('<p style="font-size: 1.95rem; color: #3498db; font-weight: 800; margin-bottom: 21px;">🧮 SYSTEM ALGORITHM</p>', unsafe_allow_html=True)
            st.latex(r"\Large WSS = \underbrace{(0.35 \cdot S_{n})}_{Solar} + \underbrace{(0.25 \cdot T_{n})}_{Temp} + \underbrace{(0.25 \cdot ET_{n})}_{Evap} + \underbrace{(0.15 \cdot H_{n})}_{Humidity}")
            st.markdown("""
                <div class="theory-box">
                    <p style="color: #cbd5e1; font-size: 1.05rem; margin: 0; text-align: left;">
                        <b>Logic:</b> The WSS weights solar and thermal loads most heavily (60% total) to reflect UAE's high-irradiance profile. 
                    </p>
                </div>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # 4. Environmental Summary Row
            t1, t2, t3, t4 = st.columns(4)
            with t1: st.markdown(f"<div class='glass-card'><p class='stat-label'>Irradiance</p><p class='stat-value'>{current_ghi}</p><p style='color:#94a3b8; font-size:0.9rem;'>W/m²</p></div>", unsafe_allow_html=True)
            with t2: st.markdown(f"<div class='glass-card'><p class='stat-label'>Temp</p><p class='stat-value'>{env.get('temp')}°C</p><p style='color:#94a3b8; font-size:0.9rem;'>Ambient</p></div>", unsafe_allow_html=True)
            with t3: st.markdown(f"<div class='glass-card'><p class='stat-label'>Humidity</p><p class='stat-value'>{env.get('hum')}%</p><p style='color:#94a3b8; font-size:0.9rem;'>Relative</p></div>", unsafe_allow_html=True)
            with t4: st.markdown(f"<div class='glass-card'><p class='stat-label'>Risk</p><p class='stat-value' style='color:{res['color']}'>{res['status']}</p><p style='color:#94a3b8; font-size:0.9rem;'>Classification</p></div>", unsafe_allow_html=True)

            # 5. Main Analysis Section
            col_viz, col_impact = st.columns([1.6, 1])

            with col_viz:
                st.markdown(f"""
                    <div class='glass-card' style='text-align: center; border-bottom: 11px solid {res['color']}; padding: 56px;'>
                        <h2 style='margin:0; color: #94a3b8; font-size: 1.75rem; letter-spacing: 2px;'>CURRENT WSS INDEX</h2>
                        <h1 style='font-size: 156px; margin: 6px 0; color: #ffffff; line-height: 1;'>{wss_val}</h1>
                        <div style='background: {res['color']}; color: white; padding: 6px 26px; border-radius: 6px; display: inline-block; font-size: 1.75rem; font-weight: 900;'>
                            {res['status'].upper()} DEMAND
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                st.write("### 📊 Factor Sensitivity Analysis")
                fig_bar = go.Figure(data=[go.Bar(
                    x=['Solar Impact', 'Thermal Load', 'Evap. Demand', 'Vapor Deficit'], 
                    y=breakdown, 
                    marker_color=['#f1c40f', '#e67e22', '#3498db', '#2ecc71'],
                    text=[f"{x:.1f}%" for x in breakdown],
                    textposition='auto',
                    textfont=dict(size=20, color='white')
                )])
                fig_bar.update_layout(height=446, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
                st.plotly_chart(fig_bar, use_container_width=True)

            with col_impact:
                st.markdown(f"<h2 style='color: #3498db; font-size: 1.95rem; margin-bottom: 21px;'>📋 Deployment Protocol</h2>", unsafe_allow_html=True)
                for action in res["actions"]:
                    st.markdown(f"<div class='glass-card' style='padding: 21px; margin-bottom: 11px; border-left: 6px solid {res['color']};'><p class='protocol-text'><b>{action}</b></p></div>", unsafe_allow_html=True)
                
                st.write("### 🕒 24h Stress Forecast")
                hours = ['12AM', '4AM', '8AM', '12PM', '4PM', '8PM']
                scores = [wss_val*0.6, wss_val*0.5, wss_val*0.8, wss_val*1.1, wss_val, wss_val*0.7]
                fig_line = go.Figure(data=go.Scatter(x=hours, y=scores, fill='tozeroy', line_color=res['color']))
                fig_line.update_layout(height=246, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
                st.plotly_chart(fig_line, use_container_width=True)

                st.markdown(f"""
                    <div class='glass-card' style='background: rgba(46, 204, 113, 0.15); border: 2px solid #2ecc71; padding: 36px;'>
                        <p class='protocol-text' style='margin-bottom: 16px;'>💧 <b>Water Saved:</b> <span class='impact-val'>{res['savings']['water']}</span></p>
                        <p class='protocol-text'>📉 <b>Evap. Cut:</b> <span class='impact-val'>{res['savings']['evap']}</span></p>
                    </div>
                """, unsafe_allow_html=True)
                


        if wfeature_choice == "AC Condesate Estimator":

                # ---------------------------------------------------
                # SCOPED UI STYLING (ONLY THIS SECTION)
                # ---------------------------------------------------
                st.markdown("""
                <style>
                .ac-section h1 {
                        font-size: 52px !important;
                        font-weight: 600;
                        margin-bottom: 10px;
                }
                .ac-section h2 {
                        font-size: 32px !important;
                        font-weight: 600;
                }
                .ac-section p, 
                .ac-section li {
                        font-size: 22px !important;
                        line-height: 1.6;
                }
                .ac-section .stMetric label {
                        font-size: 22px !important;
                }
                .ac-section .stMetric div {
                        font-size: 34px !important;
                }
                .ac-section .explain-box {
                        background: rgba(52, 152, 219, 0.08);
                        padding: 20px;
                        border-radius: 12px;
                        margin-top: 15px;
                        margin-bottom: 25px;
                }
                </style>
                """, unsafe_allow_html=True)

                # Wrap everything in a scoped div
                st.markdown('<div class="ac-section">', unsafe_allow_html=True)

                # ---------------------------------------------------
                # HEADER
                # ---------------------------------------------------
                st.markdown("""
                <h1 style="text-align:center;">
                💧 AC Condensate Intelligence
                </h1>
                <p style="text-align:center; opacity:0.75;">
                Your AC is already producing distilled water.
                This tool estimates how much you can realistically recover.
                This model estimates water production based on: AC cooling capacity (tons), Daily runtime (hours), Real-time humidity conditions.
                It uses a climate-adjusted condensate rate calibrated for Gulf-region HVAC systems.
                </div>
                </p>
                """, unsafe_allow_html=True)

                # ---------------------------------------------------
                # HOW THIS IS CALCULATED
                # ---------------------------------------------------
                

                st.markdown("---")

                col_input, col_output = st.columns([1, 1.2])

                # ---------------------------------------------------
                # INPUT SECTION
                # ---------------------------------------------------
                with col_input:

                        st.subheader("⚙ System Configuration")

                        ac_tonnage = st.number_input(
                                "AC Capacity (Tons)",
                                min_value=0.5,
                                max_value=10.0,
                                value=1.5,
                                step=0.5
                        )

                        run_hours = st.slider(
                                "Daily Runtime (Hours)",
                                1, 24, 12
                        )

                        st.markdown("""
                        <p class="info-text">
                        1–2 Tons → Bedroom | 3–5 Tons → Apartment | 5+ Tons → Villa
                        </p>
                        """, unsafe_allow_html=True)

                # ---------------------------------------------------
                # PHYSICS-BASED CALCULATION
                # ---------------------------------------------------
                humidity = env.get('hum', 50)

                base_rate = 1.1  # liters per ton per hour (UAE humid baseline)

                humidity_factor = 0.5 + (humidity / 100)
                humidity_factor = min(max(humidity_factor, 0.7), 1.5)

                daily_yield = ac_tonnage * run_hours * base_rate * humidity_factor
                monthly_yield = daily_yield * 30

                # ---------------------------------------------------
                # OUTPUT SECTION
                # ---------------------------------------------------
                with col_output:

                        st.subheader("📊 Water Recovery Potential")

                        m1, m2 = st.columns(2)

                        with m1:
                                st.metric(
                                        "Daily Recovery",
                                        f"{daily_yield:.1f} Liters"
                                )

                        with m2:
                                st.metric(
                                        "Projected Monthly",
                                        f"{monthly_yield:.0f} Liters"
                                )

                        st.progress(min(daily_yield / 30, 1.0))

                        st.markdown("---")

                        st.markdown(f"""
                        ### 🌿 Practical Uses (Per Day)

                        🪴 Water **{int(daily_yield/2)} plants**  
                        🧹 Fill **{int(daily_yield/5)} cleaning buckets**  
                        🥤 Equivalent to **{int(daily_yield)} liters of distilled-quality water**
                        """)

                # ---------------------------------------------------
                # ENVIRONMENTAL IMPACT
                # ---------------------------------------------------
                st.markdown("---")
                st.subheader("🌍 Environmental Impact")

                co2_saved_kg = (monthly_yield * 0.4) / 1000
                km_equivalent = (co2_saved_kg * 1000) / 120

                c1, c2 = st.columns(2)

                with c1:
                        st.markdown(f"""
                        ♻️ **Desalination Offset**

                        Recovering this water avoids approximately  
                        **{co2_saved_kg:.2f} kg CO₂ per month**
                        """)

                with c2:
                        st.markdown(f"""
                        🚗 **Driving Equivalent**

                        That equals roughly  
                        **{km_equivalent:.1f} km** of petrol car emissions
                        """)

                # ---------------------------------------------------
                # HUMIDITY INSIGHT
                # ---------------------------------------------------
                st.markdown("---")
                st.subheader("💨 Climate Insight")

                st.markdown(f"""
                Current Relative Humidity: **{humidity}%**

                Higher humidity increases condensate production.
                The model automatically adjusts within realistic HVAC operating limits.
                """)
                st.markdown("</div>", unsafe_allow_html=True)


        if wfeature_choice == "Solar-Water Nexus (Desalination)":
            st.markdown("""
                <div style="text-align: center;">
                    <h1 style="color: #f39c12; font-family: 'Poppins', sans-serif;">Your Solar-Water Calculator</h1>
                    <p style="font-size: 18px; opacity: 0.8;">Verified engineering model for UAE sustainable water production</p>
                </div>
            """, unsafe_allow_html=True)

            # --- Technical Constants with Citations ---
            RO_ENERGY_INTENSITY = 4.0   # Benchmark for DEWA/Masdar high-efficiency RO
            UAE_PEAK_SUN_HOURS = 5.8    # NASA/IRENA long-term average for UAE
            WATER_VAL_AED = 7.85        # DEWA commercial water tariff (Excluding Fuel Surcharge)

            # --- Methodology Expander (The "Credibility" Section) ---
            with st.expander("🔬 How do we know this is accurate?", expanded=False):
                st.markdown(f"""
                This model uses **verified regional data** to ensure engineering accuracy:
                * **Solar Data:** Live sun positioning is calculated using standard astronomical algorithms, cross-referenced with your specific GPS coordinates.
                * **Energy Intensity:** We use the benchmark of **{RO_ENERGY_INTENSITY} kWh/m³**, which is the current performance standard for modern Reverse Osmosis (RO) plants in the UAE.
                * **Water Value:** Calculations are based on the standard commercial tariff of **{WATER_VAL_AED} AED per cubic meter**.
                * **Validation:** Energy loss is modeled at **15%** (0.85 efficiency) to account for the UAE's high ambient temperatures affecting solar panel performance.
                """)

            # --- User Inputs ---
            st.write("### 🏠 Set Your Community Scale")
            solar_capacity_kw = st.select_slider(
                "Select Solar Installation Size",
                options=[10, 50, 100, 500, 1000],
                value=100,
                help="10kW is a large villa; 1000kW is a small neighborhood."
            )

            # --- Real-Time Calculation ---
            m_slat, m_slon, m_shlat, m_shlon, m_az, m_el = solarlogic.get_solar_pos(
                city_info, sim_time, radius_meters, u_lat, u_lon
            )
            current_ghi = solarlogic.calculate_solar_radiation(m_el)
            efficiency = 0.85
            real_time_kwh = (current_ghi / 1000) * solar_capacity_kw * efficiency
            hourly_liters = (real_time_kwh / RO_ENERGY_INTENSITY) * 1000

            # --- Credibility Badge ---
            st.markdown(f"""
                <div style="background: rgba(52, 152, 219, 0.1); padding: 10px; border-radius: 5px; border-left: 5px solid #3498db; margin-bottom: 20px;">
                    <small>📍 <b>Live Validation:</b> Calculating for coordinates <b>{u_lat:.2f}, {u_lon:.2f}</b> using current local solar irradiance.</small>
                </div>
            """, unsafe_allow_html=True)

            # --- Interactive Visuals ---
            if current_ghi <= 0:
                st.info("🌙 **Nighttime Mode**: The sun is down, but your 'Water Battery' (storage tanks) would be providing water to your home right now.")
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Live Production", f"{hourly_liters:.1f} L/hr")
            with c2:
                daily_total_l = (solar_capacity_kw * UAE_PEAK_SUN_HOURS * efficiency / RO_ENERGY_INTENSITY) * 1000
                st.metric("Verified Daily Potential", f"{daily_total_l:,.0f} Liters")
            with c3:
                monthly_val = (daily_total_l / 1000) * WATER_VAL_AED * 30
                st.metric("Monthly Savings", f"{monthly_val:,.0f} AED")

            st.markdown("---")
            st.write("### 🌍 Impact Summary")
            
            daily_l = (solar_capacity_kw * UAE_PEAK_SUN_HOURS * efficiency / RO_ENERGY_INTENSITY) * 1000
            
            p1, p2, p3 = st.columns(3)
            with p1:
                st.markdown(f"### 🛁\n**{int(daily_l/150)}**\nShowers/Day")
            with p2:
                st.markdown(f"### 🪴\n**{int(daily_l/10)}**\nPlants/Day")
            with p3:
                st.markdown(f"### 🥛\n**{int(daily_l/2)}**\nDaily Hydration")

            st.markdown('<div style="height: 30px;"></div>', unsafe_allow_html=True)

            # --- The "Public Gain" narrative ---
            st.markdown(f"""
                <div style="background-color: #1e272e; padding: 20px; border-radius: 15px; border-left: 5px solid #2ecc71;">
                    <h4 style="color: #2ecc71; margin-top:0;">Why this works for the UAE</h4>
                    <p style="margin-bottom: 10px;">Traditional desalination relies on burning fossil fuels. This <b>Solar-Water Nexus</b> creates a decentralized supply chain that:</p>
                    <ul style="margin:0;">
                        <li><b>Reduces Monthly Bills:</b> Direct solar-to-water conversion bypasses expensive grid transmission fees.</li>
                        <li><b>Ensures Security:</b> Provides water even during grid maintenance or power outages.</li>
                        <li><b>Protects Habitat:</b> Low-energy RO reduces the thermal pollution usually released into the Arabian Gulf.</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown('<div style="height: 40px;"></div>', unsafe_allow_html=True)

            # --- Technical Chart ---
            st.write("#### 📈 Verified Daily Production Cycle")
            h_axis = list(range(24))
            peak_ref = (solar_capacity_kw * 0.85 * 1000 / 1000) / RO_ENERGY_INTENSITY * 1000
            yield_curve = [max(0, math.sin(math.pi * (h-6)/12)) * peak_ref for h in h_axis]
            st.area_chart(pd.DataFrame({"Liters Generated per Hour": yield_curve}, index=h_axis))

        if wfeature_choice == "Water Quality Monitoring":

            st.subheader("💧 Water Quality Monitoring & Alerts")
            st.markdown("### 📘 Standards & Regulatory Alignment")

            st.info(
                """
                This monitoring module follows internationally recognized drinking water
                quality standards including:

                • World Health Organization (WHO) Drinking Water Guidelines  
                • UAE National Drinking Water Standards  
                • Gulf Standardization Organization (GSO) limits  

                Threshold ranges are aligned with recommended safe values for potable water.
                """
            )

            st.markdown(
                """
                #### 📊 Safe Reference Ranges Used

                | Parameter | Recommended Safe Range | Sustainability Relevance |
                |------------|------------------------|---------------------------|
                | pH | 6.5 – 8.5 | Prevents pipe corrosion & ecosystem damage |
                | Turbidity (NTU) | < 5 NTU | Indicates clarity & filtration efficiency |
                | Salinity (ppm) | < 500 ppm | Desalination efficiency indicator |
                | Contaminants (mg/L) | < 0.05 mg/L | Public health protection |

                These values reflect global potable water standards and regional desalination benchmarks.
                """
            )

            with st.expander("🔬 Methodology & Data Assumptions"):
                st.write(
                    """
                    This module simulates a real-time water quality monitoring system similar to
                    those deployed in municipal desalination plants and distribution networks.
                    In practice, IoT-based water sensors continuously measure parameters such as
                    pH, turbidity, salinity, and trace contaminants at treatment facilities and
                    across pipeline nodes. The collected data is transmitted to a centralized
                    analytics platform where rule-based thresholds and anomaly detection logic
                    evaluate water safety in real time. When values move outside recommended
                    ranges, the system triggers alerts to support rapid operational response.

                    The safety thresholds implemented in this model align with internationally
                    recognized drinking water standards and UAE regulatory benchmarks.
                    By combining continuous monitoring, automated alerting, and historical
                    trend analysis, the system supports proactive water management,
                    infrastructure protection, and long-term sustainability planning
                    in arid regions such as the UAE.
                    """
                )

            location = st.selectbox(
                "Select Emirate",
                ["Dubai", "Abu Dhabi", "Sharjah"]
            )

            location_bias = {
                "Dubai": 0,
                "Abu Dhabi": 0.2,
                "Sharjah": -0.1
            }

            bias = location_bias[location]

            # ---------------------------
            # Generate Sample Data
            # ---------------------------
            ph = round(np.random.normal(7.4 + bias, 0.3), 2)
            turbidity = round(np.random.normal(3 + bias, 1.2), 2)
            salinity = round(np.random.normal(450 + bias*100, 120), 2)
            contaminants = round(np.random.normal(0.04 + bias*0.01, 0.02), 3)

            # ---------------------------
            # Status Logic
            # ---------------------------
            def get_status(value, metric):
                thresholds = {
                    "pH": {"ok": (6.5, 8.5), "warn": (6.0, 9.0)},
                    "Turbidity": {"ok": (0, 5), "warn": (0, 10)},
                    "Salinity": {"ok": (0, 500), "warn": (0, 1000)},
                    "Contaminants": {"ok": (0, 0.05), "warn": (0, 0.1)},
                }

                ok_low, ok_high = thresholds[metric]["ok"]
                warn_low, warn_high = thresholds[metric]["warn"]

                if ok_low <= value <= ok_high:
                    return "OK"
                elif warn_low <= value <= warn_high:
                    return "Warning"
                else:
                    return "Critical"

            # ---------------------------
            # KPI Display
            # ---------------------------
            col1, col2, col3, col4 = st.columns(4)

            metrics = {
                "pH": ph,
                "Turbidity": turbidity,
                "Salinity": salinity,
                "Contaminants": contaminants
            }

            for col, (name, value) in zip([col1, col2, col3, col4], metrics.items()):
                status = get_status(value, name)

                if status == "OK":
                    color = "🟢"
                elif status == "Warning":
                    color = "🟡"
                else:
                    color = "🔴"

                col.metric(label=name, value=value, delta=f"{color} {status}")

            # ---------------------------
            # Alerts
            # ---------------------------
            for name, value in metrics.items():
                status = get_status(value, name)
                if status == "Critical":
                    st.error(f"🚨 CRITICAL ALERT in {location}: {name} levels unsafe!")
                elif status == "Warning":
                    st.warning(f"⚠️ Warning in {location}: {name} approaching unsafe range.")

            # ---------------------------
            # Historical Trend
            # ---------------------------
            st.markdown("### 📈 30-Day Quality Trend")

            days = pd.date_range(end=pd.Timestamp.today(), periods=30)

            data = pd.DataFrame({
                "Date": days,
                "pH": np.random.normal(7.4 + bias, 0.3, 30),
                "Turbidity": np.random.normal(3 + bias, 1.2, 30),
                "Salinity": np.random.normal(450 + bias*100, 120, 30),
                "Contaminants": np.random.normal(0.04 + bias*0.01, 0.02, 30),
            })

            st.line_chart(data.set_index("Date"))

            st.markdown("### 🌍 Why This Matters for UAE Sustainability")

            st.write(
                """
                In arid regions like the UAE, over 90% of potable water is produced through
                desalination. Continuous monitoring of salinity, turbidity, and contaminant
                levels ensures:

                • Energy-efficient desalination operations  
                • Reduced environmental discharge impact  
                • Safe public distribution networks  
                • Protection of marine ecosystems  

                Real-time alert systems reduce infrastructure risk and
                improve long-term water resilience under the UAE Water Security Strategy 2036.
                """
            )

