'''

from flask import Flask, jsonify
from flask_cors import CORS
from pymongo import MongoClient

app = Flask(__name__)
CORS(app)

MONGO_URI = 'your_mongodb_connection_string_here'  # Replace with your MongoDB connection string
db = MongoClient(MONGO_URI)["logistics_db"]

@app.route('/api/nodes', methods=['GET'])
def get_nodes():
    return jsonify([{ **n, "_id": str(n["_id"]) } for n in db.nodes.find()])

@app.route('/api/edges', methods=['GET'])
def get_edges():
    return jsonify([{ **e, "_id": str(e["_id"]) } for e in db.edges.find()])

@app.route('/api/vehicles', methods=['GET'])
def get_vehicles():
    return jsonify([{ **v, "_id": str(v["_id"]) } for v in db.drivers.find()])

@app.route('/api/ambulance', methods=['GET'])
def get_ambulance():
    return jsonify([{ **a, "_id": str(a["_id"]) } for a in db.ambulance.find()])

if __name__ == '__main__':
    app.run(debug=True, port=5000)'''

from flask import Flask, jsonify
from flask_cors import CORS
import sqlite3
import json
import os

# Bulletproof Absolute Path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "city_graph.db")

app = Flask(__name__)
CORS(app)

def query_db(query, args=(), one=False):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(query, args)
    rv = cur.fetchall()
    conn.close()
    return (rv[0] if rv else None) if one else rv

@app.route('/api/nodes', methods=['GET'])
def get_nodes():
    nodes = query_db("SELECT node_id, lat, lng FROM nodes")
    return jsonify([dict(n) for n in nodes])

@app.route('/api/edges', methods=['GET'])
def get_edges():
    query = """
        SELECT e.edge_id, e.live_traffic, 
               n1.lat as u_lat, n1.lng as u_lng, 
               n2.lat as v_lat, n2.lng as v_lng
        FROM edges e
        JOIN nodes n1 ON e.u = n1.node_id
        JOIN nodes n2 ON e.v = n2.node_id
    """
    edges = query_db(query)
    return jsonify([dict(e) for e in edges])

@app.route('/api/vehicles', methods=['GET'])
def get_vehicles():
    vehicles = query_db("SELECT vehicle_id, lat, lng FROM vehicles")
    return jsonify([dict(v) for v in vehicles])

@app.route('/api/ambulance', methods=['GET'])
def get_ambulance():
    amb = query_db("SELECT lat, lng, calculated_path FROM ambulance WHERE unit_id='AMB_01'", one=True)
    if not amb:
        return jsonify([])
    amb_dict = dict(amb)
    amb_dict['calculated_path'] = json.loads(amb_dict['calculated_path']) if amb_dict['calculated_path'] else []
    return jsonify([amb_dict])

if __name__ == '__main__':
    app.run(debug=True, port=5000)