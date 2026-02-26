import streamlit as st
import streamlit.components.v1 as components
def apply_styles():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
        
        /* 1. Global Backgrounds */
        .stApp { background-color: #0E1117 !important; }
        [data-testid="stSidebar"] { background-color: #000000 !important; }

        /* 2. SEARCH BAR: Light Grey Background with ORANGE TEXT */
        div[data-baseweb="input"] {
            background-color: #D1D5DB !important; /* Soft Grey Box */
            border-radius: 8px !important;
        }
        
        /* THIS IS THE FIX: Typed text will now be Orange */
        input {
            color: #F39C12 !important; 
            -webkit-text-fill-color: #F39C12 !important;
            font-weight: 700 !important;
        }
        
        /* Placeholder text (e.g., "Paris, France") stays dark for contrast */
        input::placeholder {
            color: #444444 !important;
            -webkit-text-fill-color: #444444 !important;
        }

        /* Target the Search Location button specifically */
button[kind="secondaryFormSubmit"], .stButton > button {
    background-color: #F39C12 !important; /* SunScout Orange */
    color: #FFFFFF !important;            /* Pure White Text */
    border: none !important;
    width: 100% !important;               /* Makes it full width in sidebar */
    font-weight: 1000 !important;          /* Makes text bold */
    transition: 0.3s !important;          /* Smooth hover effect */
}

/* Ensure the text inside the button stays white */
button[kind="secondaryFormSubmit"] p, .stButton > button p {
    color: #FFFFFF !important;
}

/* Add a hover effect so it looks professional */
button[kind="secondaryFormSubmit"]:hover, .stButton > button:hover {
    background-color: #e68a00 !important; /* Slightly darker orange on hover */
    color: #FFFFFF !important;
}
        
        .stButton > button p {
            color: #FFFFFF !important;
            font-weight: 800 !important;
        }
        
        .stButton > button:hover {
            background-color: #e68a00 !important;
            border: none !important;
        }

        /* 4. TABS & LABELS: Force White for visibility */
        h1, h2, h3, h4, h5, h6, p, span, label, [data-testid="stWidgetLabel"] p {
            color: #FFFFFF !important;
            opacity: 1 !important;
        }

        /* Active Tab Color */
        button[aria-selected="true"] p {
            color: #F39C12 !important;
        }

        /* 5. SLIDERS: Orange theme */
        .stSlider [data-baseweb="slider"] > div > div {
            background: #F39C12 !important;
        }

        .main-title { color: #F39C12 !important; font-weight: 800; text-align: center; padding: 20px 0px; font-size: 2.5rem; }
        
        
        /* CLEAN MOBILE ALIGNMENT */
        @media (max-width: 768px) {
            /* Fixes the map height on mobile */
            iframe {
                height: 450px !important;
            }
            
            /* Removes excessive padding at the bottom of the page */
            .main .block-container {
                padding-bottom: 1rem !important;
            }

            /* Ensures metrics and charts don't create huge gaps */
            [data-testid="stMetric"] {
                padding: 5px !important;
            }
        }

        /* Fixes the "iframe ghost gap" where height doesn't match content */
        div[data-testid="stHtml"] {
            margin-bottom: -30px !important;
        }
        </style>
    """, unsafe_allow_html=True)


def render_map_component(lat, lon, radius_meters, path_data, animate_trigger, sim_time, m_slat, m_slon, m_shlat, m_shlon, m_el, rise_edge, set_edge, rise_time, set_time, aqi_val):
    env = st.session_state.env_data
    wind_js = ""
    # Only render wind arrow if data exists and toggle is ON
    if env.get("wind_dir") is not None and aqi_val != "Off":
        wd = env["wind_dir"]
        wn = env["wind_name"].upper()
        # Calculate a small 100m arrow pointing FROM the wind direction TO the center
        wind_js = f"""
            var windRad = (({wd} + 180) * Math.PI) / 180;
            var sLat = {lat} - ((150/111111) * Math.cos(windRad));
            var sLon = {lon} - ((150/(111111 * Math.cos({lat} * Math.PI/180))) * Math.sin(windRad));
            var eLat = {lat} + ((30/111111) * Math.cos(windRad));
            var eLon = {lon} + ((30/(111111 * Math.cos({lat} * Math.PI/180))) * Math.sin(windRad));
            
            L.polyline([[sLat, sLon], [eLat, eLon]], {{color: '#00d2ff', weight: 4, opacity: 0.8}}).addTo(map2);
            L.marker([eLat, eLon], {{
                icon: L.divIcon({{
                    className: 'wind-arrow-container',
                    html: `<div style="transform: rotate({wd + 180}deg); color: #00d2ff; font-size: 20px;">▲</div>
                           <div style="color:#00d2ff; font-weight:800; text-shadow: 1px 1px 2px #000; font-size:11px; margin-left:25px; margin-top:-22px; white-space:nowrap;">{wn}</div>`,
                    iconSize: [20, 20], iconAnchor: [10, 10]
                }})
            }}).addTo(map2);
        """

    map_html = f"""
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <div id="map2" style="height: 550px; width: 95%; border-radius: 15px; border: 1px solid #333;"></div>
        <script>
            var street = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png');
            var satellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}');
            var map2 = L.map('map2', {{ center: [{lat}, {lon}], zoom: 17, layers: [street], zoomControl: false }});
            L.control.layers({{"Street": street, "Satellite": satellite}}, null, {{collapsed: false, position: 'topleft'}}).addTo(map2);
            
            var info = L.control({{position: 'topright'}});
            info.onAdd = function() {{
                var div = L.DomUtil.create('div', 'map-stats-card');
                div.innerHTML = `<div>🌅Sunrise: <b>{rise_time}</b></div><div>🌇Sunset: <b>{set_time}</b></div><div style="color:#F39C12;">💨 AQI: <b>{aqi_val}</b></div><div style="colour:#471910;">LEGEND:</div><div>🔴 Sunrise Line</div><div>🔵 Sunset Line</div><div>⚪ Shadow Line</div>`;
                return div;
            }};
            info.addTo(map2);

            L.circle([{lat}, {lon}], {{radius: {radius_meters}, color: 'black', weight: 4, fillOpacity: 0.1}}).addTo(map2);
            {wind_js}

            var pathData = {path_data};            
            L.polyline(pathData.map(p => [p.lat, p.lon]), {{color: '#FF7518', weight: 7, dashArray: '5, 10', opacity: 0.6}}).addTo(map2);
            L.polyline([[{lat}, {lon}], {rise_edge}], {{color: '#e74c3c', weight: 5}}).addTo(map2);
            L.polyline([[{lat}, {lon}], {set_edge}], {{color: '#3498db', weight: 5}}).addTo(map2);

            var sunIcon = L.divIcon({{ html: `<div class="sun-container"><div id="sun-time-label" class="pointing-box">--:--</div><div class="sun-emoji">☀️</div></div>`, iconSize: [80, 80], iconAnchor: [40, 62], className: 'custom-sun-icon' }});
            var sunMarker = L.marker([0, 0], {{icon: sunIcon}}).addTo(map2);
            var shadow = L.polyline([[{lat}, {lon}], [{lat}, {lon}]], {{color: '#4F4F4F', weight: 6, opacity: 0.8}}).addTo(map2);

            function update(pos) {{
                if (pos) {{
                    sunMarker.setLatLng([pos.lat, pos.lon]);
                    shadow.setLatLngs([[{lat}, {lon}], [pos.shlat, pos.shlon]]);
                    document.getElementById('sun-time-label').innerHTML = pos.time;
                    sunMarker.setOpacity(pos.el < 0 ? 0 : 1);
                    shadow.setStyle({{opacity: pos.el < 0 ? 0 : 0.8}});
                }}
            }}
            if ({str(animate_trigger).lower()}) {{
                var i = 0; setInterval(() => {{ update(pathData[i]); i = (i + 1) % pathData.length; }}, 150);
            }} else {{ update({{lat:{m_slat}, lon:{m_slon}, shlat:{m_shlat}, shlon:{m_shlon}, el:{m_el}, time:"{sim_time.strftime('%H:%M')}"}}); }}
        </script>
        <style>
            .map-stats-card {{ background: rgba(14, 17, 23, 0.85); padding: 12px; border-radius: 12px; border: 1px solid #F39C12; color: white; font-size: 13px; }}
            .custom-sun-icon, .wind-arrow-container {{ background: none; border: none; }}
            .pointing-box {{ background: #F39C12; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 13px; }}
            .sun-emoji {{ font-size: 32pt; }}
        </style>
    """
    components.html(map_html, height=550)

def render_seasonal_map(lat, lon, radius, seasonal_paths):
    import math
    paths_js = ""
    color_map = {"Summer": "#FF0000", "Autumn": "#FF8C00", "Spring": "#FFD700", "Winter": "#FFFF00"}
    
    for season_id, data in seasonal_paths.items():
        coords, label = data["coords"], data["label"]
        if coords:
            color = color_map.get(season_id, '#FFF')
            paths_js += f"L.polyline({coords}, {{color: '{color}', weight: 6, opacity: 0.8}}).addTo(map_s);"
            paths_js += f"""
                L.circleMarker({coords[0]}, {{radius: 7, color: 'white', weight: 2, fillColor: '{color}', fillOpacity: 1}}).addTo(map_s)
                 .bindTooltip('<b style="color:{color};">{season_id}</b>', {{permanent: true, direction: 'top', className: 'season-label'}});
            """
            paths_js += f"L.circleMarker({coords[-1]}, {{radius: 7, color: 'white', weight: 2, fillColor: '{color}', fillOpacity: 1}}).addTo(map_s);"


    set_coords = [lat, lon - 0.0055]
    rise_coords = [lat, lon + 0.0035]

    html_content = f"""
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <div id="map_s" style="height: 600px; width: 100%; border-radius: 15px; background: #111; border: 1px solid #444;"></div>
        <script>
            var satellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}');
            var street = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png');
            var map_s = L.map('map_s', {{ center: [{lat}, {lon}], zoom: 17, layers: [satellite], zoomControl: false }});
            
            L.control.zoom({{ position: 'bottomright' }}).addTo(map_s);
            L.control.layers({{"Satellite": satellite, "Street": street}}, null, {{position: 'topleft'}}).addTo(map_s);
            
            L.circle([{lat}, {lon}], {{ radius: {radius}, color: 'black', weight: 3, fillOpacity: 0.05 }}).addTo(map_s);
            L.circleMarker([{lat}, {lon}], {{radius: 5, color: 'white', fillColor: '#F39C12', fillOpacity: 1}}).addTo(map_s);
            
            L.marker({set_coords}, {{ opacity: 0 }}).addTo(map_s)
                .bindTooltip("SUNSET", {{ permanent: true, direction: 'center', className: 'loc-label sunset-vibrant' }});
                
            L.marker({rise_coords}, {{ opacity: 0 }}).addTo(map_s)
                .bindTooltip("SUNRISE", {{ permanent: true, direction: 'center', className: 'loc-label sunrise-vibrant' }});

            {paths_js}
        </script>
        <style>
            .season-label {{
                background: rgba(0, 0, 0, 0.8) !important;
                border: 1px solid rgba(255,255,255,0.2) !important;
                color: white !important;
                font-family: 'Inter', sans-serif !important;
                font-weight: bold !important;
                font-size: 11px !important;
                padding: 2px 6px !important;
            }}
            .leaflet-tooltip-top:before {{ display: none !important; }}

            .loc-label {{
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
                font-family: 'Inter', sans-serif !important;
                font-weight: 800 !important;
                font-size: 16px !important; 
                letter-spacing: 1.5px !important;
                pointer-events: none !important;
            }}
            .sunrise-vibrant {{ 
                color: #FF0000 !important; 
                text-shadow: 1px 1px 15px #000 !important; 
            }}
            .sunset-vibrant {{ 
                color: #0070FF !important; 
                text-shadow: 1px 1px 15px #000 !important; 
            }}
        </style>
    """
    components.html(html_content, height=620)

