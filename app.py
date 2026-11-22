import os
import sqlite3
import uuid
import json
import hashlib
from datetime import datetime
import streamlit as st
import streamlit.components.v1 as components
from werkzeug.security import generate_password_hash, check_password_hash

# ==============================================================================
# PAGE CONFIG & CUSTOM ACROSS LOGISTICS STYLING (Matches Section 4.4 Screenshots)
# ==============================================================================
st.set_page_config(
    page_title="ACROSS LOGISTICS | 3PL Secure & Trackable Delivery",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    /* Clean high-contrast light theme matching ACROSS LOGISTICS screenshots */
    .stApp {
        background-color: #f4f5f7;
        color: #1f2937;
    }
    header[data-testid="stHeader"] {
        background-color: #333333;
    }
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 1260px;
    }
    /* Top Brand Banner */
    .across-navbar {
        background-color: #333333;
        color: #ffffff;
        padding: 16px 28px;
        border-radius: 4px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 18px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.18);
    }
    .across-brand {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .across-logo {
        width: 38px;
        height: 38px;
        background: #C8102E;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        color: #ffffff;
        font-weight: 900;
        font-size: 18px;
    }
    .across-title {
        font-size: 20px;
        font-weight: 800;
        letter-spacing: 1.5px;
        line-height: 1.1;
        color: #ffffff;
    }
    .across-sub {
        font-size: 10px;
        letter-spacing: 3px;
        color: #d1d5db;
    }
    /* Hero Banner (Fig 4.4.2 Home Interface) */
    .across-hero {
        background: linear-gradient(90deg, rgba(25,25,25,0.88) 0%, rgba(45,35,35,0.72) 55%, rgba(200,16,46,0.85) 100%),
                    url('https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?auto=format&fit=crop&w=1600&q=80') center/cover no-repeat;
        color: #ffffff;
        padding: 56px 44px;
        border-radius: 4px;
        margin-bottom: 20px;
    }
    .across-hero h1 {
        font-size: 38px;
        font-weight: 300;
        color: #ffffff !important;
        max-width: 680px;
        margin-bottom: 16px;
        line-height: 1.25;
    }
    .across-hero p {
        color: #f3f4f6;
        max-width: 620px;
        font-size: 15px;
        border-top: 1px solid rgba(255,255,255,0.45);
        padding-top: 16px;
    }
    /* Cards & Metrics */
    .metric-card {
        background: #ffffff;
        border-left: 4px solid #C8102E;
        padding: 18px 20px;
        border-radius: 4px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        margin-bottom: 12px;
    }
    .metric-card h2 {
        margin: 0;
        font-size: 26px;
        color: #111827 !important;
        font-weight: 700;
    }
    .metric-card p {
        margin: 4px 0 0 0;
        font-size: 12px;
        color: #4b5563;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 600;
    }
    .section-card {
        background: #ffffff;
        padding: 22px 24px;
        border-radius: 4px;
        border: 1px solid #e5e7eb;
        margin-bottom: 18px;
    }
    .section-header {
        font-size: 18px;
        font-weight: 700;
        color: #111827;
        border-bottom: 2px solid #C8102E;
        padding-bottom: 8px;
        margin-bottom: 16px;
    }
    .contact-banner {
        background: #C8102E;
        color: #ffffff;
        padding: 36px 28px;
        border-radius: 4px;
        height: 100%;
    }
    .contact-banner h2, .contact-banner h3, .contact-banner p {
        color: #ffffff !important;
    }
    /* Primary Buttons */
    div.stButton > button {
        background-color: #C8102E;
        color: #ffffff;
        border: none;
        border-radius: 3px;
        font-weight: 600;
    }
    div.stButton > button:hover {
        background-color: #9e0b23;
        color: #ffffff;
    }
    /* High contrast text visibility */
    label, .stMarkdown p, .stMarkdown li {
        color: #1f2937 !important;
    }
    .across-hero p, .across-navbar span, .across-navbar div, .contact-banner p {
        color: #ffffff !important;
    }
</style>
""", unsafe_allow_html=True)

DATABASE = "across_logistics_3pl.db"


# ==============================================================================
# DATABASE SETUP (Section 3.7: 9 Relational Tables)
# ==============================================================================
def get_conn():
    conn = sqlite3.connect(DATABASE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    db = get_conn()
    cursor = db.cursor()

    # 3.7.1 Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin', 'customer', 'personnel')),
        status TEXT DEFAULT 'Active',
        created_at TEXT NOT NULL
    )
    """)

    # 3.7.2 Customers Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        address TEXT,
        city TEXT,
        state TEXT,
        registration_date TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    )
    """)

    # 3.7.3 Delivery Personnel Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS delivery_personnel (
        personnel_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        vehicle_number TEXT NOT NULL,
        vehicle_type TEXT NOT NULL,
        assigned_area TEXT NOT NULL,
        availability TEXT DEFAULT 'Available',
        date_registered TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    )
    """)

    # 3.7.4 Shipments Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS shipments (
        shipment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        tracking_number TEXT UNIQUE NOT NULL,
        sender_name TEXT NOT NULL,
        sender_phone TEXT NOT NULL,
        recipient_name TEXT NOT NULL,
        recipient_phone TEXT NOT NULL,
        pickup_address TEXT NOT NULL,
        delivery_address TEXT NOT NULL,
        goods_description TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        weight REAL NOT NULL,
        shipment_mode TEXT DEFAULT 'ROAD / EXPRESS',
        security_seal_hash TEXT NOT NULL,
        shipment_status TEXT DEFAULT 'Registered',
        created_at TEXT NOT NULL,
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
    )
    """)

    # 3.7.5 Delivery Assignment Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS delivery_assignments (
        assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        shipment_id INTEGER UNIQUE NOT NULL,
        personnel_id INTEGER NOT NULL,
        assigned_date TEXT NOT NULL,
        expected_delivery TEXT NOT NULL,
        assignment_status TEXT DEFAULT 'Assigned',
        FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id),
        FOREIGN KEY (personnel_id) REFERENCES delivery_personnel(personnel_id)
    )
    """)

    # 3.7.6 Tracking Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tracking (
        tracking_id INTEGER PRIMARY KEY AUTOINCREMENT,
        shipment_id INTEGER NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        location_name TEXT NOT NULL,
        status TEXT NOT NULL,
        remarks TEXT,
        recorded_at TEXT NOT NULL,
        FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id)
    )
    """)

    # 3.7.7 Notifications Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        shipment_id INTEGER,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        notification_type TEXT DEFAULT 'Status Update',
        is_read INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """)

    # 3.7.8 Proof of Delivery Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS proof_of_delivery (
        pod_id INTEGER PRIMARY KEY AUTOINCREMENT,
        shipment_id INTEGER UNIQUE NOT NULL,
        personnel_id INTEGER NOT NULL,
        recipient_name TEXT NOT NULL,
        delivery_date TEXT NOT NULL,
        delivery_time TEXT NOT NULL,
        confirmation_method TEXT NOT NULL,
        remarks TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id),
        FOREIGN KEY (personnel_id) REFERENCES delivery_personnel(personnel_id)
    )
    """)

    # 3.7.9 System Activity/Log Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS system_logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        activity TEXT NOT NULL,
        ip_address TEXT,
        created_at TEXT NOT NULL
    )
    """)

    # Contact Inquiries Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contact_inquiries (
        inquiry_id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        company_name TEXT,
        email TEXT NOT NULL,
        service_interest TEXT,
        country TEXT,
        phone TEXT,
        website TEXT,
        message TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    # Seed initial demo records
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute(
            "INSERT INTO users (full_name, email, phone, password, role, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("System Administrator", "admin@acrosslogistics.com", "+2348010000001",
             generate_password_hash("admin123"), "admin", now)
        )

        cursor.execute(
            "INSERT INTO users (full_name, email, phone, password, role, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("Johnson Kingsley", "customer@acrosslogistics.com", "+2348020000002",
             generate_password_hash("customer123"), "customer", now)
        )
        cust_uid = cursor.lastrowid
        cursor.execute(
            "INSERT INTO customers (user_id, address, city, state, registration_date) VALUES (?, ?, ?, ?, ?)",
            (cust_uid, "Gateway ICT Polytechnic Road, Saapade", "Sagamu", "Ogun State", now)
        )
        cust_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO users (full_name, email, phone, password, role, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("Adebayo Tunde (Driver)", "driver@acrosslogistics.com", "+2348030000003",
             generate_password_hash("driver123"), "personnel", now)
        )
        drv_uid = cursor.lastrowid
        cursor.execute(
            "INSERT INTO delivery_personnel (user_id, vehicle_number, vehicle_type, assigned_area, date_registered) VALUES (?, ?, ?, ?, ?)",
            (drv_uid, "OGN-482-KJA", "Heavy Cargo Van", "Lagos - Ogun - Ibadan Corridor", now)
        )
        pers_id = cursor.lastrowid

        trk_num = "ACR-2026-88412"
        seal_hash = hashlib.sha256(f"{trk_num}-{now}".encode()).hexdigest()[:16].upper()
        cursor.execute("""
            INSERT INTO shipments (
                customer_id, tracking_number, sender_name, sender_phone,
                recipient_name, recipient_phone, pickup_address, delivery_address,
                goods_description, quantity, weight, shipment_mode, security_seal_hash,
                shipment_status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cust_id, trk_num, "Johnson Kingsley", "+2348020000002",
            "Mr. Oni O.O", "+2348055551234",
            "Apapa Port Logistics Hub, Lagos", "Gateway ICT Polytechnic, Saapade, Ogun State",
            "Computer Lab Servers & Networking Equipment (Tamper-Sealed)", 4, 125.5,
            "ROAD / EXPRESS", seal_hash, "In Transit", now
        ))
        ship_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO delivery_assignments (shipment_id, personnel_id, assigned_date, expected_delivery, assignment_status)
            VALUES (?, ?, ?, ?, ?)
        """, (ship_id, pers_id, now, "Within 24 Hours", "In Progress"))

        waypoints = [
            (6.4483, 3.3590, "Apapa 3PL Warehouse Hub, Lagos", "Registered", "Goods inspected, serialized & tamper-sealed."),
            (6.6018, 3.3515, "Ikeja Regional Sorting Center, Lagos", "Dispatched", "Loaded onto vehicle OGN-482-KJA."),
            (6.8322, 3.6319, "Sagamu Interchange Checkpoint, Ogun State", "In Transit", "GPS signal verified; seal integrity intact.")
        ]
        for lat, lng, loc, st, rem in waypoints:
            cursor.execute("""
                INSERT INTO tracking (shipment_id, latitude, longitude, location_name, status, remarks, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (ship_id, lat, lng, loc, st, rem, now))

        cursor.execute("""
            INSERT INTO notifications (user_id, shipment_id, title, message, notification_type, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            cust_uid, ship_id, f"Shipment {trk_num} In Transit",
            "Your shipment passed Sagamu Interchange Checkpoint with security seal verified.",
            "Tracking Update", now
        ))

    db.commit()
    db.close()


