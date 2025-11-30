"""
CSV exporter for ad performance reports.
"""

import pandas as pd
from datetime import date
from typing import Any
import structlog

logger = structlog.get_logger(__name__)


class CSVExporter:
    """Export ad performance data to CSV format."""

    async def export(
        self,
        data: dict[str, Any],
        file_name: str | None = None,
    ) -> str:
        """
        Export metrics data to CSV format.

        Args:
            data: Dictionary containing metrics data with structure:
                  {
                      "metrics": [
                          {
                              "entity_id": str,
                              "entity_name": str,
                              "entity_type": str,
                              "platform": str,
                              "date": str,
                              "spend": float,
                              "revenue": float,
                              "roas": float,
                              "conversions": int,
                              "cpa": float,
                              "impressions": int,
                              "clicks": int,
                              "ctr": float
                          },
                          ...
                      ]
                  }
            file_name: Optional file name (without extension)

        Returns:
            Path to the generated CSV file

        Raises:
            ValueError: If data is invalid or missing required fields
        """
        log = logger.bind(file_name=file_name)
        log.info("csv_export_start")

        # Validate input data
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary")

        if "metrics" not in data:
            raise ValueError("Data must contain 'metrics' key")

        metrics = data["metrics"]
        if not isinstance(metrics, list):
            raise ValueError("Metrics must be a list")

        if len(metrics) == 0:
            raise ValueError("Metrics list cannot be empty")

        # Generate file name if not provided
        if file_name is None:
            today = date.today().isoformat()
            file_name = f"ad_performance_report_{today}"

        # Ensure file name doesn't have extension
        if file_name.endswith(".csv"):
            file_name = file_name[:-4]

        file_path = f"/tmp/{file_name}.csv"

        try:
            # Convert to DataFrame with explicit dtypes for string columns
            df = pd.DataFrame(metrics)
            
            # Ensure string columns remain as strings (not converted to int/float)
            string_columns = ["entity_id", "entity_name", "entity_type", "platform", "date"]
            for col in string_columns:
                if col in df.columns:
                    df[col] = df[col].astype(str)

            # Validate required columns exist
            required_columns = [
                "entity_id",
                "entity_name",
                "entity_type",
                "platform",
                "date",
                "spend",
                "revenue",
                "roas",
                "conversions",
                "cpa",
            ]

            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(
                    f"Missing required columns: {', '.join(missing_columns)}"
                )

            # Reorder columns for better readability
            column_order = [
                "date",
                "platform",
                "entity_type",
                "entity_id",
                "entity_name",
                "spend",
                "revenue",
                "roas",
                "conversions",
                "cpa",
                "impressions",
                "clicks",
                "ctr",
            ]

            # Only include columns that exist in the DataFrame
            ordered_columns = [col for col in column_order if col in df.columns]

            # Add any remaining columns not in the order list
            remaining_columns = [col for col in df.columns if col not in ordered_columns]
            final_columns = ordered_columns + remaining_columns

            df = df[final_columns]

            # Export to CSV
            df.to_csv(file_path, index=False, encoding="utf-8")

            log.info(
                "csv_export_complete",
                file_path=file_path,
                row_count=len(df),
                column_count=len(df.columns),
            )

            return file_path

        except Exception as e:
            log.error("csv_export_failed", error=str(e))
            raise

    def validate_data_completeness(self, data: dict[str, Any]) -> bool:
        """
        Validate that all required data is present and complete.

        Args:
            data: Data dictionary to validate

        Returns:
            True if data is complete, False otherwise
        """
        if not isinstance(data, dict):
            return False

        if "metrics" not in data:
            return False

        metrics = data["metrics"]
        if not isinstance(metrics, list) or len(metrics) == 0:
            return False

        # Check that each metric has required fields
        required_fields = [
            "entity_id",
            "entity_name",
            "entity_type",
            "platform",
            "date",
            "spend",
            "revenue",
            "roas",
            "conversions",
            "cpa",
        ]

        for metric in metrics:
            if not isinstance(metric, dict):
                return False

            for field in required_fields:
                if field not in metric:
                    return False

        return True
