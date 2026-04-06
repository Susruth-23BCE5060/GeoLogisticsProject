'''

import time
import math
import random
import heapq
from pymongo import MongoClient, UpdateOne

MONGO_URI = 'your_mongodb_connection_string_here'  # Replace with your MongoDB connection string
db = MongoClient(MONGO_URI)["logistics_db"]

def get_graph_data():
    nodes = {n["node_id"]: n["coords"] for n in db.nodes.find()}
    graph = {n: {} for n in nodes.keys()}
    edges = list(db.edges.find())
    
    # Map out connections for cars turning at intersections
    adjacency = {n: [] for n in nodes.keys()}
    
    for edge in edges:
        # Undirected graph for routing
        graph[edge["u"]][edge["v"]] = edge["base_cost"] + (edge["live_traffic"] * 1.5) # High traffic penalty
        graph[edge["v"]][edge["u"]] = graph[edge["u"]][edge["v"]]
        
        # For cars deciding where to go
        adjacency[edge["u"]].append({"neighbor": edge["v"], "edge_id": edge["edge_id"]})
        adjacency[edge["v"]].append({"neighbor": edge["u"], "edge_id": edge["edge_id"]})
        
    return nodes, graph, edges, adjacency

def dijkstra(graph, start, goal):
    queue = [(0, start, [])]
    seen = set()
    while queue:
        (cost, node, path) = heapq.heappop(queue)
        if node not in seen:
            seen.add(node)
            path = path + [node]
            if node == goal: return path
            for next_node, next_cost in graph[node].items():
                if next_node not in seen:
                    heapq.heappush(queue, (cost + next_cost, next_node, path))
    return []

def move_towards(curr, target, step):
    dx, dy = target[0] - curr[0], target[1] - curr[1]
    dist = math.hypot(dx, dy)
    if dist < step: return target
    return [curr[0] + (dx/dist)*step, curr[1] + (dy/dist)*step]

def run_simulation():
    print("🚦 Dynamic Traffic & Routing Engine Online...")
    
    while True:
        nodes, graph, edges, adjacency = get_graph_data()
        operations = []
        edge_traffic_counts = {e["edge_id"]: 0 for e in edges}

        # --- 1. MOVE 400 CARS DYNAMICALLY ---
        for car in db.drivers.find():
            curr_coords = car["location"]["coordinates"]
            target_node_id = car["target_node"]
            target_coords = nodes[target_node_id]
            
            # Move the car
            new_coords = move_towards(curr_coords, target_coords, step=0.0008)
            new_target = target_node_id
            new_edge = car["edge_id"]
            
            # If car reached the intersection, pick a random new street to turn onto
            if new_coords == target_coords:
                options = adjacency[target_node_id]
                chosen = random.choice(options)
                new_target = chosen["neighbor"]
                new_edge = chosen["edge_id"]
            
            edge_traffic_counts[new_edge] += 1
            operations.append(UpdateOne(
                {"_id": car["_id"]},
                {"$set": {"location.coordinates": new_coords, "target_node": new_target, "edge_id": new_edge}}
            ))

        # Bulk update all cars
        if operations: db.drivers.bulk_write(operations)

        # --- 2. UPDATE STREET WEIGHTS ---
        edge_ops = []
        for e_id, count in edge_traffic_counts.items():
            edge_ops.append(UpdateOne({"edge_id": e_id}, {"$set": {"live_traffic": count}}))
        if edge_ops: db.edges.bulk_write(edge_ops)

        # --- 3. RUN DIJKSTRA FOR AMBULANCE ---
        amb = db.ambulance.find_one()
        curr_node = amb.get("current_node", "N_0_0")
        goal_node = amb.get("target_node", "N_4_4")
        curr_coords = amb["location"]["coordinates"]

        if curr_node != goal_node:
            best_path = dijkstra(graph, curr_node, goal_node)
            next_hop = best_path[1] if len(best_path) > 1 else goal_node
            
            # Move ambulance
            new_coords = move_towards(curr_coords, nodes[next_hop], step=0.003)
            
            if new_coords == nodes[next_hop]:
                curr_node = next_hop # Reached intersection!

            db.ambulance.update_one(
                {"_id": amb["_id"]},
                {"$set": {"location.coordinates": new_coords, "current_node": curr_node, "calculated_path": best_path}}
            )
            print(f"Ambulance Path: {' -> '.join(best_path)}")
        else:
            print("🏁 Ambulance arrived! Restarting from bottom-left...")
            db.ambulance.update_one({"_id": amb["_id"]}, {"$set": {"current_node": "N_0_0", "location.coordinates": nodes["N_0_0"]}})

        time.sleep(0.5) # Fast loop for smooth map movement

if __name__ == "__main__":
    run_simulation()'''

import sqlite3
import time
import math
import random
import heapq
import json
import os

# Bulletproof Absolute Path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "city_graph.db")

