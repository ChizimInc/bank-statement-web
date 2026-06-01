from pydantic import BaseModel, ConfigDict


class RuleIn(BaseModel):
    pattern: str
    category: str
    priority: int = 0


class RuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pattern: str
    category: str
    priority: int
