'''
import pymongo
import random

MONGO_URI = 'your_mongodb_token_url'
db = pymongo.MongoClient(MONGO_URI)["logistics_db"]

def generate_large_graph():
    print("🧹 Wiping old database...")
    db.nodes.delete_many({})
    db.edges.delete_many({})
    db.drivers.delete_many({})
    db.ambulance.delete_many({})

    # 1. CREATE A 5x5 GRID OF NODES (25 Intersections)
    nodes = {}
    node_docs = []
    start_lng, start_lat = 80.200, 13.000
    spacing = 0.015 # Distance between intersections

    for x in range(5):
        for y in range(5):
            n_id = f"N_{x}_{y}"
            coords = [start_lng + (x * spacing), start_lat + (y * spacing)]
            nodes[n_id] = coords
            node_docs.append({"node_id": n_id, "coords": coords})
    db.nodes.insert_many(node_docs)

    # 2. CREATE EDGES (Streets connecting the grid)
    edge_docs = []
    edges_dict = {}
    for x in range(5):
        for y in range(5):
            curr = f"N_{x}_{y}"
            # Connect Right (East)
            if x < 4:
                right = f"N_{x+1}_{y}"
                e_id = f"{curr}-{right}"
                edge_docs.append({"edge_id": e_id, "u": curr, "v": right, "base_cost": 2, "live_traffic": 0})
                edges_dict[e_id] = (curr, right)
            # Connect Up (North)
            if y < 4:
                up = f"N_{x}_{y+1}"
                e_id = f"{curr}-{up}"
                edge_docs.append({"edge_id": e_id, "u": curr, "v": up, "base_cost": 2, "live_traffic": 0})
                edges_dict[e_id] = (curr, up)
    db.edges.insert_many(edge_docs)

    # 3. SPAWN 400 DYNAMIC CARS
    print("🚗 Spawning 400 moving vehicles...")
    drivers = []
    for i in range(400):
        # Pick a random street
        e_id = random.choice(list(edges_dict.keys()))
        u, v = edges_dict[e_id]
        
        # Place car randomly on that street
        progress = random.uniform(0, 1)
        lng = nodes[u][0] + (nodes[v][0] - nodes[u][0]) * progress
        lat = nodes[u][1] + (nodes[v][1] - nodes[u][1]) * progress
        
        # Decide which intersection it is driving towards
        target_node = v if random.random() > 0.5 else u

        drivers.append({
            "vehicle_id": f"CAR_{i}",
            "edge_id": e_id,
            "target_node": target_node,
            "location": {"type": "Point", "coordinates": [lng, lat]}
        })
    db.drivers.insert_many(drivers)

    # 4. INITIALIZE AMBULANCE (From Bottom-Left to Top-Right)
    db.ambulance.insert_one({
        "unit_id": "AMB_01",
        "current_node": "N_0_0",
        "target_node": "N_4_4",
        "location": {"type": "Point", "coordinates": nodes["N_0_0"]},
        "calculated_path": [],
        "moving_towards": None
    })
    
    print("✅ Massive 5x5 City Graph Seeded!")

if __name__ == "__main__":
    generate_large_graph()'''

import sqlite3
import random
import os

# Bulletproof Absolute Path: Forces the DB to be created exactly where this Python script is saved
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "city_graph.db")

def seed_sql_database():
    print(f"🧹 Initializing Optimal 10x10 SQL City Grid at: {DB_FILE}")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # --- 1. CREATE SQL TABLES ---
    cursor.executescript("""
        DROP TABLE IF EXISTS vehicles;
        DROP TABLE IF EXISTS edges;
        DROP TABLE IF EXISTS nodes;
        DROP TABLE IF EXISTS ambulance;

        CREATE TABLE nodes (
            node_id TEXT PRIMARY KEY,
            lat REAL,
            lng REAL
        );

        CREATE TABLE edges (
            edge_id TEXT PRIMARY KEY,
            u TEXT,
            v TEXT,
            base_cost REAL,
            live_traffic INTEGER DEFAULT 0,
            FOREIGN KEY(u) REFERENCES nodes(node_id),
            FOREIGN KEY(v) REFERENCES nodes(node_id)
        );

        CREATE TABLE vehicles (
            vehicle_id TEXT PRIMARY KEY,
            edge_id TEXT,
            target_node TEXT,
            lat REAL,
            lng REAL,
            FOREIGN KEY(edge_id) REFERENCES edges(edge_id)
        );

        CREATE TABLE ambulance (
            unit_id TEXT PRIMARY KEY,
            current_node TEXT,
            target_node TEXT,
            calculated_path TEXT,
            lat REAL,
            lng REAL
        );
    """)

    # --- 2. GENERATE 10x10 GRID (100 Nodes) ---
    start_lng, start_lat = 80.200, 13.000
    spacing = 0.005
    nodes = {}
    
    for x in range(10):
        for y in range(10):
            n_id = f"N_{x}_{y}"
            lng, lat = start_lng + (x * spacing), start_lat + (y * spacing)
            nodes[n_id] = (lat, lng)
            cursor.execute("INSERT INTO nodes (node_id, lat, lng) VALUES (?, ?, ?)", (n_id, lat, lng))

    # --- 3. GENERATE STREETS (180 Edges) ---
    edges_dict = {}
    for x in range(10):
        for y in range(10):
            curr = f"N_{x}_{y}"
            if x < 9:
                right = f"N_{x+1}_{y}"
                e_id = f"{curr}-{right}"
                cursor.execute("INSERT INTO edges (edge_id, u, v, base_cost) VALUES (?, ?, ?, 2)", (e_id, curr, right))
                edges_dict[e_id] = (curr, right)
            if y < 9:
                up = f"N_{x}_{y+1}"
                e_id = f"{curr}-{up}"
                cursor.execute("INSERT INTO edges (edge_id, u, v, base_cost) VALUES (?, ?, ?, 2)", (e_id, curr, up))
                edges_dict[e_id] = (curr, up)

    # --- 4. SPAWN 700 VEHICLES ---
    print("🚗 Spawning 700 moving vehicles...")
    vehicles_data = []
    for i in range(700):
        e_id = random.choice(list(edges_dict.keys()))
        u, v = edges_dict[e_id]
        progress = random.uniform(0, 1)
        lat = nodes[u][0] + (nodes[v][0] - nodes[u][0]) * progress
        lng = nodes[u][1] + (nodes[v][1] - nodes[u][1]) * progress
        target = v if random.random() > 0.5 else u
        vehicles_data.append((f"CAR_{i}", e_id, target, lat, lng))
        
    cursor.executemany("INSERT INTO vehicles (vehicle_id, edge_id, target_node, lat, lng) VALUES (?, ?, ?, ?, ?)", vehicles_data)

    # --- 5. INITIALIZE AMBULANCE ---
    amb_start = nodes["N_0_0"]
    cursor.execute("""
        INSERT INTO ambulance (unit_id, current_node, target_node, calculated_path, lat, lng) 
        VALUES ('AMB_01', 'N_0_0', 'N_9_9', '', ?, ?)
    """, (amb_start[0], amb_start[1]))

    conn.commit()
    conn.close()
    print("✅ 10x10 SQL Graph & 700 Cars Seeded Successfully!")

if __name__ == "__main__":
    seed_sql_database()
