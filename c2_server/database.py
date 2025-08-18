"""
Database management for the C2 server.
"""
import sqlite3
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy import create_engine, Column, String, DateTime, Float, Integer, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import json
import logging

from shared.models import BotClient, AttackSession, LogEntry, SessionMetrics, AttackConfig

Base = declarative_base()


class BotClientDB(Base):
    __tablename__ = "bot_clients"
    
    bot_id = Column(String, primary_key=True)
    ip_address = Column(String, nullable=False)
    hostname = Column(String, nullable=False)
    connection_time = Column(DateTime, nullable=False)
    last_heartbeat = Column(DateTime, nullable=False)
    status = Column(String, nullable=False)
    capabilities = Column(Text)  # JSON string
    current_load = Column(Float, default=0.0)


class AttackSessionDB(Base):
    __tablename__ = "attack_sessions"
    
    session_id = Column(String, primary_key=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    attack_config = Column(Text, nullable=False)  # JSON string
    participating_bots = Column(Text)  # JSON string
    metrics = Column(Text)  # JSON string
    logs = Column(Text)  # JSON string


class LogEntryDB(Base):
    __tablename__ = "log_entries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False)
    level = Column(String, nullable=False)
    source = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    bot_id = Column(String)
    attack_id = Column(String)
    session_id = Column(String)


class DatabaseManager:
    """Database manager for the C2 server."""
    
    def __init__(self, database_url: str = "sqlite+aiosqlite:///ddos_lab.db"):
        self.database_url = database_url
        self.engine = None
        self.async_session = None
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self):
        """Initialize the database connection and create tables."""
        try:
            self.engine = create_async_engine(
                self.database_url,
                echo=False,
                future=True
            )
            
            # Create tables
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            # Create async session factory
            self.async_session = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            self.logger.info("Database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def close(self):
        """Close database connections."""
        if self.engine:
            await self.engine.dispose()
    
    async def register_bot(self, bot: BotClient) -> bool:
        """Register a new bot or update existing bot information."""
        try:
            async with self.async_session() as session:
                # Check if bot already exists
                existing_bot = await session.get(BotClientDB, bot.bot_id)
                
                if existing_bot:
                    # Update existing bot
                    existing_bot.ip_address = bot.ip_address
                    existing_bot.hostname = bot.hostname
                    existing_bot.last_heartbeat = bot.last_heartbeat
                    existing_bot.status = bot.status.value
                    existing_bot.capabilities = json.dumps([cap.value for cap in bot.capabilities])
                    existing_bot.current_load = bot.current_load
                else:
                    # Create new bot
                    new_bot = BotClientDB(
                        bot_id=bot.bot_id,
                        ip_address=bot.ip_address,
                        hostname=bot.hostname,
                        connection_time=bot.connection_time,
                        last_heartbeat=bot.last_heartbeat,
                        status=bot.status.value,
                        capabilities=json.dumps([cap.value for cap in bot.capabilities]),
                        current_load=bot.current_load
                    )
                    session.add(new_bot)
                
                await session.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to register bot {bot.bot_id}: {e}")
            return False
    
    async def update_bot_heartbeat(self, bot_id: str, heartbeat_time: datetime, status: str, current_load: float) -> bool:
        """Update bot heartbeat information."""
        try:
            async with self.async_session() as session:
                bot = await session.get(BotClientDB, bot_id)
                if bot:
                    bot.last_heartbeat = heartbeat_time
                    bot.status = status
                    bot.current_load = current_load
                    await session.commit()
                    return True
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to update bot heartbeat {bot_id}: {e}")
            return False
    
    async def get_active_bots(self, heartbeat_timeout: int = 30) -> List[BotClient]:
        """Get list of active bots (those with recent heartbeats)."""
        try:
            cutoff_time = datetime.now() - timedelta(seconds=heartbeat_timeout)
            
            async with self.async_session() as session:
                from sqlalchemy import select
                
                result = await session.execute(
                    select(BotClientDB).where(
                        BotClientDB.last_heartbeat > cutoff_time
                    )
                )
                bot_records = result.scalars().all()
                
                bots = []
                for record in bot_records:
                    capabilities = json.loads(record.capabilities) if record.capabilities else []
                    bot = BotClient(
                        bot_id=record.bot_id,
                        ip_address=record.ip_address,
                        hostname=record.hostname,
                        connection_time=record.connection_time,
                        last_heartbeat=record.last_heartbeat,
                        status=record.status,
                        capabilities=capabilities,
                        current_load=record.current_load
                    )
                    bots.append(bot)
                
                return bots
                
        except Exception as e:
            self.logger.error(f"Failed to get active bots: {e}")
            return []
    
    async def remove_bot(self, bot_id: str) -> bool:
        """Remove a bot from the database."""
        try:
            async with self.async_session() as session:
                bot = await session.get(BotClientDB, bot_id)
                if bot:
                    await session.delete(bot)
                    await session.commit()
                    return True
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to remove bot {bot_id}: {e}")
            return False
    
    async def create_attack_session(self, session: AttackSession) -> bool:
        """Create a new attack session record."""
        try:
            async with self.async_session() as db_session:
                session_record = AttackSessionDB(
                    session_id=session.session_id,
                    start_time=session.start_time,
                    end_time=session.end_time,
                    attack_config=session.attack_config.json(),
                    participating_bots=json.dumps([bot.dict() for bot in session.participating_bots]),
                    metrics=session.metrics.json(),
                    logs=json.dumps([log.dict() for log in session.logs])
                )
                
                db_session.add(session_record)
                await db_session.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to create attack session {session.session_id}: {e}")
            return False
    
    async def update_attack_session(self, session: AttackSession) -> bool:
        """Update an existing attack session record."""
        try:
            async with self.async_session() as db_session:
                session_record = await db_session.get(AttackSessionDB, session.session_id)
                if session_record:
                    session_record.end_time = session.end_time
                    session_record.metrics = session.metrics.json()
                    session_record.logs = json.dumps([log.dict() for log in session.logs])
                    await db_session.commit()
                    return True
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to update attack session {session.session_id}: {e}")
            return False
    
    async def log_entry(self, entry: LogEntry) -> bool:
        """Add a log entry to the database."""
        try:
            async with self.async_session() as session:
                log_record = LogEntryDB(
                    timestamp=entry.timestamp,
                    level=entry.level,
                    source=entry.source,
                    message=entry.message,
                    bot_id=entry.bot_id,
                    attack_id=entry.attack_id
                )
                
                session.add(log_record)
                await session.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to log entry: {e}")
            return False
    
    async def get_recent_logs(self, limit: int = 100, level: Optional[str] = None) -> List[LogEntry]:
        """Get recent log entries."""
        try:
            async with self.async_session() as session:
                from sqlalchemy import select, desc
                
                query = select(LogEntryDB).order_by(desc(LogEntryDB.timestamp)).limit(limit)
                
                if level:
                    query = query.where(LogEntryDB.level == level)
                
                result = await session.execute(query)
                log_records = result.scalars().all()
                
                logs = []
                for record in log_records:
                    log = LogEntry(
                        timestamp=record.timestamp,
                        level=record.level,
                        source=record.source,
                        message=record.message,
                        bot_id=record.bot_id,
                        attack_id=record.attack_id
                    )
                    logs.append(log)
                
                return logs
                
        except Exception as e:
            self.logger.error(f"Failed to get recent logs: {e}")
            return []
    
    async def cleanup_old_records(self, log_retention_days: int = 30, session_retention_days: int = 90):
        """Clean up old log entries and sessions."""
        try:
            log_cutoff = datetime.now() - timedelta(days=log_retention_days)
            session_cutoff = datetime.now() - timedelta(days=session_retention_days)
            
            async with self.async_session() as session:
                from sqlalchemy import delete
                
                # Clean up old logs
                await session.execute(
                    delete(LogEntryDB).where(LogEntryDB.timestamp < log_cutoff)
                )
                
                # Clean up old sessions
                await session.execute(
                    delete(AttackSessionDB).where(AttackSessionDB.start_time < session_cutoff)
                )
                
                await session.commit()
                self.logger.info("Database cleanup completed")
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup old records: {e}")