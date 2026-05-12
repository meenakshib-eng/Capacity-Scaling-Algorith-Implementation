# Smart Logistics Delivery Optimization — Project Summary

## Overview

This project is an interactive Streamlit application for modeling and optimizing a delivery network composed of warehouses, hubs, and customer zones. It lets users define nodes and directed routes with capacities (packages/day), simulate route failures, and computes the maximum achievable delivery throughput using a capacity-scaling max-flow algorithm.

## Key Features

- Graph-based network model (nodes and directed edges with capacities).
- Capacity-scaling max-flow algorithm to compute overall delivery capacity.
- Visual, real-time network visualization (NetworkX + Matplotlib) highlighting active flows and bottlenecks.
- Sidebar controls to add/remove nodes and routes, run optimization, and simulate failures.
- Results page with metrics, bottleneck analysis, per-route breakdown, and algorithm execution log.

## Data Model

- `nodes`: list of dictionaries: `{id, label, type}` where `type` ∈ {`warehouse`, `hub`, `customer`}.
- `edges`: list of dictionaries: `{id, from, to, capacity}` representing directed routes.
- `st.session_state`: holds `nodes`, `edges`, `result`, `algo_log`, `failed_edge`, and an `id_counter`.

## How it works (high-level)

1. User defines the network (nodes + directed routes with capacities).
2. The app constructs a flow network by adding a super-source connected to all warehouses and a super-sink connected from all customers.
3. The capacity-scaling algorithm finds augmenting paths and increases flow until the global maximum is reached.
4. The UI displays `max_flow`, per-edge flows, saturated routes (bottlenecks), and visualizes flows on the graph.

## Capacity-Scaling Algorithm — Detailed Explanation

The app implements the capacity-scaling variant of augmenting-path max-flow algorithms. Key ideas and steps:

1. Build the residual network
   - Index nodes and create two special nodes: `S` (super-source) and `T` (super-sink).
   - `S` connects to every `warehouse` node with capacity equal to that warehouse's total outgoing capacity (sum of its outgoing route capacities).
   - Every `customer` node connects to `T` with capacity equal to that customer's total incoming capacity.
   - Add all user-defined directed routes between nodes with their capacities.

2. Initialize Δ (scaling parameter)
   - Find `Cmax`, the largest capacity value in the residual matrix.
   - Set initial Δ = 2^⌊log2(Cmax)⌋ (largest power of two ≤ Cmax).

3. Scaling phases
   - For each Δ down to 1 (Δ is halved when no Δ-sized augmenting path exists):
     - Run BFS to find augmenting paths from `S` to `T` that use only edges with residual capacity ≥ Δ.
     - For each found path, compute its bottleneck (minimum residual capacity along the path) and augment flow by that amount.
     - Repeat BFS until no more Δ-sized paths are found, then halve Δ and continue.

4. Compute results
   - `max_flow` is the sum of flows sent from `S` to the network (or equivalently into `T`).
   - Per-route flows are extracted from the flow matrix for each original directed edge (from→to).
   - Bottlenecks are routes where the computed flow is equal to the route's capacity.

### Why capacity-scaling?
- The capacity-scaling approach improves practical performance by preferring large augmentations early (when Δ is large) and avoiding many tiny augmentations that standard Ford–Fulkerson might perform.
- Complexity: the UI notes O(E² log C) where C is the maximum capacity — this reflects BFS/search work per augmentation across scaling phases.

### Notes & limitations
- The implementation uses dense NxN matrices (`cap` and `flow`). For large graphs a sparse adjacency/residual structure would be more memory- and time-efficient.
- Multiple warehouses and customer zones are handled via the super-source/sink trick.


---

*Generated: project summary & algorithm detail.*
# Capacity-Scaling-Algorith-Implementation
