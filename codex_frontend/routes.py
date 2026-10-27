"""Encaixe Flask para arquivos do frontend e seus seletores."""

from flask import Blueprint, jsonify

from .catalog import get_catalog

blueprint = Blueprint(
    "codex_frontend", __name__, static_folder="static",
    static_url_path="/codex-ui/static", url_prefix="",
)


@blueprint.get("/codex-ui/models")
def models():
    response = jsonify(get_catalog())
    response.headers["Cache-Control"] = "no-store"
    return response
