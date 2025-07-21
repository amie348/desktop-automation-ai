from .base import CLIResult, ToolResult
from .collection import ToolCollection
from .edit import EditTool
from .data_extraction import DataExtractionTool
from .data_storage import DataStorageTool
from .data_retrieval import DataRetrievalTool

# Import platform-specific implementations
import platform
if platform.system() == 'Windows':
    from .computer_windows import ComputerTool
    from .bash_windows import BashTool
else:
    from .computer import ComputerTool
    from .bash import BashTool

__ALL__ = [
    BashTool,
    CLIResult,
    ComputerTool,
    DataExtractionTool,
    DataRetrievalTool,
    DataStorageTool,
    EditTool,
    ToolCollection,
    ToolResult,
]
