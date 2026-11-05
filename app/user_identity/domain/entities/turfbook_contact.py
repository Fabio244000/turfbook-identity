from dataclasses import dataclass


@dataclass(frozen=True)
class TurfBookContact:
    phone: str
    email: str
