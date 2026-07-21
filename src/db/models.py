from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from src.db.database import Base

class Observation(Base):
    __tablename__ = "observations"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(String, index=True, nullable=False)
    category = Column(String, index=True, nullable=False)
    entity_name = Column(String, nullable=False)
    variable_name = Column(String, nullable=False)
    year = Column(Integer, nullable=True)
    period = Column(String, nullable=True)
    value = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
