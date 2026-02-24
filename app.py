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


# --- PAGE ROUTING ---
if st.session_state.page == "home":
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
            <h1 class="flowstate-title">FLOW STATE</h1>
            <p class="flowstate-subtitle">Guided by light • Sustained by water</p>
            """, 
            unsafe_allow_html=True
        )
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🚀 GO TO MAPS", use_container_width=True, type="primary"):
            st.session_state.page = "app"
            st.rerun()

    
    st.markdown("""
    <div style="color: white; font-family: 'Inter', sans-serif;">
    <h2 style="color: white;">🤩 Let the Sun guide your next big decision. </h2>
    <p>Ever wondered how much sunlight your <b>bedroom, balcony, terrace garden,</b> or <b>solar panels</b> will get throughout the year? Now you don't have to guess.</p>
    <hr style="border-top: 1px solid rgba(255,255,255,0.2); margin: 20px 0;">
    <h3 style="color: white;">🌍 What Solar Path Visualizer Does</h3>
    <p>A simple, educational purpose-built tool that <b>instantly shows how sunlight moves across any location on Earth</b>.</p>
    <ul style="list-style-type: none; padding-left: 20px; line-height: 2;">
        <li>🏠 <b>Buying a new home</b></li>
        <li>🌿 <b>Planning a balcony or terrace garden</b></li>
        <li>☀️ <b>Installing a solar geyser or solar panels</b></li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
else:
    # --- EVERYTHING BELOW IS THE MAIN APP ---
    radius_meters = 250
    target_date = date.today()

    with st.sidebar:
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
            <p class="flowstate-subtitle">Guided by light • Sustained by water</p>
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
    tab_location, tab_sunfeatures, tab_waterfeatures = st.tabs(["📍 Location Setup", "Sun Features", "Water Features"])
        
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
        wfeature_choice = st.selectbox("Analysis Tool", ["Water Stress Score (WSS)"])
        if wfeature_choice == "Water Stress Score (WSS)":
            st.markdown(f"""
                <div style="text-align: center;">
                    <h1 style="color: #3498db; font-family: 'Poppins', sans-serif;">Water Stress Intelligence</h1>
                </div>
            """, unsafe_allow_html=True)
            st.markdown('<div style="height: 50px;"></div>', unsafe_allow_html=True)

    
            u_lat, u_lon = st.session_state.coords[0], st.session_state.coords[1]
            env = st.session_state.env_data
            
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
                st.markdown(f"""
                    <div style="text-align: center; background: rgba(255,255,255,0.05); padding: 20px; border-radius: 10px; border-bottom: 5px solid {res['color']};">
                        <h2 style="margin:0; font-size: 30px;">Water Stress Score <br> {wss_val} / 100</h2>
                        <div style="background: {res['color']}; color: white; padding: 5px 20px; border-radius: 5px; display: inline-block; margin-top: 10px; font-weight: bold;">
                            ⚠️ {res['status'].upper()}
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                st.markdown('<div style="height: 40px;"></div>', unsafe_allow_html=True)

                st.write("#### Factors Contributing to Water Stress")
                
                fig_bar = go.Figure(data=[
                    go.Bar(
                        x=['Solar', 'Temperature', 'Evapotranspiration', 'Humidity'],
                        y=breakdown,
                        marker_color=['#f1c40f', '#e67e22', '#3498db', '#2ecc71'],
                        text=[f"{x:.1f}%" for x in breakdown],
                        textposition='auto',
                    )
                ])
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
                
                # Determine color based on status
                status_color = "#2ecc71" if res["status"] == "Low" else "#f1c40f" if res["status"] == "Moderate" else "#e74c3c"
                bg_color = "rgba(46, 204, 113, 0.1)" if res["status"] == "Low" else "rgba(241, 196, 15, 0.1)" if res["status"] == "Extreme" else "rgba(231, 76, 60, 0.1)"

                # Custom Styled List for Measures
                measures_html = ""
                for action in res["actions"]:
                    measures_html += f"<div style='margin-bottom: 12px;'>✅ {action}</div>"

                st.markdown(f"""
                    <div style="
                        background-color: {bg_color}; 
                        border-radius: 10px; 
                        padding: 20px; 
                        border: 1px solid {status_color};
                        color: white;
                        font-size: 20px; 
                        line-height: 1.6;
                        font-family: 'Poppins', sans-serif;
                    ">
                        {measures_html}
                    </div>
                """, unsafe_allow_html=True)

                st.markdown("---")
                st.markdown("### 📊 Estimated Impact")
                
                st.markdown(f"""
                    <div style="font-size: 20px; line-height: 2.2;">
                        💧 <b>Estimated Water Saved:</b> <span style="color: #3498db;">{res['savings']['water']}</span><br>
                        💰 <b>Monthly Cost Savings:</b> <span style="color: #2ecc71;">{res['savings']['cost']}</span><br>
                        📈 <b>Evaporation Reduction:</b> <span style="color: #f39c12;">{res['savings']['evap']}</span>
                    </div>
                """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                st.markdown(f"""
                    <div style="background: rgba(46, 204, 113, 0.1); padding: 20px; border-radius: 12px; border-left: 8px solid #2ecc71;">
                        <p style="margin:0; font-size: 18px; color: white;"><b>Eco-Efficiency</b></p>
                        <p style="margin:0; font-size: 15px; color: #bdc3c7;">Optimization is active.</p>
                    </div>
                """, unsafe_allow_html=True)
