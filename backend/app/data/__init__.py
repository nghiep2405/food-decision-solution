"""Shared persistence and data contracts for the Food Decision MVP."""

from app.data.database import connect_database, initialize_database

__all__ = ["connect_database", "initialize_database"]
