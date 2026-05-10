import flwr as fl
from typing import Dict, List, Tuple, Optional
from flwr.common import Metrics, EvaluateRes, FitRes
from loguru import logger
import time
from datetime import datetime
from ..data.duckdb_repo import DuckDBRepo

class SwarmFedAvg(fl.server.strategy.FedAvg):
    """
    Phase 19.1: Custom Federated Averaging Strategy.
    Overrides standard FedAvg to interact with the Swarm's DuckDB and models.
    """
    def __init__(self, repo: DuckDBRepo, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.repo = repo
        self.round_id = int(time.time())

    def aggregate_fit(
        self,
        server_round: int,
        results: List[Tuple[fl.server.client_proxy.ClientProxy, FitRes]],
        failures: List[BaseException],
    ) -> Tuple[Optional[fl.common.Parameters], Dict[str, fl.common.Scalar]]:
        logger.info(f"Aggregating fit results for round {server_round} from {len(results)} nodes.")
        
        aggregated_parameters, aggregated_metrics = super().aggregate_fit(server_round, results, failures)
        
        if aggregated_parameters is not None:
            # Conceptually calculate loss before/after or mock for MVP
            self.repo.con.execute("""
                INSERT INTO training_rounds_ledger 
                (round_id, start_time, end_time, nodes_participated, global_model_loss_before, global_model_loss_after)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [self.round_id + server_round, datetime.now(), datetime.now(), len(results), 0.5, 0.45])
            
            # Log contribution scores
            for client_proxy, fit_res in results:
                node_id = fit_res.metrics.get("node_id", "unknown")
                # Basic mockup of contribution score
                score = fit_res.num_examples * 0.01 
                
                self.repo.con.execute("""
                    INSERT OR REPLACE INTO federated_nodes_ledger 
                    (node_id, client_user_id, ip_address, status, total_training_rounds, alpha_contribution_score, last_ping)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, [node_id, "b2b_client", "192.168.1.1", "TRAINING", 1, score, datetime.now()])
        
        return aggregated_parameters, aggregated_metrics

class AggregationServer:
    def __init__(self, repo: DuckDBRepo):
        self.repo = repo
        self.strategy = SwarmFedAvg(
            repo=self.repo,
            fraction_fit=1.0,
            fraction_evaluate=0.5,
            min_fit_clients=2,
            min_evaluate_clients=2,
            min_available_clients=2,
        )

    def start(self, server_address: str = "0.0.0.0:8080"):
        logger.info(f"Starting Aggregation Server on {server_address}...")
        fl.server.start_server(
            server_address=server_address,
            config=fl.server.ServerConfig(num_rounds=3),
            strategy=self.strategy,
        )

if __name__ == "__main__":
    repo = DuckDBRepo("storage/db/quant_data.duckdb")
    server = AggregationServer(repo)
    server.start()
