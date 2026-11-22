import os
import sqlite3
import uuid
import hashlib
from datetime import datetime
from functools import wraps
from flask import (
    Flask, render_template_string, request, redirect,
    url_for, session, flash, g
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.urandom(24)
DATABASE = "across_logistics_3pl.db"


# ==============================================================================
# DATABASE SETUP (Section 3.7: Table Design)
# ==============================================================================
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DATABASE)
    db.execute("PRAGMA foreign_keys = ON")
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

    # Contact Inquiries Table (from Fig 4.4.1 Contact Interface)
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

    # Seed Demo Data if empty
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 1. Admin Account
        cursor.execute(
            "INSERT INTO users (full_name, email, phone, password, role, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("System Administrator", "admin@acrosslogistics.com", "+2348010000001",
             generate_password_hash("admin123"), "admin", now)
        )

        # 2. Sample Customer Account
        cursor.execute(
            "INSERT INTO users (full_name, email, phone, password, role, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("Johnson Kingsley", "customer@acrosslogistics.com", "+2348020000002",
             generate_password_hash("customer123"), "customer", now)
        )
        cust_user_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO customers (user_id, address, city, state, registration_date) VALUES (?, ?, ?, ?, ?)",
            (cust_user_id, "Gateway ICT Polytechnic Road, Saapade", "Sagamu", "Ogun State", now)
        )
        cust_id = cursor.lastrowid

        # 3. Sample Delivery Personnel Account
        cursor.execute(
            "INSERT INTO users (full_name, email, phone, password, role, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("Adebayo Tunde (Driver)", "driver@acrosslogistics.com", "+2348030000003",
             generate_password_hash("driver123"), "personnel", now)
        )
        driver_user_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO delivery_personnel (user_id, vehicle_number, vehicle_type, assigned_area, date_registered) VALUES (?, ?, ?, ?, ?)",
            (driver_user_id, "OGN-482-KJA", "Heavy Cargo Van", "Lagos - Ogun - Ibadan Corridor", now)
        )
        personnel_id = cursor.lastrowid

        # 4. Sample Trackable Shipment
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
            "ROAD / FREIGHT", seal_hash, "In Transit", now
        ))
        ship_id = cursor.lastrowid

        # Assign to Driver
        cursor.execute("""
            INSERT INTO delivery_assignments (shipment_id, personnel_id, assigned_date, expected_delivery, assignment_status)
            VALUES (?, ?, ?, ?, ?)
        """, (ship_id, personnel_id, now, "2026-11-24 16:00:00", "In Progress"))

        # Add Tracking History (Lagos -> Sagamu Expressway -> Saapade)
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

        # Add Sample Notification
        cursor.execute("""
            INSERT INTO notifications (user_id, shipment_id, title, message, notification_type, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            cust_user_id, ship_id, f"Shipment {trk_num} In Transit",
            "Your shipment passed Sagamu Interchange Checkpoint with security seal verified.",
            "Tracking Update", now
        ))

    db.commit()
    db.close()


# ==============================================================================
# HELPER FUNCTIONS & SECURITY DECORATORS
# ==============================================================================
def log_activity(user_id, activity):
    db = get_db()
    db.execute(
        "INSERT INTO system_logs (user_id, activity, ip_address, created_at) VALUES (?, ?, ?, ?)",
        (user_id, activity, request.remote_addr, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    db.commit()


def create_notification(user_id, shipment_id, title, message, n_type="Status Update"):
    db = get_db()
    db.execute(
        "INSERT INTO notifications (user_id, shipment_id, title, message, notification_type, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, shipment_id, title, message, n_type, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    db.commit()


def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                flash("Please sign in to access the Private Area.", "warning")
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                flash("Access Denied: Unauthorized role permissions.", "danger")
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)
        return wrapped
    return decorator


# ==============================================================================
# SHARED UI TEMPLATE (Matches ACROSS LOGISTICS Screenshots in Section 4.4)
# ==============================================================================
BASE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ACROSS LOGISTICS | 3PL Secure & Trackable Goods Delivery System</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        :root {
            --header-dark: #333333;
            --brand-red: #C8102E;
            --brand-red-dark: #9e0b23;
            --text-dark: #1f2937;
            --text-muted: #6b7280;
            --bg-light: #f4f5f7;
            --white: #ffffff;
            --border-color: #e5e7eb;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }
        body { background-color: var(--bg-light); color: var(--text-dark); line-height: 1.6; }

        .navbar {
            background-color: var(--header-dark);
            color: var(--white);
            padding: 0 5%;
            height: 74px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 1000;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        }
        .brand {
            display: flex;
            align-items: center;
            text-decoration: none;
            color: var(--white);
            gap: 12px;
        }
        .brand-logo {
            width: 40px;
            height: 40px;
            background: var(--brand-red);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
            overflow: hidden;
        }
        .brand-logo::after {
            content: '';
            width: 0;
            height: 0;
            border-left: 12px solid transparent;
            border-right: 12px solid transparent;
            border-bottom: 16px solid var(--white);
            margin-bottom: 4px;
        }
        .brand-text { display: flex; flex-direction: column; line-height: 1.1; }
        .brand-text strong { font-size: 19px; letter-spacing: 1.5px; font-weight: 800; }
        .brand-text span { font-size: 10px; letter-spacing: 3px; color: #d1d5db; }

        .nav-links { display: flex; align-items: center; gap: 26px; list-style: none; }
        .nav-links a {
            color: var(--white);
            text-decoration: none;
            font-size: 13.5px;
            font-weight: 500;
            transition: color 0.2s;
            padding: 6px 4px;
        }
        .nav-links a:hover, .nav-links a.active { color: #ff6b81; }
        .nav-links a.nav-pill {
            text-transform: uppercase;
            letter-spacing: 0.8px;
            font-weight: 600;
        }
        .nav-private {
            background: var(--brand-red);
            padding: 8px 16px !important;
            border-radius: 2px;
            font-weight: 600 !important;
            letter-spacing: 0.6px;
        }
        .nav-private:hover { background: var(--brand-red-dark); color: var(--white) !important; }
        .lang-badge { font-size: 12px; color: #e5e7eb; display: flex; align-items: center; gap: 5px; }

        .hero {
            position: relative;
            min-height: 490px;
            background: linear-gradient(90deg, rgba(25,25,25,0.85) 0%, rgba(45,35,35,0.65) 55%, rgba(200,16,46,0.78) 100%),
                        url('https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?auto=format&fit=crop&w=1600&q=80') center/cover no-repeat;
            color: var(--white);
            display: flex;
            flex-direction: column;
            justify-content: center;
            padding: 60px 8%;
        }
        .hero h1 {
            font-size: 46px;
            font-weight: 300;
            max-width: 720px;
            line-height: 1.2;
            margin-bottom: 35px;
        }
        .hero-bar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-top: 1px solid rgba(255,255,255,0.5);
            padding-top: 24px;
            max-width: 1100px;
            flex-wrap: wrap;
            gap: 20px;
        }
        .hero-cta {
            display: inline-flex;
            align-items: center;
            text-decoration: none;
            background: var(--brand-red);
            color: var(--white);
            font-weight: 600;
            font-size: 15px;
        }
        .hero-cta span { padding: 14px 26px; }
        .hero-cta i {
            background: #222222;
            padding: 14px 18px;
            font-style: normal;
        }
        .hero-cta:hover { background: var(--brand-red-dark); }

        .service-strip {
            background: #2b2b2b;
            color: var(--white);
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            padding: 18px 8%;
            border-top: 1px solid #444;
        }
        .service-strip a {
            color: var(--white);
            text-decoration: none;
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 8px;
        }
        .service-strip a:hover { color: #ff6b81; }

        .container { max-width: 1240px; margin: 36px auto; padding: 0 20px; }
        .card {
            background: var(--white);
            border: 1px solid var(--border-color);
            border-radius: 4px;
            padding: 26px;
            margin-bottom: 24px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.04);
        }
        .card-title {
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 16px;
            padding-bottom: 10px;
            border-bottom: 2px solid var(--brand-red);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
            gap: 18px;
            margin-bottom: 28px;
        }
        .stat-box {
            background: var(--white);
            border-left: 4px solid var(--brand-red);
            padding: 20px;
            border-radius: 4px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.05);
        }
        .stat-box h3 { font-size: 28px; color: var(--text-dark); }
        .stat-box p { font-size: 13px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }

        .form-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; }
        .form-group { margin-bottom: 14px; }
        label { display: block; font-size: 13px; font-weight: 600; margin-bottom: 5px; color: #374151; }
        input, select, textarea {
            width: 100%;
            padding: 10px 12px;
            border: 1px solid #d1d5db;
            border-radius: 3px;
            font-size: 14px;
            background: #f9fafb;
        }
        input:focus, select:focus, textarea:focus {
            outline: none;
            border-color: var(--brand-red);
            background: var(--white);
        }
        .btn {
            display: inline-block;
            padding: 10px 20px;
            background: var(--brand-red);
            color: var(--white);
            border: none;
            border-radius: 3px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
        }
        .btn:hover { background: var(--brand-red-dark); }
        .btn-dark { background: var(--header-dark); }
        .btn-dark:hover { background: #111827; }
        .btn-sm { padding: 6px 12px; font-size: 12px; }

        .table-wrap { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
        th, td { padding: 12px 14px; text-align: left; border-bottom: 1px solid var(--border-color); }
        th { background: #f8fafc; font-weight: 700; color: #374151; text-transform: uppercase; font-size: 12px; }
        tr:hover { background: #f9fafb; }

        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11.5px;
            font-weight: 700;
        }
        .badge-registered { background: #e0f2fe; color: #0369a1; }
        .badge-assigned { background: #fef3c7; color: #92400e; }
        .badge-intransit { background: #ede9fe; color: #5b21b6; }
        .badge-delivered { background: #dcfce7; color: #166534; }
        .badge-delayed, .badge-cancelled { background: #fee2e2; color: #991b1b; }

        .alert { padding: 12px 18px; border-radius: 3px; margin-bottom: 18px; font-size: 14px; font-weight: 500; }
        .alert-success { background: #dcfce7; color: #166534; border-left: 4px solid #16a34a; }
        .alert-danger, .alert-warning { background: #fee2e2; color: #991b1b; border-left: 4px solid #dc2626; }
        .alert-info { background: #e0f2fe; color: #075985; border-left: 4px solid #0284c7; }

        .tracking-header { background: var(--white); padding: 40px 8% 24px; border-bottom: 1px solid var(--border-color); }
        .tracking-header h1 { font-size: 36px; font-weight: 700; max-width: 520px; line-height: 1.2; }
        .tracking-divider { width: 420px; max-width: 100%; height: 2px; background: #222; margin: 18px 0; }
        .tracking-workspace { display: grid; grid-template-columns: 1.3fr 1fr; min-height: 500px; background: var(--white); }
        @media (max-width: 900px) { .tracking-workspace { grid-template-columns: 1fr; } }
        #map { width: 100%; min-height: 480px; z-index: 1; }
        .tracking-panel { padding: 28px; border-left: 1px solid var(--border-color); }
        .mode-tabs { display: flex; gap: 18px; border-bottom: 1px solid var(--border-color); margin-bottom: 18px; }
        .mode-tab {
            padding: 8px 4px;
            font-size: 13px;
            font-weight: 700;
            color: var(--text-muted);
            border-bottom: 3px solid transparent;
        }
        .mode-tab.active { color: #1d4ed8; border-bottom-color: #1d4ed8; }
        .search-bar-box { display: flex; margin-bottom: 22px; }
        .search-bar-box input { border-radius: 2px 0 0 2px; border-right: none; }
        .search-bar-box button {
            background: #2563eb;
            color: white;
            border: none;
            padding: 0 20px;
            cursor: pointer;
            font-weight: bold;
            border-radius: 0 2px 2px 0;
        }

        .timeline { border-left: 2px solid var(--brand-red); margin-left: 10px; padding-left: 20px; }
        .timeline-item { position: relative; margin-bottom: 18px; }
        .timeline-item::before {
            content: '';
            width: 12px;
            height: 12px;
            background: var(--brand-red);
            border-radius: 50%;
            position: absolute;
            left: -27px;
            top: 4px;
        }

        .contact-split { display: grid; grid-template-columns: 1fr 1.1fr; min-height: 540px; }
        @media (max-width: 850px) { .contact-split { grid-template-columns: 1fr; } }
        .contact-left { background: var(--brand-red); color: var(--white); padding: 60px 10%; }
        .contact-left h1 { font-size: 40px; margin-bottom: 18px; }
        .contact-left hr { border: 0; border-top: 1px solid rgba(255,255,255,0.6); margin-bottom: 28px; }
        .contact-right { background: var(--white); padding: 50px 10%; }
        .contact-right h2 { color: var(--brand-red); margin-bottom: 20px; }

        footer {
            background: var(--header-dark);
            color: #d1d5db;
            text-align: center;
            padding: 24px;
            margin-top: 50px;
            font-size: 13px;
        }
    </style>
</head>
<body>

<nav class="navbar">
    <a href="{{ url_for('home') }}" class="brand">
        <div class="brand-logo"></div>
        <div class="brand-text">
            <strong>ACROSS</strong>
            <span>LOGISTICS</span>
        </div>
    </a>

    <ul class="nav-links">
        <li><a href="{{ url_for('track_shipment') }}" class="nav-pill">TRACKING</a></li>
        {% if session.get('user_id') %}
            <li><a href="{{ url_for('dashboard') }}" class="nav-pill nav-private">PRIVATE AREA ({{ session.get('role')|upper }})</a></li>
        {% else %}
            <li><a href="{{ url_for('login') }}" class="nav-pill nav-private">PRIVATE AREA</a></li>
        {% endif %}
        <li><a href="{{ url_for('home') }}">Home</a></li>
        <li><a href="{{ url_for('home') }}#services">Services</a></li>
        <li><a href="{{ url_for('contact') }}">Contact</a></li>
        <li class="lang-badge">🇬🇧 EN</li>
        {% if session.get('user_id') %}
            <li><a href="{{ url_for('logout') }}" style="color:#fca5a5;">Logout</a></li>
        {% endif %}
    </ul>
</nav>

{% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
        <div class="container" style="margin-bottom:0;">
            {% for category, msg in messages %}
                <div class="alert alert-{{ category }}">{{ msg }}</div>
            {% endfor %}
        </div>
    {% endif %}
{% endwith %}

{{ content | safe }}

<footer>
    <p><strong>ACROSS LOGISTICS — 3PL Secure & Trackable Goods Delivery System</strong></p>
    <p>Department of Computer Science, Gateway (ICT) Polytechnic, Saapade, Ogun State | Real-Time GPS & Tamper-Evident Traceability</p>
</footer>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
{{ extra_scripts | safe }}
</body>
</html>
"""


# ==============================================================================
# PUBLIC ROUTES (Home, Real-Time Tracking, Contact)
# ==============================================================================
@app.route("/")
def home():
    content = render_template_string("""
    <section class="hero">
        <h1>The integral logistic solutions that your company needs.</h1>
        <div class="hero-bar">
            <p style="max-width:540px; color:#f3f4f6; font-size:15px;">
                End-to-end Third-Party Logistics (3PL) platform featuring tamper-evident shipment serialization,
                role-based security access control, live GPS waypoint monitoring, and digital Proof of Delivery (POD).
            </p>
            <a href="{{ url_for('track_shipment') }}" class="hero-cta">
                <span>Track Your Shipment Now</span>
                <i>&rarr;</i>
            </a>
        </div>
    </section>

    <div class="service-strip" id="services">
        <a href="{{ url_for('track_shipment') }}">&#128230; Real-Time GPS Tracking</a>
        <a href="{{ url_for('login') }}">&#127981; Warehouse & 3PL Hub</a>
        <a href="{{ url_for('login') }}">&#128666; Road & Fleet Dispatch</a>
        <a href="{{ url_for('login') }}">&#128274; Tamper-Sealed Security</a>
        <a href="{{ url_for('contact') }}">&#128222; 24/7 Customer Support</a>
    </div>

    <div class="container">
        <div class="stats-grid">
            <div class="stat-box">
                <h3>100%</h3>
                <p>Tamper-Sealed Traceability</p>
            </div>
            <div class="stat-box">
                <h3>GPS / IoT</h3>
                <p>Live Waypoint Telemetry</p>
            </div>
            <div class="stat-box">
                <h3>RBAC</h3>
                <p>Encrypted Multi-Role Access</p>
            </div>
            <div class="stat-box">
                <h3>Digital POD</h3>
                <p>Verified Recipient Sign-Off</p>
            </div>
        </div>

        <div class="card">
            <div class="card-title">Quick Shipment Verification</div>
            <form action="{{ url_for('track_shipment') }}" method="GET" style="display:flex; gap:12px; flex-wrap:wrap;">
                <input type="text" name="tracking_number" placeholder="Enter Tracking ID (e.g., ACR-2026-88412)" style="flex:1; min-width:250px;" required>
                <button type="submit" class="btn">Track Goods</button>
            </form>
        </div>
    </div>
    """)
    return render_template_string(BASE_HTML, content=content, extra_scripts="")


@app.route("/tracking")
def track_shipment():
    db = get_db()
    tracking_number = request.args.get("tracking_number", "").strip().upper()
    shipment = None
    history = []
    pod = None
    driver = None

    if tracking_number:
        shipment = db.execute("SELECT * FROM shipments WHERE tracking_number = ?", (tracking_number,)).fetchone()
        if shipment:
            history = db.execute(
                "SELECT * FROM tracking WHERE shipment_id = ? ORDER BY tracking_id ASC",
                (shipment["shipment_id"],)
            ).fetchall()
            pod = db.execute(
                "SELECT * FROM proof_of_delivery WHERE shipment_id = ?",
                (shipment["shipment_id"],)
            ).fetchone()
            driver = db.execute("""
                SELECT u.full_name, u.phone, dp.vehicle_number, dp.vehicle_type
                FROM delivery_assignments da
                JOIN delivery_personnel dp ON da.personnel_id = dp.personnel_id
                JOIN users u ON dp.user_id = u.user_id
                WHERE da.shipment_id = ?
            """, (shipment["shipment_id"],)).fetchone()
        else:
            flash(f"No shipment found with Tracking Number '{tracking_number}'.", "warning")

    history_dicts = [dict(row) for row in history]

    content = render_template_string("""
    <div class="tracking-header">
        <h1>Please enter the tracking number</h1>
        <div class="tracking-divider"></div>
        <p style="font-size:14px; color:#4b5563;">
            In case no results appear in the search please contact us
            <a href="{{ url_for('contact') }}" style="color:#C8102E; font-weight:600;">here</a>.
            (Demo Tracking ID: <strong>ACR-2026-88412</strong>)
        </p>
    </div>

    <div class="tracking-workspace">
        <div id="map"></div>

        <div class="tracking-panel">
            <div class="mode-tabs">
                <div class="mode-tab active">&#128666; ROAD / EXPRESS</div>
                <div class="mode-tab">&#9992; AIR FREIGHT</div>
                <div class="mode-tab">&#128674; OCEAN CARGO</div>
            </div>

            <form method="GET" action="{{ url_for('track_shipment') }}" class="search-bar-box">
                <input type="text" name="tracking_number" value="{{ tracking_number }}" placeholder="Tracking / Waybill / Reference Number" required>
                <button type="submit">&#128269;</button>
            </form>

            {% if shipment %}
                <div style="background:#f8fafc; border:1px solid #e2e8f0; padding:16px; border-radius:4px; margin-bottom:20px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                        <strong style="font-size:16px; color:#C8102E;">{{ shipment['tracking_number'] }}</strong>
                        <span class="badge badge-{{ shipment['shipment_status']|lower|replace(' ', '') }}">{{ shipment['shipment_status'] }}</span>
                    </div>
                    <p style="font-size:13px;"><strong>Goods:</strong> {{ shipment['goods_description'] }} (Qty: {{ shipment['quantity'] }}, {{ shipment['weight'] }} kg)</p>
                    <p style="font-size:13px;"><strong>Route:</strong> {{ shipment['pickup_address'] }} &rarr; {{ shipment['delivery_address'] }}</p>
                    <p style="font-size:13px;"><strong>Recipient:</strong> {{ shipment['recipient_name'] }} ({{ shipment['recipient_phone'] }})</p>
                    <p style="font-size:12px; color:#047857; margin-top:6px;">
                        &#128274; <strong>Tamper-Evident Security Seal Hash:</strong> <code>{{ shipment['security_seal_hash'] }}</code>
                    </p>
                    {% if driver %}
                        <p style="font-size:12.5px; margin-top:6px; color:#1e40af;">
                            &#128666; <strong>Assigned Courier:</strong> {{ driver['full_name'] }} | Vehicle: {{ driver['vehicle_number'] }} ({{ driver['vehicle_type'] }})
                        </p>
                    {% endif %}
                </div>

                <h4 style="margin-bottom:14px; font-size:14px; text-transform:uppercase; color:#374151;">Real-Time Checkpoints & Audit Trail</h4>
                <div class="timeline">
                    {% for item in history %}
                        <div class="timeline-item">
                            <strong style="font-size:13.5px;">{{ item['status'] }} — {{ item['location_name'] }}</strong>
                            <p style="font-size:12.5px; color:#4b5563;">{{ item['remarks'] }}</p>
                            <small style="color:#6b7280;">GPS: {{ item['latitude'] }}, {{ item['longitude'] }} | {{ item['recorded_at'] }}</small>
                        </div>
                    {% endfor %}
                </div>

                {% if pod %}
                    <div style="background:#dcfce7; border:1px solid #86efac; padding:14px; border-radius:4px; margin-top:16px;">
                        <strong style="color:#166534;">&#9989; Digital Proof of Delivery Verified</strong>
                        <p style="font-size:13px; margin-top:4px;">Received by: <strong>{{ pod['recipient_name'] }}</strong> via {{ pod['confirmation_method'] }}</p>
                        <p style="font-size:12px; color:#15803d;">Delivered on {{ pod['delivery_date'] }} at {{ pod['delivery_time'] }} — {{ pod['remarks'] }}</p>
                    </div>
                {% endif %}
            {% else %}
                <div style="text-align:center; padding:40px 10px; color:#6b7280;">
                    <p style="font-size:15px;">Enter a valid tracking code above to inspect live GPS coordinates, security seal status, and delivery history.</p>
                </div>
            {% endif %}
        </div>
    </div>
    """, tracking_number=tracking_number, shipment=shipment, history=history, pod=pod, driver=driver)

    extra_scripts = render_template_string("""
    <script>
        var points = {{ history_json | tojson }};
        var defaultCenter = [6.6500, 3.5000];
        var map = L.map('map').setView(defaultCenter, 9);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap contributors'
        }).addTo(map);

        if (points.length > 0) {
            var latlngs = [];
            points.forEach(function(pt, idx) {
                var coord = [pt.latitude, pt.longitude];
                latlngs.push(coord);
                var marker = L.marker(coord).addTo(map);
                marker.bindPopup("<b>" + pt.status + "</b><br>" + pt.location_name + "<br><small>" + pt.recorded_at + "</small>");
                if (idx === points.length - 1) {
                    marker.openPopup();
                }
            });
            var polyline = L.polyline(latlngs, {color: '#C8102E', weight: 4}).addTo(map);
            map.fitBounds(polyline.getBounds(), {padding: [40, 40]});
        }
    </script>
    """, history_json=history_dicts)

    return render_template_string(BASE_HTML, content=content, extra_scripts=extra_scripts)


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        db = get_db()
        db.execute("""
            INSERT INTO contact_inquiries
            (first_name, last_name, company_name, email, service_interest, country, phone, website, message, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request.form["first_name"], request.form["last_name"], request.form.get("company_name", ""),
            request.form["email"], request.form.get("service_interest", ""), request.form.get("country", "Nigeria"),
            request.form.get("phone", ""), request.form.get("website", ""), request.form["message"],
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        db.commit()
        flash("Thank you! Your inquiry has been received by our Customer Service department.", "success")
        return redirect(url_for("contact"))

    content = render_template_string("""
    <div class="contact-split">
        <div class="contact-left">
            <h1>Contact us</h1>
            <hr>
            <h3 style="font-weight:600; margin-bottom:18px;">Need further information?<br>Personalized advice?</h3>
            <p style="font-size:15px; opacity:0.95; margin-bottom:48px;">
                Our Customer Service department will meet all your needs.
            </p>
            <div style="margin-top:auto;">
                <small style="opacity:0.85;">Nigeria & West Africa Hub</small>
                <h2 style="font-size:26px; margin-top:4px;">+234 801 000 0001</h2>
                <p style="font-size:13px; margin-top:6px;">Saapade / Sagamu Logistics Corridor, Ogun State</p>
            </div>
        </div>

        <div class="contact-right">
            <h2>Contact form:</h2>
            <form method="POST">
                <div class="form-grid">
                    <div class="form-group">
                        <input type="text" name="first_name" placeholder="First Name*" required>
                    </div>
                    <div class="form-group">
                        <input type="text" name="last_name" placeholder="Last Name*" required>
                    </div>
                </div>
                <div class="form-grid">
                    <div class="form-group">
                        <input type="text" name="company_name" placeholder="Company Name*">
                    </div>
                    <div class="form-group">
                        <input type="email" name="email" placeholder="Company email*" required>
                    </div>
                </div>
                <div class="form-grid">
                    <div class="form-group">
                        <select name="service_interest">
                            <option value="3PL Warehousing & Distribution">Service of interest: 3PL Warehousing</option>
                            <option value="Secure Goods Delivery">Secure Trackable Goods Delivery</option>
                            <option value="Fleet & Last-Mile Logistics">Last-Mile Distribution</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <select name="country">
                            <option value="Nigeria">Nigeria</option>
                            <option value="Ghana">Ghana</option>
                            <option value="United Kingdom">United Kingdom</option>
                            <option value="Spain">Spain</option>
                        </select>
                    </div>
                </div>
                <div class="form-group">
                    <input type="text" name="phone" placeholder="Phone Number (+234...)">
                </div>
                <div class="form-group">
                    <input type="text" name="website" placeholder="Company Website">
                </div>
                <div class="form-group">
                    <textarea name="message" rows="4" placeholder="Please provide us with more details about your needs*" required></textarea>
                </div>
                <button type="submit" class="btn">Send Inquiry</button>
            </form>
        </div>
    </div>
    """)
    return render_template_string(BASE_HTML, content=content, extra_scripts="")


# ==============================================================================
# AUTHENTICATION ROUTES (Section 3.5.1 & 3.5.2)
# ==============================================================================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        if user and check_password_hash(user["password"], password):
            if user["status"] != "Active":
                flash("Your account is suspended. Contact the Administrator.", "danger")
                return redirect(url_for("login"))
            session["user_id"] = user["user_id"]
            session["full_name"] = user["full_name"]
            session["role"] = user["role"]
            log_activity(user["user_id"], f"User logged in ({user['role']})")
            flash(f"Welcome back, {user['full_name']}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password.", "danger")

    content = render_template_string("""
    <div class="container" style="max-width:960px;">
        <div class="form-grid" style="gap:28px;">
            <div class="card">
                <div class="card-title">Private Area — Secure Login</div>
                <form method="POST">
                    <div class="form-group">
                        <label>Email Address</label>
                        <input type="email" name="email" required placeholder="Enter registered email">
                    </div>
                    <div class="form-group">
                        <label>Password</label>
                        <input type="password" name="password" required placeholder="Enter password">
                    </div>
                    <button type="submit" class="btn" style="width:100%;">Sign In</button>
                </form>

                <div style="margin-top:22px; background:#f8fafc; padding:14px; border-radius:4px; font-size:12.5px; border:1px solid #e2e8f0;">
                    <strong>Demo Credentials (Pre-loaded):</strong><br>
                    &bull; <b>Admin:</b> admin@acrosslogistics.com / <code>admin123</code><br>
                    &bull; <b>Customer:</b> customer@acrosslogistics.com / <code>customer123</code><br>
                    &bull; <b>Driver:</b> driver@acrosslogistics.com / <code>driver123</code>
                </div>
            </div>

            <div class="card">
                <div class="card-title">New Customer Registration</div>
                <form method="POST" action="{{ url_for('register') }}">
                    <div class="form-group">
                        <label>Full Name / Organization</label>
                        <input type="text" name="full_name" required>
                    </div>
                    <div class="form-grid">
                        <div class="form-group">
                            <label>Email Address</label>
                            <input type="email" name="email" required>
                        </div>
                        <div class="form-group">
                            <label>Phone Number</label>
                            <input type="text" name="phone" required>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Residential / Business Address</label>
                        <input type="text" name="address" required>
                    </div>
                    <div class="form-grid">
                        <div class="form-group">
                            <label>City</label>
                            <input type="text" name="city" required>
                        </div>
                        <div class="form-group">
                            <label>State</label>
                            <input type="text" name="state" required>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Password (min. 6 characters)</label>
                        <input type="password" name="password" minlength="6" required>
                    </div>
                    <button type="submit" class="btn btn-dark" style="width:100%;">Create Customer Account</button>
                </form>
            </div>
        </div>
    </div>
    """)
    return render_template_string(BASE_HTML, content=content, extra_scripts="")


@app.route("/register", methods=["POST"])
def register():
    db = get_db()
    email = request.form["email"].strip().lower()
    existing = db.execute("SELECT user_id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        flash("Email address is already registered.", "danger")
        return redirect(url_for("login"))

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO users (full_name, email, phone, password, role, created_at) VALUES (?, ?, ?, ?, 'customer', ?)",
        (request.form["full_name"], email, request.form["phone"],
         generate_password_hash(request.form["password"]), now)
    )
    user_id = cursor.lastrowid
    cursor.execute(
        "INSERT INTO customers (user_id, address, city, state, registration_date) VALUES (?, ?, ?, ?, ?)",
        (user_id, request.form["address"], request.form["city"], request.form["state"], now)
    )
    db.commit()
    log_activity(user_id, "New customer account registered")
    flash("Registration successful! You can now sign in.", "success")
    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    if "user_id" in session:
        log_activity(session["user_id"], "User logged out")
    session.clear()
    flash("You have been securely logged out.", "info")
    return redirect(url_for("home"))


# ==============================================================================
# ROLE-BASED PRIVATE AREA DASHBOARD (Admin / Customer / Delivery Personnel)
# ==============================================================================
@app.route("/dashboard")
@login_required()
def dashboard():
    role = session["role"]
    if role == "admin":
        return admin_dashboard()
    elif role == "customer":
        return customer_dashboard()
    elif role == "personnel":
        return personnel_dashboard()
    return redirect(url_for("home"))


def admin_dashboard():
    db = get_db()
    stats = {
        "customers": db.execute("SELECT COUNT(*) FROM customers").fetchone()[0],
        "shipments": db.execute("SELECT COUNT(*) FROM shipments").fetchone()[0],
        "in_transit": db.execute("SELECT COUNT(*) FROM shipments WHERE shipment_status IN ('Dispatched','In Transit','Out for Delivery')").fetchone()[0],
        "delivered": db.execute("SELECT COUNT(*) FROM shipments WHERE shipment_status = 'Delivered'").fetchone()[0],
        "personnel": db.execute("SELECT COUNT(*) FROM delivery_personnel").fetchone()[0],
    }

    shipments = db.execute("""
        SELECT s.*, u.full_name AS customer_name, da.personnel_id, du.full_name AS driver_name
        FROM shipments s
        JOIN customers c ON s.customer_id = c.customer_id
        JOIN users u ON c.user_id = u.user_id
        LEFT JOIN delivery_assignments da ON s.shipment_id = da.shipment_id
        LEFT JOIN delivery_personnel dp ON da.personnel_id = dp.personnel_id
        LEFT JOIN users du ON dp.user_id = du.user_id
        ORDER BY s.shipment_id DESC
    """).fetchall()

    personnel_list = db.execute("""
        SELECT dp.*, u.full_name, u.phone, u.email
        FROM delivery_personnel dp
        JOIN users u ON dp.user_id = u.user_id
    """).fetchall()

    logs = db.execute("""
        SELECT l.*, u.full_name FROM system_logs l
        LEFT JOIN users u ON l.user_id = u.user_id
        ORDER BY l.log_id DESC LIMIT 10
    """).fetchall()

    content = render_template_string("""
    <div class="container">
        <h2 style="margin-bottom:18px;">3PL Operations Command Center — Administrator</h2>

        <div class="stats-grid">
            <div class="stat-box"><h3>{{ stats.customers }}</h3><p>Registered Customers</p></div>
            <div class="stat-box"><h3>{{ stats.shipments }}</h3><p>Total Shipments</p></div>
            <div class="stat-box"><h3>{{ stats.in_transit }}</h3><p>Active In-Transit</p></div>
            <div class="stat-box"><h3>{{ stats.delivered }}</h3><p>Completed Deliveries</p></div>
            <div class="stat-box"><h3>{{ stats.personnel }}</h3><p>Fleet Personnel</p></div>
        </div>

        <div class="card">
            <div class="card-title">All Shipments & Courier Assignment</div>
            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>Tracking ID</th>
                            <th>Customer</th>
                            <th>Goods & Weight</th>
                            <th>Destination</th>
                            <th>Security Seal</th>
                            <th>Status</th>
                            <th>Assigned Driver</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for s in shipments %}
                        <tr>
                            <td><a href="{{ url_for('track_shipment', tracking_number=s['tracking_number']) }}"><strong>{{ s['tracking_number'] }}</strong></a></td>
                            <td>{{ s['customer_name'] }}</td>
                            <td>{{ s['goods_description'] }} ({{ s['weight'] }}kg)</td>
                            <td>{{ s['delivery_address'] }}</td>
                            <td><code>{{ s['security_seal_hash'] }}</code></td>
                            <td><span class="badge badge-{{ s['shipment_status']|lower|replace(' ', '') }}">{{ s['shipment_status'] }}</span></td>
                            <td>{{ s['driver_name'] or 'Unassigned' }}</td>
                            <td>
                                {% if s['shipment_status'] != 'Delivered' %}
                                <form method="POST" action="{{ url_for('assign_shipment') }}" style="display:flex; gap:6px;">
                                    <input type="hidden" name="shipment_id" value="{{ s['shipment_id'] }}">
                                    <select name="personnel_id" required style="padding:5px; font-size:12px;">
                                        <option value="">Select Driver...</option>
                                        {% for p in personnel_list %}
                                            <option value="{{ p['personnel_id'] }}" {% if s['personnel_id'] == p['personnel_id'] %}selected{% endif %}>
                                                {{ p['full_name'] }} ({{ p['vehicle_number'] }})
                                            </option>
                                        {% endfor %}
                                    </select>
                                    <button type="submit" class="btn btn-sm">Assign</button>
                                </form>
                                {% else %}
                                    <span style="color:#166534; font-size:12px; font-weight:600;">POD Archived</span>
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="form-grid">
            <div class="card">
                <div class="card-title">Register Delivery Personnel</div>
                <form method="POST" action="{{ url_for('add_personnel') }}">
                    <div class="form-grid">
                        <div class="form-group"><label>Full Name</label><input type="text" name="full_name" required></div>
                        <div class="form-group"><label>Phone Number</label><input type="text" name="phone" required></div>
                    </div>
                    <div class="form-grid">
                        <div class="form-group"><label>Email</label><input type="email" name="email" required></div>
                        <div class="form-group"><label>Password</label><input type="password" name="password" required></div>
                    </div>
                    <div class="form-grid">
                        <div class="form-group"><label>Vehicle Reg. Number</label><input type="text" name="vehicle_number" placeholder="e.g., LAG-902-XY" required></div>
                        <div class="form-group"><label>Vehicle Type</label><input type="text" name="vehicle_type" placeholder="e.g., Box Truck / Van" required></div>
                    </div>
                    <div class="form-group"><label>Assigned Route / Area</label><input type="text" name="assigned_area" placeholder="e.g., Ikeja - Ibadan Expressway" required></div>
                    <button type="submit" class="btn">Register Driver</button>
                </form>
            </div>

            <div class="card">
                <div class="card-title">Security & System Activity Audit Log</div>
                <div class="table-wrap">
                    <table>
                        <thead><tr><th>User</th><th>Activity</th><th>IP</th><th>Timestamp</th></tr></thead>
                        <tbody>
                            {% for l in logs %}
                            <tr>
                                <td>{{ l['full_name'] or 'System' }}</td>
                                <td>{{ l['activity'] }}</td>
                                <td>{{ l['ip_address'] }}</td>
                                <td>{{ l['created_at'] }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    """, stats=stats, shipments=shipments, personnel_list=personnel_list, logs=logs)
    return render_template_string(BASE_HTML, content=content, extra_scripts="")


@app.route("/admin/add-personnel", methods=["POST"])
@login_required("admin")
def add_personnel():
    db = get_db()
    email = request.form["email"].strip().lower()
    if db.execute("SELECT user_id FROM users WHERE email = ?", (email,)).fetchone():
        flash("Email already exists.", "danger")
        return redirect(url_for("dashboard"))

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = db.cursor()
    cur.execute(
        "INSERT INTO users (full_name, email, phone, password, role, created_at) VALUES (?, ?, ?, ?, 'personnel', ?)",
        (request.form["full_name"], email, request.form["phone"], generate_password_hash(request.form["password"]), now)
    )
    uid = cur.lastrowid
    cur.execute(
        "INSERT INTO delivery_personnel (user_id, vehicle_number, vehicle_type, assigned_area, date_registered) VALUES (?, ?, ?, ?, ?)",
        (uid, request.form["vehicle_number"], request.form["vehicle_type"], request.form["assigned_area"], now)
    )
    db.commit()
    log_activity(session["user_id"], f"Registered delivery personnel: {request.form['full_name']}")
    flash("Delivery personnel added successfully.", "success")
    return redirect(url_for("dashboard"))


@app.route("/admin/assign-shipment", methods=["POST"])
@login_required("admin")
def assign_shipment():
    db = get_db()
    shipment_id = request.form["shipment_id"]
    personnel_id = request.form["personnel_id"]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    db.execute("DELETE FROM delivery_assignments WHERE shipment_id = ?", (shipment_id,))
    db.execute(
        "INSERT INTO delivery_assignments (shipment_id, personnel_id, assigned_date, expected_delivery, assignment_status) VALUES (?, ?, ?, ?, 'Assigned')",
        (shipment_id, personnel_id, now, "Within 48 Hours")
    )
    db.execute("UPDATE shipments SET shipment_status = 'Assigned' WHERE shipment_id = ?", (shipment_id,))

    ship = db.execute("""
        SELECT s.tracking_number, c.user_id FROM shipments s
        JOIN customers c ON s.customer_id = c.customer_id
        WHERE s.shipment_id = ?
    """, (shipment_id,)).fetchone()

    db.execute(
        "INSERT INTO tracking (shipment_id, latitude, longitude, location_name, status, remarks, recorded_at) VALUES (?, ?, ?, ?, 'Assigned', ?, ?)",
        (shipment_id, 6.5244, 3.3792, "3PL Central Dispatch Hub", "Courier assigned and scheduled for pickup.", now)
    )
    db.commit()

    create_notification(
        ship["user_id"], shipment_id,
        f"Courier Assigned — {ship['tracking_number']}",
        "A verified delivery personnel has been assigned to transport your shipment."
    )
    log_activity(session["user_id"], f"Assigned shipment {ship['tracking_number']} to personnel ID {personnel_id}")
    flash("Shipment assigned and customer notified.", "success")
    return redirect(url_for("dashboard"))


def customer_dashboard():
    db = get_db()
    customer = db.execute("SELECT * FROM customers WHERE user_id = ?", (session["user_id"],)).fetchone()
    shipments = db.execute(
        "SELECT * FROM shipments WHERE customer_id = ? ORDER BY shipment_id DESC",
        (customer["customer_id"],)
    ).fetchall()
    notifications = db.execute(
        "SELECT * FROM notifications WHERE user_id = ? ORDER BY notification_id DESC LIMIT 6",
        (session["user_id"],)
    ).fetchall()

    content = render_template_string("""
    <div class="container">
        <h2 style="margin-bottom:18px;">Customer Portal — Welcome, {{ session['full_name'] }}</h2>

        <div class="form-grid" style="grid-template-columns: 1.4fr 1fr;">
            <div class="card">
                <div class="card-title">Register New Shipment for Delivery</div>
                <form method="POST" action="{{ url_for('create_shipment') }}">
                    <div class="form-grid">
                        <div class="form-group"><label>Sender Name</label><input type="text" name="sender_name" value="{{ session['full_name'] }}" required></div>
                        <div class="form-group"><label>Sender Phone</label><input type="text" name="sender_phone" required></div>
                    </div>
                    <div class="form-grid">
                        <div class="form-group"><label>Recipient Name</label><input type="text" name="recipient_name" required></div>
                        <div class="form-group"><label>Recipient Phone</label><input type="text" name="recipient_phone" required></div>
                    </div>
                    <div class="form-grid">
                        <div class="form-group"><label>Pickup Address</label><input type="text" name="pickup_address" required></div>
                        <div class="form-group"><label>Delivery Destination Address</label><input type="text" name="delivery_address" required></div>
                    </div>
                    <div class="form-group"><label>Description of Goods</label><input type="text" name="goods_description" placeholder="e.g., Electronics, Medical Supplies, Documents" required></div>
                    <div class="form-grid">
                        <div class="form-group"><label>Quantity (Packages)</label><input type="number" name="quantity" min="1" value="1" required></div>
                        <div class="form-group"><label>Total Weight (kg)</label><input type="number" step="0.1" name="weight" min="0.1" value="5.0" required></div>
                    </div>
                    <button type="submit" class="btn">Generate Tracking ID & Submit Shipment</button>
                </form>
            </div>

            <div class="card">
                <div class="card-title">Real-Time Shipment Notifications</div>
                {% if notifications %}
                    {% for n in notifications %}
                        <div style="padding:12px; border-bottom:1px solid #e5e7eb; background:#f9fafb; margin-bottom:8px; border-radius:3px;">
                            <strong style="font-size:13.5px; color:#C8102E;">{{ n['title'] }}</strong>
                            <p style="font-size:13px; margin:4px 0;">{{ n['message'] }}</p>
                            <small style="color:#6b7280;">{{ n['created_at'] }}</small>
                        </div>
                    {% endfor %}
                {% else %}
                    <p style="color:#6b7280; font-size:14px;">No notifications yet.</p>
                {% endif %}
            </div>
        </div>

        <div class="card">
            <div class="card-title">My Shipments & Tracking References</div>
            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>Tracking Number</th>
                            <th>Recipient</th>
                            <th>Destination</th>
                            <th>Goods</th>
                            <th>Tamper Seal</th>
                            <th>Status</th>
                            <th>Track</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for s in shipments %}
                        <tr>
                            <td><strong>{{ s['tracking_number'] }}</strong></td>
                            <td>{{ s['recipient_name'] }}</td>
                            <td>{{ s['delivery_address'] }}</td>
                            <td>{{ s['goods_description'] }} ({{ s['quantity'] }})</td>
                            <td><code>{{ s['security_seal_hash'] }}</code></td>
                            <td><span class="badge badge-{{ s['shipment_status']|lower|replace(' ', '') }}">{{ s['shipment_status'] }}</span></td>
                            <td><a href="{{ url_for('track_shipment', tracking_number=s['tracking_number']) }}" class="btn btn-sm btn-dark">Live Map</a></td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    """, shipments=shipments, notifications=notifications)
    return render_template_string(BASE_HTML, content=content, extra_scripts="")


@app.route("/customer/create-shipment", methods=["POST"])
@login_required("customer")
def create_shipment():
    db = get_db()
    customer = db.execute("SELECT * FROM customers WHERE user_id = ?", (session["user_id"],)).fetchone()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    trk_num = f"ACR-2026-{uuid.uuid4().hex[:5].upper()}"
    seal_hash = hashlib.sha256(f"{trk_num}-{now}".encode()).hexdigest()[:16].upper()

    cur = db.cursor()
    cur.execute("""
        INSERT INTO shipments (
            customer_id, tracking_number, sender_name, sender_phone,
            recipient_name, recipient_phone, pickup_address, delivery_address,
            goods_description, quantity, weight, security_seal_hash, shipment_status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Registered', ?)
    """, (
        customer["customer_id"], trk_num, request.form["sender_name"], request.form["sender_phone"],
        request.form["recipient_name"], request.form["recipient_phone"],
        request.form["pickup_address"], request.form["delivery_address"],
        request.form["goods_description"], int(request.form["quantity"]), float(request.form["weight"]),
        seal_hash, now
    ))
    ship_id = cur.lastrowid

    cur.execute("""
        INSERT INTO tracking (shipment_id, latitude, longitude, location_name, status, remarks, recorded_at)
        VALUES (?, ?, ?, ?, 'Registered', 'Shipment registered & assigned tamper-evident digital seal.', ?)
    """, (ship_id, 6.5244, 3.3792, request.form["pickup_address"], now))
    db.commit()

    create_notification(
        session["user_id"], ship_id,
        f"Shipment Registered: {trk_num}",
        f"Your shipment to {request.form['recipient_name']} is registered with Seal ID {seal_hash}."
    )
    log_activity(session["user_id"], f"Created shipment {trk_num}")
    flash(f"Shipment registered! Tracking Number: {trk_num}", "success")
    return redirect(url_for("dashboard"))


def personnel_dashboard():
    db = get_db()
    personnel = db.execute("SELECT * FROM delivery_personnel WHERE user_id = ?", (session["user_id"],)).fetchone()
    assigned = db.execute("""
        SELECT s.*, da.expected_delivery
        FROM delivery_assignments da
        JOIN shipments s ON da.shipment_id = s.shipment_id
        WHERE da.personnel_id = ?
        ORDER BY s.shipment_id DESC
    """, (personnel["personnel_id"],)).fetchall()

    content = render_template_string("""
    <div class="container">
        <h2 style="margin-bottom:6px;">Courier & Fleet Portal — {{ session['full_name'] }}</h2>
        <p style="color:#4b5563; margin-bottom:20px;">
            Vehicle: <strong>{{ personnel['vehicle_number'] }}</strong> ({{ personnel['vehicle_type'] }}) | Corridor: {{ personnel['assigned_area'] }}
        </p>

        {% for s in assigned %}
        <div class="card">
            <div class="card-title">
                <span>Tracking ID: {{ s['tracking_number'] }} &mdash; {{ s['goods_description'] }}</span>
                <span class="badge badge-{{ s['shipment_status']|lower|replace(' ', '') }}">{{ s['shipment_status'] }}</span>
            </div>
            <p style="font-size:14px; margin-bottom:14px;">
                <strong>Pickup:</strong> {{ s['pickup_address'] }} &nbsp;|&nbsp;
                <strong>Destination:</strong> {{ s['delivery_address'] }} &nbsp;|&nbsp;
                <strong>Recipient:</strong> {{ s['recipient_name'] }} ({{ s['recipient_phone'] }})
            </p>

            {% if s['shipment_status'] != 'Delivered' %}
            <div class="form-grid">
                <form method="POST" action="{{ url_for('update_tracking') }}" style="background:#f8fafc; padding:16px; border-radius:4px;">
                    <h4 style="margin-bottom:10px; color:#1e3a8a;">1. Log GPS Checkpoint & Status Update</h4>
                    <input type="hidden" name="shipment_id" value="{{ s['shipment_id'] }}">
                    <div class="form-grid">
                        <div class="form-group">
                            <label>Delivery Stage</label>
                            <select name="status" required>
                                <option value="Picked Up">Picked Up</option>
                                <option value="Dispatched">Dispatched</option>
                                <option value="In Transit" selected>In Transit</option>
                                <option value="Out for Delivery">Out for Delivery</option>
                                <option value="Delayed">Delayed</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Current Location / Checkpoint</label>
                            <input type="text" name="location_name" placeholder="e.g., Sagamu Interchange, Ogun" required>
                        </div>
                    </div>
                    <div class="form-grid">
                        <div class="form-group"><label>GPS Latitude</label><input type="number" step="any" name="latitude" value="6.8322" required></div>
                        <div class="form-group"><label>GPS Longitude</label><input type="number" step="any" name="longitude" value="3.6319" required></div>
                    </div>
                    <div class="form-group"><label>Checkpoint Remarks</label><input type="text" name="remarks" value="Package seal intact; proceeding along route." required></div>
                    <button type="submit" class="btn btn-dark btn-sm">Transmit GPS Update</button>
                </form>

                <form method="POST" action="{{ url_for('submit_pod') }}" style="background:#f0fdf4; padding:16px; border-radius:4px; border:1px solid #bbf7d0;">
                    <h4 style="margin-bottom:10px; color:#166534;">2. Complete Delivery & Proof of Delivery (POD)</h4>
                    <input type="hidden" name="shipment_id" value="{{ s['shipment_id'] }}">
                    <div class="form-group">
                        <label>Recipient Full Name</label>
                        <input type="text" name="recipient_name" value="{{ s['recipient_name'] }}" required>
                    </div>
                    <div class="form-group">
                        <label>Verification Method</label>
                        <select name="confirmation_method">
                            <option value="Digital Signature & OTP">Digital Signature & OTP</option>
                            <option value="Recipient National ID Verified">Recipient ID Verified</option>
                            <option value="Tamper-Seal Scan Confirmed">Tamper-Seal Scan Confirmed</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Final Delivery Remarks</label>
                        <input type="text" name="remarks" value="Delivered in intact condition." required>
                    </div>
                    <button type="submit" class="btn btn-sm">Confirm Delivery & Issue POD</button>
                </form>
            </div>
            {% else %}
                <p style="color:#166534; font-weight:600;">&#9989; Shipment Delivered & Proof of Delivery Recorded.</p>
            {% endif %}
        </div>
        {% else %}
            <div class="card"><p>No shipments currently assigned to you.</p></div>
        {% endfor %}
    </div>
    """, personnel=personnel, assigned=assigned)
    return render_template_string(BASE_HTML, content=content, extra_scripts="")


@app.route("/personnel/update-tracking", methods=["POST"])
@login_required("personnel")
def update_tracking():
    db = get_db()
    shipment_id = request.form["shipment_id"]
    status = request.form["status"]
    loc = request.form["location_name"]
    lat = float(request.form["latitude"])
    lng = float(request.form["longitude"])
    remarks = request.form["remarks"]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    db.execute("UPDATE shipments SET shipment_status = ? WHERE shipment_id = ?", (status, shipment_id))
    db.execute("""
        INSERT INTO tracking (shipment_id, latitude, longitude, location_name, status, remarks, recorded_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (shipment_id, lat, lng, loc, status, remarks, now))

    ship = db.execute("""
        SELECT s.tracking_number, c.user_id FROM shipments s
        JOIN customers c ON s.customer_id = c.customer_id
        WHERE s.shipment_id = ?
    """, (shipment_id,)).fetchone()
    db.commit()

    create_notification(
        ship["user_id"], shipment_id,
        f"Shipment {ship['tracking_number']} — {status}",
        f"Location update: {loc}. {remarks}"
    )
    log_activity(session["user_id"], f"Updated tracking for {ship['tracking_number']} to {status}")
    flash("GPS checkpoint and delivery status updated.", "success")
    return redirect(url_for("dashboard"))


@app.route("/personnel/submit-pod", methods=["POST"])
@login_required("personnel")
def submit_pod():
    db = get_db()
    personnel = db.execute("SELECT * FROM delivery_personnel WHERE user_id = ?", (session["user_id"],)).fetchone()
    shipment_id = request.form["shipment_id"]
    now_dt = datetime.now()
    now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")

    ship = db.execute("""
        SELECT s.*, c.user_id FROM shipments s
        JOIN customers c ON s.customer_id = c.customer_id
        WHERE s.shipment_id = ?
    """, (shipment_id,)).fetchone()

    db.execute("UPDATE shipments SET shipment_status = 'Delivered' WHERE shipment_id = ?", (shipment_id,))
    db.execute("UPDATE delivery_assignments SET assignment_status = 'Completed' WHERE shipment_id = ?", (shipment_id,))
    db.execute("""
        INSERT INTO proof_of_delivery
        (shipment_id, personnel_id, recipient_name, delivery_date, delivery_time, confirmation_method, remarks, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        shipment_id, personnel["personnel_id"], request.form["recipient_name"],
        now_dt.strftime("%Y-%m-%d"), now_dt.strftime("%H:%M:%S"),
        request.form["confirmation_method"], request.form["remarks"], now_str
    ))
    db.execute("""
        INSERT INTO tracking (shipment_id, latitude, longitude, location_name, status, remarks, recorded_at)
        VALUES (?, ?, ?, ?, 'Delivered', ?, ?)
    """, (shipment_id, 6.9125, 3.6680, ship["delivery_address"],
          f"Delivered to {request.form['recipient_name']} ({request.form['confirmation_method']})", now_str))
    db.commit()

    create_notification(
        ship["user_id"], shipment_id,
        f"Delivered: {ship['tracking_number']}",
        f"Your shipment was delivered to {request.form['recipient_name']}. Digital POD is available."
    )
    log_activity(session["user_id"], f"Submitted Proof of Delivery for {ship['tracking_number']}")
    flash("Delivery confirmed and Digital Proof of Delivery archived!", "success")
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
