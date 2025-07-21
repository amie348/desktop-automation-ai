import json
from typing import Literal, Any, Dict, List
from datetime import datetime

from anthropic.types.beta import BetaToolComputerUse20241022Param

from .base import BaseAnthropicTool, ToolResult


class DataStorageTool(BaseAnthropicTool):
    """
    A tool for storing extracted data in memory using class variables.
    Provides persistent storage across tool calls within the same session.
    """

    api_type: Literal["computer_20241022"] = "computer_20241022"
    name: Literal["data_storage"] = "data_storage"

    # Class variables for in-memory storage
    _data_store: Dict[str, Dict[str, Any]] = {}
    _categories: Dict[str, List[str]] = {}
    _metadata: Dict[str, Dict[str, Any]] = {}
    _next_id: int = 1

    def to_params(self) -> BetaToolComputerUse20241022Param:
        return {
            "name": self.name,
            "type": self.api_type,
        }

    async def __call__(
        self,
        *,
        action: str,
        data: str | None = None,
        data_id: str | None = None,
        category: str = "general",
        description: str = "",
        metadata: str | None = None,
    ) -> ToolResult:
        """
        Store, update, or manage extracted data in memory.
        
        Args:
            action: Action to perform (store, update, delete, get_info)
            data: JSON string of the data to store (for store/update actions)
            data_id: ID of the data entry (for update/delete/get_info actions)
            category: Category to classify the data
            description: Description of the data
            metadata: Additional metadata as JSON string
        """
        try:
            if action == "store":
                return await self._store_data(data, category, description, metadata)
            elif action == "update":
                return await self._update_data(data_id, data, metadata)
            elif action == "delete":
                return await self._delete_data(data_id)
            elif action == "get_info":
                return await self._get_storage_info(data_id)
            elif action == "clear_category":
                return await self._clear_category(category)
            elif action == "list_categories":
                return await self._list_categories()
            else:
                return ToolResult(error=f"Unknown action: {action}")

        except Exception as e:
            return ToolResult(error=f"Data storage operation failed: {str(e)}")

    async def _store_data(self, data: str, category: str, description: str, metadata: str | None) -> ToolResult:
        """Store new data entry."""
        try:
            # Parse the data
            parsed_data = json.loads(data) if data else {}
            parsed_metadata = json.loads(metadata) if metadata else {}

            # Generate unique ID
            data_id = f"data_{self._next_id:06d}"
            self._next_id += 1

            # Store the data
            self._data_store[data_id] = {
                "id": data_id,
                "data": parsed_data,
                "category": category,
                "description": description,
                "timestamp": datetime.now().isoformat(),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }

            # Store metadata
            self._metadata[data_id] = {
                "size_bytes": len(data) if data else 0,
                "data_type": type(parsed_data).__name__,
                "custom_metadata": parsed_metadata,
            }

            # Update category index
            if category not in self._categories:
                self._categories[category] = []
            self._categories[category].append(data_id)

            result = {
                "action": "stored",
                "data_id": data_id,
                "category": category,
                "description": description,
                "timestamp": self._data_store[data_id]["timestamp"],
                "total_entries": len(self._data_store),
                "category_count": len(self._categories.get(category, []))
            }

            return ToolResult(
                output=json.dumps(result, indent=2),
                system=f"Data stored successfully with ID: {data_id}"
            )

        except json.JSONDecodeError as e:
            return ToolResult(error=f"Invalid JSON data: {str(e)}")

    async def _update_data(self, data_id: str, data: str | None, metadata: str | None) -> ToolResult:
        """Update existing data entry."""
        if data_id not in self._data_store:
            return ToolResult(error=f"Data ID not found: {data_id}")

        try:
            entry = self._data_store[data_id]

            # Update data if provided
            if data:
                parsed_data = json.loads(data)
                entry["data"] = parsed_data
                self._metadata[data_id]["size_bytes"] = len(data)
                self._metadata[data_id]["data_type"] = type(parsed_data).__name__

            # Update metadata if provided
            if metadata:
                parsed_metadata = json.loads(metadata)
                self._metadata[data_id]["custom_metadata"].update(parsed_metadata)

            entry["updated_at"] = datetime.now().isoformat()

            result = {
                "action": "updated",
                "data_id": data_id,
                "updated_at": entry["updated_at"],
                "size_bytes": self._metadata[data_id]["size_bytes"]
            }

            return ToolResult(
                output=json.dumps(result, indent=2),
                system=f"Data updated successfully: {data_id}"
            )

        except json.JSONDecodeError as e:
            return ToolResult(error=f"Invalid JSON data: {str(e)}")

    async def _delete_data(self, data_id: str) -> ToolResult:
        """Delete data entry."""
        if data_id not in self._data_store:
            return ToolResult(error=f"Data ID not found: {data_id}")

        entry = self._data_store[data_id]
        category = entry["category"]

        # Remove from data store
        del self._data_store[data_id]
        del self._metadata[data_id]

        # Remove from category index
        if category in self._categories and data_id in self._categories[category]:
            self._categories[category].remove(data_id)
            if not self._categories[category]:
                del self._categories[category]

        result = {
            "action": "deleted",
            "data_id": data_id,
            "category": category,
            "remaining_entries": len(self._data_store)
        }

        return ToolResult(
            output=json.dumps(result, indent=2),
            system=f"Data deleted successfully: {data_id}"
        )

    async def _get_storage_info(self, data_id: str | None) -> ToolResult:
        """Get information about stored data."""
        if data_id:
            # Get specific entry info
            if data_id not in self._data_store:
                return ToolResult(error=f"Data ID not found: {data_id}")

            entry = self._data_store[data_id]
            metadata = self._metadata[data_id]

            result = {
                "data_id": data_id,
                "category": entry["category"],
                "description": entry["description"],
                "created_at": entry["created_at"],
                "updated_at": entry["updated_at"],
                "size_bytes": metadata["size_bytes"],
                "data_type": metadata["data_type"],
                "custom_metadata": metadata["custom_metadata"]
            }
        else:
            # Get overall storage info
            total_size = sum(meta["size_bytes"] for meta in self._metadata.values())
            
            result = {
                "total_entries": len(self._data_store),
                "total_size_bytes": total_size,
                "categories": {cat: len(ids) for cat, ids in self._categories.items()},
                "all_data_ids": list(self._data_store.keys())
            }

        return ToolResult(
            output=json.dumps(result, indent=2),
            system="Storage information retrieved successfully"
        )

    async def _clear_category(self, category: str) -> ToolResult:
        """Clear all data from a specific category."""
        if category not in self._categories:
            return ToolResult(error=f"Category not found: {category}")

        data_ids = self._categories[category].copy()
        deleted_count = 0

        for data_id in data_ids:
            if data_id in self._data_store:
                del self._data_store[data_id]
                del self._metadata[data_id]
                deleted_count += 1

        del self._categories[category]

        result = {
            "action": "category_cleared",
            "category": category,
            "deleted_count": deleted_count,
            "remaining_entries": len(self._data_store)
        }

        return ToolResult(
            output=json.dumps(result, indent=2),
            system=f"Category '{category}' cleared successfully"
        )

    async def _list_categories(self) -> ToolResult:
        """List all categories and their entry counts."""
        result = {
            "categories": {cat: len(ids) for cat, ids in self._categories.items()},
            "total_categories": len(self._categories),
            "total_entries": len(self._data_store)
        }

        return ToolResult(
            output=json.dumps(result, indent=2),
            system="Categories listed successfully"
        ) 