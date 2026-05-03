# -*- coding: utf-8 -*-
import os
import random
import string
from datetime import datetime, timezone, timedelta
from flask import Flask, request, jsonify
from supabase import create_client, Client
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY environment variables.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def generate_key() -> str:
    chars = string.ascii_uppercase + string.digits
    seg1 = "".join(random.choices(chars, k=5))
    seg2 = "".join(random.choices(chars, k=5))
    return f"WATER-{seg1}-{seg2}"


def delete_expired_keys():
    now = datetime.now(timezone.utc).isoformat()
    try:
        supabase.table("keys").delete().lt("expires_at", now).not_.is_("expires_at", "null").execute()
    except Exception:
        pass


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/generate", methods=["POST"])
@limiter.limit("10 per minute")
def generate():
    delete_expired_keys()
    data = request.get_json(silent=True) or {}
    duration_hours = data.get("duration_hours")
    duration_days = data.get("duration_days")
    duration_minutes = data.get("duration_minutes")

    if duration_minutes is not None:
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=float(duration_minutes))
    elif duration_hours is not None:
        expires_at = datetime.now(timezone.utc) + timedelta(hours=float(duration_hours))
    elif duration_days is not None:
        expires_at = datetime.now(timezone.utc) + timedelta(days=float(duration_days))
    else:
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

    max_attempts = 5
    for _ in range(max_attempts):
        new_key = generate_key()
        try:
            result = supabase.table("keys").insert({
                "key": new_key,
                "expires_at": expires_at.isoformat()
            }).execute()
            if result.data:
                return jsonify({
                    "key": new_key,
                    "expires_at": expires_at.isoformat()
                }), 201
        except Exception as e:
            error_msg = str(e)
            if "duplicate" in error_msg.lower() or "unique" in error_msg.lower():
                continue
            return jsonify({"error": "Database error", "detail": error_msg}), 500

    return jsonify({"error": "Failed to generate a unique key after multiple attempts."}), 500


@app.route("/validate", methods=["POST"])
@limiter.limit("30 per minute")
def validate():
    delete_expired_keys()
    data = request.get_json(silent=True)
    if not data or "key" not in data:
        return jsonify({"error": "Missing 'key' in request body."}), 400

    key_to_check = str(data["key"]).strip().upper()
    now = datetime.now(timezone.utc).isoformat()

    try:
        result = supabase.table("keys").select("key", "expires_at").eq("key", key_to_check).execute()
        if not result.data:
            return jsonify({"valid": False}), 200
        row = result.data[0]
        expires_at = row.get("expires_at")
        if expires_at and expires_at < now:
            supabase.table("keys").delete().eq("key", key_to_check).execute()
            return jsonify({"valid": False, "reason": "expired"}), 200
        return jsonify({"valid": True}), 200
    except Exception as e:
        return jsonify({"error": "Database error", "detail": str(e)}), 500


@app.route("/listkeys", methods=["GET"])
def list_keys():
    delete_expired_keys()
    try:
        result = supabase.table("keys").select("key", "expires_at", "created_at").order("created_at", desc=True).execute()
        return jsonify({"keys": result.data}), 200
    except Exception as e:
        return jsonify({"error": "Database error", "detail": str(e)}), 500


@app.route("/deletekey", methods=["POST"])
def delete_key():
    data = request.get_json(silent=True)
    if not data or "key" not in data:
        return jsonify({"error": "Missing 'key' in request body."}), 400

    key_to_delete = str(data["key"]).strip().upper()

    try:
        result = supabase.table("keys").select("key").eq("key", key_to_delete).execute()
        if not result.data:
            return jsonify({"error": "Key not found."}), 404
        supabase.table("keys").delete().eq("key", key_to_delete).execute()
        return jsonify({"deleted": True, "key": key_to_delete}), 200
    except Exception as e:
        return jsonify({"error": "Database error", "detail": str(e)}), 500


@app.errorhandler(429)
def rate_limit_handler(e):
    return jsonify({"error": "Rate limit exceeded. Please slow down."}), 429


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
