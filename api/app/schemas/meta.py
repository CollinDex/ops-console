"""Filter metadata response models."""

from pydantic import BaseModel


class Option(BaseModel):
    value: str
    label: str


class ScoreBandOut(BaseModel):
    key: str
    label: str
    min: int
    max: int


class FilterMeta(BaseModel):
    stages: list[Option]
    sectors: list[Option]
    check_types: list[Option]
    score_bands: list[ScoreBandOut]
