"""LangGraph tools for enhanced language model capabilities.

This package contains custom tools that can be used with LangGraph to extend
the capabilities of language models. Includes web search and database query tools.
"""

from langchain_core.tools.base import BaseTool

from .duckduckgosearch import duckduckgo_search_tool
from .patient_db_query import (
    query_document_extractions,
    vector_search_document_extractions,
)

tools: list[BaseTool] = [
    duckduckgo_search_tool,
    query_document_extractions,
    vector_search_document_extractions,
]
