from sqlalchemy import Column, Integer, String

from app.db import Base


class CategoryRule(Base):
    __tablename__ = "category_rules"

    id = Column(Integer, primary_key=True, index=True)
    pattern = Column(String, nullable=False)
    category = Column(String, nullable=False)
    priority = Column(Integer, nullable=False, default=0)
