"""
Enterprise Audit Logging System
Comprehensive audit trail for compliance (GDPR, SOX, etc.)
WHO, WHAT, WHEN, WHERE tracking for all user activities
"""
import datetime as dt
import json
import uuid
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass, asdict
from sqlalchemy import String, Text, DateTime, Integer, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from src.db.base import Base
import logging
import asyncio
from contextlib import asynccontextmanager


class AuditEventType(str, Enum):
    """
    Standardized audit event types for compliance
    """
    # Authentication events
    LOGIN_SUCCESS = "auth.login.success"
    LOGIN_FAILURE = "auth.login.failure"
    LOGOUT = "auth.logout"
    PASSWORD_CHANGE = "auth.password.change"
    PASSWORD_RESET = "auth.password.reset"
    SESSION_EXPIRED = "auth.session.expired"
    
    # Authorization events
    ACCESS_GRANTED = "authz.access.granted"
    ACCESS_DENIED = "authz.access.denied"
    PERMISSION_ESCALATION = "authz.permission.escalation"
    
    # Data access events (GDPR compliance)
    DATA_VIEW = "data.view"
    DATA_CREATE = "data.create"
    DATA_UPDATE = "data.update"
    DATA_DELETE = "data.delete"
    DATA_EXPORT = "data.export"
    DATA_DOWNLOAD = "data.download"
    
    # Admin events
    USER_CREATE = "admin.user.create"
    USER_UPDATE = "admin.user.update"
    USER_DELETE = "admin.user.delete"
    USER_DISABLE = "admin.user.disable"
    
    # Interview events
    INTERVIEW_CREATE = "interview.create"
    INTERVIEW_START = "interview.start"
    INTERVIEW_COMPLETE = "interview.complete"
    INTERVIEW_CANCEL = "interview.cancel"
    
    # File events
    FILE_UPLOAD = "file.upload"
    FILE_DELETE = "file.delete"
    FILE_ACCESS = "file.access"
    
    # Security events
    SUSPICIOUS_ACTIVITY = "security.suspicious"
    RATE_LIMIT_EXCEEDED = "security.rate_limit"
    INVALID_TOKEN = "security.invalid_token"
    UNAUTHORIZED_ACCESS = "security.unauthorized"
    
    # System events
    SYSTEM_ERROR = "system.error"
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"


