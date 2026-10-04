from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class Sponsor(Base):
    __tablename__ = "sponsors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sponsor_name = Column(String(255), nullable=False)
    contact_person = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    trials = relationship("Trial", back_populates="sponsor")

class Trial(Base):
    __tablename__ = "trials"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    trial_title = Column(String(255), nullable=False)
    nct_number = Column(String(50), nullable=False, unique=True)   # now explicitly unique
    available_slots = Column(Integer, nullable=False, default=10)
    sponsor_id = Column(Integer, ForeignKey("sponsors.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    sponsor = relationship("Sponsor", back_populates="trials")
    sites = relationship("TrialSite", cascade="all, delete-orphan", passive_deletes=True)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)


class SessionToken(Base):
    __tablename__ = "sessions"

    id = Column(String(64), primary_key=True)              # the session token
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=False)

class TrialSite(Base):
    __tablename__ = "trial_sites"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trial_id = Column(Integer, ForeignKey("trials.id", ondelete="CASCADE"), nullable=False)
    site_name = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False)