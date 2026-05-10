from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from src.data.duckdb_repo import DuckDBRepo

router = APIRouter()

class WarGameBattle(BaseModel):
    battle_id: str
    scenario_description: str
    simulated_sharpe: float
    max_drawdown: float
    survival_status: str
    evolved_countermeasure: str

class WarGameResponse(BaseModel):
    total_battles_fought: int
    main_swarm_survival_rate: float
    active_nightmare_universes: int
    recent_battles: List[WarGameBattle]

def get_repo() -> DuckDBRepo:
    return DuckDBRepo("storage/db/quant_data.duckdb")

@router.get("/", response_model=WarGameResponse)
def get_war_game_telemetry():
    repo = get_repo()
    
    # 1. Fetch Summary Stats
    stats_df = repo.con.execute("""
        SELECT 
            COUNT(*) as total, 
            SUM(CASE WHEN survival_status = 'SURVIVED' THEN 1 ELSE 0 END) as survived 
        FROM adversarial_wargame_ledger
    """).df()
    
    total_battles = int(stats_df['total'].iloc[0]) if not stats_df.empty else 0
    survived = int(stats_df['survived'].iloc[0]) if not stats_df.empty else 0
    survival_rate = (survived / total_battles * 100) if total_battles > 0 else 0.0

    # 2. Fetch Active Universes
    active_univ_df = repo.con.execute("SELECT COUNT(*) as active FROM synthetic_market_universes WHERE is_active = TRUE").df()
    active_nightmares = int(active_univ_df['active'].iloc[0]) if not active_univ_df.empty else 0

    # 3. Fetch Recent Battles
    battles_df = repo.con.execute("""
        SELECT l.battle_id, u.scenario_description, l.simulated_sharpe, l.max_drawdown, l.survival_status, l.evolved_countermeasure
        FROM adversarial_wargame_ledger l
        JOIN synthetic_market_universes u ON l.universe_id = u.universe_id
        ORDER BY u.generation_date DESC
        LIMIT 10
    """).df()

    recent_battles = []
    for _, row in battles_df.iterrows():
        recent_battles.append(WarGameBattle(
            battle_id=row['battle_id'][:8],
            scenario_description=row['scenario_description'],
            simulated_sharpe=float(row['simulated_sharpe']),
            max_drawdown=float(row['max_drawdown']),
            survival_status=row['survival_status'],
            evolved_countermeasure=row['evolved_countermeasure']
        ))

    return WarGameResponse(
        total_battles_fought=total_battles,
        main_swarm_survival_rate=survival_rate,
        active_nightmare_universes=active_nightmares,
        recent_battles=recent_battles
    )
