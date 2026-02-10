import os

from flask import Blueprint, render_template


views_bp = Blueprint("views", __name__)


@views_bp.get("/")
def home():
    return render_template("home.html")


@views_bp.get("/dashboard")
def public_dashboard():
    return render_template("dashboard.html")


@views_bp.get("/login")
def login_view():
    return render_template("login.html")


@views_bp.get("/register")
def register_view():
    return render_template("register.html")


@views_bp.get("/citizen")
def citizen_dashboard_view():
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    return render_template("citizen_dashboard.html", google_maps_api_key=api_key)


@views_bp.get("/worker")
def worker_dashboard_view():
    return render_template("worker_dashboard.html")


@views_bp.get("/admin")
def admin_dashboard_view():
    return render_template("admin_dashboard.html")


@views_bp.get("/issue/<issue_id>")
def issue_detail_view(issue_id):
    return render_template("issue_detail.html", issue_id=issue_id)


@views_bp.get("/forgot-password")
def forgot_password_view():
    return render_template("forgot_password.html")


@views_bp.get("/reset-password")
def reset_password_view():
    return render_template("reset_password.html")


@views_bp.get("/search")
def search_view():
    return render_template("search.html")


@views_bp.get("/profile")
def profile_view():
    return render_template("profile.html")


@views_bp.get("/about")
def about_view():
    return render_template("about.html")


@views_bp.get("/contact")
def contact_view():
    return render_template("contact.html")


@views_bp.get("/faq")
def faq_view():
    return render_template("faq.html")

