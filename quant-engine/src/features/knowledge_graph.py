import pandas as pd
import numpy as np
import networkx as nx
from loguru import logger
from ..data.duckdb_repo import DuckDBRepo

class KnowledgeGraph:
    """
    Phase 7.2: Supply Chain Knowledge Graph.
    Calculates Spillover Sentiment using PageRank-variant (PRD 7.1).
    """
    
    def __init__(self, repo: DuckDBRepo):
        self.repo = repo
        self.graph = nx.DiGraph()

    def build_graph(self):
        """Construct the NetworkX graph from DB edges."""
        logger.info("Building Supply Chain Knowledge Graph...")
        
        try:
            edges_df = self.repo.execute("SELECT source_ticker, target_ticker, relationship_type, weight FROM supply_chain_edges").df()
            
            self.graph.clear()
            for _, row in edges_df.iterrows():
                self.graph.add_edge(
                    row['source_ticker'], 
                    row['target_ticker'], 
                    type=row['relationship_type'], 
                    weight=row['weight']
                )
            
            logger.info(f"Graph built with {self.graph.number_of_nodes()} nodes and {self.graph.number_of_edges()} edges.")
        except Exception as e:
            logger.error(f"Failed to build graph: {e}")

    def calculate_spillover(self, gamma: float = 0.85) -> pd.Series:
        """
        Calculate Spillover Sentiment (PRD 7.1).
        S_tilde = S_i + gamma * sum(W_ji * S_j)
        """
        logger.info("Propagating Graph Alpha Shocks...")
        
        # 1. Fetch latest sentiment scores (Intrinsic Sentiment)
        sentiment_df = self.repo.execute("""
            SELECT ticker, sentiment_score 
            FROM nlp_sentiment_ledger 
            WHERE date = (SELECT MAX(date) FROM nlp_sentiment_ledger)
        """).df()
        
        if sentiment_df.empty:
            logger.warning("No recent sentiment found for spillover calculation.")
            return pd.Series(dtype=float)

        intrinsic_s = dict(zip(sentiment_df['ticker'], sentiment_df['sentiment_score']))
        
        spillover_scores = {}
        
        for node in self.graph.nodes():
            s_i = intrinsic_s.get(node, 0.0)
            
            # Sum influence from neighbors (Predecessors in DiGraph represent suppliers/upstream)
            neighbor_influence = 0.0
            for neighbor in self.graph.predecessors(node):
                w_ji = self.graph[neighbor][node].get('weight', 1.0)
                s_j = intrinsic_s.get(neighbor, 0.0)
                neighbor_influence += w_ji * s_j
                
            spillover_scores[node] = s_i + (gamma * neighbor_influence)
            
        return pd.Series(spillover_scores)

    def get_graph_data(self) -> dict:
        """Serialize for frontend KnowledgeGraphResponse."""
        nodes = []
        # Get sector info for grouping
        metadata = self.repo.execute("SELECT ticker, sector FROM idx_metadata").df()
        sectors = dict(zip(metadata['ticker'], metadata['sector']))
        
        # Get 30d sentiment for coloring
        sent_30d = self.repo.execute("""
            SELECT ticker, AVG(sentiment_score) as avg_s 
            FROM nlp_sentiment_ledger 
            GROUP BY ticker
        """).df()
        sent_map = dict(zip(sent_30d['ticker'], sent_30d['avg_s']))

        for node in self.graph.nodes():
            nodes.append({
                "id": node,
                "group": sectors.get(node, 'UNKNOWN'),
                "sentiment_30d": float(sent_map.get(node, 0.0))
            })
            
        links = []
        for u, v, d in self.graph.edges(data=True):
            links.append({
                "source": u,
                "target": v,
                "type": d.get('type', 'UNKNOWN'),
                "value": float(d.get('weight', 1.0))
            })
            
        return {"nodes": nodes, "links": links}
