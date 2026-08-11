"""
store.py
This is the Python equivalent of your C++ MarketPlace class: it holds all
users, properties, and listings, and provides the search/register/transaction
operations. Instead of C++ fixed arrays, it uses plain dicts, and instead of
losing everything when the program exits, it saves to data.json.
"""

import json
import os
from datetime import date

from models import (
    Buyer, Renter, Owner, Property, Listing,
    BuyTransaction, RentTransaction, Message,
)

DATA_FILE = os.path.join(os.path.dirname(__file__), "data.json")


class MarketPlace:
    def __init__(self):
        self.users = {}        # id -> Buyer/Renter/Owner
        self.properties = {}   # id -> Property
        self.listings = {}     # id -> Listing
        self.transactions = [] # list of dicts (receipts)
        self.messages = {}     # id -> Message
        self.load()

    # ---------- persistence ----------

    def save(self):
        data = {
            "users": [u.to_dict() for u in self.users.values()],
            "properties": [p.to_dict() for p in self.properties.values()],
            "listings": [l.to_dict() for l in self.listings.values()],
            "transactions": self.transactions,
            "messages": [m.to_dict() for m in self.messages.values()],
        }
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def load(self):
        if not os.path.exists(DATA_FILE):
            return
        with open(DATA_FILE) as f:
            data = json.load(f)

        for ud in data.get("users", []):
            role = ud["role"]
            if role == "buyer":
                u = Buyer(ud["name"], ud["phone"], ud["email"], ud.get("balance", 0))
                u.favorites = ud.get("favorites", [])
            elif role == "renter":
                u = Renter(ud["name"], ud["phone"], ud["email"],
                           ud.get("balance", 0), ud.get("rental_months", 1))
                u.favorites = ud.get("favorites", [])
            else:
                u = Owner(ud["name"], ud["phone"], ud["email"])
            u.id = ud["id"]  # override the auto-generated id with the saved one
            u.password = ud.get("password")
            self.users[u.id] = u

        for pd in data.get("properties", []):
            p = Property(pd["owner_id"], pd["location"], pd["price"],
                         pd["type"], pd["bedrooms"], pd["available"])
            p.id = pd["id"]
            self.properties[p.id] = p

        for ld in data.get("listings", []):
            l = Listing(ld["property_id"], ld["owner_id"], ld["post_date"], ld["status"])
            l.id = ld["id"]
            self.listings[l.id] = l

        self.transactions = data.get("transactions", [])

        for msgd in data.get("messages", []):
            msg = Message(msgd["sender_id"], msgd["sender_role"],
                         msgd["receiver_id"], msgd["content"], msgd["date"])
            msg.id = msgd["id"]
            msg.is_read = msgd.get("is_read", False)
            self.messages[msg.id] = msg

        # After loading, fast-forward each ID counter past the highest ID we
        # just loaded from disk, so new records never collide with old ones.
        import models as m
        if self.users:
            m._user_ids = _counter_after(max(self.users))
        if self.properties:
            m._property_ids = _counter_after(max(self.properties))
        if self.listings:
            m._listing_ids = _counter_after(max(self.listings))
        if self.messages:
            m._message_ids = _counter_after(max(self.messages))

    # ---------- users ----------

    def register_user(self, user):
        self.users[user.id] = user
        self.save()
        return user

    def get_user(self, user_id):
        return self.users.get(int(user_id))

    def find_user_by_email(self, email):
        for u in self.users.values():
            if u.email.lower() == email.lower():
                return u
        return None

    # ---------- properties & listings ----------

    def add_property(self, owner_id, location, price, type_, bedrooms):
        p = Property(owner_id, location, price, type_, bedrooms, available=True)
        self.properties[p.id] = p
        self.save()
        return p

    def create_listing(self, property_id, owner_id):
        l = Listing(property_id, owner_id, date.today().isoformat(), status="Pending")
        self.listings[l.id] = l
        self.save()
        return l

    def delete_listing(self, listing_id):
        self.listings.pop(int(listing_id), None)
        self.save()

    def get_listing(self, listing_id):
        return self.listings.get(int(listing_id))

    def owner_properties(self, owner_id):
        return [p for p in self.properties.values() if p.owner_id == owner_id]

    def owner_listings(self, owner_id):
        return [l for l in self.listings.values() if l.owner_id == owner_id]

    def approved_listings(self):
        return [l for l in self.listings.values() if l.status == "Approved"]

    # ---------- search (fixed: returns ALL matches, not just the first) ----------

    def search_listings(self, location=None, max_price=None, bedrooms=None, type_=None):
        results = self.approved_listings()
        if location:
            results = [l for l in results
                       if location.lower() in self.properties[l.property_id].location.lower()]
        if max_price:
            results = [l for l in results if self.properties[l.property_id].price <= float(max_price)]
        if bedrooms:
            results = [l for l in results if self.properties[l.property_id].bedrooms == int(bedrooms)]
        if type_:
            results = [l for l in results if self.properties[l.property_id].type == type_]
        return results

    # ---------- favorites ----------

    def add_favorite(self, user, listing_id):
        listing_id = int(listing_id)
        if listing_id not in user.favorites:
            user.favorites.append(listing_id)
            self.save()

    def remove_favorite(self, user, listing_id):
        listing_id = int(listing_id)
        if listing_id in user.favorites:
            user.favorites.remove(listing_id)
            self.save()

    # ---------- transactions ----------

    def buy_property(self, buyer, prop):
        if buyer.balance < prop.price:
            return False, "Insufficient balance."
        buyer.balance -= prop.price
        prop.available = False
        t = BuyTransaction(buyer, prop, date.today().isoformat())
        self.transactions.append(t.to_dict())
        for l in self.listings.values():
            if l.property_id == prop.id:
                l.status = "Sold"
        self.save()
        return True, t.to_dict()

    def rent_property(self, renter, prop):
        total = prop.price * renter.rental_months
        if renter.balance < total:
            return False, "Insufficient balance."
        renter.balance -= total
        prop.available = False
        t = RentTransaction(renter, prop, date.today().isoformat())
        self.transactions.append(t.to_dict())
        for l in self.listings.values():
            if l.property_id == prop.id:
                l.status = "Rented"
        self.save()
        return True, t.to_dict()

    # ---------- messages ----------

    def send_message(self, sender, receiver_id, content):
        msg = Message(sender.id, sender.role, receiver_id, content, date.today().isoformat())
        self.messages[msg.id] = msg
        self.save()
        return msg

    def messages_for_owner(self, owner_id):
        return [m for m in self.messages.values() if m.receiver_id == owner_id]

    # ---------- admin ----------

    def pending_listings(self):
        return [l for l in self.listings.values() if l.status == "Pending"]

    def approve_listing(self, listing_id):
        l = self.get_listing(listing_id)
        if l:
            l.status = "Approved"
            self.save()

    def reject_listing(self, listing_id):
        l = self.get_listing(listing_id)
        if l:
            l.status = "Rejected"
            self.save()


def _counter_after(highest_id):
    """Return a fresh itertools.count starting right after the highest ID seen."""
    import itertools
    return itertools.count(highest_id + 1)


# Single shared instance the Flask app imports
marketplace = MarketPlace()
