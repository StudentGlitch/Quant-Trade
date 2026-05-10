import os
from pathlib import Path
from datetime import datetime
from loguru import logger
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from ..data.duckdb_repo import DuckDBRepo

class PitchBookGenerator:
    """
    Phase 30.2: Automated Pitch Book Compiler.
    Generates PDF marketing materials for institutional LPs.
    """
    def __init__(self, repo: DuckDBRepo, workspace_root: str):
        self.repo = repo
        self.workspace_root = Path(workspace_root)
        self.output_dir = self.workspace_root / "storage" / "artifacts" / "pitch_books"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.styles = getSampleStyleSheet()
        self.styles.add(ParagraphStyle(name='FundTitle', fontSize=24, leading=30, spaceAfter=20, alignment=1, textColor=colors.HexColor('#1e3a8a')))
        self.styles.add(ParagraphStyle(name='SectionHeader', fontSize=18, leading=22, spaceBefore=15, spaceAfter=10, textColor=colors.HexColor('#1f2937')))
        self.styles.add(ParagraphStyle(name='BodyText', fontSize=10, leading=14, spaceAfter=8))

    def generate_monthly_pitchbook(self) -> str:
        """Compiles the full 4-page PDF Pitch Book."""
        file_name = f"Darwinian_Swarm_TearSheet_{datetime.now().strftime('%Y_%m')}.pdf"
        output_path = self.output_dir / file_name
        
        logger.info(f"Generating Institutional Pitch Book: {output_path}")
        
        doc = SimpleDocTemplate(str(output_path), pagesize=letter)
        story = []

        # Cover Page
        story.append(Paragraph("Darwinian Quant Swarm", self.styles['FundTitle']))
        story.append(Paragraph("Apex Sentience: Autonomous Multi-Modal Macro Fund", self.styles['Heading2']))
        story.append(Spacer(1, 50))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y')}", self.styles['Normal']))
        story.append(PageBreak())

        # Page 1: Executive Summary
        story.append(Paragraph("Executive Summary & Performance", self.styles['SectionHeader']))
        story.append(Paragraph("The Darwinian Quant Swarm is a fully autonomous, self-healing quantitative hedge fund. It utilizes federated learning, econometric forecasting, and multi-modal perception to execute delta-neutral options arbitrage and global macro directional trades.", self.styles['BodyText']))
        
        # Mock Performance Data Table
        perf_data = [
            ['Metric', 'Swarm Portfolio', 'IHSG Benchmark'],
            ['1Y Return', '+42.5%', '+8.2%'],
            ['Sharpe Ratio', '2.85', '0.65'],
            ['Max Drawdown', '-4.2%', '-12.5%'],
            ['Beta', '0.15', '1.0']
        ]
        t = Table(perf_data, colWidths=[150, 100, 100])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f3f4f6')),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(Spacer(1, 20))
        story.append(t)
        story.append(PageBreak())

        # Page 2 & 3: Methodology and Risk (Placeholders for brevity)
        story.append(Paragraph("Swarm Methodology & Risk Governance", self.styles['SectionHeader']))
        story.append(Paragraph("Our proprietary LangGraph-based 'Autonomous War Room' forces adversarial debate among specialized LLM personas before any capital is committed. Risk limits are strictly enforced via 99% CVaR boundaries.", self.styles['BodyText']))
        story.append(PageBreak())
        
        # Page 4: Live Trade Examples
        story.append(Paragraph("Autonomous War Room: Live Trade Examples", self.styles['SectionHeader']))
        
        try:
            recent_trades = self.repo.con.execute("""
                SELECT ticker, final_decision, blended_conviction 
                FROM war_room_transcripts 
                ORDER BY date DESC LIMIT 3
            """).df()
            
            for _, row in recent_trades.iterrows():
                trade_text = f"<b>{row['ticker']}</b>: Executed <b>{row['final_decision']}</b> with conviction score {row['blended_conviction']:.2f}."
                story.append(Paragraph(trade_text, self.styles['BodyText']))
                story.append(Spacer(1, 10))
        except Exception as e:
            logger.warning(f"Could not fetch trade examples for pitch book: {e}")

        # Build PDF
        try:
            doc.build(story)
            logger.success(f"Pitch Book successfully generated at {output_path}")
            return str(output_path)
        except Exception as e:
            logger.error(f"Failed to build PDF: {e}")
            return ""

if __name__ == "__main__":
    repo = DuckDBRepo("storage/db/quant_data.duckdb")
    generator = PitchBookGenerator(repo, os.getcwd())
    generator.generate_monthly_pitchbook()
