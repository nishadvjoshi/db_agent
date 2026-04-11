import networkx as nx
from app.catalog_store import CatalogStore
from app.config import settings

def build_graph(run_id: str) -> nx.DiGraph:
    store = CatalogStore()
    con = store._conn()
    cur = con.cursor()
    g = nx.DiGraph()
    try:
        cur.execute(
            """SELECT schema_name, table_name, column_name,
                      ref_schema_name, ref_table_name, ref_column_name
               FROM `foreign_keys` WHERE run_id=%s""",
            (run_id,),
        )
        fks = cur.fetchall()
        for s, t, c, rs, rt, rc in fks:
            src = f"{s}.{t}"
            dst = f"{rs}.{rt}"
            g.add_node(src)
            g.add_node(dst)
            g.add_edge(src, dst, src_col=c, dst_col=rc)
    finally:
        cur.close()
        con.close()
    return g

def shortest_join_path(g: nx.DiGraph, start: str, end: str):
    try:
        path = nx.shortest_path(g, start, end)
        edges = []
        for i in range(len(path) - 1):
            data = g.get_edge_data(path[i], path[i + 1])
            edges.append((path[i], path[i + 1], data))
        return path, edges
    except Exception:
        return None, []
