import cloudinary.uploader
from flask import Blueprint, jsonify, request


upload_bp = Blueprint("upload", __name__)


@upload_bp.post("/upload-image")
def upload_image():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    try:
        result = cloudinary.uploader.upload(file)
    except Exception as e:
        return jsonify({"error": "Upload failed", "details": str(e)}), 500

    return jsonify({"url": result.get("secure_url")})


