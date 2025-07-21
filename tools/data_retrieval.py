import json
from typing import Literal, Any, Dict, List
from datetime import datetime

from anthropic.types.beta import BetaToolComputerUse20241022Param

from .base import BaseAnthropicTool, ToolResult
from .data_storage import DataStorageTool


class DataRetrievalTool(BaseAnthropicTool):
    """
    A tool for retrieving and searching stored data from memory.
    Works with DataStorageTool to access previously extracted data.
    """

    api_type: Literal["computer_20241022"] = "computer_20241022"
    name: Literal["data_retrieval"] = "data_retrieval"

    def to_params(self) -> BetaToolComputerUse20241022Param:
        return {
            "name": self.name,
            "type": self.api_type,
        }

    async def __call__(
        self,
        *,
        action: str,
        data_id: str | None = None,
        category: str | None = None,
        search_term: str | None = None,
        limit: int = 10,
        include_data: bool = True,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> ToolResult:
        """
        Retrieve and search stored data.
        
        Args:
            action: Action to perform (get, search, list, summary)
            data_id: Specific data ID to retrieve
            category: Filter by category
            search_term: Search term to look for in descriptions and data
            limit: Maximum number of results to return
            include_data: Whether to include the actual data or just metadata
            date_from: Filter from date (ISO format)
            date_to: Filter to date (ISO format)
        """
        try:
            if action == "get":
                return await self._get_data(data_id, include_data)
            elif action == "search":
                return await self._search_data(search_term, category, limit, include_data, date_from, date_to)
            elif action == "list":
                return await self._list_data(category, limit, include_data, date_from, date_to)
            elif action == "summary":
                return await self._get_summary(category)
            elif action == "recent":
                return await self._get_recent_data(limit, category, include_data)
            else:
                return ToolResult(error=f"Unknown action: {action}")

        except Exception as e:
            return ToolResult(error=f"Data retrieval operation failed: {str(e)}")

    async def _get_data(self, data_id: str | None, include_data: bool) -> ToolResult:
        """Get specific data by ID."""
        if not data_id:
            return ToolResult(error="Data ID is required for get action")

        if data_id not in DataStorageTool._data_store:
            return ToolResult(error=f"Data ID not found: {data_id}")

        entry = DataStorageTool._data_store[data_id]
        metadata = DataStorageTool._metadata[data_id]

        result = {
            "data_id": data_id,
            "category": entry["category"],
            "description": entry["description"],
            "created_at": entry["created_at"],
            "updated_at": entry["updated_at"],
            "size_bytes": metadata["size_bytes"],
            "data_type": metadata["data_type"],
        }

        if include_data:
            result["data"] = entry["data"]

        result["custom_metadata"] = metadata["custom_metadata"]

        return ToolResult(
            output=json.dumps(result, indent=2),
            system=f"Data retrieved successfully: {data_id}"
        )

    async def _search_data(
        self, 
        search_term: str | None, 
        category: str | None, 
        limit: int, 
        include_data: bool,
        date_from: str | None,
        date_to: str | None
    ) -> ToolResult:
        """Search data based on criteria."""
        results = []
        search_stats = {
            "total_searched": 0,
            "matches_found": 0,
            "categories_searched": [],
            "search_term": search_term,
            "date_range": f"{date_from or 'any'} to {date_to or 'any'}"
        }

        # Filter by category if specified
        data_ids_to_search = []
        if category:
            if category in DataStorageTool._categories:
                data_ids_to_search = DataStorageTool._categories[category]
                search_stats["categories_searched"] = [category]
            else:
                return ToolResult(error=f"Category not found: {category}")
        else:
            data_ids_to_search = list(DataStorageTool._data_store.keys())
            search_stats["categories_searched"] = list(DataStorageTool._categories.keys())

        search_stats["total_searched"] = len(data_ids_to_search)

        for data_id in data_ids_to_search:
            if len(results) >= limit:
                break

            entry = DataStorageTool._data_store[data_id]
            metadata = DataStorageTool._metadata[data_id]

            # Date filtering
            if date_from or date_to:
                entry_date = datetime.fromisoformat(entry["created_at"])
                if date_from and entry_date < datetime.fromisoformat(date_from):
                    continue
                if date_to and entry_date > datetime.fromisoformat(date_to):
                    continue

            # Text search
            if search_term:
                search_text = (
                    entry["description"].lower() + " " +
                    str(entry["data"]).lower() + " " +
                    entry["category"].lower()
                )
                if search_term.lower() not in search_text:
                    continue

            # Build result
            result_entry = {
                "data_id": data_id,
                "category": entry["category"],
                "description": entry["description"],
                "created_at": entry["created_at"],
                "updated_at": entry["updated_at"],
                "size_bytes": metadata["size_bytes"],
                "data_type": metadata["data_type"],
                "relevance_score": self._calculate_relevance(search_term, entry) if search_term else 1.0
            }

            if include_data:
                result_entry["data"] = entry["data"]

            results.append(result_entry)
            search_stats["matches_found"] += 1

        # Sort by relevance if searching
        if search_term:
            results.sort(key=lambda x: x["relevance_score"], reverse=True)

        final_result = {
            "search_stats": search_stats,
            "results": results,
            "result_count": len(results),
            "more_available": search_stats["matches_found"] > limit
        }

        return ToolResult(
            output=json.dumps(final_result, indent=2),
            system=f"Search completed. Found {len(results)} results."
        )

    async def _list_data(
        self, 
        category: str | None, 
        limit: int, 
        include_data: bool,
        date_from: str | None,
        date_to: str | None
    ) -> ToolResult:
        """List data entries with optional filtering."""
        results = []

        # Get data IDs to list
        if category:
            if category not in DataStorageTool._categories:
                return ToolResult(error=f"Category not found: {category}")
            data_ids = DataStorageTool._categories[category]
        else:
            data_ids = list(DataStorageTool._data_store.keys())

        # Sort by creation date (newest first)
        data_ids.sort(
            key=lambda x: DataStorageTool._data_store[x]["created_at"], 
            reverse=True
        )

        for data_id in data_ids[:limit]:
            entry = DataStorageTool._data_store[data_id]
            metadata = DataStorageTool._metadata[data_id]

            # Date filtering
            if date_from or date_to:
                entry_date = datetime.fromisoformat(entry["created_at"])
                if date_from and entry_date < datetime.fromisoformat(date_from):
                    continue
                if date_to and entry_date > datetime.fromisoformat(date_to):
                    continue

            result_entry = {
                "data_id": data_id,
                "category": entry["category"],
                "description": entry["description"],
                "created_at": entry["created_at"],
                "updated_at": entry["updated_at"],
                "size_bytes": metadata["size_bytes"],
                "data_type": metadata["data_type"]
            }

            if include_data:
                result_entry["data"] = entry["data"]

            results.append(result_entry)

        final_result = {
            "results": results,
            "result_count": len(results),
            "total_available": len(data_ids),
            "category_filter": category,
            "date_filter": f"{date_from or 'any'} to {date_to or 'any'}"
        }

        return ToolResult(
            output=json.dumps(final_result, indent=2),
            system=f"Listed {len(results)} data entries."
        )

    async def _get_summary(self, category: str | None) -> ToolResult:
        """Get summary statistics of stored data."""
        if category and category not in DataStorageTool._categories:
            return ToolResult(error=f"Category not found: {category}")

        data_ids = (
            DataStorageTool._categories[category] if category 
            else list(DataStorageTool._data_store.keys())
        )

        if not data_ids:
            result = {
                "category": category or "all",
                "total_entries": 0,
                "total_size_bytes": 0,
                "data_types": {},
                "date_range": None
            }
        else:
            entries = [DataStorageTool._data_store[data_id] for data_id in data_ids]
            metadata_list = [DataStorageTool._metadata[data_id] for data_id in data_ids]

            # Calculate statistics
            total_size = sum(meta["size_bytes"] for meta in metadata_list)
            data_types = {}
            for meta in metadata_list:
                dtype = meta["data_type"]
                data_types[dtype] = data_types.get(dtype, 0) + 1

            dates = [entry["created_at"] for entry in entries]
            date_range = {
                "earliest": min(dates),
                "latest": max(dates)
            }

            result = {
                "category": category or "all",
                "total_entries": len(data_ids),
                "total_size_bytes": total_size,
                "average_size_bytes": total_size // len(data_ids),
                "data_types": data_types,
                "date_range": date_range,
                "categories_included": [category] if category else list(DataStorageTool._categories.keys())
            }

        return ToolResult(
            output=json.dumps(result, indent=2),
            system="Summary generated successfully"
        )

    async def _get_recent_data(self, limit: int, category: str | None, include_data: bool) -> ToolResult:
        """Get most recently created/updated data entries."""
        data_ids = (
            DataStorageTool._categories[category] if category and category in DataStorageTool._categories
            else list(DataStorageTool._data_store.keys())
        )

        if not data_ids:
            return ToolResult(error=f"No data found in category: {category}" if category else "No data stored")

        # Sort by updated_at (most recent first)
        data_ids.sort(
            key=lambda x: DataStorageTool._data_store[x]["updated_at"], 
            reverse=True
        )

        results = []
        for data_id in data_ids[:limit]:
            entry = DataStorageTool._data_store[data_id]
            metadata = DataStorageTool._metadata[data_id]

            result_entry = {
                "data_id": data_id,
                "category": entry["category"],
                "description": entry["description"],
                "created_at": entry["created_at"],
                "updated_at": entry["updated_at"],
                "size_bytes": metadata["size_bytes"],
                "data_type": metadata["data_type"]
            }

            if include_data:
                result_entry["data"] = entry["data"]

            results.append(result_entry)

        final_result = {
            "results": results,
            "result_count": len(results),
            "category_filter": category,
            "sorted_by": "most_recent_update"
        }

        return ToolResult(
            output=json.dumps(final_result, indent=2),
            system=f"Retrieved {len(results)} most recent data entries."
        )

    def _calculate_relevance(self, search_term: str, entry: Dict[str, Any]) -> float:
        """Calculate relevance score for search results."""
        if not search_term:
            return 1.0

        score = 0.0
        search_lower = search_term.lower()

        # Description relevance (weight: 3.0)
        description = entry["description"].lower()
        if search_lower in description:
            score += 3.0
            # Bonus for exact match
            if search_lower == description:
                score += 2.0

        # Data content relevance (weight: 2.0)
        data_str = str(entry["data"]).lower()
        if search_lower in data_str:
            score += 2.0

        # Category relevance (weight: 1.0)
        category = entry["category"].lower()
        if search_lower in category:
            score += 1.0

        # Recency bonus (newer entries get slight boost)
        try:
            entry_date = datetime.fromisoformat(entry["updated_at"])
            days_old = (datetime.now() - entry_date).days
            recency_score = max(0, 1 - (days_old / 30))  # Boost for entries less than 30 days old
            score += recency_score * 0.5
        except:
            pass

        return score 