import os

import pytest

from codebase.key_vault import clear_key_pool, load_key_pool, save_key_pool


@pytest.mark.skipif(os.name != "nt", reason="Windows DPAPI test")
def test_key_vault_encrypts_deduplicates_and_deletes(tmp_path):
    vault_path = tmp_path / "gemini-key-pool.dpapi"
    keys = ["first-test-key", "second-test-key", "first-test-key"]

    assert save_key_pool(keys, vault_path) is True
    assert load_key_pool(vault_path) == ["first-test-key", "second-test-key"]
    assert b"first-test-key" not in vault_path.read_bytes()
    assert save_key_pool(keys, vault_path) is False

    assert clear_key_pool(vault_path) is True
    assert load_key_pool(vault_path) == []
