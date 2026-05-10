import json
import uuid
import math
from datetime import datetime
from typing import TypedDict, Annotated, Sequence
import operator
from loguru import logger
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from .personas import get_quant_dev_prompt, get_macro_economist_prompt, get_risk_manager_prompt, get_cio_prompt
from ..data.duckdb_repo import DuckDBRepo

class WarRoomState(TypedDict):
    ticker: str
    data_context: str
    messages: Annotated[Sequence[BaseMessage], operator.add]
    votes: dict
    final_conviction: float
    final_decision: str
    iteration: int

class WarRoomGraph:
    """
    Phase 26: Autonomous War Room using LangGraph.
    Orchestrates a cyclic debate between specialized LLM agents.
    """
    def __init__(self, repo: DuckDBRepo):
        self.repo = repo
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(WarRoomState)
        
        workflow.add_node("Quant_Agent", self.quant_node)
        workflow.add_node("Macro_Agent", self.macro_node)
        workflow.add_node("Risk_Agent", self.risk_node)
        workflow.add_node("Rebuttal", self.rebuttal_node)
        workflow.add_node("CIO_Agent", self.cio_node)
        
        # Parallel evaluation
        workflow.set_entry_point("Quant_Agent")
        workflow.add_edge("Quant_Agent", "Macro_Agent")
        workflow.add_edge("Macro_Agent", "Risk_Agent")
        
        # Risk routes to rebuttal
        workflow.add_edge("Risk_Agent", "Rebuttal")
        
        # Conditional edge after rebuttal
        workflow.add_conditional_edges(
            "Rebuttal",
            self.should_continue,
            {
                "continue": "Quant_Agent",
                "end": "CIO_Agent"
            }
        )
        
        workflow.add_edge("CIO_Agent", END)
        return workflow.compile()

    def _mock_llm_call(self, prompt: str, persona: str) -> str:
        # In production, this would call Hermes LLM or OpenAI
        # For MVP, mock responses based on persona
        if persona == "Quant":
            return "Given the XGBoost momentum and IV skew, I vote STRONG_BUY (1.0)."
        elif persona == "Macro":
            return "VAR models indicate liquidity contraction. I vote HOLD (0.0)."
        elif persona == "Risk":
            return "Tail risk is elevated. Delta is neutral. I vote STRONG_SELL (-1.0)."
        else:
            return "Rebuttal: The macro data is lagging."

    def _extract_vote(self, response: str) -> float:
        # Mock extraction of V_p from text
        if "STRONG_BUY" in response: return 1.0
        if "HOLD" in response: return 0.0
        if "STRONG_SELL" in response: return -1.0
        return 0.0

    def quant_node(self, state: WarRoomState):
        logger.info(f"War Room: Quant Agent analyzing {state['ticker']}")
        response = self._mock_llm_call(state['data_context'], "Quant")
        vote = self._extract_vote(response)
        
        votes = state.get("votes", {})
        votes["QUANT_DEV"] = vote
        
        return {
            "messages": [AIMessage(content=f"[Quant Dev]: {response}")],
            "votes": votes
        }

    def macro_node(self, state: WarRoomState):
        logger.info(f"War Room: Macro Economist analyzing {state['ticker']}")
        response = self._mock_llm_call(state['data_context'], "Macro")
        vote = self._extract_vote(response)
        
        votes = state.get("votes", {})
        votes["MACRO_ECONOMIST"] = vote
        
        return {
            "messages": [AIMessage(content=f"[Macro Economist]: {response}")],
            "votes": votes
        }

    def risk_node(self, state: WarRoomState):
        logger.info(f"War Room: Risk Manager analyzing {state['ticker']}")
        response = self._mock_llm_call(state['data_context'], "Risk")
        vote = self._extract_vote(response)
        
        votes = state.get("votes", {})
        votes["RISK_MANAGER"] = vote
        
        return {
            "messages": [AIMessage(content=f"[Risk Manager]: {response}")],
            "votes": votes,
            "iteration": state.get("iteration", 0) + 1
        }

    def rebuttal_node(self, state: WarRoomState):
        logger.info(f"War Room: Rebuttal Phase Round {state['iteration']}")
        response = self._mock_llm_call("Rebuttal", "Rebuttal")
        return {
            "messages": [AIMessage(content=f"[Rebuttal]: {response}")]
        }

    def should_continue(self, state: WarRoomState):
        if state.get("iteration", 0) >= 1: # Strict cycle cap
            return "end"
        return "continue"

    def cio_node(self, state: WarRoomState):
        logger.info("War Room: CIO Synthesizing final verdict.")
        
        # 1. Fetch Historical Accuracy
        # In prod, query persona_track_records
        accuracies = {
            "QUANT_DEV": 0.2, # Low accuracy
            "MACRO_ECONOMIST": 0.9, # High accuracy
            "RISK_MANAGER": 0.5
        }
        
        # 2. Accuracy-Weighted Conviction Scoring (Softmax)
        votes = state.get("votes", {})
        exp_sum = sum([math.exp(a) for a in accuracies.values()])
        weights = {p: math.exp(a)/exp_sum for p, a in accuracies.items()}
        
        c_final = 0.0
        for p, vote in votes.items():
            if p in weights:
                c_final += weights[p] * vote
                
        decision = "HOLD"
        if c_final > 0.3: decision = "STRONG_BUY"
        elif c_final < -0.3: decision = "STRONG_SELL"
        
        # Veto Rule
        if c_final < -0.5:
            decision = "VETO"

        # 3. Save to DB
        debate_id = str(uuid.uuid4())
        transcript = [{"role": type(m).__name__, "content": m.content} for m in state["messages"]]
        
        self.repo.con.execute("""
            INSERT OR REPLACE INTO war_room_transcripts 
            (debate_id, ticker, date, transcript, final_decision, blended_conviction, cio_summary)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [debate_id, state['ticker'], datetime.now().date(), json.dumps(transcript), decision, c_final, "Calculated via Accuracy-Weighted Voting"])
        
        return {
            "final_conviction": c_final,
            "final_decision": decision,
            "messages": [AIMessage(content=f"[CIO]: Final Decision: {decision} (Conviction: {c_final:.2f})")]
        }

    def run_debate(self, ticker: str, data_context: str) -> dict:
        initial_state = {
            "ticker": ticker,
            "data_context": data_context,
            "messages": [HumanMessage(content=f"Initiating debate for {ticker}. Please review data: {data_context}")],
            "votes": {},
            "final_conviction": 0.0,
            "final_decision": "",
            "iteration": 0
        }
        final_state = self.graph.invoke(initial_state)
        return final_state
