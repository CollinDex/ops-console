"""Shared request dependencies."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Query

from app.core.errors import ValidationFailed

SEARCH_MAX_LENGTH = 100


@dataclass(frozen=True)
class Pagination:
    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def get_pagination(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Pagination:
    return Pagination(page=page, page_size=page_size)


PaginationDep = Annotated[Pagination, Depends(get_pagination)]


def like_escape(term: str) -> str:
    """Escape LIKE wildcards. Use with escape="\\\\" on the ilike call."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def clean_search(term: str | None) -> str | None:
    """Trim the term; an empty term means no search. Over 100 characters is a 422."""
    if term is None:
        return None
    term = term.strip()
    if len(term) > SEARCH_MAX_LENGTH:
        raise ValidationFailed(
            "The request is invalid.",
            details=[
                {
                    "field": "search",
                    "message": f"Search must be at most {SEARCH_MAX_LENGTH} characters.",
                }
            ],
        )
    return term or None
