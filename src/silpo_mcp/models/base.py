"""Shared Pydantic base for Silpo models.

Allows construction/validation using either camelCase aliases (as returned by
the Silpo server) or snake_case field names (convenience).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SilpoModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
