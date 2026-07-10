import pytest
from sqlalchemy import Column, Date, DateTime, Integer, MetaData, String, Table


@pytest.fixture
def users() -> Table:
    metadata = MetaData()
    return Table(
        "users",
        metadata,
        Column("id", Integer),
        Column("age", Integer),
        Column("name", String),
        Column("status", String),
        Column("created_at", DateTime),
        Column("birth_date", Date),
    )


@pytest.fixture
def items() -> Table:
    return Table("items", MetaData(), Column("name", String), Column("sku", String))
