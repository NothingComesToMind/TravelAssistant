"""Validated request, tool, and response contracts."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class TripRequest(BaseModel):
    destination: str = Field(min_length=2, max_length=40)
    days: int = Field(ge=1, le=7)
    preferences: str = Field(default="", max_length=200)
    start_date: date | None = None

    @field_validator("destination", "preferences")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class Place(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)
    address: str = ""


class Weather(BaseModel):
    date: str
    day_weather: str = ""
    night_weather: str = ""
    day_temp: str = ""
    night_temp: str = ""


class RouteSegment(BaseModel):
    from_id: str
    to_id: str
    status: Literal["available", "unavailable"]
    distance_m: int | None = None
    duration_s: int | None = None
    polyline: list[list[float]] = Field(default_factory=list)


class DayPlan(BaseModel):
    day: int
    date: str | None = None
    attractions: list[Place]
    hotel: Place | None = None
    weather: Weather | None = None
    routes: list[RouteSegment] = Field(default_factory=list)


class TripPlan(BaseModel):
    destination: str
    days: list[DayPlan]
    warnings: list[str] = Field(default_factory=list)
    data_mode: Literal["demo", "live"]