def execute_complex_sql(conn):
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE edges 
        SET live_traffic = COALESCE((
            SELECT COUNT(vehicle_id) 
            FROM vehicles 
            WHERE vehicles.edge_id = edges.edge_id
        ), 0);
    """)
    conn.commit()

def get_live_graph(conn):
    cursor = conn.cursor()
    nodes = {row[0]: (row[1], row[2]) for row in cursor.execute("SELECT node_id, lat, lng FROM nodes")}
    
    graph = {n: {} for n in nodes.keys()}
    adjacency = {n: [] for n in nodes.keys()}
    
    for row in cursor.execute("SELECT edge_id, u, v, base_cost, live_traffic FROM edges"):
        e_id, u, v, base_cost, traffic = row
        weight = base_cost + (traffic * 1.5) # Heavy penalty for traffic
        graph[u][v] = weight
        graph[v][u] = weight
        adjacency[u].append({"neighbor": v, "edge_id": e_id})
        adjacency[v].append({"neighbor": u, "edge_id": e_id})
        
    return nodes, graph, adjacency

def dijkstra(graph, start, goal):
    queue = [(0, start, [])]
    seen = set()
    while queue:
        (cost, node, path) = heapq.heappop(queue)
        if node not in seen:
            seen.add(node)
            path = path + [node]
            if node == goal: return path
            for next_node, next_cost in graph[node].items():
                if next_node not in seen:
                    heapq.heappush(queue, (cost + next_cost, next_node, path))
    return []

def move_towards(curr, target, step):
    dlat, dlng = target[0] - curr[0], target[1] - curr[1]
    dist = math.hypot(dlat, dlng)
    if dist < step: return target # Snaps exactly to the intersection
    return (curr[0] + (dlat/dist)*step, curr[1] + (dlng/dist)*step)

def run_simulation():
    print(f"🚦 10x10 SQL Traffic Engine Online... Connected to: {DB_FILE}")
    conn = sqlite3.connect(DB_FILE)
    
    while True:
        execute_complex_sql(conn)
        nodes, graph, adjacency = get_live_graph(conn)
        cursor = conn.cursor()

        # 1. MOVE 700 CARS DYNAMICALLY (Speed stays at 0.00015)
        cars = cursor.execute("SELECT vehicle_id, edge_id, target_node, lat, lng FROM vehicles").fetchall()
        update_cars = []
        
        for car in cars:
            v_id, e_id, t_node, lat, lng = car
            target_coords = nodes[t_node]
            
            new_lat, new_lng = move_towards((lat, lng), target_coords, step=0.00015)
            new_t_node, new_e_id = t_node, e_id
            
            if (new_lat, new_lng) == target_coords:
                options = adjacency[t_node]
                chosen = random.choice(options)
                new_t_node, new_e_id = chosen["neighbor"], chosen["edge_id"]
                
            update_cars.append((new_e_id, new_t_node, new_lat, new_lng, v_id))
            
        cursor.executemany("UPDATE vehicles SET edge_id=?, target_node=?, lat=?, lng=? WHERE vehicle_id=?", update_cars)

        # 2. RUN DIJKSTRA FOR AMBULANCE (With Intersection Locking)
        amb = cursor.execute("SELECT current_node, target_node, lat, lng, calculated_path FROM ambulance WHERE unit_id='AMB_01'").fetchone()
        curr_node, goal_node, a_lat, a_lng, calc_path_str = amb

        if curr_node != goal_node:
            
            # Are we sitting exactly on an intersection?
            if (a_lat, a_lng) == nodes[curr_node]:
                # YES: Run Dijkstra to find the best street to turn down based on current traffic
                best_path = dijkstra(graph, curr_node, goal_node)
                calc_path_str = json.dumps(best_path)
                next_hop = best_path[1] if len(best_path) > 1 else goal_node
            else:
                # NO: We are mid-street. Keep driving to the next intersection in our locked path.
                best_path = json.loads(calc_path_str) if calc_path_str else [curr_node, goal_node]
                next_hop = best_path[1] if len(best_path) > 1 else goal_node
                
            # Move ambulance (Math fixed to guarantee 6.5 seconds per block)
            new_a_lat, new_a_lng = move_towards((a_lat, a_lng), nodes[next_hop], step=0.0003)
            
            # Did we just reach the end of the street? Update curr_node so we run Dijkstra next tick.
            if (new_a_lat, new_a_lng) == nodes[next_hop]: 
                curr_node = next_hop
                
            cursor.execute("UPDATE ambulance SET lat=?, lng=?, current_node=?, calculated_path=? WHERE unit_id='AMB_01'", 
                           (new_a_lat, new_a_lng, curr_node, calc_path_str))
        else:
            # Restart scenario
            cursor.execute("UPDATE ambulance SET current_node='N_0_0', lat=?, lng=? WHERE unit_id='AMB_01'", 
                           (nodes["N_0_0"][0], nodes["N_0_0"][1]))

        conn.commit()
        time.sleep(0.4) 

if __name__ == "__main__":
    run_simulation()