from datetime import date

from pydantic import BaseModel


class DashboardPoint(BaseModel):
    date: date
    mentions: int


class DashboardSummary(BaseModel):
    total_mentions: int
    total_domains: int
    total_profiles: int
    new_mentions_7d: int
    needs_verification: int
    evolution: list[DashboardPoint]
