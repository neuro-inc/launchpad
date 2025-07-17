from uuid import UUID

from pydantic import BaseModel


class AppPoolRead(BaseModel):
    id: UUID
    name: str
    description: str
    is_shared: bool
