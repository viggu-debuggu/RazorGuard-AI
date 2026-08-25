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
        Walks the graph to find relational overlaps:
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

        # Find devices associated with the start user
        # User -> Transaction -> Device
        user_txs = [t for s, t, data in self.G.out_edges(start, data=True) if data.get("relation") == "INITIATED"]
        
        devices: Set[str] = set()
        ips: Set[str] = set()
        
        for tx in user_txs:
            for _, tgt, data in self.G.out_edges(tx, data=True):
                if data.get("relation") == "FROM_DEVICE":
                    devices.add(tgt)
                elif data.get("relation") == "FROM_IP":
                    ips.add(tgt)

        # Tracing device overlap (via transaction relationships)
        for dev in devices:
            # Device <- Transaction (incoming edge)
            in_edges = self.G.in_edges(dev, data=True)
            for src_tx, _, data in in_edges:
                if data.get("relation") == "FROM_DEVICE":
                    # Transaction <- User (incoming edge)
                    tx_in_edges = self.G.in_edges(src_tx, data=True)
                    for other_user, _, tx_data in tx_in_edges:
                        if tx_data.get("relation") == "INITIATED" and other_user != start:
                            shared_users.add(other_user)
                            shared_entities.append(f"Device overlapping: {dev.split(':', 1)[1]} shared with {other_user.split(':', 1)[1]}")
                            paths_evidence.append({
                                "type": "Device Overlap",
                                "node": dev,
                                "linked_account": other_user
                            })

        # Tracing IP overlap
        for ip in ips:
            in_edges = self.G.in_edges(ip, data=True)
            for src_tx, _, data in in_edges:
                if data.get("relation") == "FROM_IP":
                    tx_in_edges = self.G.in_edges(src_tx, data=True)
                    for other_user, _, tx_data in tx_in_edges:
                        if tx_data.get("relation") == "INITIATED" and other_user != start:
                            shared_users.add(other_user)
                            shared_entities.append(f"IP overlapping: {ip.split(':', 1)[1]} shared with {other_user.split(':', 1)[1]}")
                            paths_evidence.append({
                                "type": "IP Overlap",
                                "node": ip,
                                "linked_account": other_user
                            })

        return len(shared_users), shared_entities, paths_evidence