class AuditSeverity(str, Enum):
    """
    Audit event severity levels
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AuditContext:
    """
    Context information for audit events
    """
    user_id: Optional[int] = None
    user_email: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    tenant_id: Optional[int] = None
    
    # Additional context
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None
    resource_name: Optional[str] = None
    
    # Request details
    endpoint: Optional[str] = None
    method: Optional[str] = None
    status_code: Optional[int] = None
    
    # Geographic info (for compliance)
    country: Optional[str] = None
    region: Optional[str] = None


class AuditLog(Base):
    """
    Audit log database model
    Immutable audit trail for compliance
    """
    __tablename__ = "audit_logs"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Event identification
    event_id: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid.uuid4()))
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default=AuditSeverity.MEDIUM)
    
    # Temporal information
    timestamp: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False, 
        default=func.now(),
        index=True
    )
    
    # Actor information (WHO)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    user_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    
    # Location information (WHERE)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True, index=True)  # IPv6 support
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Resource information (WHAT)
    resource_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    resource_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    resource_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Request information
    endpoint: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    method: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    
    # Event details
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    
    # Tenant information (multi-tenancy)
    tenant_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    
    # Compliance fields
    retention_date: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<AuditLog {self.event_type} by user {self.user_id} at {self.timestamp}>"


class AuditLogger:
    """
    Enterprise audit logging service
    Thread-safe, async-compatible audit logging
    """
    
    def __init__(self):
        self.logger = logging.getLogger("audit")
        self._queue: List[Dict] = []
        self._batch_size = 100
        self._flush_interval = 60  # seconds
        
    async def log(
        self,
        event_type: AuditEventType,
        message: str,
        context: Optional[AuditContext] = None,
        severity: AuditSeverity = AuditSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Log an audit event
        """
        context = context or AuditContext()
        
        audit_record = {
            "event_type": event_type.value,
            "message": message,
            "severity": severity.value,
            "timestamp": dt.datetime.utcnow(),
            "details": details or {},
            **asdict(context)
        }
        
        # Store in database
        await self._store_audit_record(audit_record)
        
        # Also log to application logs
        self._log_to_app_logger(audit_record)
    
    async def _store_audit_record(self, record: Dict):
        """
        Store audit record in database
        """
        try:
            from src.db.session import async_session_factory
            
            async with async_session_factory() as session:
                audit_log = AuditLog(
                    event_type=record["event_type"],
                    severity=record["severity"],
                    message=record["message"],
                    user_id=record.get("user_id"),
                    user_email=record.get("user_email"),
                    session_id=record.get("session_id"),
                    ip_address=record.get("ip_address"),
                    user_agent=record.get("user_agent"),
                    country=record.get("country"),
                    region=record.get("region"),
                    resource_type=record.get("resource_type"),
                    resource_id=record.get("resource_id"),
                    resource_name=record.get("resource_name"),
                    endpoint=record.get("endpoint"),
                    method=record.get("method"),
                    status_code=record.get("status_code"),
                    request_id=record.get("request_id"),
                    tenant_id=record.get("tenant_id"),
                    details=record.get("details"),
                    retention_date=self._calculate_retention_date(record["event_type"])
                )
                
                session.add(audit_log)
                await session.commit()
                
        except Exception as e:
            # Critical: audit logging failure
            self.logger.error(f"Failed to store audit record: {e}", exc_info=True)
    
    def _log_to_app_logger(self, record: Dict):
        """
        Log to application logger for real-time monitoring
        """
        log_message = f"AUDIT [{record['event_type']}] {record['message']}"
        
        if record["severity"] == AuditSeverity.CRITICAL:
            self.logger.critical(log_message, extra=record)
        elif record["severity"] == AuditSeverity.HIGH:
            self.logger.error(log_message, extra=record)
        elif record["severity"] == AuditSeverity.MEDIUM:
            self.logger.warning(log_message, extra=record)
        else:
            self.logger.info(log_message, extra=record)
    
    def _calculate_retention_date(self, event_type: str) -> Optional[dt.datetime]:
        """
        Calculate retention date based on event type and compliance requirements
        """
        # Different retention periods for different event types
        retention_periods = {
            # Security events - 7 years (SOX compliance)
            "security": 7 * 365,
            "auth": 7 * 365,
            
            # Data access - 6 years (GDPR)
            "data": 6 * 365,
            
            # Admin events - 10 years
            "admin": 10 * 365,
            
            # System events - 1 year
            "system": 365,
            
            # Default - 3 years
            "default": 3 * 365
        }
        
        # Determine category
        category = "default"
        for cat in retention_periods:
            if event_type.startswith(cat):
                category = cat
                break
        
        days = retention_periods[category]
        return dt.datetime.utcnow() + dt.timedelta(days=days)
    
    async def search_audit_logs(
        self,
        start_date: Optional[dt.datetime] = None,
        end_date: Optional[dt.datetime] = None,
        user_id: Optional[int] = None,
        event_types: Optional[List[str]] = None,
        resource_type: Optional[str] = None,
        ip_address: Optional[str] = None,
        limit: int = 1000
    ) -> List[AuditLog]:
        """
        Search audit logs for compliance reporting
        """
        from src.db.session import async_session_factory
        from sqlalchemy import select, and_
        
        async with async_session_factory() as session:
            query = select(AuditLog)
            conditions = []
            
            if start_date:
                conditions.append(AuditLog.timestamp >= start_date)
            if end_date:
                conditions.append(AuditLog.timestamp <= end_date)
            if user_id:
                conditions.append(AuditLog.user_id == user_id)
            if event_types:
                conditions.append(AuditLog.event_type.in_(event_types))
            if resource_type:
                conditions.append(AuditLog.resource_type == resource_type)
            if ip_address:
                conditions.append(AuditLog.ip_address == ip_address)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            query = query.order_by(AuditLog.timestamp.desc()).limit(limit)
            
            result = await session.execute(query)
            return list(result.scalars().all())
    
    async def generate_compliance_report(
        self,
        start_date: dt.datetime,
        end_date: dt.datetime,
        report_type: str = "gdpr"
    ) -> Dict[str, Any]:
        """
        Generate compliance reports for auditors
        """
        logs = await self.search_audit_logs(start_date=start_date, end_date=end_date)
        
        # Categorize events
        report = {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "summary": {
                "total_events": len(logs),
                "security_events": len([l for l in logs if l.event_type.startswith("security")]),
                "data_access_events": len([l for l in logs if l.event_type.startswith("data")]),
                "auth_events": len([l for l in logs if l.event_type.startswith("auth")]),
                "admin_events": len([l for l in logs if l.event_type.startswith("admin")]),
            },
            "details": {
                "high_severity_events": [
                    {
                        "event_id": log.event_id,
                        "event_type": log.event_type,
                        "timestamp": log.timestamp.isoformat(),
                        "user_id": log.user_id,
                        "message": log.message
                    }
                    for log in logs if log.severity in [AuditSeverity.HIGH, AuditSeverity.CRITICAL]
                ]
            }
        }
        
        return report


# Global audit logger instance
audit_logger = AuditLogger()


# Convenience functions for common audit events
async def audit_login_success(user_id: int, email: str, context: AuditContext):
    """Log successful login"""
    await audit_logger.log(
        AuditEventType.LOGIN_SUCCESS,
        f"User {email} logged in successfully",
        context,
        AuditSeverity.LOW,
        {"user_id": user_id, "email": email}
    )


async def audit_login_failure(email: str, reason: str, context: AuditContext):
    """Log failed login attempt"""
    await audit_logger.log(
        AuditEventType.LOGIN_FAILURE,
        f"Failed login attempt for {email}: {reason}",
        context,
        AuditSeverity.MEDIUM,
        {"email": email, "failure_reason": reason}
    )


async def audit_data_access(user_id: int, resource_type: str, resource_id: int, action: str, context: AuditContext):
    """Log data access for GDPR compliance"""
    await audit_logger.log(
        AuditEventType.DATA_VIEW if action == "view" else AuditEventType.DATA_UPDATE,
        f"User {user_id} {action} {resource_type} {resource_id}",
        context,
        AuditSeverity.LOW,
        {"action": action, "resource_type": resource_type, "resource_id": resource_id}
    )


async def audit_security_event(event_type: str, details: Dict, context: AuditContext):
    """Log security events"""
    await audit_logger.log(
        AuditEventType.SUSPICIOUS_ACTIVITY,
        f"Security event: {event_type}",
        context,
        AuditSeverity.HIGH,
        details
    )


@asynccontextmanager
async def audit_context(user_id: Optional[int] = None, session_id: Optional[str] = None):
    """
    Context manager for audit logging
    Automatically captures context information
    """
    context = AuditContext(
        user_id=user_id,
        session_id=session_id,
        request_id=str(uuid.uuid4())
    )
    
    try:
        yield context
    except Exception as e:
        # Log exceptions as audit events
        await audit_logger.log(
            AuditEventType.SYSTEM_ERROR,
            f"System error: {str(e)}",
            context,
            AuditSeverity.HIGH,
            {"exception": str(e), "exception_type": type(e).__name__}
        )
        raise
