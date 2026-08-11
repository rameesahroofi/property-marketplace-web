"""
models.py
Direct translation of the original C++ OOP design into Python.

Mapping from the C++ project:
    User (abstract)      -> User (base dict-backed class)
    Buyer / Renter / Owner-> Buyer / Renter / Owner  (inherit User)
    Property              -> Property
    Listing               -> Listing
    MarketPlace           -> MarketPlace (the in-memory "database")
    BuyTransaction/       -> BuyTransaction / RentTransaction
      RentTransaction
    Admin                 -> Admin
    Message               -> Message

Fixes applied vs. the original C++ version:
    - No fixed-size arrays (Listing[100], Bfavourites[10], etc.) -> Python lists,
      so there's no artificial cap on listings/favorites/properties.
    - search_by_* now returns ALL matches, not just the first one.
    - Owner is looked up directly via owner_id stored on the Property,
      instead of reverse-engineering it from digits of the property ID.
    - Data persists to a JSON file between runs (store.py handles this).
"""

import itertools

# Simple auto-incrementing ID generators (replaces manual ID math in the C++ version)
_property_ids = itertools.count(1)
_listing_ids = itertools.count(1)
_user_ids = itertools.count(1)
_transaction_ids = itertools.count(1)
_message_ids = itertools.count(1)


# ---------- User hierarchy ----------

class User:
    """Base class. Mirrors the abstract User class in C++."""
    role = "user"  # overridden by subclasses

    def __init__(self, name, phone, email):
        self.id = next(_user_ids)
        self.name = name
        self.phone = phone
        self.email = email
        self.password = None  # set by register route

    def to_dict(self):
        return {
            "id": self.id,
            "role": self.role,
            "name": self.name,
            "phone": self.phone,
            "email": self.email,
            "password": self.password,
        }


class Buyer(User):
    role = "buyer"

    def __init__(self, name, phone, email, balance=0.0):
        super().__init__(name, phone, email)
        self.balance = balance
        self.favorites = []  # list of listing IDs (was Listing* Bfavourites[10])

    def to_dict(self):
        d = super().to_dict()
        d.update({"balance": self.balance, "favorites": self.favorites})
        return d


class Renter(User):
    role = "renter"

    def __init__(self, name, phone, email, balance=0.0, rental_months=1):
        super().__init__(name, phone, email)
        self.balance = balance
        self.rental_months = rental_months
        self.favorites = []

    def to_dict(self):
        d = super().to_dict()
        d.update({
            "balance": self.balance,
            "rental_months": self.rental_months,
            "favorites": self.favorites,
        })
        return d


class Owner(User):
    role = "owner"

    def __init__(self, name, phone, email):
        super().__init__(name, phone, email)

    def to_dict(self):
        return super().to_dict()


# ---------- Property ----------

class Property:
    """Mirrors the C++ Property class."""

    def __init__(self, owner_id, location, price, type_, bedrooms, available=True):
        self.id = next(_property_ids)
        self.owner_id = owner_id       # stored directly (fixes the digit-math bug)
        self.location = location
        self.price = float(price)
        self.type = type_              # "sale" or "rent"
        self.bedrooms = int(bedrooms)
        self.available = available

    def to_dict(self):
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "location": self.location,
            "price": self.price,
            "type": self.type,
            "bedrooms": self.bedrooms,
            "available": self.available,
        }


# ---------- Listing ----------

class Listing:
    """Mirrors the C++ Listing class (wraps a Property + status)."""

    def __init__(self, property_id, owner_id, post_date, status="Pending"):
        self.id = next(_listing_ids)
        self.property_id = property_id
        self.owner_id = owner_id
        self.status = status          # Pending / Approved / Rejected / Sold / Rented
        self.post_date = post_date

    def to_dict(self):
        return {
            "id": self.id,
            "property_id": self.property_id,
            "owner_id": self.owner_id,
            "status": self.status,
            "post_date": self.post_date,
        }


# ---------- Transactions ----------

class Transaction:
    def __init__(self, date):
        self.id = next(_transaction_ids)
        self.date = date

    def to_dict(self):
        return {"id": self.id, "date": self.date}


class BuyTransaction(Transaction):
    def __init__(self, buyer, prop, date):
        super().__init__(date)
        self.buyer_id = buyer.id
        self.property_id = prop.id
        self.amount = prop.price
        self.type = "buy"

    def to_dict(self):
        d = super().to_dict()
        d.update({
            "type": self.type,
            "buyer_id": self.buyer_id,
            "property_id": self.property_id,
            "amount": self.amount,
        })
        return d


class RentTransaction(Transaction):
    def __init__(self, renter, prop, date):
        super().__init__(date)
        self.renter_id = renter.id
        self.property_id = prop.id
        self.monthly_rent = prop.price
        self.months = renter.rental_months
        self.total = self.monthly_rent * self.months
        self.type = "rent"

    def to_dict(self):
        d = super().to_dict()
        d.update({
            "type": self.type,
            "renter_id": self.renter_id,
            "property_id": self.property_id,
            "monthly_rent": self.monthly_rent,
            "months": self.months,
            "total": self.total,
        })
        return d


# ---------- Message ----------

class Message:
    def __init__(self, sender_id, sender_role, receiver_id, content, date):
        self.id = next(_message_ids)
        self.sender_id = sender_id
        self.sender_role = sender_role  # "buyer" or "renter"
        self.receiver_id = receiver_id  # owner id
        self.content = content
        self.date = date
        self.is_read = False

    def to_dict(self):
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "sender_role": self.sender_role,
            "receiver_id": self.receiver_id,
            "content": self.content,
            "date": self.date,
            "is_read": self.is_read,
        }
