import os

from dotenv import load_dotenv
from flask import Flask, render_template
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pymongo import MongoClient


mongo_client = None
db = None


def create_app():
    """Application factory for Urban Pulse Flask app."""
    load_dotenv()

    app = Flask(__name__, static_folder="../static", template_folder="../templates")

    # Basic configuration
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
    # Fallback to local MongoDB if MONGO_URI is not set
    app.config["MONGO_URI"] = os.getenv("MONGO_URI") or "mongodb://localhost:27017"
    app.config["JWT_SECRET"] = os.getenv("JWT_SECRET", "jwt-secret")
    app.config["CLOUDINARY_URL"] = os.getenv("CLOUDINARY_URL", "")
    
    # Enable CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Rate limiting
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per hour", "50 per minute"],
        storage_uri="memory://"
    )

    global mongo_client, db
    
    # Try to connect to MongoDB with better error handling
    try:
        mongo_client = MongoClient(
            app.config["MONGO_URI"],
            serverSelectionTimeoutMS=5000  # 5 second timeout
        )
        # Test the connection
        mongo_client.admin.command('ping')
        db_name = os.getenv("MONGO_DB_NAME", "urban_pulse")
        db = mongo_client[db_name]
        print(f"✅ Connected to MongoDB: {db_name}")
    except Exception as e:
        print("\n" + "="*70)
        print("❌ MONGODB CONNECTION ERROR")
        print("="*70)
        print(f"\nError: {str(e)}\n")
        print("🔧 QUICK FIX:")
        print("-" * 70)
        print("Option 1: Use MongoDB Atlas (FREE, 5 minutes)")
        print("  1. Go to: https://www.mongodb.com/cloud/atlas/register")
        print("  2. Create FREE account and cluster")
        print("  3. Get connection string")
        print("  4. Update MONGO_URI in .env file")
        print("  5. Run: python seed.py")
        print("  6. Restart: python run.py")
        print("\nOption 2: Install MongoDB Locally")
        print("  1. Download: https://www.mongodb.com/try/download/community")
        print("  2. Install and start MongoDB service")
        print("  3. Run: python seed.py")
        print("  4. Restart: python run.py")
        print("\n📖 See QUICK_FIX.md for detailed instructions")
        print("="*70 + "\n")
        raise SystemExit("MongoDB connection required. Please set up MongoDB and try again.")

    # Register blueprints
    from .routes.auth import auth_bp
    from .routes.issues import issues_bp
    from .routes.worker import worker_bp
    from .routes.impact import impact_bp
    from .routes.admin import admin_bp
    from .routes.upload import upload_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(issues_bp, url_prefix="/api/issues")
    app.register_blueprint(worker_bp, url_prefix="/api/worker")
    app.register_blueprint(impact_bp, url_prefix="/api/impact")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(upload_bp, url_prefix="/api")
    
    from .routes.notifications import notifications_bp
    app.register_blueprint(notifications_bp, url_prefix="/api/notifications")
    
    from .routes.search import search_bp
    app.register_blueprint(search_bp, url_prefix="/api/search")
    
    from .routes.comments import comments_bp
    app.register_blueprint(comments_bp, url_prefix="/api/comments")
    
    from .routes.votes import votes_bp
    app.register_blueprint(votes_bp, url_prefix="/api/votes")
    
    from .routes.users import users_bp
    app.register_blueprint(users_bp, url_prefix="/api/users")
    
    from .routes.analytics import analytics_bp
    app.register_blueprint(analytics_bp, url_prefix="/api/analytics")
    
    from .routes.public import public_bp
    app.register_blueprint(public_bp, url_prefix="/api/public")
    
    from .routes.nearby import nearby_bp
    app.register_blueprint(nearby_bp, url_prefix="/api/nearby")
    
    from .routes.bulk import bulk_bp
    app.register_blueprint(bulk_bp, url_prefix="/api/bulk")

    # Public views
    from .routes.views import views_bp

    app.register_blueprint(views_bp)

    # Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template("500.html"), 500

    return app


