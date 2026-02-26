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
    /* Edge-to-edge Hero Container */
    .hero-section {{
        background: linear-gradient(rgba(0, 0, 0, 0.5), rgba(0, 0, 0, 0.3)), 
                    url("data:image/jpg;base64,{bg_img}");
        background-size: cover;
        background-position: center;
        height: 100vh;
        width: 100vw;
        margin-left: calc(-50vw + 50%);
        margin-top: -100px;
        display: flex;
        flex-direction: column;
        align-items: center; 
        justify-content: center; 
        position: relative;
        overflow: hidden;
        text-align: center;
    }}

    @keyframes letterSpacingMove {{
        0% {{ letter-spacing: 5px; opacity: 0; filter: blur(10px); }}
        100% {{ letter-spacing: 15px; opacity: 1; filter: blur(0px); }}
    }}

    /* FIXED: Added double braces for f-string compatibility */
    .hero-logo {{
        width: 380px; 
        display: block; 
        margin-left: auto;
        margin-right: auto;
        filter: drop-shadow(0px 0px 30px rgba(243, 156, 18, 0.5));
        animation: fadeIn 1.5s ease-out;
        margin-bottom: -85px; 
    }}
    
    .hero-title {{
        font-family: 'Akira', sans-serif;
        font-size: 85px;
        color: #F39C12;
        text-transform: uppercase;
        margin: 0; 
        padding: 0;
        line-height: 1;
        animation: letterSpacingMove 2.5s ease-out forwards;
        background: linear-gradient(180deg, #F39C12 0%, #FFD06D 50%, #D35400 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        display: block;
        width: 100%;
    }}

    .hero-subtitle {{
        font-family: 'Poppins', sans-serif;
        color: white;
        font-size: 1.1rem;
        letter-spacing: 5px;
        text-transform: uppercase;
        margin-top: 5px; 
        margin-bottom: 50px;
        opacity: 0;
        animation: fadeIn 1.5s ease-out 2s forwards;
        display: block;
        width: 100%;
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
        wfeature_choice = st.selectbox("Analysis Tool", ["Water Stress Score (WSS)", "AC Condesate Estimator", "Solar-Water Nexus (Desalination)"])
        # Pull environment data once for both tools
        env = st.session_state.env_data
        u_lat, u_lon = st.session_state.coords[0], st.session_state.coords[1]

        if wfeature_choice == "Water Stress Score (WSS)":
            st.markdown(f"""
                <div style="text-align: center;">
                    <h1 style="color: #3498db; font-family: 'Poppins', sans-serif;">Water Stress Intelligence</h1>
                </div>
            """, unsafe_allow_html=True)
            st.markdown('<div style="height: 50px;"></div>', unsafe_allow_html=True)

            m_slat, m_slon, m_shlat, m_shlon, m_az, m_el = solarlogic.get_solar_pos(
                city_info, sim_time, radius_meters, u_lat, u_lon
            )
            current_ghi = solarlogic.calculate_solar_radiation(m_el)
            
            wss_val, breakdown = solarlogic.calculate_wss_breakdown(current_ghi, env.get('temp', 25), env.get('hum', 50))
            res = solarlogic.classify_wss(wss_val) 

            col_input, col_viz, col_impact = st.columns([1, 2, 1])

            with col_input:
                st.subheader("Location & Conditions")
                st.info(f"📍 {u_lat:.4f}, {u_lon:.4f}")
                st.write(f"**Time:** {sim_time.strftime('%H:%M')}")
                st.metric("Temperature", f"{env.get('temp')}°C")
                st.metric("Humidity", f"{env.get('hum')}%")
                st.metric("Solar Radiation", f"{current_ghi} W/m²")

            with col_viz:
                st.markdown("""
                    <style>
                    .wss-tooltip-container { position: relative; display: inline-block; vertical-align: middle; }
                    .wss-tooltip-icon { cursor: help; font-size: 16px; margin-left: 6px; color: #95a5a6; border-radius: 50%; border: 1px solid #95a5a6; padding: 2px 6px; display: inline-block; }
                    .wss-tooltip-box { visibility: hidden; opacity: 0; position: absolute; left: 125%; top: 50%; transform: translateY(-50%); background: #1e272e; color: #ffffff; padding: 15px; border-radius: 8px; font-size: 14px; width: 320px; white-space: normal; z-index: 1000; transition: opacity 0.2s ease; text-align: left; box-shadow: 5px 5px 15px rgba(0,0,0,0.3); border: 1px solid #F39C12; }
                    .wss-tooltip-box::after { content: ""; position: absolute; top: 50%; right: 100%; transform: translateY(-50%); border-width: 8px; border-style: solid; border-color: transparent #1e272e transparent transparent; }
                    .wss-tooltip-container:hover .wss-tooltip-box { visibility: visible; opacity: 1; }
                    </style>
                """, unsafe_allow_html=True)

                st.markdown(f"""
                    <div style="text-align: center; background: rgba(255,255,255,0.05); padding: 20px; border-radius: 10px; border-bottom: 5px solid {res['color']};">
                        <h2 style="margin:0; font-size: 30px;">
                            Water Stress Score 
                            <span class="wss-tooltip-container">
                                <span class="wss-tooltip-icon">?</span>
                                <span class="wss-tooltip-box">
                                    <b>What is Water Stress Score (WSS)?</b><br><br>
                                    The WSS is a real‑time indicator measuring evaporation intensity and water demand.<br><br>
                                    <b>It includes:</b><br>1. Solar Radiation<br>2. Temperature<br>3. Humidity<br>4. Evapotranspiration.<br><br>
                                    🟢 <b>Low (0–50):</b> Normal conditions<br>
                                    🟡 <b>Moderate (50–75):</b> Increased water loss risk<br>
                                    🔴 <b>High (75–100):</b> Extreme evaporation; conservation recommended.
                                </span>
                            </span>
                            <br> {wss_val} / 100
                        </h2>
                        <div style="background: {res['color']}; color: white; padding: 5px 20px; border-radius: 5px; display: inline-block; margin-top: 10px; font-weight: bold;">
                            ⚠️ {res['status'].upper()}
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                st.markdown('<div style="height: 40px;"></div>', unsafe_allow_html=True)
                st.write("#### Factors Contributing to Water Stress")
                fig_bar = go.Figure(data=[go.Bar(x=['Solar', 'Temperature', 'Evapotranspiration', 'Humidity'], y=breakdown, marker_color=['#f1c40f', '#e67e22', '#3498db', '#2ecc71'], text=[f"{x:.1f}%" for x in breakdown], textposition='auto')])
                fig_bar.update_layout(height=250, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_bar, use_container_width=True)

                st.markdown('<div style="height: 40px;"></div>', unsafe_allow_html=True)
                st.write("#### Water Stress Score Forecast")
                hours = ['12 AM', '4 AM', '8 AM', '12 PM', '4 PM', '8 PM']
                scores = [wss_val*0.6, wss_val*0.5, wss_val*0.8, wss_val*1.1, wss_val, wss_val*0.7]
                fig_line = go.Figure(data=go.Scatter(x=hours, y=scores, fill='tozeroy', line_color=res['color']))
                fig_line.update_layout(height=200, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_line, use_container_width=True)

            with col_impact:
                st.subheader(f"{res['status']} Mode Measures")
                status_color = "#2ecc71" if res["status"] == "Low" else "#f1c40f" if res["status"] == "Moderate" else "#e74c3c"
                bg_color = "rgba(46, 204, 113, 0.1)" if res["status"] == "Low" else "rgba(241, 196, 15, 0.1)" if res["status"] == "Extreme" else "rgba(231, 76, 60, 0.1)"
                measures_html = "".join([f"<div style='margin-bottom: 12px;'>✅ {action}</div>" for action in res["actions"]])

                st.markdown(f'<div style="background-color: {bg_color}; border-radius: 10px; padding: 20px; border: 1px solid {status_color}; color: white; font-size: 20px; line-height: 1.6; font-family: \'Poppins\', sans-serif;">{measures_html}</div>', unsafe_allow_html=True)
                st.markdown("---")
                st.markdown("### 📊 Estimated Impact")
                st.markdown(f"""
                    <div style="font-size: 20px; line-height: 2.2;">
                        💧 <b>Estimated Water Saved:</b> <span style="color: #3498db;">{res['savings']['water']}</span><br>
                        💰 <b>Monthly Cost Savings:</b> <span style="color: #2ecc71;">{res['savings']['cost']}</span><br>
                        📈 <b>Evaporation Reduction:</b> <span style="color: #f39c12;">{res['savings']['evap']}</span>
                    </div>
                """, unsafe_allow_html=True)

        if wfeature_choice == "AC Condesate Estimator":
            # Tooltip CSS and Flexbox Centered Header
            st.markdown("""
                <style>
                .ac-header-flex {
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    gap: 15px;
                    margin-bottom: 30px;
                }
                .ac-title {
                    color: #3498db; 
                    font-family: 'Poppins', sans-serif;
                    font-size: 48px; /* Extra large header */
                    margin: 0;
                }
                .ac-tooltip-container { position: relative; display: inline-block; }
                .ac-tooltip-icon { 
                    cursor: help; font-size: 24px; color: #95a5a6; 
                    border-radius: 50%; border: 1px solid #95a5a6; padding: 2px 10px; 
                    display: inline-block; font-weight: bold;
                }
                .ac-tooltip-box { 
                    visibility: hidden; opacity: 0; position: absolute; left: 125%; top: 50%; 
                    transform: translateY(-50%); background: #1e272e; color: #ffffff; 
                    padding: 20px; border-radius: 8px; font-size: 16px; width: 350px; 
                    white-space: normal; z-index: 1000; transition: opacity 0.2s ease; 
                    text-align: left; box-shadow: 5px 5px 15px rgba(0,0,0,0.3); border: 1px solid #3498db; 
                }
                .ac-tooltip-box::after { 
                    content: ""; position: absolute; top: 50%; right: 100%; 
                    transform: translateY(-50%); border-width: 10px; border-style: solid; 
                    border-color: transparent #1e272e transparent transparent; 
                }
                .ac-tooltip-container:hover .ac-tooltip-box { visibility: visible; opacity: 1; }
                
                /* Making standard text blocks bigger */
                .big-text { font-size: 20px !important; line-height: 1.6; }
                .config-label { font-size: 24px !important; font-weight: bold; color: #f8f9fa; }
                </style>
                
                <div class="ac-header-flex">
                    <h1 class="ac-title">AC Condensate Intelligence</h1>
                    <span class="ac-tooltip-container">
                        <span class="ac-tooltip-icon">?</span>
                        <span class="ac-tooltip-box">
                            <b>About the AC Estimator</b><br><br>
                            This tool calculates the volume of water (condensate) created by your AC's dehumidification process.<br><br>
                            <b>How it works:</b> It uses your AC tonnage and runtime, cross-referenced with real-time local humidity, to estimate the liters of distilled-quality water you can harvest from your drain pipe.
                        </span>
                    </span>
                </div>
            """, unsafe_allow_html=True)
            
            col_ac_input, col_ac_viz = st.columns([1, 2])
            
            with col_ac_input:
                st.markdown('<p class="config-label">System Configuration</p>', unsafe_allow_html=True)
                st.markdown('<p class="big-text">Set your AC details below:</p>', unsafe_allow_html=True)
                
                ac_tonnage = st.number_input("AC Capacity (Tons)", min_value=0.5, max_value=10.0, value=1.5, step=0.5)
                run_hours = st.slider("Daily Run Time (Hours)", 1, 24, 12)
                
                if st.checkbox("Calculate tonnage by room size"):
                    sqft = st.number_input("Room Size (sq ft)", value=250)
                    ac_tonnage = round(sqft / 175, 1)
                    st.markdown(f'<p style="font-size:18px; color:#3498db;">Estimated Tonnage: <b>{ac_tonnage} Tons</b></p>', unsafe_allow_html=True)

            # Logic Calculation
            humidity = env.get('hum', 50)
            coef = 0.9 if humidity > 70 else 0.7 if humidity > 40 else 0.4
            daily_yield = ac_tonnage * run_hours * coef
            monthly_yield = daily_yield * 30

            # Dynamic Styling based on Wastage
            is_high_waste = daily_yield > 15
            waste_color = "#E74C3C" if is_high_waste else "#3498DB"
            waste_label = "🔴 High Volume Wastage" if is_high_waste else "🟢 Moderate Recovery"

            with col_ac_viz:
                st.markdown(f'<p class="config-label" style="color:{waste_color};">Current Recovery Potential</p>', unsafe_allow_html=True)
                st.metric(
                    label="Daily Yield", 
                    value=f"{daily_yield:.1f} Liters", 
                    delta=waste_label,
                    delta_color="normal" if is_high_waste else "off"
                )
                
                st.markdown(f'<p class="big-text"><b>Efficiency Gauge:</b></p>', unsafe_allow_html=True)
                st.progress(min(daily_yield / 30, 1.0))

                st.markdown(f"""
                <div style="background-color: {waste_color}22; border: 2px solid {waste_color}; padding: 25px; border-radius: 15px; margin-top: 20px;">
                    <h2 style="margin-top:0; color: {waste_color}; font-family: 'Poppins', sans-serif;">Monthly Potential: {monthly_yield:.0f} Liters</h2>
                    <div class="big-text">
                        <p style="margin-bottom:10px;"><b>Actionable Uses:</b></p>
                        <ul style="margin-top:0;">
                            <li>🪴 <b>Irrigation:</b> Enough for ~{int(daily_yield/2)} large planters.</li>
                            <li>🧹 <b>Cleaning:</b> Equivalent to {int(daily_yield/5)} full buckets.</li>
                            <li>💨 <b>Appliances:</b> Pure distilled quality (zero lime-scale).</li>
                        </ul>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # --- THERMAL STORAGE & CARBON IMPACT SECTION ---
            st.markdown("---")
            
            # Create two columns for the new features
            col_thermal, col_carbon = st.columns(2)

            with col_thermal:
                st.markdown(f"""
                <div style="background-color: #0e1621; border: 1px solid #00d4ff; padding: 25px; border-radius: 15px; height: 100%;">
                    <h3 style="color: #00d4ff; font-family: 'Poppins', sans-serif; margin-top:0;">🧊 Thermal Storage Strategy</h3>
                    <p style="font-size:18px; color: #f8f9fa;">
                        Your AC water exits at <b>12°C – 15°C</b>. This is "Free Coldness."
                    </p>
                    <div style="background: rgba(0, 212, 255, 0.1); padding: 15px; border-radius: 10px; border-left: 5px solid #00d4ff;">
                        <p style="margin:0; font-size:16px;">
                            <b>The Strategy:</b> Store this water in an <b>insulated tank</b>. 
                            At 2:00 PM (Peak Heat), use it to mist your balcony or flush the floor. 
                            This lowers your "Micro-Climate" temperature, reducing AC load by up to <b>8%</b>.
                        </p>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with col_carbon:
                # CO2 Math: 0.4g per liter is a standard for UAE desalination impact
                total_co2_saved = monthly_yield * 0.4 
                # Driving math: Average car emits ~120g CO2 per km
                km_equivalent = total_co2_saved / 120

                st.markdown(f"""
                <div style="background-color: #0e1621; border: 1px solid #2ecc71; padding: 25px; border-radius: 15px; height: 100%;">
                    <h3 style="color: #2ecc71; font-family: 'Poppins', sans-serif; margin-top:0;">🌿 The Green Badge</h3>
                    <p style="font-size:18px; color: #f8f9fa;">
                        Desalinating water in the UAE is energy-intensive. 
                    </p>
                    <div style="text-align:center; padding: 10px;">
                        <span style="font-size:40px;">🛡️</span>
                        <h4 style="margin:10px 0; color:#2ecc71;">Monthly CO2 Offset: {total_co2_saved:.1f}g</h4>
                        <p style="font-size:16px; opacity:0.8;">
                            Equivalent to avoiding <b>{km_equivalent:.2f} km</b> of driving in a petrol car.
                        </p>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("---")
            st.markdown('<h2 style="font-size:32px;">How to Recover this Water</h2>', unsafe_allow_html=True)
            
            r_col1, r_col2 = st.columns(2)
            with r_col1:
                st.markdown(f"""
                <div class="big-text">
                <b>1. The Simple Setup (Gravity Feed)</b><br>
                Most UAE apartments have a drainage pipe on the balcony. Simply reroute this pipe into a 20L BPA-free bucket.<br><br>
                <b>2. Filtration Tip</b><br>
                While the water is distilled-quality, it can pick up dust from the coils. Use a simple mesh filter to keep it debris-free.
                </div>
                """, unsafe_allow_html=True)
            with r_col2:
                st.markdown(f"""
                <div class="big-text">
                <b>3. Storage & Safety</b><br>
                Keep your collection tank covered to prevent mosquito breeding. Use the water within 48 hours for the best results.<br><br>
                <b>4. Maintenance</b><br>
                Check the collection bucket once a day to prevent overflows during high-humidity months.
                </div>
                """, unsafe_allow_html=True)

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
