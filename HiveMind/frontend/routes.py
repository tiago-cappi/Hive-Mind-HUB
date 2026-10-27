"""Serve the isolated Hive Mind frontend assets without assistant endpoints."""

from flask import Blueprint


blueprint = Blueprint(
    "hivemind_frontend",
    __name__,
    static_folder="static",
    static_url_path="/hive-ui/static",
    url_prefix="",
)
