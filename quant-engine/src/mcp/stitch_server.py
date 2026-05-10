import asyncio
from mcp.server import Server
from mcp.server.models import Tool
from loguru import logger
from ..data.duckdb_repo import DuckDBRepo
from ..derivatives.vol_surface import VolatilitySurfaceMapper
import json

class StitchMCPServer:
    """
    Phase 21.1: The Model Context Protocol Server.
    Unifies the Swarm's disparate databases into semantic tools.
    """
    def __init__(self, db_path: str) -> None:
        self.repo = DuckDBRepo(db_path)
        self.server = Server("quant-swarm-stitch")
        self.mapper = VolatilitySurfaceMapper(self.repo)
        self._register_tools()

    def _register_tools(self) -> None:
        @self.server.tool()
        async def get_volatility_surface(ticker: str) -> str:
            """Fetches the 3D IV matrix for rendering the surface chart."""
            logger.info(f"MCP Tool: get_volatility_surface for {ticker}")
            try:
                expirations, strikes, iv_matrix = self.mapper.generate_surface_matrix(ticker)
                return json.dumps({
                    "ticker": ticker,
                    "expirations": expirations,
                    "strikes": strikes,
                    "iv_matrix": iv_matrix
                })
            except Exception as e:
                return f"Error fetching volatility surface: {str(e)}"

        @self.server.tool()
        async def get_ceo_hesitation(ticker: str) -> str:
            """Fetches the vocal hesitation index (VHI) and audio snippets."""
            logger.info(f"MCP Tool: get_ceo_hesitation for {ticker}")
            try:
                res = self.repo.con.execute("""
                    SELECT hesitation_index, audio_sentiment_score, transcript 
                    FROM audio_perception_ledger 
                    WHERE ticker = ? 
                    ORDER BY date DESC LIMIT 1
                """, [ticker]).fetchone()
                
                if not res:
                    return f"No audio data found for {ticker}."
                
                return json.dumps({
                    "vhi": res[0],
                    "sentiment": res[1],
                    "transcript_snippet": res[2][:500] + "..."
                })
            except Exception as e:
                return f"Error fetching audio perception: {str(e)}"

        @self.server.tool()
        async def get_alpha_signals(ticker: str) -> str:
            """Fetches the latest ML and LLM signals for a ticker."""
            logger.info(f"MCP Tool: get_alpha_signals for {ticker}")
            try:
                res = self.repo.con.execute("""
                    SELECT ml_signal, llm_signal, vibe, final_blended_signal 
                    FROM paper_trades 
                    WHERE ticker = ? 
                    ORDER BY signal_date DESC LIMIT 1
                """, [ticker]).fetchone()
                
                if not res:
                    return f"No active signals for {ticker}."
                
                return json.dumps({
                    "ml": res[0],
                    "llm": res[1],
                    "vibe": res[2],
                    "total": res[3]
                })
            except Exception as e:
                return f"Error fetching alpha signals: {str(e)}"

    async def run(self):
        """Run the server using stdio transport."""
        from mcp.server.stdio import stdio_server
        async with stdio_server() as (read_stream, write_server):
            await self.server.run(read_stream, write_server, self.server.create_initialization_options())

if __name__ == "__main__":
    import os
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(BASE_DIR, "storage", "db", "quant_data.duckdb")
    
    server = StitchMCPServer(db_path)
    asyncio.run(server.run())
