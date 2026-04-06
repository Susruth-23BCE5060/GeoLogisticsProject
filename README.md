# 🚑 GeoLogistics Intelligence System

**Real-Time Emergency Vehicle Routing Using Dynamic Dijkstra & MongoDB**

The GeoLogistics Intelligence System is a real-time simulation built on a NoSQL database architecture. It models an urban grid, continuously tracks 700 independent moving vehicles, and dynamically routes an emergency ambulance using a live-weighted Dijkstra algorithm. As traffic density shifts, the system autonomously recalculates the optimal path, ensuring the ambulance avoids congestion.

---

## 📖 Project Background: Aim vs. Reality

### The Original Aim
The initial objective of this project was to map the exact, real-world street network of Chennai, simulate live traffic flow, and route an ambulance dynamically using real-world geographic coordinates and real-time mapping APIs. 

### What We Built (The Pivot)
We abstracted the city environment into a **parametric 10x10 Spatial Grid** (100 intersections, 180 road segments, and 700 simulated vehicles). We built our own self-contained simulation engine and graph network, pushing all the spatial tracking and traffic aggregation into a MongoDB database.

### Why We Made This Change
Transitioning from a real-world map to a simulated grid was a deliberate engineering decision based on several constraints:
1. **API Rate Limits & Cost:** Real-world routing engines (like Google Maps or Mapbox) charge per request. Calculating alternate routes for dynamic traffic multiple times per second would trigger massive API costs and immediate rate-limit bans.
2. **Complex Map Geometries:** Real map data (OpenStreetMap) contains irregular geometries, overpasses, and one-way streets. Cleaning this into a mathematically perfect bidirectional graph for live Dijkstra testing requires enterprise-level GIS preprocessing, which was beyond the scope of a NoSQL database project.
3. **Microscopic Traffic Physics:** Simulating actual cars taking left turns, adhering to lane physics, and accelerating realistically requires a dedicated 3D physics engine, distracting from the core objective of testing database write-speeds and graph logic.

---

## 🔮 Future Scope: Achieving the Real-World Output
To transition this project from a grid simulation to the actual streets of Chennai, the following infrastructure upgrades would be required:
1. **Self-Hosted OSRM (Open Source Routing Machine):** To bypass Google Maps API costs, a local OSRM server must be spun up using OpenStreetMap data, allowing unlimited, free routing calculations per second.
2. **Microscopic Traffic Simulation Integration:** Integrating with an engine like **Eclipse SUMO** (Simulation of Urban MObility) to handle realistic vehicle kinematics (acceleration, braking, traffic lights) instead of basic vector interpolation.
3. **Advanced GIS Pipeline:** Utilizing tools like GDAL to clean OpenStreetMap data and seamlessly convert street geometries into native MongoDB GeoJSON LineStrings for highly accurate spatial querying.

---

## ✨ Key Features
* **Live NoSQL Traffic Aggregation:** Uses MongoDB Aggregation Pipelines to process high-frequency spatial writes (700+ vehicles updating multiple times a second) without frame drops.
* **Dynamic Pathfinding:** Implements Dijkstra's Algorithm with dynamic edge-weights based on live vehicle counts.
* **Intersection Locking Engine:** A custom physics constraint ensuring the ambulance commits to a street and only recalculates paths exactly at intersection nodes, preventing erratic U-turns mid-street.
* **Real-Time Visualization:** A custom Leaflet.js dashboard rendering 2.5 frames per second over a fast Flask REST API.

---

## 🛠️ Tech Stack
* **Database:** MongoDB (NoSQL)
* **Backend:** Python 3.x
* **API Framework:** Flask & Flask-CORS
* **Frontend:** HTML5, CSS3, JavaScript, Leaflet.js (Canvas Rendering)

---

## 🏗️ System Architecture

```mermaid
graph TD
    subgraph "Client / Frontend Layer"
        UI["💻 index.html<br>(Leaflet.js & HTML5 Canvas)"]
    end

    subgraph "API Gateway"
        API["🌐 app.py<br>(Flask REST API)"]
    end

    subgraph "Backend Simulation Engine"
        SIM["⚙️ simulator.py<br>(Traffic Brain & Dijkstra Algorithm)"]
        SEED["🌱 seed_data.py<br>(Grid & Data Generator)"]
    end

    subgraph "Database Layer"
        DB[("🍃 MongoDB<br>(NoSQL Document Database)")]
    end

    UI == "1. Polls /api/* every 400ms" ==> API
    API -- "2. Reads Live Simulation State" --> DB
    
    SIM -- "A. Executes Traffic Aggregation Pipeline" --> DB
    SIM -- "B. Calculates Dijkstra Optimal Path" --> SIM
    SIM -- "C. Bulk Writes 700+ Vehicle Locations" --> DB
    
    SEED -. "One-time Setup: Initializes 10x10 Grid" .-> DB
