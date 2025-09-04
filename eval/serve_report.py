#!/usr/bin/env python3
"""
Alice v2 Eval Trend Dashboard Generator
Creates HTML dashboard with Plotly trend charts
"""

import glob
import json
import os
from datetime import datetime
from typing import Any, Dict, List

import plotly.graph_objects as go
from plotly.subplots import make_subplots


class TrendDashboard:
    def __init__(self, eval_runs_dir: str = "eval_runs"):
        self.eval_runs_dir = eval_runs_dir
        self.reports = []

    def load_reports(self) -> List[Dict[str, Any]]:
        """Load all evaluation reports from eval_runs directory"""
        if not os.path.exists(self.eval_runs_dir):
            print(f"⚠️  Eval runs directory not found: {self.eval_runs_dir}")
            return []

        # Find all JSON reports
        json_files = glob.glob(os.path.join(self.eval_runs_dir, "*.json"))

        reports = []
        for json_file in json_files:
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    report = json.load(f)
                    reports.append(report)
            except Exception as e:
                print(f"⚠️  Error loading {json_file}: {e}")

        # Sort by timestamp
        reports.sort(key=lambda x: x.get("timestamp", ""))

        print(f"📊 Loaded {len(reports)} evaluation reports")
        return reports

    def create_trend_charts(self, reports: List[Dict[str, Any]]) -> go.Figure:
        """Create trend charts for key metrics"""
        if not reports:
            # Create empty figure if no reports
            fig = go.Figure()
            fig.add_annotation(
                text="No evaluation reports found",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=20),
            )
            return fig

        # Extract data for charts
        timestamps = []
        easy_schema_ok = []
        medium_schema_ok = []
        hard_schema_ok = []
        tool_precision = []
        latency_p95 = []
        success_rate = []

        for report in reports:
            metrics = report.get("metrics", {})
            timestamp = report.get("timestamp", "")

            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    timestamps.append(dt)

                    easy_schema_ok.append(
                        metrics.get("easy.schema_ok_first", 0.0) * 100
                    )
                    medium_schema_ok.append(
                        metrics.get("medium.schema_ok_first", 0.0) * 100
                    )
                    hard_schema_ok.append(
                        metrics.get("hard.schema_ok_first", 0.0) * 100
                    )
                    tool_precision.append(metrics.get("tool_precision", 0.0) * 100)
                    latency_p95.append(metrics.get("latency_p95_ms", 0))
                    success_rate.append(metrics.get("success_rate", 0.0) * 100)
                except Exception as e:
                    print(f"⚠️  Error parsing timestamp {timestamp}: {e}")

        # Create subplots
        fig = make_subplots(
            rows=3,
            cols=2,
            subplot_titles=(
                "Schema OK Rate (EASY)",
                "Schema OK Rate (MEDIUM)",
                "Schema OK Rate (HARD)",
                "Tool Precision",
                "Latency P95 (ms)",
                "Success Rate",
            ),
            specs=[
                [{"secondary_y": False}, {"secondary_y": False}],
                [{"secondary_y": False}, {"secondary_y": False}],
                [{"secondary_y": False}, {"secondary_y": False}],
            ],
        )

        # Add traces
        if timestamps:
            # Schema OK rates
            fig.add_trace(
                go.Scatter(
                    x=timestamps,
                    y=easy_schema_ok,
                    name="EASY",
                    line=dict(color="green"),
                ),
                row=1,
                col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=timestamps,
                    y=medium_schema_ok,
                    name="MEDIUM",
                    line=dict(color="orange"),
                ),
                row=1,
                col=2,
            )
            fig.add_trace(
                go.Scatter(
                    x=timestamps, y=hard_schema_ok, name="HARD", line=dict(color="red")
                ),
                row=2,
                col=1,
            )

            # Tool precision
            fig.add_trace(
                go.Scatter(
                    x=timestamps,
                    y=tool_precision,
                    name="Tool Precision",
                    line=dict(color="blue"),
                ),
                row=2,
                col=2,
            )

            # Latency P95
            fig.add_trace(
                go.Scatter(
                    x=timestamps,
                    y=latency_p95,
                    name="Latency P95",
                    line=dict(color="purple"),
                ),
                row=3,
                col=1,
            )

            # Success rate
            fig.add_trace(
                go.Scatter(
                    x=timestamps,
                    y=success_rate,
                    name="Success Rate",
                    line=dict(color="brown"),
                ),
                row=3,
                col=2,
            )

        # Update layout
        fig.update_layout(
            title="Alice v2 Evaluation Trends",
            height=900,
            showlegend=True,
            template="plotly_white",
        )

        # Add threshold lines
        for i in range(1, 4):
            for j in range(1, 3):
                fig.add_hline(
                    y=95,
                    line_dash="dash",
                    line_color="red",
                    annotation_text="95% threshold",
                    row=i,
                    col=j,
                )

        return fig

    def create_summary_table(self, reports: List[Dict[str, Any]]) -> str:
        """Create HTML summary table"""
        if not reports:
            return "<p>No evaluation reports available</p>"

        # Get latest report
        latest = reports[-1]
        metrics = latest.get("metrics", {})

        html = """
        <div class="summary-table">
            <h3>Latest Evaluation Summary</h3>
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <tr style="background-color: #f5f5f5;">
                    <th style="padding: 10px; border: 1px solid #ddd;">Metric</th>
                    <th style="padding: 10px; border: 1px solid #ddd;">Value</th>
                    <th style="padding: 10px; border: 1px solid #ddd;">Status</th>
                </tr>
        """

        # EASY schema_ok
        easy_ok = metrics.get("easy.schema_ok_first", 0.0) * 100
        html += f"""
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">EASY schema_ok@first</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{easy_ok:.1f}%</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{'✅ PASS' if easy_ok >= 95 else '❌ FAIL'}</td>
                </tr>
        """

        # MEDIUM schema_ok
        medium_ok = metrics.get("medium.schema_ok_first", 0.0) * 100
        html += f"""
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">MEDIUM schema_ok@first</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{medium_ok:.1f}%</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{'✅ PASS' if medium_ok >= 95 else '❌ FAIL'}</td>
                </tr>
        """

        # Tool precision
        tool_prec = metrics.get("tool_precision", 0.0) * 100
        html += f"""
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Tool precision</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{tool_prec:.1f}%</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{'✅ PASS' if tool_prec >= 85 else '❌ FAIL'}</td>
                </tr>
        """

        # Latency P95
        latency = metrics.get("latency_p95_ms", 0)
        html += f"""
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Latency P95</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{latency:.0f}ms</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{'✅ PASS' if latency <= 900 else '❌ FAIL'}</td>
                </tr>
        """

        html += """
            </table>
        </div>
        """

        return html

    def generate_html(
        self, reports: List[Dict[str, Any]], output_file: str = "eval/index.html"
    ):
        """Generate complete HTML dashboard"""
        # Create charts
        fig = self.create_trend_charts(reports)

        # Create summary table
        summary_table = self.create_summary_table(reports)

        # Generate HTML
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Alice v2 Evaluation Dashboard</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f8f9fa;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background-color: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                h1 {{
                    color: #333;
                    text-align: center;
                    margin-bottom: 30px;
                }}
                .summary-table {{
                    margin: 20px 0;
                }}
                .summary-table h3 {{
                    color: #555;
                    margin-bottom: 15px;
                }}
                .summary-table table {{
                    width: 100%;
                    border-collapse: collapse;
                }}
                .summary-table th, .summary-table td {{
                    padding: 12px;
                    text-align: left;
                    border: 1px solid #ddd;
                }}
                .summary-table th {{
                    background-color: #f5f5f5;
                    font-weight: bold;
                }}
                .chart-container {{
                    margin: 30px 0;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 40px;
                    color: #666;
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 Alice v2 Evaluation Dashboard</h1>
                
                {summary_table}
                
                <div class="chart-container">
                    <div id="trend-charts"></div>
                </div>
                
                <div class="footer">
                    <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p>Total reports: {len(reports)}</p>
                </div>
            </div>
            
            <script>
                {fig.to_json()}
                Plotly.newPlot('trend-charts', fig.data, fig.layout);
            </script>
        </body>
        </html>
        """

        # Create output directory
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        # Write HTML file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"📊 Dashboard generated: {output_file}")


def main():
    """Main dashboard generation function"""
    import argparse

    parser = argparse.ArgumentParser(description="Alice v2 Trend Dashboard Generator")
    parser.add_argument(
        "--eval-runs-dir", default="eval_runs", help="Directory with evaluation reports"
    )
    parser.add_argument("--output", default="eval/index.html", help="Output HTML file")

    args = parser.parse_args()

    try:
        # Create dashboard generator
        dashboard = TrendDashboard(eval_runs_dir=args.eval_runs_dir)

        # Load reports
        reports = dashboard.load_reports()

        # Generate dashboard
        dashboard.generate_html(reports, args.output)

        print("✅ Dashboard generation completed!")

    except Exception as e:
        print(f"❌ Dashboard generation failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
