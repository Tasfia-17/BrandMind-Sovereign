"""Test BrandMemory store and recall."""
from unittest.mock import patch, MagicMock

def test_brand_memory_store():
    with patch("memory.brand_memory.Memory") as MockMem:
        instance = MockMem.from_config.return_value
        from memory.brand_memory import BrandMemory
        bm = BrandMemory("test_brand")
        bm.store("test fact")
        instance.add.assert_called_once()
