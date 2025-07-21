import json
from typing import Literal, Any
from datetime import datetime

from anthropic.types.beta import BetaToolComputerUse20241022Param

from .base import BaseAnthropicTool, ToolResult


class DataExtractionTool(BaseAnthropicTool):
    """
    A tool for extracting structured data from screenshots or images.
    Analyzes visual content and returns structured data in JSON format.
    """

    api_type: Literal["computer_20241022"] = "computer_20241022"
    name: Literal["data_extraction"] = "data_extraction"

    def to_params(self) -> BetaToolComputerUse20241022Param:
        return {
            "name": self.name,
            "type": self.api_type,
        }

    async def __call__(
        self,
        *,
        extraction_type: str,
        extraction_instructions: str,
        screenshot_data: str | None = None,
        category: str = "general",
        source_description: str = "",
    ) -> ToolResult:
        """
        Extract structured data from a screenshot or visual content.
        
        Args:
            extraction_type: Type of extraction (table, form, text, list, etc.)
            extraction_instructions: Specific instructions for what to extract
            screenshot_data: Base64 encoded screenshot data (optional, will take screenshot if not provided)
            category: Category to classify the extracted data
            source_description: Description of the data source
        """
        try:
            # If no screenshot provided, take one automatically
            if not screenshot_data:
                from .computer_windows import ComputerTool
                computer = ComputerTool()
                screenshot_result = await computer(action="screenshot")
                if screenshot_result.error:
                    return ToolResult(error=f"Failed to take screenshot: {screenshot_result.error}")
                screenshot_data = screenshot_result.base64_image

            # Create extraction prompt based on type and instructions
            extraction_prompt = self._create_extraction_prompt(
                extraction_type, extraction_instructions, category
            )

            # For now, return a structured template that will be processed by the main AI
            # The actual extraction will happen through the AI's vision capabilities
            extraction_result = {
                "extraction_id": f"extract_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
                "timestamp": datetime.now().isoformat(),
                "extraction_type": extraction_type,
                "category": category,
                "source_description": source_description,
                "instructions": extraction_instructions,
                "status": "ready_for_processing",
                "screenshot_available": bool(screenshot_data)
            }

            return ToolResult(
                output=json.dumps(extraction_result, indent=2),
                base64_image=screenshot_data,
                system=f"Data extraction task prepared. Use the screenshot and instructions to extract {extraction_type} data."
            )

        except Exception as e:
            return ToolResult(error=f"Data extraction failed: {str(e)}")

    def _create_extraction_prompt(self, extraction_type: str, instructions: str, category: str) -> str:
        """Create a structured prompt for data extraction based on type."""
        
        base_prompt = f"""
EXTRACT {extraction_type.upper()} DATA:

Instructions: {instructions}
Category: {category}

Please analyze the screenshot and extract the requested data in a structured JSON format.
"""

        type_specific_prompts = {
            "table": """
Return data as:
{
  "table_data": [
    {"column1": "value1", "column2": "value2", ...},
    ...
  ],
  "headers": ["column1", "column2", ...],
  "row_count": number
}
""",
            "form": """
Return data as:
{
  "form_fields": {
    "field_name": "field_value",
    ...
  },
  "form_title": "title if visible"
}
""",
            "text": """
Return data as:
{
  "extracted_text": "full text content",
  "sections": ["section1", "section2", ...] if applicable
}
""",
            "list": """
Return data as:
{
  "list_items": ["item1", "item2", ...],
  "list_type": "ordered/unordered"
}
""",
            "contact": """
Return data as:
{
  "contacts": [
    {
      "name": "name",
      "email": "email",
      "phone": "phone",
      "company": "company"
    }
  ]
}
""",
            "product": """
Return data as:
{
  "products": [
    {
      "name": "product_name",
      "price": "price",
      "description": "description",
      "availability": "in_stock/out_of_stock"
    }
  ]
}
"""
        }

        return base_prompt + type_specific_prompts.get(extraction_type, """
Return data as structured JSON that best represents the extracted information.
""") 