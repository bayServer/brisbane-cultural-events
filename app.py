from flask import Flask, request, redirect, url_for, session, render_template, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import requests

# ============================================================
# APP SETUP
# ============================================================

app = Flask(__name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "brisbane_visitor.db")

app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "change-this-secret-key"

db = SQLAlchemy(app)

# ============================================================
# API SETTINGS
# ============================================================

OPENWEATHER_API_KEY = "PASTE_YOUR_REAL_OPENWEATHER_KEY_HERE"

CREATIVE_EVENTS_API_URL = (
    "https://www.data.brisbane.qld.gov.au/api/explore/v2.1/catalog/datasets/"
    "creative-events/records?limit=20"
)

DEFAULT_IMAGE_URL = (
    "https://images.unsplash.com/photo-1518998053901-5348d3961a04"
    "?auto=format&fit=crop&w=1200&q=80"
)

# ============================================================
# DATABASE MODELS
# ============================================================

class Activity(db.Model):
    __tablename__ = "activities"

    activity_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    suburb = db.Column(db.String(80), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price_range = db.Column(db.String(30), nullable=True)
    website_link = db.Column(db.String(500), nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    cultural_tag = db.Column(db.String(80), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    star_rating = db.Column(db.Float, nullable=True)


class CulturalExperience(db.Model):
    __tablename__ = "cultural_experiences"

    cultural_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    suburb = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price_range = db.Column(db.String(30), nullable=True)
    website_link = db.Column(db.String(500), nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    cultural_tag = db.Column(db.String(80), nullable=True)
    family_friendly = db.Column(db.String(20), default="Unknown")
    booking_required = db.Column(db.String(20), default="Unknown")
    event_type = db.Column(db.String(120), nullable=True)
    start_datetime = db.Column(db.String(80), nullable=True)
    end_datetime = db.Column(db.String(80), nullable=True)
    formatted_datetime = db.Column(db.String(200), nullable=True)
    venue_address = db.Column(db.String(250), nullable=True)
    api_event_id = db.Column(db.String(120), nullable=True, unique=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    star_rating = db.Column(db.Float, nullable=True)
    source = db.Column(db.String(80), default="Manual")


class Favourite(db.Model):
    __tablename__ = "favourites"

    favourite_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    activity_id = db.Column(db.Integer, db.ForeignKey("activities.activity_id"), nullable=False)
    activity = db.relationship("Activity")


class CulturalFavourite(db.Model):
    __tablename__ = "cultural_favourites"

    cultural_favourite_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    cultural_id = db.Column(db.Integer, db.ForeignKey("cultural_experiences.cultural_id"), nullable=False)
    cultural_experience = db.relationship("CulturalExperience")


class Review(db.Model):
    __tablename__ = "reviews"

    review_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    activity_id = db.Column(db.Integer, db.ForeignKey("activities.activity_id"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    activity = db.relationship("Activity")


class CulturalReview(db.Model):
    __tablename__ = "cultural_reviews"

    cultural_review_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    cultural_id = db.Column(db.Integer, db.ForeignKey("cultural_experiences.cultural_id"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=False)
    cultural_experience = db.relationship("CulturalExperience")


class OlympicFavourite(db.Model):
    __tablename__ = "olympic_favourites"

    olympic_favourite_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    event_id = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(100), nullable=True)
    location = db.Column(db.String(150), nullable=True)
    schedule = db.Column(db.String(200), nullable=True)
    description = db.Column(db.Text, nullable=True)


class OlympicReview(db.Model):
    __tablename__ = "olympic_reviews"

    olympic_review_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    event_id = db.Column(db.String(100), nullable=False)
    event_name = db.Column(db.String(150), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=False)


# ============================================================
# DATABASE HELPERS
# ============================================================

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


def create_users_table():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            userID INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            phone_number TEXT UNIQUE,
            first_name TEXT,
            surname TEXT,
            DOB TEXT,
            email TEXT UNIQUE,
            password TEXT NOT NULL,
            user_profile TEXT DEFAULT 'Tourist'
        )
    """)
    conn.commit()
    conn.close()


def add_missing_column(table_name, column_name, column_type):
    conn = get_db_connection()
    columns = [row[1] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()]

    if column_name not in columns:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
        conn.commit()

    conn.close()


def add_missing_columns():
    create_users_table()

    user_columns = {
        "phone_number": "TEXT",
        "first_name": "TEXT",
        "surname": "TEXT",
        "DOB": "TEXT",
        "email": "TEXT",
        "user_profile": "TEXT DEFAULT 'Tourist'"
    }

    for column, column_type in user_columns.items():
        add_missing_column("Users", column, column_type)

    cultural_columns = {
        "price_range": "TEXT",
        "website_link": "TEXT",
        "image_url": "TEXT",
        "cultural_tag": "TEXT",
        "family_friendly": "TEXT DEFAULT 'Unknown'",
        "booking_required": "TEXT DEFAULT 'Unknown'",
        "event_type": "TEXT",
        "start_datetime": "TEXT",
        "end_datetime": "TEXT",
        "formatted_datetime": "TEXT",
        "venue_address": "TEXT",
        "api_event_id": "TEXT",
        "latitude": "REAL",
        "longitude": "REAL",
        "star_rating": "REAL",
        "source": "TEXT DEFAULT 'Manual'"
    }

    for column, column_type in cultural_columns.items():
        add_missing_column("cultural_experiences", column, column_type)


# ============================================================
# ROLE / SESSION HELPERS
# ============================================================

def normalise_role(role):
    role = (role or "Tourist").strip().lower()

    if role == "admin":
        return "Admin"
    if role == "local":
        return "Local"
    if role == "guest":
        return "Guest"

    return "Tourist"


def is_guest():
    return session.get("is_guest") is True or session.get("user_profile") == "Guest"


def is_admin():
    return (
        "user" in session
        and session.get("user_profile") == "Admin"
        and session.get("is_guest") is False
    )


def require_user_or_guest():
    if "user" not in session:
        flash("Please log in or continue as a guest.", "error")
        return False
    return True


def guest_blocked_message():
    flash("Guests cannot use this feature. Please create an account or log in.", "error")
    return redirect(url_for("register"))


@app.before_request
def refresh_session_role():
    skip_endpoints = {"login", "register", "continue_as_guest", "static"}

    if request.endpoint in skip_endpoints:
        return

    if "user" not in session:
        return

    if session.get("user") == "Guest":
        session["user_profile"] = "Guest"
        session["is_guest"] = True
        return

    conn = get_db_connection()
    user = conn.execute(
        "SELECT username, user_profile FROM Users WHERE username = ?",
        (session["user"],)
    ).fetchone()
    conn.close()

    if user:
        session["user_profile"] = normalise_role(user["user_profile"])
        session["is_guest"] = False


@app.context_processor
def inject_user_data():
    return {
        "user": session.get("user"),
        "user_profile": session.get("user_profile", "Guest"),
        "is_admin": is_admin(),
        "is_guest": is_guest()
    }


# ============================================================
# WEATHER API
# ============================================================

def backup_weather():
    return {
        "temp": 27,
        "desc": "Partly Cloudy",
        "icon": "02d",
        "city": "Brisbane",
        "feels_like": 28,
        "humidity": 65
    }


def get_weather():
    api_key = (OPENWEATHER_API_KEY or "").strip()

    if not api_key or "PASTE_YOUR" in api_key:
        return backup_weather()

    try:
        response = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": "Brisbane,AU", "appid": api_key, "units": "metric"},
            timeout=10
        )

        if response.status_code != 200:
            return backup_weather()

        data = response.json()
        return {
            "temp": round(data["main"]["temp"]),
            "desc": data["weather"][0]["description"].title(),
            "icon": data["weather"][0]["icon"],
            "city": data["name"],
            "feels_like": round(data["main"]["feels_like"]),
            "humidity": data["main"]["humidity"]
        }

    except Exception:
        return backup_weather()


# ============================================================
# REVIEW HELPERS
# ============================================================

def build_review_data(reviews, id_field):
    review_data = {}

    for review in reviews:
        item_id = getattr(review, id_field)

        if item_id not in review_data:
            review_data[item_id] = {"count": 0, "total": 0, "average": 0, "comments": []}

        review_data[item_id]["count"] += 1
        review_data[item_id]["total"] += review.rating
        review_data[item_id]["comments"].append(review)

    for item_id, data in review_data.items():
        data["average"] = round(data["total"] / data["count"], 1)

    return review_data


def get_review_data():
    return build_review_data(Review.query.order_by(Review.review_id.desc()).all(), "activity_id")


def get_cultural_review_data():
    return build_review_data(
        CulturalReview.query.order_by(CulturalReview.cultural_review_id.desc()).all(),
        "cultural_id"
    )


def get_olympic_review_data():
    return build_review_data(
        OlympicReview.query.order_by(OlympicReview.olympic_review_id.desc()).all(),
        "event_id"
    )


# ============================================================
# JSON API HELPER
# ============================================================

def extract_api_event_id(record):
    web_link = record.get("web_link") or ""

    if "eventid%3d" in web_link:
        return web_link.split("eventid%3d")[-1].split("%")[0].split("&")[0]

    if "eventid=" in web_link:
        return web_link.split("eventid=")[-1].split("&")[0]

    name = record.get("subject") or "unknown"
    start = record.get("start_datetime") or "unknown"
    return f"{name}-{start}"[:120]


def convert_event_type(event_type):
    if isinstance(event_type, list):
        return ", ".join(event_type)
    return event_type or "Creative Event"


def get_price_range(cost):
    cost_text = str(cost or "").lower()

    if "free" in cost_text:
        return "Free"
    if "paid" in cost_text or "$" in cost_text:
        return "Paid"
    return "Unknown"


def get_family_friendly(record, description, category):
    combined_text = f"{record.get('age', '')} {description} {category}".lower()

    if "all ages" in combined_text or "family" in combined_text or "children" in combined_text or "child" in combined_text:
        return "Yes"

    return "Unknown"


def refresh_cultural_experiences_from_json():
    response = requests.get(CREATIVE_EVENTS_API_URL, timeout=15)
    response.raise_for_status()

    data = response.json()
    records = data.get("results", [])
    imported_count = 0

    for record in records:
        api_event_id = extract_api_event_id(record)

        name = record.get("subject") or record.get("title") or "Untitled Cultural Event"
        venue = record.get("venue") or record.get("location") or "Brisbane"
        description = record.get("description") or "No description provided."
        category = record.get("primaryeventtype") or convert_event_type(record.get("event_type"))
        cost = record.get("cost") or "Unknown"
        price_range = get_price_range(cost)
        family_friendly = get_family_friendly(record, description, category)
        booking_required = record.get("bookingsrequired") or record.get("bookings") or "Unknown"
        image_url = record.get("eventimage") or record.get("image") or DEFAULT_IMAGE_URL
        website_link = record.get("web_link") or "https://visit.brisbane.qld.au/"
        start_datetime = record.get("start_datetime")
        end_datetime = record.get("end_datetime")
        formatted_datetime = record.get("formatteddatetime")
        venue_address = record.get("venueaddress")

        existing = CulturalExperience.query.filter_by(api_event_id=api_event_id).first()

        if not existing:
            existing = CulturalExperience.query.filter_by(name=name, suburb=venue).first()

        if existing:
            existing.name = name
            existing.category = category
            existing.suburb = venue
            existing.description = description
            existing.price_range = price_range
            existing.website_link = website_link
            existing.image_url = image_url
            existing.cultural_tag = "Arts and Culture"
            existing.family_friendly = family_friendly
            existing.booking_required = booking_required
            existing.event_type = category
            existing.start_datetime = start_datetime
            existing.end_datetime = end_datetime
            existing.formatted_datetime = formatted_datetime
            existing.venue_address = venue_address
            existing.api_event_id = api_event_id
            existing.latitude = existing.latitude or -27.4698
            existing.longitude = existing.longitude or 153.0251
            existing.star_rating = existing.star_rating or 4.5
            existing.source = "JSON API"
        else:
            new_item = CulturalExperience(
                name=name,
                category=category,
                suburb=venue,
                description=description,
                price_range=price_range,
                website_link=website_link,
                image_url=image_url,
                cultural_tag="Arts and Culture",
                family_friendly=family_friendly,
                booking_required=booking_required,
                event_type=category,
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                formatted_datetime=formatted_datetime,
                venue_address=venue_address,
                api_event_id=api_event_id,
                latitude=-27.4698,
                longitude=153.0251,
                star_rating=4.5,
                source="JSON API"
            )
            db.session.add(new_item)

        imported_count += 1

    db.session.commit()
    return imported_count


# ============================================================
# AUTHENTICATION
# ============================================================

@app.route("/")
def index():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    success = request.args.get("success")

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM Users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user"] = user["username"]
            session["user_profile"] = normalise_role(user["user_profile"])
            session["is_guest"] = False

            flash(f"Welcome back, {user['username']}!", "success")

            if session["user_profile"] == "Admin":
                return redirect(url_for("admin_dashboard"))

            return redirect(url_for("home"))

        error = "Incorrect username or password."

    return render_template("login.html", error=error, success=success)


@app.route("/continue-as-guest")
def continue_as_guest():
    session.clear()
    session["user"] = "Guest"
    session["user_profile"] = "Guest"
    session["is_guest"] = True
    flash("You are browsing as a guest. Create an account to save favourites, comment, rate or use the day planner.", "info")
    return redirect(url_for("home"))


@app.route("/register", methods=["GET", "POST"])
def register():
    error = None

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()
        user_profile = normalise_role(request.form.get("user_profile", "Tourist"))

        if user_profile == "Admin":
            user_profile = "Tourist"

        if not username or not password or not confirm_password:
            error = "Please fill in all required fields."
        elif password != confirm_password:
            error = "Passwords do not match."
        else:
            conn = get_db_connection()
            existing_user = conn.execute(
                "SELECT * FROM Users WHERE username = ? OR email = ?",
                (username, email)
            ).fetchone()

            if existing_user:
                error = "Username or email already exists."
            else:
                conn.execute(
                    "INSERT INTO Users (username, email, password, user_profile) VALUES (?, ?, ?, ?)",
                    (username, email, generate_password_hash(password), user_profile)
                )
                conn.commit()
                conn.close()
                return redirect(url_for("login", success="Account created successfully. Please log in."))

            conn.close()

    return render_template("register.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ============================================================
# MAIN PAGES
# ============================================================

@app.route("/home")
def home():
    if not require_user_or_guest():
        return redirect(url_for("login"))

    weather = get_weather()
    cultural_experiences = CulturalExperience.query.order_by(CulturalExperience.name.asc()).all()
    cultural_review_data = get_cultural_review_data()

    cultural_favourite_ids = []
    if not is_guest():
        cultural_favourite_ids = [
            fav.cultural_id for fav in CulturalFavourite.query.filter_by(username=session["user"]).all()
        ]

    def popularity_score(item):
        if item.cultural_id in cultural_review_data:
            return (
                cultural_review_data[item.cultural_id]["average"],
                cultural_review_data[item.cultural_id]["count"]
            )
        return (item.star_rating or 0, 0)

    popular_cultural_experiences = sorted(cultural_experiences, key=popularity_score, reverse=True)[:3]

    return render_template(
        "index.html",
        weather=weather,
        popular_cultural_experiences=popular_cultural_experiences,
        cultural_favourite_ids=cultural_favourite_ids,
        cultural_review_data=cultural_review_data
    )


@app.route("/locations")
def locations():
    if not require_user_or_guest():
        return redirect(url_for("login"))

    cultural_experiences = CulturalExperience.query.order_by(CulturalExperience.name.asc()).all()
    activities = Activity.query.order_by(Activity.name.asc()).all()

    cultural_categories = sorted({item.category for item in cultural_experiences if item.category})
    activity_categories = sorted({activity.category for activity in activities if activity.category})

    favourite_ids = []
    cultural_favourite_ids = []

    if not is_guest():
        favourite_ids = [fav.activity_id for fav in Favourite.query.filter_by(username=session["user"]).all()]
        cultural_favourite_ids = [fav.cultural_id for fav in CulturalFavourite.query.filter_by(username=session["user"]).all()]

    return render_template(
        "weather_location.html",
        cultural_experiences=cultural_experiences,
        activities=activities,
        cultural_categories=cultural_categories,
        activity_categories=activity_categories,
        favourite_ids=favourite_ids,
        cultural_favourite_ids=cultural_favourite_ids,
        review_data=get_review_data(),
        cultural_review_data=get_cultural_review_data()
    )


@app.route("/library")
def library():
    if not require_user_or_guest():
        return redirect(url_for("login"))

    if is_guest():
        flash("Guests cannot access My Library. Please create an account or log in.", "error")
        return redirect(url_for("register"))

    return render_template(
        "library.html",
        favourites=Favourite.query.filter_by(username=session["user"]).all(),
        cultural_favourites=CulturalFavourite.query.filter_by(username=session["user"]).all(),
        olympic_favourites=OlympicFavourite.query.filter_by(username=session["user"]).all(),
        review_data=get_review_data(),
        cultural_review_data=get_cultural_review_data(),
        olympic_review_data=get_olympic_review_data()
    )


@app.route("/olympic-events")
def olympic_events():
    if not require_user_or_guest():
        return redirect(url_for("login"))

    olympic_favourite_ids = []
    if not is_guest():
        olympic_favourite_ids = [
            fav.event_id for fav in OlympicFavourite.query.filter_by(username=session["user"]).all()
        ]

    return render_template(
        "olympic_events.html",
        olympic_favourite_ids=olympic_favourite_ids,
        olympic_review_data=get_olympic_review_data()
    )


# ============================================================
# CULTURAL FAVOURITES AND REVIEWS
# ============================================================

@app.route("/add-cultural-favourite/<int:cultural_id>", methods=["POST"])
def add_cultural_favourite(cultural_id):
    if not require_user_or_guest():
        return redirect(url_for("login"))
    if is_guest():
        return guest_blocked_message()

    item = CulturalExperience.query.get(cultural_id)
    if not item:
        flash("This cultural experience could not be found.", "error")
        return redirect(url_for("locations"))

    existing = CulturalFavourite.query.filter_by(username=session["user"], cultural_id=cultural_id).first()

    if existing:
        flash(f"{item.name} is already in your library.", "info")
    else:
        db.session.add(CulturalFavourite(username=session["user"], cultural_id=cultural_id))
        db.session.commit()
        flash(f"{item.name} has been added to your library.", "success")

    return redirect(request.referrer or url_for("locations"))


@app.route("/remove-cultural-favourite/<int:cultural_id>", methods=["POST"])
def remove_cultural_favourite(cultural_id):
    if not require_user_or_guest():
        return redirect(url_for("login"))
    if is_guest():
        return guest_blocked_message()

    favourite = CulturalFavourite.query.filter_by(username=session["user"], cultural_id=cultural_id).first()

    if favourite:
        item_name = favourite.cultural_experience.name if favourite.cultural_experience else "Cultural experience"
        db.session.delete(favourite)
        db.session.commit()
        flash(f"{item_name} has been removed from your library.", "success")
    else:
        flash("This cultural experience was not found in your library.", "error")

    return redirect(request.referrer or url_for("locations"))


@app.route("/remove-library-cultural-favourite/<int:cultural_favourite_id>", methods=["POST"])
def remove_library_cultural_favourite(cultural_favourite_id):
    if not require_user_or_guest():
        return redirect(url_for("login"))
    if is_guest():
        return guest_blocked_message()

    favourite = CulturalFavourite.query.filter_by(
        cultural_favourite_id=cultural_favourite_id,
        username=session["user"]
    ).first()

    if favourite:
        db.session.delete(favourite)
        db.session.commit()
        flash("Saved cultural experience removed from your library.", "success")
    else:
        flash("This saved cultural experience could not be found.", "error")

    return redirect(url_for("library"))


@app.route("/add-cultural-review/<int:cultural_id>", methods=["POST"])
def add_cultural_review(cultural_id):
    if not require_user_or_guest():
        return redirect(url_for("login"))
    if is_guest():
        return guest_blocked_message()

    item = CulturalExperience.query.get(cultural_id)
    if not item:
        flash("This cultural experience could not be found.", "error")
        return redirect(url_for("locations"))

    try:
        rating = int(request.form.get("rating", 5))
    except ValueError:
        rating = 5

    rating = max(1, min(5, rating))
    comment = request.form.get("comment", "").strip()

    if not comment:
        flash("Please write a comment before posting.", "error")
        return redirect(request.referrer or url_for("locations"))

    db.session.add(CulturalReview(
        username=session["user"],
        cultural_id=cultural_id,
        rating=rating,
        comment=comment
    ))
    db.session.commit()

    flash(f"Your review for {item.name} has been posted.", "success")
    return redirect(request.referrer or url_for("locations"))


# ============================================================
# ACTIVITY FAVOURITES AND REVIEWS
# ============================================================

@app.route("/add-favourite/<int:activity_id>", methods=["POST"])
def add_favourite(activity_id):
    if not require_user_or_guest():
        return redirect(url_for("login"))
    if is_guest():
        return guest_blocked_message()

    activity = Activity.query.get(activity_id)
    if not activity:
        flash("Sorry, this activity could not be found.", "error")
        return redirect(request.referrer or url_for("locations"))

    existing = Favourite.query.filter_by(username=session["user"], activity_id=activity_id).first()

    if existing:
        flash(f"{activity.name} is already in your library.", "info")
    else:
        db.session.add(Favourite(username=session["user"], activity_id=activity_id))
        db.session.commit()
        flash(f"{activity.name} has been added to your library.", "success")

    return redirect(request.referrer or url_for("locations"))


@app.route("/remove-favourite/<int:activity_id>", methods=["POST"])
def remove_favourite(activity_id):
    if not require_user_or_guest():
        return redirect(url_for("login"))
    if is_guest():
        return guest_blocked_message()

    favourite = Favourite.query.filter_by(username=session["user"], activity_id=activity_id).first()

    if favourite:
        db.session.delete(favourite)
        db.session.commit()
        flash("Activity removed from your library.", "success")
    else:
        flash("This activity was not found in your library.", "error")

    return redirect(request.referrer or url_for("library"))


@app.route("/remove-library-favourite/<int:favourite_id>", methods=["POST"])
def remove_library_favourite(favourite_id):
    if not require_user_or_guest():
        return redirect(url_for("login"))
    if is_guest():
        return guest_blocked_message()

    favourite = Favourite.query.filter_by(favourite_id=favourite_id, username=session["user"]).first()

    if favourite:
        db.session.delete(favourite)
        db.session.commit()
        flash("Saved activity removed from your library.", "success")
    else:
        flash("This saved activity could not be found.", "error")

    return redirect(url_for("library"))


@app.route("/add-comment/<int:activity_id>", methods=["POST"])
def add_comment(activity_id):
    if not require_user_or_guest():
        return redirect(url_for("login"))
    if is_guest():
        return guest_blocked_message()

    activity = Activity.query.get(activity_id)
    if not activity:
        flash("Sorry, this activity could not be found.", "error")
        return redirect(url_for("locations"))

    try:
        rating = int(request.form.get("rating", 5))
    except ValueError:
        rating = 5

    rating = max(1, min(5, rating))
    comment_text = request.form.get("comment", "").strip()

    if not comment_text:
        flash("Please write a comment before posting.", "error")
        return redirect(request.referrer or url_for("locations"))

    db.session.add(Review(
        username=session["user"],
        activity_id=activity_id,
        rating=rating,
        comment=comment_text
    ))
    db.session.commit()

    flash(f"Your review for {activity.name} has been posted.", "success")
    return redirect(request.referrer or url_for("locations"))


# ============================================================
# OLYMPIC FAVOURITES AND REVIEWS
# ============================================================

@app.route("/add-olympic-favourite", methods=["GET", "POST"])
@app.route("/add-olympic-favorite", methods=["GET", "POST"])
def add_olympic_favourite():
    if not require_user_or_guest():
        return redirect(url_for("login"))
    if is_guest():
        return guest_blocked_message()

    if request.method == "GET":
        return redirect(url_for("olympic_events"))

    event_id = request.form.get("event_id", "").strip()
    name = request.form.get("name", "").strip()
    category = request.form.get("category", "").strip()
    location = request.form.get("location", "").strip()
    schedule = request.form.get("schedule", "").strip()
    description = request.form.get("description", "").strip()

    if not event_id or not name:
        flash("Sorry, this Olympic event could not be saved.", "error")
        return redirect(url_for("olympic_events"))

    existing = OlympicFavourite.query.filter_by(username=session["user"], event_id=event_id).first()

    if existing:
        flash(f"{name} is already in your library.", "info")
    else:
        db.session.add(OlympicFavourite(
            username=session["user"],
            event_id=event_id,
            name=name,
            category=category,
            location=location,
            schedule=schedule,
            description=description
        ))
        db.session.commit()
        flash(f"{name} has been added to your library.", "success")

    return redirect(request.referrer or url_for("olympic_events"))


@app.route("/remove-olympic-favourite/<event_id>", methods=["GET", "POST"])
@app.route("/remove-olympic-favorite/<event_id>", methods=["GET", "POST"])
def remove_olympic_favourite(event_id):
    if not require_user_or_guest():
        return redirect(url_for("login"))
    if is_guest():
        return guest_blocked_message()

    favourite = OlympicFavourite.query.filter_by(username=session["user"], event_id=event_id).first()

    if favourite:
        event_name = favourite.name
        db.session.delete(favourite)
        db.session.commit()
        flash(f"{event_name} has been removed from your library.", "success")
    else:
        flash("This Olympic event was not found in your library.", "error")

    return redirect(request.referrer or url_for("olympic_events"))


@app.route("/remove-library-olympic-favourite/<int:olympic_favourite_id>", methods=["POST"])
def remove_library_olympic_favourite(olympic_favourite_id):
    if not require_user_or_guest():
        return redirect(url_for("login"))
    if is_guest():
        return guest_blocked_message()

    favourite = OlympicFavourite.query.filter_by(
        olympic_favourite_id=olympic_favourite_id,
        username=session["user"]
    ).first()

    if favourite:
        db.session.delete(favourite)
        db.session.commit()
        flash("Saved Olympic event removed from your library.", "success")
    else:
        flash("This saved Olympic event could not be found.", "error")

    return redirect(url_for("library"))


@app.route("/add-olympic-review/<event_id>", methods=["POST"])
def add_olympic_review(event_id):
    if not require_user_or_guest():
        return redirect(url_for("login"))
    if is_guest():
        return guest_blocked_message()

    event_name = request.form.get("event_name", "").strip() or event_id.replace("-", " ").title()
    comment_text = request.form.get("comment", "").strip()

    try:
        rating = int(request.form.get("rating", 5))
    except ValueError:
        rating = 5

    rating = max(1, min(5, rating))

    if not comment_text:
        flash("Please write a comment before posting.", "error")
        return redirect(request.referrer or url_for("olympic_events"))

    db.session.add(OlympicReview(
        username=session["user"],
        event_id=event_id,
        event_name=event_name,
        rating=rating,
        comment=comment_text
    ))
    db.session.commit()

    flash(f"Your review for {event_name} has been posted.", "success")
    return redirect(request.referrer or url_for("olympic_events"))


# ============================================================
# DAY PLANNER
# ============================================================

@app.route("/day-planner", methods=["GET", "POST"])
def day_planner():
    if not require_user_or_guest():
        return redirect(url_for("login"))
    if is_guest():
        flash("Guests cannot access the Day Planner. Please create an account or log in.", "error")
        return redirect(url_for("register"))

    saved_activity_favourites = Favourite.query.filter_by(username=session["user"]).all()
    saved_cultural_favourites = CulturalFavourite.query.filter_by(username=session["user"]).all()

    saved_activities = [fav.activity for fav in saved_activity_favourites if fav.activity]
    saved_cultural_experiences = [fav.cultural_experience for fav in saved_cultural_favourites if fav.cultural_experience]

    generated_plan = []
    total_cost = 0
    plan_date = ""
    start_time = "09:00"
    group_size = 1
    pace = "balanced"

    def estimate_price(price_range):
        price = (price_range or "").lower()
        if price == "free":
            return 0
        if price == "paid":
            return 25
        if price == "premium":
            return 90
        return 0

    def add_minutes(time_string, minutes):
        hour, minute = map(int, time_string.split(":"))
        total = hour * 60 + minute + minutes
        return f"{(total // 60) % 24:02d}:{total % 60:02d}"

    def pretty_time(time_string):
        hour, minute = map(int, time_string.split(":"))
        suffix = "AM" if hour < 12 else "PM"
        display_hour = hour % 12 or 12
        return f"{display_hour}:{minute:02d} {suffix}"

    if request.method == "POST":
        selected_cultural_ids = request.form.getlist("cultural_experiences")
        selected_activity_ids = request.form.getlist("activities")
        plan_date = request.form.get("plan_date", "")
        start_time = request.form.get("start_time", "09:00")
        pace = request.form.get("pace", "balanced")

        try:
            group_size = max(1, min(20, int(request.form.get("group_size", 1))))
        except ValueError:
            group_size = 1

        selected_items = []

        for cultural_id in selected_cultural_ids:
            item = CulturalExperience.query.get(int(cultural_id))
            if item:
                selected_items.append({
                    "name": item.name,
                    "category": item.category,
                    "suburb": item.suburb,
                    "description": item.description,
                    "price_range": item.price_range,
                    "website_link": item.website_link,
                    "latitude": item.latitude,
                    "longitude": item.longitude,
                    "booking_required": item.booking_required,
                    "type": "Cultural Experience"
                })

        for activity_id in selected_activity_ids:
            item = Activity.query.get(int(activity_id))
            if item:
                selected_items.append({
                    "name": item.name,
                    "category": item.category,
                    "suburb": item.suburb,
                    "description": item.description,
                    "price_range": item.price_range,
                    "website_link": item.website_link,
                    "latitude": item.latitude,
                    "longitude": item.longitude,
                    "booking_required": "",
                    "type": "Visitor Activity"
                })

        if not selected_items:
            for item in saved_cultural_experiences[:3]:
                selected_items.append({
                    "name": item.name,
                    "category": item.category,
                    "suburb": item.suburb,
                    "description": item.description,
                    "price_range": item.price_range,
                    "website_link": item.website_link,
                    "latitude": item.latitude,
                    "longitude": item.longitude,
                    "booking_required": item.booking_required,
                    "type": "Cultural Experience"
                })

        current_time = start_time

        for index, item in enumerate(selected_items, start=1):
            duration = 90
            travel_minutes = 20 if pace == "balanced" else 30 if pace == "relaxed" else 15
            end_time = add_minutes(current_time, duration)
            next_time = add_minutes(end_time, travel_minutes)
            price = estimate_price(item.get("price_range"))
            total_cost += price

            generated_plan.append({
                "number": index,
                "name": item["name"],
                "category": item["category"],
                "suburb": item["suburb"],
                "description": item["description"],
                "price_range": item["price_range"],
                "website_link": item["website_link"],
                "type": item["type"],
                "start_time": pretty_time(current_time),
                "end_time": pretty_time(end_time),
                "next_time": pretty_time(next_time),
                "duration": duration,
                "travel_minutes": travel_minutes,
                "price": price,
                "availability": "Check the official website for bookings and current times.",
                "opening_note": "Check the listed event schedule before visiting.",
                "transport_note": "Use public transport where possible and check Translink first.",
                "google_transit_url": f"https://www.google.com/maps/dir/?api=1&destination={item.get('latitude')},{item.get('longitude')}&travelmode=transit",
                "translink_url": "https://jp.translink.com.au/plan-your-journey/journey-planner"
            })

            current_time = next_time

        if generated_plan:
            flash("Your suggested timetable has been created successfully.", "success")
        else:
            flash("Please save some cultural experiences or activities before creating a timetable.", "error")

    return render_template(
        "day_planner.html",
        saved_activities=saved_activities,
        saved_cultural_experiences=saved_cultural_experiences,
        generated_plan=generated_plan,
        total_cost=total_cost,
        plan_date=plan_date,
        start_time=start_time,
        group_size=group_size,
        pace=pace
    )


# ============================================================
# SMALL INTERNAL JSON ROUTE FOR TRAVEL LINKS
# ============================================================

@app.route("/api/travel-plan")
def api_travel_plan():
    destination_name = request.args.get("destination_name", "").strip()
    destination_lat = request.args.get("destination_lat", "").strip()
    destination_lng = request.args.get("destination_lng", "").strip()

    if destination_lat and destination_lng:
        google_maps_url = (
            "https://www.google.com/maps/dir/?api=1"
            f"&destination={destination_lat},{destination_lng}"
            "&travelmode=transit"
        )
    else:
        google_maps_url = "https://www.google.com/maps"

    return jsonify({
        "destination_name": destination_name,
        "destination_lat": destination_lat,
        "destination_lng": destination_lng,
        "google_maps_url": google_maps_url,
        "translink_url": "https://jp.translink.com.au/plan-your-journey/journey-planner"
    })


# ============================================================
# ADMIN ROUTES
# ============================================================

@app.route("/admin")
def admin_dashboard():
    if "user" not in session:
        flash("Please log in first.", "error")
        return redirect(url_for("login"))

    if not is_admin():
        flash("You do not have permission to access the admin dashboard.", "error")
        return redirect(url_for("home"))

    conn = get_db_connection()
    users = conn.execute("""
        SELECT userID, username, first_name, surname, email, user_profile
        FROM Users
        ORDER BY username ASC
    """).fetchall()
    conn.close()

    all_cultural_experiences = CulturalExperience.query.order_by(CulturalExperience.name.asc()).all()

    total_users = len(users)
    total_activities = Activity.query.count()
    total_cultural_experiences = CulturalExperience.query.count()
    total_api_events = CulturalExperience.query.filter_by(source="JSON API").count()
    total_cultural_favourites = CulturalFavourite.query.count()
    total_activity_favourites = Favourite.query.count()
    total_olympic_favourites = OlympicFavourite.query.count()
    total_reviews = Review.query.count() + CulturalReview.query.count() + OlympicReview.query.count()

    return render_template(
        "admin.html",
        users=users,
        all_cultural_experiences=all_cultural_experiences,
        cultural_experiences=all_cultural_experiences,
        total_users=total_users,
        total_activities=total_activities,
        total_cultural_experiences=total_cultural_experiences,
        total_api_events=total_api_events,
        total_cultural_favourites=total_cultural_favourites,
        total_activity_favourites=total_activity_favourites,
        total_olympic_favourites=total_olympic_favourites,
        total_reviews=total_reviews
    )


@app.route("/admin/refresh-cultural-json", methods=["POST"])
def admin_refresh_cultural_json():
    if not is_admin():
        flash("You do not have permission to use this feature.", "error")
        return redirect(url_for("home"))

    try:
        imported_count = refresh_cultural_experiences_from_json()
        flash(f"JSON cultural events refreshed successfully. {imported_count} records processed.", "success")
    except requests.exceptions.RequestException:
        flash("The Brisbane Creative Events API could not be reached. Cached database records are still available.", "error")
    except Exception as error:
        flash(f"Could not refresh JSON data. Error: {error}", "error")

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/add-cultural-experience", methods=["POST"])
def admin_add_cultural_experience():
    if not is_admin():
        flash("You do not have permission to use this feature.", "error")
        return redirect(url_for("home"))

    name = request.form.get("name", "").strip()
    category = request.form.get("category", "").strip()
    suburb = request.form.get("suburb", "").strip()
    description = request.form.get("description", "").strip()

    if not name or not category or not suburb or not description:
        flash("Please fill in name, category, suburb and description.", "error")
        return redirect(url_for("admin_dashboard"))

    try:
        latitude = float(request.form.get("latitude", -27.4698))
    except ValueError:
        latitude = -27.4698

    try:
        longitude = float(request.form.get("longitude", 153.0251))
    except ValueError:
        longitude = 153.0251

    try:
        star_rating = float(request.form.get("star_rating", 4.5))
    except ValueError:
        star_rating = 4.5

    db.session.add(CulturalExperience(
        name=name,
        category=category,
        suburb=suburb,
        description=description,
        price_range=request.form.get("price_range", "Unknown").strip(),
        website_link=request.form.get("website_link", "").strip(),
        image_url=request.form.get("image_url", "").strip() or DEFAULT_IMAGE_URL,
        cultural_tag=request.form.get("cultural_tag", "Arts and Culture").strip(),
        family_friendly=request.form.get("family_friendly", "Unknown").strip(),
        booking_required=request.form.get("booking_required", "Unknown").strip(),
        event_type=request.form.get("event_type", category).strip(),
        latitude=latitude,
        longitude=longitude,
        star_rating=max(1, min(5, star_rating)),
        source="Admin"
    ))
    db.session.commit()

    flash(f"{name} has been added to cultural experiences.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/delete-cultural-experience/<int:cultural_id>", methods=["POST"])
def admin_delete_cultural_experience(cultural_id):
    if not is_admin():
        flash("You do not have permission to use this feature.", "error")
        return redirect(url_for("home"))

    item = CulturalExperience.query.get(cultural_id)

    if not item:
        flash("Cultural experience not found.", "error")
        return redirect(url_for("admin_dashboard"))

    CulturalFavourite.query.filter_by(cultural_id=cultural_id).delete()
    CulturalReview.query.filter_by(cultural_id=cultural_id).delete()
    db.session.delete(item)
    db.session.commit()

    flash("Cultural experience deleted.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/delete-cultural-review/<int:cultural_review_id>", methods=["POST"])
def admin_delete_cultural_review(cultural_review_id):
    if not is_admin():
        flash("You do not have permission to use this feature.", "error")
        return redirect(url_for("home"))

    review = CulturalReview.query.get(cultural_review_id)

    if review:
        db.session.delete(review)
        db.session.commit()
        flash("Cultural review deleted.", "success")
    else:
        flash("Review not found.", "error")

    return redirect(request.referrer or url_for("admin_dashboard"))


@app.route("/admin/delete-review/<int:review_id>", methods=["POST"])
def admin_delete_review(review_id):
    if not is_admin():
        flash("You do not have permission to use this feature.", "error")
        return redirect(url_for("home"))

    review = Review.query.get(review_id)

    if review:
        db.session.delete(review)
        db.session.commit()
        flash("Review deleted.", "success")
    else:
        flash("Review not found.", "error")

    return redirect(request.referrer or url_for("admin_dashboard"))


@app.route("/admin/delete-olympic-review/<int:olympic_review_id>", methods=["POST"])
def admin_delete_olympic_review(olympic_review_id):
    if not is_admin():
        flash("You do not have permission to use this feature.", "error")
        return redirect(url_for("home"))

    review = OlympicReview.query.get(olympic_review_id)

    if review:
        db.session.delete(review)
        db.session.commit()
        flash("Olympic review deleted.", "success")
    else:
        flash("Review not found.", "error")

    return redirect(request.referrer or url_for("admin_dashboard"))


# ============================================================
# START APP
# ============================================================

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        add_missing_columns()

    app.run(debug=True)
