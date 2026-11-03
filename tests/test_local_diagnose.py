import hashlib
import pytest
from backend.moirae.local_playtest import create_playtest
from backend.moirae.local_diagnose import inspect


def test_diagnosis_preserves_database_and_omits_secrets(tmp_path):
    path = tmp_path / 'local.sqlite3'
    create_playtest(path, 'henrique@example.test', 'test-only-password-123')
    before = hashlib.sha256(path.read_bytes()).digest()
    result = inspect(path, 'henrique@example.test')
    assert result['profile']['email_verified'] == 1
    assert result['current_terms']
    assert result['orders'][0]['status'] == 'local_test'
    assert not inspect(path, 'missing@example.test')['account_exists']
    assert 'password' not in str(result) and 'token_hash' not in str(result)
    assert hashlib.sha256(path.read_bytes()).digest() == before
    with pytest.raises(FileNotFoundError):
        inspect(tmp_path / 'wrong.sqlite3', 'henrique@example.test')
    assert not (tmp_path / 'wrong.sqlite3').exists()
