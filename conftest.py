import pytest


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Libera acesso ao banco para todos os testes por padrão."""
    pass
