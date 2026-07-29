from datetime import datetime

from sqlalchemy import  DateTime, Float, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Prediction(Base):
    """ Stores the single of a single URL phishing analysis """

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(2048), index=True)
    is_phishing: Mapped[bool]
    phishing_probability: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
