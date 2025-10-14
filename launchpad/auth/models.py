import dataclasses


@dataclasses.dataclass
class User:
    id: str
    email: str
    name: str
    groups: list[str] = dataclasses.field(default_factory=list)
