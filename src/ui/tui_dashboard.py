from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, Input
from textual.containers import Vertical
from ..data.duckdb_repo import DuckDBRepo

class QuantDashboardApp(App):
    """A Textual TUI for monitoring the Quant Engine."""

    CSS = """
    DataTable {
        height: 100%;
        border: solid green;
    }
    Input {
        dock: top;
        margin: 1 0;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh Data")
    ]

    def __init__(self, db_path: str = "storage/db/quant_data.duckdb"):
        super().__init__()
        self.db_path = db_path
        self.full_data = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Footer()
        with Vertical():
            yield Input(placeholder="Search ticker or vibe...", id="search")
            yield DataTable(id="trades_table")

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        self.action_refresh()

    def action_refresh(self) -> None:
        """Fetches data from DuckDB and populates the table."""
        table = self.query_one(DataTable)
        table.clear(columns=True)

        columns = [
            "Trade ID", "Ticker", "Date", "ML Signal", "LLM Signal",
            "Blended", "Dir", "Vibe", "Size", "Status"
        ]
        table.add_columns(*columns)

        try:
            with DuckDBRepo(self.db_path) as repo:
                res = repo.con.execute("SELECT count(*) FROM information_schema.tables WHERE table_name='paper_trades'").fetchone()
                if res and res[0] > 0:
                    df = repo.con.execute("""
                        SELECT
                            substr(CAST(trade_id AS VARCHAR), 1, 8) as trade_id,
                            ticker,
                            signal_date,
                            round(ml_signal, 3) as ml_signal,
                            round(llm_signal, 3) as llm_signal,
                            round(final_blended_signal, 3) as blended,
                            final_direction,
                            vibe,
                            round(position_size, 2) as size,
                            status
                        FROM paper_trades
                        ORDER BY signal_date DESC
                        LIMIT 100
                    """).df()

                    self.full_data = df.to_dict('records')
                    self._populate_table(self.full_data)
                else:
                    self.full_data = []
                    table.add_row(*(["No data or table missing"] * len(columns)))

        except Exception as e:
            table.add_row(*([f"Error: {str(e)}"] * len(columns)))

    def _populate_table(self, data: list[dict]):
        table = self.query_one(DataTable)
        table.clear()
        for row in data:
            table.add_row(
                str(row.get('trade_id', '')),
                str(row.get('ticker', '')),
                str(row.get('signal_date', '')),
                str(row.get('ml_signal', '')),
                str(row.get('llm_signal', '')),
                str(row.get('blended', '')),
                str(row.get('final_direction', '')),
                str(row.get('vibe', '')),
                str(row.get('size', '')),
                str(row.get('status', ''))
            )

    def on_input_changed(self, event: Input.Changed) -> None:
        """Filter the table based on search input."""
        search_term = event.value.lower()
        if not search_term:
            self._populate_table(self.full_data)
            return

        filtered_data = [
            row for row in self.full_data
            if search_term in str(row.get('ticker', '')).lower()
            or search_term in str(row.get('vibe', '')).lower()
        ]
        self._populate_table(filtered_data)

if __name__ == "__main__":
    app = QuantDashboardApp()
    app.run()
