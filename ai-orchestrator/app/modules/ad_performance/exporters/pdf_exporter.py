"""
PDF exporter for ad performance reports.
"""

import io
from datetime import date
from typing import Any
import structlog

logger = structlog.get_logger(__name__)


class PDFExporter:
    """Export ad performance data to PDF format with charts."""

    def __init__(self):
        """Initialize PDF exporter."""
        self._reportlab_available = False
        self._matplotlib_available = False
        self._check_dependencies()

    def _check_dependencies(self):
        """Check if required dependencies are available."""
        try:
            import reportlab  # noqa: F401
            self._reportlab_available = True
        except ImportError:
            logger.warning("reportlab not available, PDF export will be limited")

        try:
            import matplotlib  # noqa: F401
            self._matplotlib_available = True
        except ImportError:
            logger.warning("matplotlib not available, charts will not be included")

    async def export(
        self,
        data: dict[str, Any],
        file_name: str | None = None,
        include_charts: bool = True,
    ) -> str:
        """
        Export report data to PDF format.

        Args:
            data: Dictionary containing report data with structure:
                  {
                      "date": str,
                      "summary": {
                          "total_spend": float,
                          "total_revenue": float,
                          "overall_roas": float,
                          "total_conversions": int,
                          "avg_cpa": float
                      },
                      "ai_analysis": {
                          "key_insights": [str, ...],
                          "trends": {"roas_trend": str, ...}
                      },
                      "metrics": [...],  # Optional for charts
                      "recommendations": [...]  # Optional
                  }
            file_name: Optional file name (without extension)
            include_charts: Whether to include charts in the PDF

        Returns:
            Path to the generated PDF file

        Raises:
            ValueError: If data is invalid or missing required fields
            ImportError: If reportlab is not available
        """
        log = logger.bind(file_name=file_name, include_charts=include_charts)
        log.info("pdf_export_start")

        # Validate input data
        self._validate_data(data)

        # Generate file name if not provided
        if file_name is None:
            report_date = data.get("date", date.today().isoformat())
            file_name = f"ad_performance_report_{report_date}"

        # Ensure file name doesn't have extension
        if file_name.endswith(".pdf"):
            file_name = file_name[:-4]

        file_path = f"/tmp/{file_name}.pdf"

      