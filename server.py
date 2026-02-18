"""
YGGDRASIL ENGINE — Server
Lance le moteur + la visualisation 3D.

Usage:
    python server.py
    → http://localhost:5000
"""
import json
import os
from pathlib import Path

try:
    from flask import Flask, jsonify, send_from_directory, request
except ImportError:
    print("Flask not installed. Run: pip install flask")
    print("Generating static data instead...")
    
    # Fallback: just generate the viz data
    from engine.symbols import load
    db = load()
    viz_path = Path("viz/data.json")
    db.export_viz_json(viz_path)
    print(f"Data exported to {viz_path}")
    print(f"Open viz/index.html directly in your browser.")
    exit(0)

from engine.symbols import SymbolDatabase
from engine.holes import HoleDetector, CONTINENTS, map_symbol_to_continents

app = Flask(__name__, static_folder="viz")

# Load data once
db = SymbolDatabase()
viz_data_path = Path("viz/data.json")
db.export_viz_json(viz_data_path)
print(f"[SERVER] Viz data exported to {viz_data_path}")


@app.route("/")
def index():
    return send_from_directory("viz", "index.html")


@app.route("/data.json")
def data():
    return send_from_directory("viz", "data.json")


@app.route("/api/stats")
def stats():
    return jsonify(db.stats())


@app.route("/api/strate/<int:n>")
def strate(n):
    symbols = db.strate(n)
    return jsonify({
        "strate": n,
        "count": len(symbols),
        "symbols": [s.to_dict() for s in symbols]
    })


@app.route("/api/domain/<name>")
def domain(name):
    symbols = db.domain(name)
    return jsonify({
        "domain": name,
        "count": len(symbols),
        "symbols": [s.to_dict() for s in symbols]
    })


@app.route("/api/domains")
def domains():
    return jsonify(db.domains)


@app.route("/api/continents")
def continents():
    result = {}
    for continent, domain_list in CONTINENTS.items():
        symbols = []
        for d in domain_list:
            symbols.extend(db.domain(d))
        result[continent] = {
            "domains": domain_list,
            "symbol_count": len(symbols),
            "symbols": [s.to_dict() for s in symbols[:20]],  # First 20 only
        }
    return jsonify(result)


@app.route("/api/hole/search")
def hole_search():
    """Search for structural holes between two domains via OpenAlex."""
    a = request.args.get("a", "")
    b = request.args.get("b", "")
    if not a or not b:
        return jsonify({"error": "Provide ?a=domain&b=domain"}), 400
    
    from engine.openalex import search_structural_hole
    result = search_structural_hole(a, b)
    return jsonify(result)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n🌳 YGGDRASIL ENGINE v0.1.0")
    print(f"   {len(db.symbols)} symboles × 7 strates")
    print(f"   http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=True)
