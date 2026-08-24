from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.api.dependencies.auth import get_current_user
from app.models.user import User
from knowledge_graph.network_builder import PaymentNetworkGraph
import networkx as nx

router = APIRouter()


@router.get("/neighbors")
def get_graph_neighbors(
    node_id: str,
    node_type: str = "User",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns connected nodes and edge properties for a given network node."""
    graph = PaymentNetworkGraph()
    graph.build_from_db(db)
    
    start_node = f"{node_type}:{node_id}"
    if start_node not in graph.G:
        return {"nodes": [], "edges": []}
        
    # Get neighbors
    neighbors = list(graph.G.neighbors(start_node)) + list(graph.G.predecessors(start_node))
    neighbors = list(set(neighbors)) # unique list
    
    nodes = [{"id": start_node, "label": start_node, "type": node_type}]
    edges = []
    
    for neighbor in neighbors:
        n_type, n_id = neighbor.split(":", 1)
        nodes.append({"id": neighbor, "label": neighbor, "type": n_type})
        
        # Outgoing edges
        if graph.G.has_edge(start_node, neighbor):
            data = graph.G.get_edge_data(start_node, neighbor)
            edges.append({
                "source": start_node,
                "target": neighbor,
                "relation": data.get("relation", "LINK"),
                "weight": data.get("weight", 1.0)
            })
        # Incoming edges
        if graph.G.has_edge(neighbor, start_node):
            data = graph.G.get_edge_data(neighbor, start_node)
            edges.append({
                "source": neighbor,
                "target": start_node,
                "relation": data.get("relation", "LINK"),
                "weight": data.get("weight", 1.0)
            })
            
    return {"nodes": nodes, "edges": edges}


@router.get("/visualize")
def get_graph_visualization(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Exports the entire payment network graph as a list of nodes and edges for front-end rendering."""
    graph = PaymentNetworkGraph()
    graph.build_from_db(db)
    
    nodes = []
    edges = []
    
    for node in graph.G.nodes:
        # Default fallback split if type is missing
        if ":" in node:
            n_type, n_id = node.split(":", 1)
        else:
            n_type, n_id = "Entity", node
        nodes.append({"id": node, "label": n_id, "type": n_type})
        
    for u, v, data in graph.G.edges(data=True):
        edges.append({
            "source": u,
            "target": v,
            "relation": data.get("relation", "LINK"),
            "weight": data.get("weight", 1.0)
        })
        
    return {"nodes": nodes, "edges": edges}
