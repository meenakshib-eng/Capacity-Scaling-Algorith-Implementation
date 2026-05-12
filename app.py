import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import math
import time

# ══════════════════════════════════════════════════
#  PAGE CONFIG
# ══════════════════════════════════════════════════
st.set_page_config(
    page_title="Smart Logistics Optimizer",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════
#  CUSTOM CSS
# ══════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&display=swap');

html, body, [class*="css"] { font-family: 'IBM Plex Mono', monospace; }

/* Header banner */
.main-header {
    background: linear-gradient(135deg, #0b0f1a 0%, #101623 100%);
    border: 1px solid #1e2d45;
    border-radius: 10px;
    padding: 18px 24px;
    margin-bottom: 20px;
}
.main-header h1 { color: #f5a623; font-size: 22px; margin: 0 0 4px 0; }
.main-header p  { color: #8fa3c0; font-size: 12px; margin: 0; letter-spacing: .1em; }

/* Metric cards */
.metric-row { display: flex; gap: 12px; margin-bottom: 16px; }
.metric-card {
    flex: 1; border-radius: 8px; padding: 16px;
    border: 1px solid; text-align: center;
}
.metric-card .val { font-size: 36px; font-weight: 700; line-height: 1; }
.metric-card .lbl { font-size: 10px; letter-spacing: .15em; margin-bottom: 6px; }
.metric-card .unit{ font-size: 11px; margin-top: 4px; color: #8fa3c0; }

.card-green { background:#27ae7515; border-color:#27ae7550; }
.card-green .val, .card-green .lbl { color: #27ae75; }
.card-red   { background:#e24a4a15; border-color:#e24a4a50; }
.card-red   .val, .card-red   .lbl { color: #e24a4a; }
.card-blue  { background:#4a90e215; border-color:#4a90e250; }
.card-blue  .val, .card-blue  .lbl { color: #4a90e2; }

/* Result boxes */
.result-box {
    background: #101623; border: 1px solid #1e2d45;
    border-radius: 8px; padding: 16px; margin-bottom: 14px;
}
.result-box-title {
    font-size: 10px; letter-spacing: .18em;
    margin-bottom: 12px; font-weight: 600;
}
.algo-line { font-size: 12px; line-height: 2; font-family: monospace; }
.bottleneck-item {
    display: flex; justify-content: space-between;
    padding: 7px 0; border-top: 1px solid #e24a4a30;
    font-size: 12px;
}
.formula { font-size: 15px; text-align: center; padding: 10px 0; }
.tag {
    display: inline-block; font-size: 10px; padding: 2px 8px;
    border-radius: 3px; font-family: monospace;
}

/* Sidebar */
section[data-testid="stSidebar"] { background: #0b0f1a !important; }
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stTextInput label,
section[data-testid="stSidebar"] .stNumberInput label { color: #8fa3c0 !important; font-size: 11px !important; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════
#  SESSION STATE INIT
# ══════════════════════════════════════════════════
def init_state():
    if "nodes" not in st.session_state:
        st.session_state.nodes = [
            {"id": "W1", "label": "Warehouse A",     "type": "warehouse"},
            {"id": "W2", "label": "Warehouse B",     "type": "warehouse"},
            {"id": "H1", "label": "Kochi Hub",       "type": "hub"},
            {"id": "H2", "label": "Trivandrum Hub",  "type": "hub"},
            {"id": "C1", "label": "Customer Zone 1", "type": "customer"},
            {"id": "C2", "label": "Customer Zone 2", "type": "customer"},
        ]
    if "edges" not in st.session_state:
        st.session_state.edges = [
            {"id":"e1","from":"W1","to":"H1","capacity":50},
            {"id":"e2","from":"W1","to":"H2","capacity":30},
            {"id":"e3","from":"W2","to":"H1","capacity":40},
            {"id":"e4","from":"W2","to":"H2","capacity":35},
            {"id":"e5","from":"H1","to":"C1","capacity":45},
            {"id":"e6","from":"H1","to":"C2","capacity":20},
            {"id":"e7","from":"H2","to":"C1","capacity":25},
            {"id":"e8","from":"H2","to":"C2","capacity":40},
        ]
    if "result"       not in st.session_state: st.session_state.result       = None
    if "algo_log"     not in st.session_state: st.session_state.algo_log     = []
    if "failed_edge"  not in st.session_state: st.session_state.failed_edge  = None
    if "id_counter"   not in st.session_state: st.session_state.id_counter   = 200

init_state()


# ══════════════════════════════════════════════════
#  CAPACITY SCALING MAX-FLOW
# ══════════════════════════════════════════════════
def capacity_scaling(nodes, edges):
    if not nodes or not edges:
        return {"max_flow": 0, "edge_flows": {}, "bottlenecks": []}

    ids   = [n["id"] for n in nodes]
    N     = len(ids) + 2
    S     = len(ids)       # super-source
    T     = len(ids) + 1   # super-sink
    idx   = {nid: i for i, nid in enumerate(ids)}

    # Residual capacity matrix
    cap  = [[0.0]*N for _ in range(N)]
    flow = [[0.0]*N for _ in range(N)]

    # Super-source → warehouses
    for n in nodes:
        if n["type"] == "warehouse":
            total_out = sum(e["capacity"] for e in edges if e["from"] == n["id"])
            cap[S][idx[n["id"]]] = total_out

    # Customers → super-sink
    for n in nodes:
        if n["type"] == "customer":
            total_in = sum(e["capacity"] for e in edges if e["to"] == n["id"])
            cap[idx[n["id"]]][T] = total_in

    # User-defined routes
    for e in edges:
        cap[idx[e["from"]]][idx[e["to"]]] += e["capacity"]

    max_cap = max(cap[i][j] for i in range(N) for j in range(N))
    if max_cap == 0:
        return {"max_flow": 0, "edge_flows": {}, "bottlenecks": []}

    delta = 2 ** int(math.log2(max_cap))
    log   = []
    log.append(f"Max capacity edge   : {int(max_cap)} packages")
    log.append(f"Initial Δ = 2^⌊log₂({int(max_cap)})⌋ = {delta}")

    def bfs(delta):
        parent = [-1] * N
        parent[S] = S
        queue = [S]
        while queue:
            u = queue.pop(0)
            for v in range(N):
                if parent[v] == -1 and cap[u][v] - flow[u][v] >= delta:
                    parent[v] = u
                    if v == T:
                        return parent
                    queue.append(v)
        return None

    total_flow = 0
    while delta >= 1:
        log.append(f"Phase Δ={delta:<6}  → searching augmenting paths…")
        path_count = 0
        parent = bfs(delta)
        while parent:
            # Bottleneck
            path_flow = float("inf")
            v = T
            while v != S:
                u = parent[v]
                path_flow = min(path_flow, cap[u][v] - flow[u][v])
                v = u
            # Augment
            v = T
            while v != S:
                u = parent[v]
                flow[u][v] += path_flow
                flow[v][u] -= path_flow
                v = u
            total_flow += path_flow
            path_count += 1
            parent = bfs(delta)

        if path_count:
            log.append(f"           Found {path_count} path(s), pushed flow +{path_count*delta if path_count else 0}")
        else:
            log.append(f"           No path found → halving Δ")
        delta //= 2

    log.append("─" * 46)
    log.append(f"✓ Maximum flow = {int(total_flow)} packages/day")

    # Per-edge flows
    edge_flows = {}
    for e in edges:
        edge_flows[f"{e['from']}-{e['to']}"] = max(0, flow[idx[e["from"]]][idx[e["to"]]])

    # Bottlenecks
    bottlenecks = [
        e for e in edges
        if edge_flows.get(f"{e['from']}-{e['to']}", 0) >= e["capacity"] > 0
    ]

    return {
        "max_flow":    int(total_flow),
        "edge_flows":  edge_flows,
        "bottlenecks": bottlenecks,
        "init_delta":  2 ** int(math.log2(max_cap)) if max_cap >= 1 else 1,
        "max_cap":     int(max_cap),
    }, log


# ══════════════════════════════════════════════════
#  NETWORK GRAPH (NetworkX + Matplotlib)
# ══════════════════════════════════════════════════
TYPE_COLOR = {"warehouse": "#f5a623", "hub": "#4a90e2", "customer": "#27ae75"}
TYPE_ICON  = {"warehouse": "🏭",       "hub": "🔀",       "customer": "📦"}

def build_positions():
    warehouses = [n for n in st.session_state.nodes if n["type"] == "warehouse"]
    hubs       = [n for n in st.session_state.nodes if n["type"] == "hub"]
    customers  = [n for n in st.session_state.nodes if n["type"] == "customer"]
    pos = {}

    def col(arr, x):
        n = len(arr)
        for i, node in enumerate(arr):
            y = 0.5 if n == 1 else i / (n - 1)
            pos[node["id"]] = (x, y)

    col(warehouses, 0.1)
    col(hubs,       0.5)
    col(customers,  0.9)
    return pos

def draw_network(result=None, failed_edge_id=None):
    nodes = st.session_state.nodes
    edges = st.session_state.edges
    pos   = build_positions()

    fig, ax = plt.subplots(figsize=(12, 5.5))
    fig.patch.set_facecolor("#101623")
    ax.set_facecolor("#101623")
    ax.axis("off")

    G = nx.DiGraph()
    for n in nodes:
        G.add_node(n["id"])

    # Draw edges
    active_edges = [e for e in edges if e["id"] != failed_edge_id]
    failed_edges = [e for e in edges if e["id"] == failed_edge_id]

    for edge in active_edges:
        f   = result["edge_flows"].get(f"{edge['from']}-{edge['to']}", 0) if result else 0
        util = f / edge["capacity"] if edge["capacity"] > 0 else 0
        is_bottle = result and any(
            b["from"] == edge["from"] and b["to"] == edge["to"]
            for b in result["bottlenecks"]
        ) if result else False

        if not result:
            color, width = "#2a3d57", 1.5
        elif is_bottle:
            color, width = "#e24a4a", 3.0
        elif util > 0:
            alpha = int(80 + util * 175)
            color = "#27ae75"
            width = 1.5 + util * 3
        else:
            color, width = "#2a3d57", 1.2

        label = f"{int(f)}/{edge['capacity']}" if result else f"{edge['capacity']}"

        nx.draw_networkx_edges(
            G, pos,
            edgelist=[(edge["from"], edge["to"])],
            edge_color=color,
            width=width,
            arrows=True,
            arrowsize=18,
            arrowstyle="-|>",
            connectionstyle="arc3,rad=0.08",
            ax=ax,
            min_source_margin=28,
            min_target_margin=28,
        )
        # Edge label
        src, dst = pos[edge["from"]], pos[edge["to"]]
        mx = (src[0] + dst[0]) / 2
        my = (src[1] + dst[1]) / 2 + 0.04
        lbl_color = "#e24a4a" if is_bottle else ("#27ae75" if (result and util>0) else "#4a5f78")
        ax.text(mx, my, label, ha="center", va="center", fontsize=7.5,
                color=lbl_color, fontfamily="monospace",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="#101623", edgecolor="none"))

    # Failed edges
    for edge in failed_edges:
        nx.draw_networkx_edges(
            G, pos,
            edgelist=[(edge["from"], edge["to"])],
            edge_color="#e24a4a40",
            width=1.0,
            style="dashed",
            arrows=False,
            ax=ax,
        )

    # Nodes
    for node in nodes:
        x, y = pos[node["id"]]
        color = TYPE_COLOR[node["type"]]
        circle = plt.Circle((x, y), 0.055, color=color, alpha=0.25, zorder=3)
        border = plt.Circle((x, y), 0.058, fill=False, edgecolor=color, linewidth=1.8, zorder=4)
        ax.add_patch(circle)
        ax.add_patch(border)
        ax.text(x, y + 0.005, TYPE_ICON[node["type"]], ha="center", va="center",
                fontsize=16, zorder=5)
        ax.text(x, y - 0.09, node["label"], ha="center", va="center",
                fontsize=8, color=color, fontfamily="monospace", fontweight="bold", zorder=5)

    # Layer titles
    ax.text(0.10, 1.05, "WAREHOUSES", ha="center", fontsize=9,
            color="#f5a62380", fontfamily="monospace", transform=ax.transAxes)
    ax.text(0.50, 1.05, "DELIVERY HUBS", ha="center", fontsize=9,
            color="#4a90e280", fontfamily="monospace", transform=ax.transAxes)
    ax.text(0.90, 1.05, "CUSTOMERS", ha="center", fontsize=9,
            color="#27ae7580", fontfamily="monospace", transform=ax.transAxes)

    # Legend
    if result:
        patches = [
            mpatches.Patch(color="#27ae75", label="Active flow"),
            mpatches.Patch(color="#e24a4a", label="Bottleneck"),
            mpatches.Patch(color="#2a3d57", label="Unused route"),
        ]
        ax.legend(handles=patches, loc="lower right", fontsize=8,
                  facecolor="#0b0f1a", edgecolor="#1e2d45",
                  labelcolor="white", framealpha=0.9)

    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.18, 1.18)
    plt.tight_layout()
    return fig


# ══════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### 🚚 Logistics Optimizer")
    st.markdown("---")

    # ── Add Node ──
    st.markdown("**▸ ADD NODE**")
    node_type  = st.selectbox("Type", ["warehouse", "hub", "customer"],
                              format_func=lambda x: f"{TYPE_ICON[x]} {x.capitalize()}")
    node_label = st.text_input("Node name", placeholder="e.g. Chennai Hub")
    if st.button("➕ Add Node", use_container_width=True):
        if node_label.strip():
            st.session_state.id_counter += 1
            prefix = {"warehouse":"W","hub":"H","customer":"C"}[node_type]
            st.session_state.nodes.append({
                "id":    f"{prefix}{st.session_state.id_counter}",
                "label": node_label.strip(),
                "type":  node_type,
            })
            st.session_state.result = None
            st.success(f"Added {node_label}")
        else:
            st.error("Enter a node name.")

    st.markdown("---")

    # ── Add Route ──
    st.markdown("**▸ ADD ROUTE**")
    node_options = {n["id"]: f"{TYPE_ICON[n['type']]} {n['label']}"
                    for n in st.session_state.nodes}
    if len(st.session_state.nodes) >= 2:
        node_ids = list(node_options.keys())
        from_node = st.selectbox("From", node_ids,
                                 format_func=lambda x: node_options[x], key="sel_from")
        to_node   = st.selectbox("To",   node_ids,
                                 format_func=lambda x: node_options[x], key="sel_to",
                                 index=min(1, len(node_ids)-1))
        capacity  = st.number_input("Capacity (packages/day)", min_value=1, value=30, step=5)
        if st.button("➕ Add Route", use_container_width=True):
            if from_node == to_node:
                st.error("From and To must differ.")
            else:
                st.session_state.id_counter += 1
                st.session_state.edges.append({
                    "id":       f"e{st.session_state.id_counter}",
                    "from":     from_node,
                    "to":       to_node,
                    "capacity": capacity,
                })
                st.session_state.result = None
                st.success(f"Route added ({capacity} pkg/day)")
    else:
        st.info("Add at least 2 nodes first.")

    st.markdown("---")

    # ── Route Failure Simulation ──
    st.markdown("**▸ SIMULATE ROUTE FAILURE**")
    fail_options = {"": "None (normal operation)"}
    for e in st.session_state.edges:
        fr = next((n["label"] for n in st.session_state.nodes if n["id"]==e["from"]), e["from"])
        to = next((n["label"] for n in st.session_state.nodes if n["id"]==e["to"]),   e["to"])
        fail_options[e["id"]] = f"{fr} → {to}  ({e['capacity']} pkg)"

    selected_fail = st.selectbox("Failed route", list(fail_options.keys()),
                                 format_func=lambda x: fail_options[x])
    if selected_fail:
        st.session_state.failed_edge = selected_fail
        st.error("⚡ Route failure active")
    else:
        st.session_state.failed_edge = None

    st.markdown("---")

    # ── Run / Reset ──
    run_clicked   = st.button("▶ RUN OPTIMIZATION", use_container_width=True, type="primary")
    reset_clicked = st.button("↺ Reset to Default", use_container_width=True)

    if reset_clicked:
        for key in ["nodes","edges","result","algo_log","failed_edge"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()


# ══════════════════════════════════════════════════
#  RUN ALGORITHM
# ══════════════════════════════════════════════════
if run_clicked:
    active_edges = [e for e in st.session_state.edges
                    if e["id"] != st.session_state.failed_edge]
    with st.spinner("Running Capacity Scaling Algorithm…"):
        time.sleep(0.4)   # small pause for effect
        res, log = capacity_scaling(st.session_state.nodes, active_edges)
    st.session_state.result   = res
    st.session_state.algo_log = log


# ══════════════════════════════════════════════════
#  MAIN CONTENT
# ══════════════════════════════════════════════════
st.markdown("""
<div class="main-header">
  <h1>🚚 Smart Logistics Delivery Optimization System</h1>
  <p>CAPACITY SCALING ALGORITHM &nbsp;·&nbsp; MAX-FLOW NETWORK ANALYSIS &nbsp;·&nbsp; REAL-TIME VISUALIZATION</p>
</div>
""", unsafe_allow_html=True)

# Header metrics
nodes = st.session_state.nodes
w_count = sum(1 for n in nodes if n["type"]=="warehouse")
h_count = sum(1 for n in nodes if n["type"]=="hub")
c_count = sum(1 for n in nodes if n["type"]=="customer")
e_count = len(st.session_state.edges)

hm1, hm2, hm3, hm4 = st.columns(4)
hm1.metric("🏭 Warehouses",  w_count)
hm2.metric("🔀 Hubs",        h_count)
hm3.metric("📦 Customers",   c_count)
hm4.metric("🛤️ Routes",     e_count)

st.markdown("---")

# ── TABS ──
tab1, tab2, tab3 = st.tabs(["📡 Network Graph", "🛤️ Route Manager", "📊 Results & Analysis"])

# ─────────────── TAB 1: Network Graph ───────────────
with tab1:
    result = st.session_state.result
    fig    = draw_network(result=result, failed_edge_id=st.session_state.failed_edge)
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

    if result:
        st.info(f"✅ Optimization complete — Maximum delivery capacity: **{result['max_flow']} packages/day**. "
                f"Edge labels show `flow / capacity`.")
    else:
        st.caption("Click **▶ RUN OPTIMIZATION** in the sidebar to calculate maximum delivery capacity.")


# ─────────────── TAB 2: Route Manager ───────────────
with tab2:
    result = st.session_state.result
    edges  = st.session_state.edges

    if not edges:
        st.info("No routes yet. Add routes from the sidebar.")
    else:
        st.markdown("#### All Routes")

        # Table header
        cols = st.columns([2, 2, 1.2, 1.2, 2, 1.5, 0.7])
        for col, h in zip(cols, ["FROM","TO","CAPACITY","FLOW","UTILISATION","STATUS","DEL"]):
            col.markdown(f"<small style='color:#4a5f78;letter-spacing:.1em'>{h}</small>",
                         unsafe_allow_html=True)
        st.markdown("<hr style='margin:4px 0;border-color:#1e2d45'>", unsafe_allow_html=True)

        to_delete = None
        for edge in edges:
            fr_node = next((n for n in st.session_state.nodes if n["id"]==edge["from"]), None)
            to_node = next((n for n in st.session_state.nodes if n["id"]==edge["to"]),   None)
            flow_val = 0
            util     = 0
            if result:
                flow_val = result["edge_flows"].get(f"{edge['from']}-{edge['to']}", 0)
                util     = flow_val / edge["capacity"] if edge["capacity"] > 0 else 0

            is_failed = edge["id"] == st.session_state.failed_edge
            is_bottle = result and any(
                b["from"]==edge["from"] and b["to"]==edge["to"]
                for b in result["bottlenecks"]
            ) if result else False

            if is_failed:   status = "⚡ FAILED"
            elif is_bottle: status = "⚠️ BOTTLENECK"
            elif result and flow_val > 0: status = "✅ ACTIVE"
            elif result:    status = "💤 IDLE"
            else:           status = "—"

            bar = ""
            if result:
                pct    = min(int(util*100), 100)
                b_col  = "#e24a4a" if util>=1 else ("#f5a623" if util>0.7 else "#27ae75")
                bar    = f"""<div style='background:#1d2640;border-radius:3px;height:6px;width:100%'>
                    <div style='width:{pct}%;height:100%;background:{b_col};border-radius:3px'></div>
                </div><small style='color:{b_col}'>{pct}%</small>"""

            cols = st.columns([2, 2, 1.2, 1.2, 2, 1.5, 0.7])
            cols[0].write(f"{TYPE_ICON.get(fr_node['type'],'')} {fr_node['label']}" if fr_node else "?")
            cols[1].write(f"{TYPE_ICON.get(to_node['type'],'')} {to_node['label']}" if to_node else "?")
            cols[2].write(f"{edge['capacity']} pkg")
            cols[3].write(f"{int(flow_val)} pkg" if result else "—")
            cols[4].markdown(bar if result else "—", unsafe_allow_html=True)
            cols[5].write(status)
            if cols[6].button("✕", key=f"del_{edge['id']}"):
                to_delete = edge["id"]

        if to_delete:
            st.session_state.edges = [e for e in st.session_state.edges if e["id"] != to_delete]
            if st.session_state.failed_edge == to_delete:
                st.session_state.failed_edge = None
            st.session_state.result = None
            st.rerun()


# ─────────────── TAB 3: Results & Analysis ───────────────
with tab3:
    result = st.session_state.result

    if not result:
        st.markdown("""
        <div style='text-align:center;padding:60px;color:#4a5f78;font-size:14px;'>
            ▶ Click <strong style='color:#f5a623'>RUN OPTIMIZATION</strong> in the sidebar<br>
            <span style='font-size:11px'>The Capacity Scaling Algorithm will compute maximum flow through your delivery network</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        active_edges = [e for e in st.session_state.edges
                        if e["id"] != st.session_state.failed_edge]
        active_flows = sum(1 for v in result["edge_flows"].values() if v > 0)

        # ── Stat Cards ──
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"""<div class="metric-card card-green">
              <div class="lbl">MAX DELIVERIES</div>
              <div class="val">{result['max_flow']}</div>
              <div class="unit">packages / day</div>
            </div>""", unsafe_allow_html=True)
        with c2:
            n_bot = len(result["bottlenecks"])
            st.markdown(f"""<div class="metric-card card-red">
              <div class="lbl">BOTTLENECKS</div>
              <div class="val">{n_bot}</div>
              <div class="unit">routes at full capacity</div>
            </div>""", unsafe_allow_html=True)
        with c3:
            st.markdown(f"""<div class="metric-card card-blue">
              <div class="lbl">ACTIVE ROUTES</div>
              <div class="val">{active_flows}</div>
              <div class="unit">of {len(active_edges)} available</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Bottleneck Analysis ──
        if result["bottlenecks"]:
            bottle_html = ""
            for b in result["bottlenecks"]:
                fr = next((n["label"] for n in st.session_state.nodes if n["id"]==b["from"]), b["from"])
                to = next((n["label"] for n in st.session_state.nodes if n["id"]==b["to"]),   b["to"])
                bottle_html += f"""<div class="bottleneck-item">
                    <span>{TYPE_ICON.get(next((n['type'] for n in st.session_state.nodes if n['id']==b['from']),'hub'),'🔀')} {fr}
                    &nbsp;→&nbsp;
                    {TYPE_ICON.get(next((n['type'] for n in st.session_state.nodes if n['id']==b['to']),'hub'),'🔀')} {to}</span>
                    <span style="color:#e24a4a">{b['capacity']} pkg/day &nbsp;(100% FULL)</span>
                </div>"""
            st.markdown(f"""
            <div class="result-box" style="border-color:#e24a4a50;background:#e24a4a10">
              <div class="result-box-title" style="color:#e24a4a">⚠ BOTTLENECK ROUTES — CAPACITY FULLY UTILIZED</div>
              {bottle_html}
              <div style="font-size:11px;color:#8fa3c0;margin-top:10px;padding-top:8px;border-top:1px solid #e24a4a30">
                💡 Increasing capacity on bottleneck routes will directly increase total delivery capacity.
              </div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""<div class="result-box" style="border-color:#27ae7550">
              <div class="result-box-title" style="color:#27ae75">✓ NETWORK HEALTH — NO BOTTLENECKS DETECTED</div>
              <div style="font-size:12px;color:#8fa3c0">
                All routes are operating below maximum capacity. The delivery network is well-balanced.
              </div>
            </div>""", unsafe_allow_html=True)

        # ── Algorithm Formula ──
        max_cap    = result.get("max_cap", 1)
        init_delta = result.get("init_delta", 1)
        st.markdown(f"""
        <div class="result-box">
          <div class="result-box-title" style="color:#9b7de8">▸ CAPACITY SCALING FORMULA</div>
          <div class="formula">
            Δ = 2<sup>⌊log₂(C<sub>max</sub>)⌋</sup>
            = 2<sup>⌊log₂({max_cap})⌋</sup>
            = <strong style="color:#f5a623;font-size:18px">{init_delta}</strong>
          </div>
          <div style="font-size:11px;color:#4a5f78;text-align:center;margin-top:6px">
            Δ is halved each phase until Δ &lt; 1 &nbsp;·&nbsp; Complexity: O(E² log C)
          </div>
        </div>""", unsafe_allow_html=True)

        # ── Algorithm Log ──
        log_html = "".join(
            f"<div class='algo-line' style='color:"
            f"{'#27ae75' if '✓' in l or 'complete' in l else '#e24a4a' if 'halving' in l or 'Bottleneck' in l else '#f5a623' if 'Initial' in l or 'Max cap' in l else '#4a90e2' if '→' in l and 'path' in l else '#8fa3c0'}'>"
            f"<span style='color:#2a3d57;margin-right:10px'>{str(i).zfill(2)}</span>{l}</div>"
            for i, l in enumerate(st.session_state.algo_log)
        )
        st.markdown(f"""
        <div class="result-box">
          <div class="result-box-title" style="color:#f5a623">▸ ALGORITHM EXECUTION LOG</div>
          <div style="font-family:monospace">{log_html}</div>
        </div>""", unsafe_allow_html=True)

        # ── Route Flow Breakdown ──
        flow_html = ""
        for e in active_edges:
            fr = next((n for n in st.session_state.nodes if n["id"]==e["from"]), None)
            to = next((n for n in st.session_state.nodes if n["id"]==e["to"]),   None)
            f    = int(result["edge_flows"].get(f"{e['from']}-{e['to']}", 0))
            util = f / e["capacity"] if e["capacity"] > 0 else 0
            pct  = min(int(util*100), 100)
            col  = "#e24a4a" if util>=1 else ("#f5a623" if util>0.7 else "#27ae75" if util>0 else "#2a3d57")
            fr_lbl = f"{TYPE_ICON.get(fr['type'],'')} {fr['label']}" if fr else "?"
            to_lbl = f"{TYPE_ICON.get(to['type'],'')} {to['label']}" if to else "?"
            flow_html += f"""
            <div style="display:flex;align-items:center;gap:12px;padding:6px 0;border-top:1px solid #1e2d45;font-size:11px">
              <span style="flex:1;color:#8fa3c0">{fr_lbl} → {to_lbl}</span>
              <div style="width:120px;background:#1d2640;border-radius:3px;height:5px">
                <div style="width:{pct}%;height:100%;background:{col};border-radius:3px"></div>
              </div>
              <span style="min-width:80px;text-align:right;color:{col}">{f}/{e['capacity']} pkg</span>
            </div>"""

        st.markdown(f"""
        <div class="result-box">
          <div class="result-box-title" style="color:#4a90e2">▸ ROUTE-WISE FLOW BREAKDOWN</div>
          {flow_html}
        </div>""", unsafe_allow_html=True)