def log_activity(user_id, activity):
    db = get_conn()
    db.execute(
        "INSERT INTO system_logs (user_id, activity, ip_address, created_at) VALUES (?, ?, ?, ?)",
        (user_id, activity, "Streamlit-Session", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    db.commit()
    db.close()


def create_notification(user_id, shipment_id, title, message, n_type="Status Update"):
    db = get_conn()
    db.execute(
        "INSERT INTO notifications (user_id, shipment_id, title, message, notification_type, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, shipment_id, title, message, n_type, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    db.commit()
    db.close()


# Initialize DB on startup
init_db()

# Session State Initialization
if "user" not in st.session_state:
    st.session_state.user = None
if "page" not in st.session_state:
    st.session_state.page = "Home"
if "quick_trk" not in st.session_state:
    st.session_state.quick_trk = "ACR-2026-88412"


# ==============================================================================
# NAVIGATION BAR (Matches ACROSS LOGISTICS Top Header)
# ==============================================================================
role_badge = f" ({st.session_state.user['role'].upper()})" if st.session_state.user else ""
st.markdown(f"""
<div class="across-navbar">
    <div class="across-brand">
        <div class="across-logo">&#9650;</div>
        <div>
            <div class="across-title">ACROSS</div>
            <div class="across-sub">LOGISTICS</div>
        </div>
    </div>
    <div style="font-size:13px; letter-spacing:0.6px;">
        3PL SECURE & TRACKABLE GOODS DELIVERY SYSTEM &nbsp;|&nbsp; 🇬🇧 EN
    </div>
</div>
""", unsafe_allow_html=True)

nav_cols = st.columns([1.1, 1.3, 1.6, 1.1, 1.0])
with nav_cols[0]:
    if st.button("🏠 Home", use_container_width=True):
        st.session_state.page = "Home"
        st.rerun()
with nav_cols[1]:
    if st.button("📍 TRACKING", use_container_width=True):
        st.session_state.page = "Tracking"
        st.rerun()
with nav_cols[2]:
    label = f"🔐 PRIVATE AREA{role_badge}" if st.session_state.user else "🔐 PRIVATE AREA (LOGIN)"
    if st.button(label, use_container_width=True):
        st.session_state.page = "Private Area"
        st.rerun()
with nav_cols[3]:
    if st.button("📞 Contact", use_container_width=True):
        st.session_state.page = "Contact"
        st.rerun()
with nav_cols[4]:
    if st.session_state.user:
        if st.button("🚪 Logout", use_container_width=True):
            log_activity(st.session_state.user["user_id"], "User logged out")
            st.session_state.user = None
            st.session_state.page = "Home"
            st.rerun()


# ==============================================================================
# PAGE 1: HOME INTERFACE (Fig. 4.4.2)
# ==============================================================================
def render_home():
    st.markdown("""
    <div class="across-hero">
        <h1>The integral logistic solutions that your company needs.</h1>
        <p>
            End-to-end Third-Party Logistics (3PL) platform featuring tamper-evident shipment serialization,
            role-based security access control, real-time GPS waypoint tracking, and digital Proof of Delivery (POD).
        </p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown('<div class="metric-card"><h2>100%</h2><p>Tamper-Sealed Chain of Custody</p></div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="metric-card"><h2>GPS / IoT</h2><p>Live Waypoint Telemetry</p></div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="metric-card"><h2>RBAC</h2><p>Encrypted Multi-Role Security</p></div>', unsafe_allow_html=True)
    with c4:
        st.markdown('<div class="metric-card"><h2>Digital POD</h2><p>Verified Recipient Sign-Off</p></div>', unsafe_allow_html=True)

    st.markdown('<div class="section-card"><div class="section-header">Quick Shipment Verification</div>', unsafe_allow_html=True)
    qcol1, qcol2 = st.columns([4, 1])
    with qcol1:
        trk_input = st.text_input("Enter Tracking Number", value=st.session_state.quick_trk, label_visibility="collapsed", placeholder="e.g. ACR-2026-88412")
    with qcol2:
        if st.button("Track Goods", use_container_width=True):
            st.session_state.quick_trk = trk_input.strip().upper()
            st.session_state.page = "Tracking"
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# ==============================================================================
# PAGE 2: REAL-TIME TRACKING INTERFACE (Fig. 4.4.4)
# ==============================================================================
def render_tracking():
    st.markdown("""
    <div class="section-card">
        <h2 style="margin:0 0 6px 0; color:#111827;">Please enter the tracking number</h2>
        <div style="width:320px; height:2px; background:#222; margin:10px 0 12px 0;"></div>
        <p style="margin:0; font-size:14px;">In case no results appear in the search please use the Contact page. (Demo ID: <b>ACR-2026-88412</b>)</p>
    </div>
    """, unsafe_allow_html=True)

    col_map, col_info = st.columns([1.25, 1])

    with col_info:
        mode = st.radio("Transport Mode", ["🚚 ROAD / EXPRESS", "✈️ AIR FREIGHT", "🚢 OCEAN CARGO"], horizontal=True)
        scol1, scol2 = st.columns([3.5, 1])
        with scol1:
            trk_query = st.text_input("Tracking / Waybill / Reference Number", value=st.session_state.quick_trk, label_visibility="collapsed").strip().upper()
        with scol2:
            search_clicked = st.button("🔍 Track", use_container_width=True)

        if search_clicked:
            st.session_state.quick_trk = trk_query

        db = get_conn()
        shipment = db.execute("SELECT * FROM shipments WHERE tracking_number = ?", (trk_query,)).fetchone() if trk_query else None
        history = []
        pod = None
        driver = None

        if shipment:
            history = db.execute("SELECT * FROM tracking WHERE shipment_id = ? ORDER BY tracking_id ASC", (shipment["shipment_id"],)).fetchall()
            pod = db.execute("SELECT * FROM proof_of_delivery WHERE shipment_id = ?", (shipment["shipment_id"],)).fetchone()
            driver = db.execute("""
                SELECT u.full_name, u.phone, dp.vehicle_number, dp.vehicle_type
                FROM delivery_assignments da
                JOIN delivery_personnel dp ON da.personnel_id = dp.personnel_id
                JOIN users u ON dp.user_id = u.user_id
                WHERE da.shipment_id = ?
            """, (shipment["shipment_id"],)).fetchone()

            st.success(f"**{shipment['tracking_number']}** — Status: **{shipment['shipment_status']}**")
            st.markdown(f"""
            <div class="section-card" style="padding:16px;">
                <p><b>Goods:</b> {shipment['goods_description']} (Qty: {shipment['quantity']}, {shipment['weight']} kg)</p>
                <p><b>Origin:</b> {shipment['pickup_address']}</p>
                <p><b>Destination:</b> {shipment['delivery_address']}</p>
                <p><b>Recipient:</b> {shipment['recipient_name']} ({shipment['recipient_phone']})</p>
                <p style="color:#047857;">🔒 <b>Tamper-Evident Seal Hash:</b> <code>{shipment['security_seal_hash']}</code></p>
                {"<p>🚚 <b>Assigned Courier:</b> " + driver['full_name'] + " | Vehicle: " + driver['vehicle_number'] + "</p>" if driver else ""}
            </div>
            """, unsafe_allow_html=True)

            st.markdown("#### Real-Time Checkpoints & Audit Trail")
            for item in history:
                st.markdown(f"""
                <div style="border-left:3px solid #C8102E; padding-left:12px; margin-bottom:12px; background:#fff; padding:10px 12px; border-radius:3px;">
                    <b>{item['status']} — {item['location_name']}</b><br>
                    <span style="font-size:13px;">{item['remarks']}</span><br>
                    <small style="color:#6b7280;">GPS: {item['latitude']}, {item['longitude']} | {item['recorded_at']}</small>
                </div>
                """, unsafe_allow_html=True)

            if pod:
                st.info(f"✅ **Digital Proof of Delivery Verified** — Received by **{pod['recipient_name']}** via {pod['confirmation_method']} on {pod['delivery_date']} at {pod['delivery_time']}.")
        elif trk_query:
            st.warning(f"No shipment found matching '{trk_query}'.")
        db.close()

    with col_map:
        points_data = [
            {
                "lat": h["latitude"],
                "lng": h["longitude"],
                "loc": h["location_name"],
                "status": h["status"],
                "time": h["recorded_at"]
            } for h in history
        ]
        map_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <style>html, body, #map {{ height: 100%; margin: 0; padding: 0; border-radius: 4px; }}</style>
        </head>
        <body>
            <div id="map"></div>
            <script>
                var points = {json.dumps(points_data)};
                var map = L.map('map').setView([6.6500, 3.5000], 9);
                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                    attribution: '&copy; OpenStreetMap contributors'
                }}).addTo(map);
                if (points.length > 0) {{
                    var latlngs = [];
                    points.forEach(function(pt, idx) {{
                        var c = [pt.lat, pt.lng];
                        latlngs.push(c);
                        var m = L.marker(c).addTo(map);
                        m.bindPopup("<b>" + pt.status + "</b><br>" + pt.loc + "<br><small>" + pt.time + "</small>");
                        if (idx === points.length - 1) m.openPopup();
                    }});
                    var line = L.polyline(latlngs, {{color: '#C8102E', weight: 4}}).addTo(map);
                    map.fitBounds(line.getBounds(), {{padding: [40, 40]}});
                }}
            </script>
        </body>
        </html>
        """
        components.html(map_html, height=540)


# ==============================================================================
# PAGE 3: CONTACT INTERFACE (Fig. 4.4.3)
# ==============================================================================
def render_contact():
    c_left, c_right = st.columns([1, 1.2])
    with c_left:
        st.markdown("""
        <div class="contact-banner">
            <h2>Contact us</h2>
            <hr style="border-color:rgba(255,255,255,0.6);">
            <h3>Need further information?<br>Personalized advice?</h3>
            <p>Our Customer Service department will meet all your needs.</p>
            <br><br>
            <p style="font-size:13px; opacity:0.9;">Nigeria & West Africa Logistics Hub</p>
            <h2>+234 801 000 0001</h2>
            <p style="font-size:13px;">Saapade / Sagamu Corridor, Ogun State</p>
        </div>
        """, unsafe_allow_html=True)

    with c_right:
        st.markdown('<div class="section-card"><div class="section-header" style="color:#C8102E;">Contact form:</div>', unsafe_allow_html=True)
        with st.form("contact_form"):
            r1c1, r1c2 = st.columns(2)
            fname = r1c1.text_input("First Name*")
            lname = r1c2.text_input("Last Name*")
            r2c1, r2c2 = st.columns(2)
            cname = r2c1.text_input("Company Name*")
            cemail = r2c2.text_input("Company email*")
            r3c1, r3c2 = st.columns(2)
            service = r3c1.selectbox("Service of interest", ["3PL Warehousing & Distribution", "Secure Trackable Delivery", "Last-Mile Logistics"])
            country = r3c2.selectbox("Country", ["Nigeria", "Ghana", "United Kingdom", "Spain"])
            phone = st.text_input("Phone Number", value="+234 ")
            website = st.text_input("Company Website")
            msg = st.text_area("Please provide us with more details about your needs*")
            if st.form_submit_button("Send Inquiry"):
                if fname and lname and cemail and msg:
                    db = get_conn()
                    db.execute("""
                        INSERT INTO contact_inquiries (first_name, last_name, company_name, email, service_interest, country, phone, website, message, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (fname, lname, cname, cemail, service, country, phone, website, msg, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    db.commit()
                    db.close()
                    st.success("Thank you! Your inquiry has been received by our Customer Service department.")
                else:
                    st.error("Please fill all required (*) fields.")
        st.markdown("</div>", unsafe_allow_html=True)


# ==============================================================================
# PAGE 4: PRIVATE AREA (AUTH + ROLE-BASED DASHBOARDS)
# ==============================================================================
def render_auth():
    col_login, col_reg = st.columns(2)
    with col_login:
        st.markdown('<div class="section-card"><div class="section-header">Private Area — Secure Login</div>', unsafe_allow_html=True)
        with st.form("login_form"):
            email = st.text_input("Email Address").strip().lower()
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Sign In"):
                db = get_conn()
                user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
                db.close()
                if user and check_password_hash(user["password"], password):
                    st.session_state.user = dict(user)
                    log_activity(user["user_id"], f"User logged in ({user['role']})")
                    st.rerun()
                else:
                    st.error("Invalid email or password.")
        st.info("""
        **Pre-Loaded Demo Credentials:**
        - **Admin:** `admin@acrosslogistics.com` / `admin123`
        - **Customer:** `customer@acrosslogistics.com` / `customer123`
        - **Driver:** `driver@acrosslogistics.com` / `driver123`
        """)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_reg:
        st.markdown('<div class="section-card"><div class="section-header">New Customer Registration</div>', unsafe_allow_html=True)
        with st.form("register_form"):
            r_name = st.text_input("Full Name / Organization*")
            rc1, rc2 = st.columns(2)
            r_email = rc1.text_input("Email Address*").strip().lower()
            r_phone = rc2.text_input("Phone Number*")
            r_addr = st.text_input("Residential / Business Address*")
            rc3, rc4 = st.columns(2)
            r_city = rc3.text_input("City*")
            r_state = rc4.text_input("State*")
            r_pass = st.text_input("Password (min 6 chars)*", type="password")
            if st.form_submit_button("Create Customer Account"):
                if r_name and r_email and r_phone and len(r_pass) >= 6:
                    db = get_conn()
                    if db.execute("SELECT user_id FROM users WHERE email = ?", (r_email,)).fetchone():
                        st.error("Email already registered.")
                    else:
                        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        cur = db.cursor()
                        cur.execute(
                            "INSERT INTO users (full_name, email, phone, password, role, created_at) VALUES (?, ?, ?, ?, 'customer', ?)",
                            (r_name, r_email, r_phone, generate_password_hash(r_pass), now)
                        )
                        uid = cur.lastrowid
                        cur.execute(
                            "INSERT INTO customers (user_id, address, city, state, registration_date) VALUES (?, ?, ?, ?, ?)",
                            (uid, r_addr, r_city, r_state, now)
                        )
                        db.commit()
                        log_activity(uid, "New customer account registered")
                        st.success("Account created! You can now sign in on the left.")
                    db.close()
                else:
                    st.error("Complete all required fields (password >= 6 chars).")
        st.markdown("</div>", unsafe_allow_html=True)


def render_admin_dashboard():
    db = get_conn()
    st.subheader("3PL Operations Command Center — Administrator")

    c_count = db.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    s_count = db.execute("SELECT COUNT(*) FROM shipments").fetchone()[0]
    t_count = db.execute("SELECT COUNT(*) FROM shipments WHERE shipment_status IN ('Dispatched','In Transit','Out for Delivery')").fetchone()[0]
    d_count = db.execute("SELECT COUNT(*) FROM shipments WHERE shipment_status = 'Delivered'").fetchone()[0]
    p_count = db.execute("SELECT COUNT(*) FROM delivery_personnel").fetchone()[0]

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.markdown(f'<div class="metric-card"><h2>{c_count}</h2><p>Customers</p></div>', unsafe_allow_html=True)
    m2.markdown(f'<div class="metric-card"><h2>{s_count}</h2><p>Total Shipments</p></div>', unsafe_allow_html=True)
    m3.markdown(f'<div class="metric-card"><h2>{t_count}</h2><p>In Transit</p></div>', unsafe_allow_html=True)
    m4.markdown(f'<div class="metric-card"><h2>{d_count}</h2><p>Delivered</p></div>', unsafe_allow_html=True)
    m5.markdown(f'<div class="metric-card"><h2>{p_count}</h2><p>Fleet Drivers</p></div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📦 Shipments & Assignment", "🚚 Register Fleet Personnel", "🛡️ Security Audit Logs"])

    with tab1:
        shipments = db.execute("""
            SELECT s.*, u.full_name AS customer_name, du.full_name AS driver_name
            FROM shipments s
            JOIN customers c ON s.customer_id = c.customer_id
            JOIN users u ON c.user_id = u.user_id
            LEFT JOIN delivery_assignments da ON s.shipment_id = da.shipment_id
            LEFT JOIN delivery_personnel dp ON da.personnel_id = dp.personnel_id
            LEFT JOIN users du ON dp.user_id = du.user_id
            ORDER BY s.shipment_id DESC
        """).fetchall()
        personnel_list = db.execute("""
            SELECT dp.personnel_id, u.full_name, dp.vehicle_number
            FROM delivery_personnel dp JOIN users u ON dp.user_id = u.user_id
        """).fetchall()

        if shipments:
            st.dataframe([dict(row) for row in shipments], use_container_width=True)

        active_ships = [s for s in shipments if s["shipment_status"] != "Delivered"]
        if active_ships and personnel_list:
            st.markdown("#### Assign Delivery Personnel to Shipment")
            with st.form("assign_form"):
                ac1, ac2 = st.columns(2)
                ship_map = {f"{s['tracking_number']} ({s['delivery_address']})": s["shipment_id"] for s in active_ships}
                drv_map = {f"{p['full_name']} [{p['vehicle_number']}]": p["personnel_id"] for p in personnel_list}
                sel_ship = ac1.selectbox("Select Shipment", list(ship_map.keys()))
                sel_drv = ac2.selectbox("Select Delivery Personnel", list(drv_map.keys()))
                if st.form_submit_button("Assign Courier"):
                    sid = ship_map[sel_ship]
                    pid = drv_map[sel_drv]
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    db.execute("DELETE FROM delivery_assignments WHERE shipment_id = ?", (sid,))
                    db.execute(
                        "INSERT INTO delivery_assignments (shipment_id, personnel_id, assigned_date, expected_delivery, assignment_status) VALUES (?, ?, ?, 'Within 48 Hours', 'Assigned')",
                        (sid, pid, now)
                    )
                    db.execute("UPDATE shipments SET shipment_status = 'Assigned' WHERE shipment_id = ?", (sid,))
                    info = db.execute("SELECT s.tracking_number, c.user_id FROM shipments s JOIN customers c ON s.customer_id = c.customer_id WHERE s.shipment_id = ?", (sid,)).fetchone()
                    db.execute(
                        "INSERT INTO tracking (shipment_id, latitude, longitude, location_name, status, remarks, recorded_at) VALUES (?, 6.5244, 3.3792, '3PL Central Dispatch Hub', 'Assigned', 'Courier assigned and scheduled for pickup.', ?)",
                        (sid, now)
                    )
                    db.commit()
                    create_notification(info["user_id"], sid, f"Courier Assigned — {info['tracking_number']}", "A verified delivery driver has been assigned to your shipment.")
                    log_activity(st.session_state.user["user_id"], f"Assigned {info['tracking_number']} to driver ID {pid}")
                    st.success("Courier assigned and customer notified!")
                    st.rerun()

    with tab2:
        with st.form("add_driver_form"):
            dc1, dc2 = st.columns(2)
            d_name = dc1.text_input("Driver Full Name*")
            d_phone = dc2.text_input("Phone Number*")
            dc3, dc4 = st.columns(2)
            d_email = dc3.text_input("Email*").strip().lower()
            d_pass = dc4.text_input("Password*", type="password")
            dc5, dc6 = st.columns(2)
            v_num = dc5.text_input("Vehicle Registration Number*", placeholder="e.g. LAG-902-XY")
            v_type = dc6.text_input("Vehicle Type*", placeholder="e.g. Box Truck / Van")
            area = st.text_input("Assigned Route / Corridor*", placeholder="e.g. Ikeja - Ibadan Expressway")
            if st.form_submit_button("Register Delivery Personnel"):
                if d_name and d_email and d_pass and v_num:
                    if db.execute("SELECT user_id FROM users WHERE email = ?", (d_email,)).fetchone():
                        st.error("Email already exists.")
                    else:
                        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        cur = db.cursor()
                        cur.execute(
                            "INSERT INTO users (full_name, email, phone, password, role, created_at) VALUES (?, ?, ?, ?, 'personnel', ?)",
                            (d_name, d_email, d_phone, generate_password_hash(d_pass), now)
                        )
                        uid = cur.lastrowid
                        cur.execute(
                            "INSERT INTO delivery_personnel (user_id, vehicle_number, vehicle_type, assigned_area, date_registered) VALUES (?, ?, ?, ?, ?)",
                            (uid, v_num, v_type, area, now)
                        )
                        db.commit()
                        log_activity(st.session_state.user["user_id"], f"Registered driver {d_name}")
                        st.success("Delivery personnel registered!")
                        st.rerun()
                else:
                    st.error("Please fill all required fields.")

    with tab3:
        logs = db.execute("""
            SELECT l.log_id, COALESCE(u.full_name, 'System') AS user, l.activity, l.created_at
            FROM system_logs l LEFT JOIN users u ON l.user_id = u.user_id
            ORDER BY l.log_id DESC LIMIT 25
        """).fetchall()
        st.dataframe([dict(r) for r in logs], use_container_width=True)

    db.close()


def render_customer_dashboard():
    db = get_conn()
    uid = st.session_state.user["user_id"]
    customer = db.execute("SELECT * FROM customers WHERE user_id = ?", (uid,)).fetchone()
    st.subheader(f"Customer Portal — Welcome, {st.session_state.user['full_name']}")

    col_form, col_notif = st.columns([1.4, 1])
    with col_form:
        st.markdown('<div class="section-card"><div class="section-header">Register New Shipment for Delivery</div>', unsafe_allow_html=True)
        with st.form("new_shipment_form"):
            c1, c2 = st.columns(2)
            s_name = c1.text_input("Sender Name*", value=st.session_state.user["full_name"])
            s_phone = c2.text_input("Sender Phone*", value=st.session_state.user["phone"])
            c3, c4 = st.columns(2)
            r_name = c3.text_input("Recipient Name*")
            r_phone = c4.text_input("Recipient Phone*")
            c5, c6 = st.columns(2)
            p_addr = c5.text_input("Pickup Address*")
            d_addr = c6.text_input("Delivery Destination Address*")
            desc = st.text_input("Description of Goods*", placeholder="e.g., Electronics, Medical Supplies")
            c7, c8 = st.columns(2)
            qty = c7.number_input("Quantity (Packages)", min_value=1, value=1)
            wt = c8.number_input("Total Weight (kg)", min_value=0.1, value=5.0)
            if st.form_submit_button("Generate Tracking ID & Submit Shipment"):
                if r_name and r_phone and p_addr and d_addr and desc:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    trk = f"ACR-2026-{uuid.uuid4().hex[:5].upper()}"
                    seal = hashlib.sha256(f"{trk}-{now}".encode()).hexdigest()[:16].upper()
                    cur = db.cursor()
                    cur.execute("""
                        INSERT INTO shipments (
                            customer_id, tracking_number, sender_name, sender_phone,
                            recipient_name, recipient_phone, pickup_address, delivery_address,
                            goods_description, quantity, weight, security_seal_hash, shipment_status, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Registered', ?)
                    """, (customer["customer_id"], trk, s_name, s_phone, r_name, r_phone, p_addr, d_addr, desc, int(qty), float(wt), seal, now))
                    sid = cur.lastrowid
                    cur.execute(
                        "INSERT INTO tracking (shipment_id, latitude, longitude, location_name, status, remarks, recorded_at) VALUES (?, 6.5244, 3.3792, ?, 'Registered', 'Shipment registered & sealed.', ?)",
                        (sid, p_addr, now)
                    )
                    db.commit()
                    create_notification(uid, sid, f"Shipment Registered: {trk}", f"Your shipment to {r_name} is registered with Seal ID {seal}.")
                    log_activity(uid, f"Created shipment {trk}")
                    st.session_state.quick_trk = trk
                    st.success(f"Shipment Registered! Tracking Number: **{trk}**")
                    st.rerun()
                else:
                    st.error("Please fill all required fields.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_notif:
        st.markdown('<div class="section-card"><div class="section-header">Automated Shipment Notifications</div>', unsafe_allow_html=True)
        notifs = db.execute("SELECT * FROM notifications WHERE user_id = ? ORDER BY notification_id DESC LIMIT 6", (uid,)).fetchall()
        if notifs:
            for n in notifs:
                st.markdown(f"""
                <div style="background:#f9fafb; border-left:3px solid #C8102E; padding:10px 12px; margin-bottom:10px; border-radius:3px;">
                    <b style="color:#C8102E;">{n['title']}</b><br>
                    <span style="font-size:13px;">{n['message']}</span><br>
                    <small style="color:#6b7280;">{n['created_at']}</small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.write("No notifications yet.")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-card"><div class="section-header">My Shipments & Tracking References</div>', unsafe_allow_html=True)
    my_ships = db.execute(
        "SELECT tracking_number, recipient_name, delivery_address, goods_description, quantity, security_seal_hash, shipment_status, created_at FROM shipments WHERE customer_id = ? ORDER BY shipment_id DESC",
        (customer["customer_id"],)
    ).fetchall()
    if my_ships:
        st.dataframe([dict(r) for r in my_ships], use_container_width=True)
    else:
        st.write("No shipments registered yet.")
    st.markdown("</div>", unsafe_allow_html=True)
    db.close()


def render_personnel_dashboard():
    db = get_conn()
    uid = st.session_state.user["user_id"]
    pers = db.execute("SELECT * FROM delivery_personnel WHERE user_id = ?", (uid,)).fetchone()
    st.subheader(f"Courier & Fleet Portal — {st.session_state.user['full_name']}")
    st.caption(f"Vehicle: {pers['vehicle_number']} ({pers['vehicle_type']}) | Corridor: {pers['assigned_area']}")

    assigned = db.execute("""
        SELECT s.* FROM delivery_assignments da
        JOIN shipments s ON da.shipment_id = s.shipment_id
        WHERE da.personnel_id = ? ORDER BY s.shipment_id DESC
    """, (pers["personnel_id"],)).fetchall()

    if not assigned:
        st.info("No shipments currently assigned to you.")
        db.close()
        return

    for s in assigned:
        with st.expander(f"📦 {s['tracking_number']} — {s['goods_description']} [{s['shipment_status']}]", expanded=True):
            st.write(f"**Pickup:** {s['pickup_address']}  |  **Destination:** {s['delivery_address']}  |  **Recipient:** {s['recipient_name']} ({s['recipient_phone']})")
            if s["shipment_status"] != "Delivered":
                c1, c2 = st.columns(2)
                with c1:
                    with st.form(f"gps_form_{s['shipment_id']}"):
                        st.markdown("**1. Log GPS Checkpoint & Status Update**")
                        new_st = st.selectbox("Delivery Stage", ["Picked Up", "Dispatched", "In Transit", "Out for Delivery", "Delayed"], index=2)
                        loc = st.text_input("Current Location / Checkpoint*", placeholder="e.g., Sagamu Interchange, Ogun")
                        g1, g2 = st.columns(2)
                        lat = g1.number_input("Latitude", value=6.8322, format="%.4f")
                        lng = g2.number_input("Longitude", value=3.6319, format="%.4f")
                        rem = st.text_input("Checkpoint Remarks", value="Package seal intact; proceeding along route.")
                        if st.form_submit_button("Transmit GPS Update"):
                            if loc:
                                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                db.execute("UPDATE shipments SET shipment_status = ? WHERE shipment_id = ?", (new_st, s["shipment_id"]))
                                db.execute(
                                    "INSERT INTO tracking (shipment_id, latitude, longitude, location_name, status, remarks, recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                    (s["shipment_id"], lat, lng, loc, new_st, rem, now)
                                )
                                cust = db.execute("SELECT user_id FROM customers WHERE customer_id = ?", (s["customer_id"],)).fetchone()
                                db.commit()
                                create_notification(cust["user_id"], s["shipment_id"], f"Shipment {s['tracking_number']} — {new_st}", f"Location update: {loc}. {rem}")
                                log_activity(uid, f"Updated {s['tracking_number']} to {new_st}")
                                st.success("GPS checkpoint updated!")
                                st.rerun()
                with c2:
                    with st.form(f"pod_form_{s['shipment_id']}"):
                        st.markdown("**2. Complete Delivery & Issue Digital POD**")
                        rec_name = st.text_input("Recipient Full Name*", value=s["recipient_name"])
                        method = st.selectbox("Confirmation Method", ["Digital Signature & OTP", "Recipient ID Verified", "Tamper-Seal Scan Confirmed"])
                        pod_rem = st.text_input("Final Delivery Remarks", value="Delivered in intact condition.")
                        if st.form_submit_button("Confirm Delivery & Issue POD"):
                            now_dt = datetime.now()
                            now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")
                            db.execute("UPDATE shipments SET shipment_status = 'Delivered' WHERE shipment_id = ?", (s["shipment_id"],))
                            db.execute("UPDATE delivery_assignments SET assignment_status = 'Completed' WHERE shipment_id = ?", (s["shipment_id"],))
                            db.execute("""
                                INSERT INTO proof_of_delivery (shipment_id, personnel_id, recipient_name, delivery_date, delivery_time, confirmation_method, remarks, created_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """, (s["shipment_id"], pers["personnel_id"], rec_name, now_dt.strftime("%Y-%m-%d"), now_dt.strftime("%H:%M:%S"), method, pod_rem, now_str))
                            db.execute(
                                "INSERT INTO tracking (shipment_id, latitude, longitude, location_name, status, remarks, recorded_at) VALUES (?, 6.9125, 3.6680, ?, 'Delivered', ?, ?)",
                                (s["shipment_id"], s["delivery_address"], f"Delivered to {rec_name} ({method})", now_str)
                            )
                            cust = db.execute("SELECT user_id FROM customers WHERE customer_id = ?", (s["customer_id"],)).fetchone()
                            db.commit()
                            create_notification(cust["user_id"], s["shipment_id"], f"Delivered: {s['tracking_number']}", f"Delivered to {rec_name}. Digital POD archived.")
                            log_activity(uid, f"Issued POD for {s['tracking_number']}")
                            st.success("Proof of Delivery recorded!")
                            st.rerun()
            else:
                st.success("✅ Delivered & Proof of Delivery Archived.")
    db.close()


# ==============================================================================
# ROUTER
# ==============================================================================
if st.session_state.page == "Home":
    render_home()
elif st.session_state.page == "Tracking":
    render_tracking()
elif st.session_state.page == "Contact":
    render_contact()
elif st.session_state.page == "Private Area":
    if not st.session_state.user:
        render_auth()
    else:
        role = st.session_state.user["role"]
        if role == "admin":
            render_admin_dashboard()
        elif role == "customer":
            render_customer_dashboard()
        elif role == "personnel":
            render_personnel_dashboard()
