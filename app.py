"""
app.py
Flask web app for the Property MarketPlace.

Run locally:
    pip install -r requirements.txt
    python app.py
Then open http://127.0.0.1:5000

Simple demo auth: no hashing/security here on purpose — this is a portfolio/
learning project, not something meant to hold real user data. If you deploy
this beyond a demo, look into Flask-Login + werkzeug.security password hashing.
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash

from models import Buyer, Renter, Owner
from store import marketplace

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-this"  # fine for a demo, not for production

ADMIN_PASSWORD = "admin123"  # simple hardcoded admin password for demo purposes


# ---------- helpers ----------

def current_user():
    uid = session.get("user_id")
    if uid is None:
        return None
    return marketplace.get_user(uid)


@app.context_processor
def inject_user():
    return {"current_user": current_user()}


# ---------- public pages ----------

@app.route("/")
def home():
    location = request.args.get("location", "").strip()
    max_price = request.args.get("max_price", "").strip()
    bedrooms = request.args.get("bedrooms", "").strip()
    type_ = request.args.get("type", "").strip()

    results = marketplace.search_listings(
        location=location or None,
        max_price=max_price or None,
        bedrooms=bedrooms or None,
        type_=type_ or None,
    )
    listings = [
        {"listing": l, "property": marketplace.properties[l.property_id],
         "owner": marketplace.get_user(l.owner_id)}
        for l in results
    ]
    return render_template("index.html", listings=listings,
                           filters={"location": location, "max_price": max_price,
                                   "bedrooms": bedrooms, "type": type_})


@app.route("/listing/<int:listing_id>")
def listing_detail(listing_id):
    listing = marketplace.get_listing(listing_id)
    if not listing:
        flash("Listing not found.")
        return redirect(url_for("home"))
    prop = marketplace.properties[listing.property_id]
    owner = marketplace.get_user(listing.owner_id)
    return render_template("listing_detail.html", listing=listing, property=prop, owner=owner)


# ---------- auth ----------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        role = request.form["role"]
        name = request.form["name"]
        phone = request.form["phone"]
        email = request.form["email"]
        password = request.form["password"]

        if marketplace.find_user_by_email(email):
            flash("An account with that email already exists.")
            return redirect(url_for("register"))

        if role == "buyer":
            balance = float(request.form.get("balance") or 0)
            user = Buyer(name, phone, email, balance)
        elif role == "renter":
            balance = float(request.form.get("balance") or 0)
            months = int(request.form.get("rental_months") or 1)
            user = Renter(name, phone, email, balance, months)
        elif role == "owner":
            user = Owner(name, phone, email)
        else:
            flash("Invalid role.")
            return redirect(url_for("register"))

        user.password = password
        marketplace.register_user(user)
        session["user_id"] = user.id
        flash(f"Welcome, {user.name}! Your account has been created.")
        return redirect(url_for(f"{role}_dashboard"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = marketplace.find_user_by_email(email)
        if user and user.password == password:
            session["user_id"] = user.id
            return redirect(url_for(f"{user.role}_dashboard"))
        flash("Incorrect email or password.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ---------- owner dashboard ----------

@app.route("/owner")
def owner_dashboard():
    user = current_user()
    if not user or user.role != "owner":
        return redirect(url_for("login"))
    properties = marketplace.owner_properties(user.id)
    listings = marketplace.owner_listings(user.id)
    messages = marketplace.messages_for_owner(user.id)
    return render_template("owner_dashboard.html", properties=properties,
                           listings=listings, messages=messages,
                           marketplace=marketplace)


@app.route("/owner/add-property", methods=["POST"])
def add_property():
    user = current_user()
    if not user or user.role != "owner":
        return redirect(url_for("login"))
    marketplace.add_property(
        owner_id=user.id,
        location=request.form["location"],
        price=request.form["price"],
        type_=request.form["type"],
        bedrooms=request.form["bedrooms"],
    )
    flash("Property added.")
    return redirect(url_for("owner_dashboard"))


@app.route("/owner/create-listing/<int:property_id>", methods=["POST"])
def create_listing(property_id):
    user = current_user()
    if not user or user.role != "owner":
        return redirect(url_for("login"))
    marketplace.create_listing(property_id, user.id)
    flash("Listing created and sent for admin approval.")
    return redirect(url_for("owner_dashboard"))


# ---------- buyer / renter dashboards ----------

@app.route("/buyer")
def buyer_dashboard():
    user = current_user()
    if not user or user.role != "buyer":
        return redirect(url_for("login"))
    favorites = [
        {"listing": marketplace.get_listing(lid),
         "property": marketplace.properties[marketplace.get_listing(lid).property_id]}
        for lid in user.favorites if marketplace.get_listing(lid)
    ]
    return render_template("buyer_dashboard.html", user=user, favorites=favorites)


@app.route("/renter")
def renter_dashboard():
    user = current_user()
    if not user or user.role != "renter":
        return redirect(url_for("login"))
    favorites = [
        {"listing": marketplace.get_listing(lid),
         "property": marketplace.properties[marketplace.get_listing(lid).property_id]}
        for lid in user.favorites if marketplace.get_listing(lid)
    ]
    return render_template("renter_dashboard.html", user=user, favorites=favorites)


@app.route("/favorites/add/<int:listing_id>", methods=["POST"])
def add_favorite(listing_id):
    user = current_user()
    if not user or user.role not in ("buyer", "renter"):
        return redirect(url_for("login"))
    marketplace.add_favorite(user, listing_id)
    flash("Added to favorites.")
    return redirect(request.referrer or url_for("home"))


@app.route("/favorites/remove/<int:listing_id>", methods=["POST"])
def remove_favorite(listing_id):
    user = current_user()
    if not user or user.role not in ("buyer", "renter"):
        return redirect(url_for("login"))
    marketplace.remove_favorite(user, listing_id)
    flash("Removed from favorites.")
    return redirect(request.referrer or url_for("home"))


# ---------- transactions ----------

@app.route("/listing/<int:listing_id>/buy", methods=["POST"])
def buy(listing_id):
    user = current_user()
    if not user or user.role != "buyer":
        flash("Log in as a buyer to purchase a property.")
        return redirect(url_for("login"))
    listing = marketplace.get_listing(listing_id)
    prop = marketplace.properties[listing.property_id]
    ok, result = marketplace.buy_property(user, prop)
    if ok:
        return render_template("receipt.html", kind="Purchase", receipt=result,
                               user=user, property=prop)
    flash(result)
    return redirect(url_for("listing_detail", listing_id=listing_id))


@app.route("/listing/<int:listing_id>/rent", methods=["POST"])
def rent(listing_id):
    user = current_user()
    if not user or user.role != "renter":
        flash("Log in as a renter to rent a property.")
        return redirect(url_for("login"))
    listing = marketplace.get_listing(listing_id)
    prop = marketplace.properties[listing.property_id]
    ok, result = marketplace.rent_property(user, prop)
    if ok:
        return render_template("receipt.html", kind="Rental", receipt=result,
                               user=user, property=prop)
    flash(result)
    return redirect(url_for("listing_detail", listing_id=listing_id))


# ---------- messaging ----------

@app.route("/listing/<int:listing_id>/message", methods=["POST"])
def send_message(listing_id):
    user = current_user()
    if not user or user.role not in ("buyer", "renter"):
        flash("Log in to message an owner.")
        return redirect(url_for("login"))
    listing = marketplace.get_listing(listing_id)
    marketplace.send_message(user, listing.owner_id, request.form["content"])
    flash("Message sent.")
    return redirect(url_for("listing_detail", listing_id=listing_id))


# ---------- admin ----------

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["is_admin"] = True
        else:
            flash("Incorrect admin password.")
            return redirect(url_for("admin"))

    if not session.get("is_admin"):
        return render_template("admin_login.html")

    pending = marketplace.pending_listings()
    all_listings = list(marketplace.listings.values())
    return render_template("admin.html", pending=pending, all_listings=all_listings,
                           marketplace=marketplace)


@app.route("/admin/approve/<int:listing_id>", methods=["POST"])
def approve_listing(listing_id):
    if not session.get("is_admin"):
        return redirect(url_for("admin"))
    marketplace.approve_listing(listing_id)
    flash("Listing approved.")
    return redirect(url_for("admin"))


@app.route("/admin/reject/<int:listing_id>", methods=["POST"])
def reject_listing(listing_id):
    if not session.get("is_admin"):
        return redirect(url_for("admin"))
    marketplace.reject_listing(listing_id)
    flash("Listing rejected.")
    return redirect(url_for("admin"))


@app.route("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)
