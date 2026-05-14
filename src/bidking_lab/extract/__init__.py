"""Read game install files → structured hints / raw manifests."""

from bidking_lab.extract.streaming_assets import list_streaming_assets_tree
from bidking_lab.extract.tables import (
    assert_uniform_columns,
    decode_table_text,
    discover_tables,
    iter_table_rows,
    load_table_rows,
)

__all__ = [
    "assert_uniform_columns",
    "decode_table_text",
    "discover_tables",
    "iter_table_rows",
    "list_streaming_assets_tree",
    "load_table_rows",
]
