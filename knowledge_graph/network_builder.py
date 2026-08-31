import networkx as nx
from typing import List, Dict, Any, Set, Tuple
from sqlalchemy.orm import Session
from app.models.graph import GraphEdge
from app.models.transaction import Transaction

class PaymentNetworkGraph:
    """NetworkX graph wrapper to build, update, and traverse the payment relationship network."""
    
    def __init__(self):
        self.G = nx.DiGraph()

    def build_from_db(self, db: Session) -> None:
        """Loads all relational edges from the database into the NetworkX graph."""
        self.G.clear()
        edges = db.query(GraphEdge).all()
        for edge in edges:
            source = f"{edge.source_type}:{edge.source_id}"
            target = f"{edge.target_type}:{edge.target_id}"
            self.G.add_edge(source, target, relation=edge.relation, weight=edge.weight)

    def add_transaction_nodes_and_edges(self, tx: Transaction) -> List[Dict[str, Any]]:
        """
        Dynamically registers transaction relations into the graph.
        Returns: List of dictionary representations of GraphEdge configurations to insert into SQL.
        """
        tx_node = f"Transaction:{tx.transaction_id}"
        user_node = f"User:{tx.user_id}"
        device_node = f"Device:{tx.device_fingerprint}"
        ip_node = f"IP:{tx.ip_address}"
        card_node = f"Card:{tx.billing_country}_{tx.card_country}" # generic card representation for privacy
        merchant_node = f"Merchant:{tx.merchant_id}"

        # Define edges to build
        raw_edges = [
            (user_node, tx_node, "INITIATED"),
            (tx_node, device_node, "FROM_DEVICE"),
            (tx_node, ip_node, "FROM_IP"),
            (tx_node, merchant_node, "TO_MERCHANT"),
            (tx_node, card_node, "USED_CARD"),
        ]

        sql_edges_payload = []
        for src, tgt, rel in raw_edges:
            self.G.add_edge(src, tgt, relation=rel, weight=1.0)
            
            # Parse types and IDs back for the SQL GraphEdge representation
            src_type, src_id = src.split(":", 1)
            tgt_type, tgt_id = tgt.split(":", 1)
            
            sql_edges_payload.append({
                "source_type": src_type,
                "source_id": src_id,
                "relation": rel,
                "target_type": tgt_type,
                "target_id": tgt_id,
                "weight": 1.0
            })
            
        return sql_edges_payload

    def walk_shared_relationships(self, start_node_id: str, start_node_type: str = "User") -> Tuple[int, List[str], List[Dict[str, Any]]]:
        """
        Walks the graph to find relational overlaps using a cycle-safe, hop-limited BFS traversal:
        1. Device sharing: Distinct accounts sharing hardware.
        2. IP sharing: Distinct accounts sharing IP addresses.
        Returns: Tuple of (degrees_of_sharing: int, shared_entities: list[str], paths: list[dict])
        """
        start = f"{start_node_type}:{start_node_id}"
        if start not in self.G:
            return 0, [], []

        shared_users: Set[str] = set()
        shared_entities: List[str] = []
        paths_evidence: List[Dict[str, Any]] = []

        # BFS queue elements: (current_node, path_history)
        # Hop limit: max 4 hops (User -> Tx -> Dev/IP -> Tx -> User)
        queue = [(start, [start])]
        
        while queue:
            node, path = queue.pop(0)
            hops = len(path) - 1
            
            # Stop if we exceeded the 4-hop limit
            if hops >= 4:
                continue
                
            # Hop 1: User -> Transaction (outgoing edge, relation INITIATED)
            if hops == 0:
                for _, target, data in self.G.out_edges(node, data=True):
                    if data.get("relation") == "INITIATED" and target not in path:
                        queue.append((target, path + [target]))
                        
            # Hop 2: Transaction -> Device / IP (outgoing edge, relation FROM_DEVICE / FROM_IP)
            elif hops == 1:
                for _, target, data in self.G.out_edges(node, data=True):
                    rel = data.get("relation")
                    if rel in ["FROM_DEVICE", "FROM_IP"] and target not in path:
                        queue.append((target, path + [target]))
                        
            # Hop 3: Device / IP -> Transaction (incoming edge to Device / IP, relation FROM_DEVICE / FROM_IP)
            elif hops == 2:
                for src, _, data in self.G.in_edges(node, data=True):
                    rel = data.get("relation")
                    is_valid = False
                    if "Device:" in node and rel == "FROM_DEVICE":
                        is_valid = True
                    elif "IP:" in node and rel == "FROM_IP":
                        is_valid = True
                        
                    if is_valid and src not in path:
                        queue.append((src, path + [src]))
                        
            # Hop 4: Transaction -> other User (incoming edge to Transaction, relation INITIATED)
            elif hops == 3:
                for src, _, data in self.G.in_edges(node, data=True):
                    if data.get("relation") == "INITIATED":
                        other_user = src
                        if other_user != start:
                            shared_users.add(other_user)
                            matched_entity = path[2]
                            entity_name = matched_entity.split(":", 1)[1]
                            entity_type = "Device" if "Device:" in matched_entity else "IP"
                            
                            log_msg = f"{entity_type} overlapping: {entity_name} shared with {other_user.split(':', 1)[1]}"
                            if log_msg not in shared_entities:
                                shared_entities.append(log_msg)
                                
                            paths_evidence.append({
                                "type": f"{entity_type} Overlap",
                                "node": matched_entity,
                                "linked_account": other_user
                            })

        return len(shared_users), shared_entities, paths_evidence

