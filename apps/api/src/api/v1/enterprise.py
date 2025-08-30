"""
Enterprise API Endpoints
Health checks, GDPR endpoints, and system monitoring
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from typing import Dict, Any, Optional
import io
from src.core.health import get_health_status, get_readiness_status, get_liveness_status
from src.core.gdpr import gdpr_manager, DataSubjectRequestType
from src.core.rbac import rbac_manager, Permission, AccessContext, ResourceType
from src.core.audit import audit_logger, AuditEventType, AuditContext, AuditSeverity
from src.auth import current_active_user
from src.db.models.user import User


router = APIRouter(prefix="/enterprise", tags=["enterprise"])


# Health Check Endpoints
@router.get("/health")
async def health_check():
    """Comprehensive health check for monitoring systems"""
    return await get_health_status()


@router.get("/health/ready")
async def readiness_check():
    """Kubernetes readiness probe"""
    result = await get_readiness_status()
    if not result["ready"]:
        raise HTTPException(status_code=503, detail="Service not ready")
    return result


@router.get("/health/live")
async def liveness_check():
    """Kubernetes liveness probe"""
    result = await get_liveness_status()
    if not result["alive"]:
        raise HTTPException(status_code=503, detail="Service not alive")
    return result


# GDPR Data Subject Rights Endpoints
@router.post("/gdpr/access-request")
async def submit_data_access_request(
    subject_email: str,
    request: Request,
    subject_name: Optional[str] = None
):
    """Submit GDPR data access request (Article 15)"""

    # Log the request
    context = AuditContext(
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
        endpoint="/enterprise/gdpr/access-request",
        method="POST"
    )
    
    await audit_logger.log(
        AuditEventType.DATA_VIEW,
        f"GDPR access request submitted for {subject_email}",
        context,
        AuditSeverity.MEDIUM,
        {"subject_email": subject_email, "subject_name": subject_name}
    )
    
    request_id = await gdpr_manager.submit_access_request(
        subject_email=subject_email,
        subject_name=subject_name
    )
    
    return {
        "request_id": request_id,
        "status": "submitted",
        "message": "Data access request submitted. You will receive an email with further instructions.",
        "estimated_completion": "Within 30 days as per GDPR requirements"
    }


@router.post("/gdpr/erasure-request")
async def submit_data_erasure_request(
    subject_email: str,
    reason: str,
    request: Request
):
    """Submit GDPR data erasure request (Article 17 - Right to be forgotten)"""

    # Log the request
    context = AuditContext(
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
        endpoint="/enterprise/gdpr/erasure-request",
        method="POST"
    )
    
    await audit_logger.log(
        AuditEventType.DATA_DELETE,
        f"GDPR erasure request submitted for {subject_email}",
        context,
        AuditSeverity.HIGH,
        {"subject_email": subject_email, "reason": reason}
    )
    
    request_id = await gdpr_manager.submit_erasure_request(
        subject_email=subject_email,
        reason=reason
    )
    
    return {
        "request_id": request_id,
        "status": "submitted",
        "message": "Data erasure request submitted. We will review and process within 30 days.",
        "note": "Some data may be retained for legal compliance purposes."
    }


@router.get("/gdpr/export-data")
async def export_personal_data(
    subject_email: str,
    format_type: str = "json",
    user: User = Depends(current_active_user)
):
    """Export personal data (Article 20 - Data portability)"""
    
    # Check permission
    context = AccessContext(user_id=user.id)
    has_permission = await rbac_manager.check_permission(context, Permission.DATA_EXPORT)
    
    if not has_permission:
        raise HTTPException(status_code=403, detail="Insufficient permissions for data export")
    
    # Export data
    data = await gdpr_manager.export_personal_data(subject_email, format_type)
    
    # Log the export
    audit_context = AuditContext(
        user_id=user.id,
        user_email=user.email,
        endpoint="/enterprise/gdpr/export-data",
        method="GET"
    )
    
    await audit_logger.log(
        AuditEventType.DATA_EXPORT,
        f"Personal data exported for {subject_email}",
        audit_context,
        AuditSeverity.HIGH,
        {"subject_email": subject_email, "format": format_type, "exported_by": user.email}
    )
    
    # Return as download
    if format_type == "json":
        return StreamingResponse(
            io.BytesIO(data),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=personal_data_{subject_email}.json"}
        )
    elif format_type == "zip":
        return StreamingResponse(
            io.BytesIO(data),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename=personal_data_{subject_email}.zip"}
        )
    else:
        raise HTTPException(status_code=400, detail="Unsupported format type")


# RBAC Management Endpoints
@router.post("/rbac/grant-permission")
async def grant_resource_permission(
    target_user_id: int,
    resource_type: ResourceType,
    resource_id: int,
    access_level: str,
    user: User = Depends(current_active_user)
):
    """Grant resource-specific permission to user"""
    
    # Check if current user can grant permissions
    context = AccessContext(user_id=user.id)
    has_permission = await rbac_manager.check_permission(context, Permission.USER_UPDATE)
    
    if not has_permission:
        raise HTTPException(status_code=403, detail="Cannot grant permissions")
    
    from src.core.rbac import AccessLevel
    await rbac_manager.grant_permission(
        user_id=target_user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        access_level=AccessLevel(access_level),
        granted_by=user.id
    )
    
    # Log the permission grant
    audit_context = AuditContext(
        user_id=user.id,
        user_email=user.email,
        endpoint="/enterprise/rbac/grant-permission",
        method="POST"
    )
    
    await audit_logger.log(
        AuditEventType.ACCESS_GRANTED,
        f"Permission granted to user {target_user_id}",
        audit_context,
        AuditSeverity.MEDIUM,
        {
            "target_user_id": target_user_id,
            "resource_type": resource_type.value,
            "resource_id": resource_id,
            "access_level": access_level,
            "granted_by": user.id
        }
    )
    
    return {
        "status": "success",
        "message": f"Permission granted to user {target_user_id}",
        "details": {
            "resource_type": resource_type.value,
            "resource_id": resource_id,
            "access_level": access_level
        }
    }


# System Monitoring Endpoints
@router.get("/metrics/system")
async def get_system_metrics(user: User = Depends(current_active_user)):
    """Get system performance metrics"""
    
    # Check permission
    context = AccessContext(user_id=user.id)
    has_permission = await rbac_manager.check_permission(context, Permission.SYSTEM_MONITOR)
    
    if not has_permission:
        raise HTTPException(status_code=403, detail="Insufficient permissions for system monitoring")
    
    from src.core.metrics import collector
    metrics = collector.snapshot()
    
    # Add additional system info
    import psutil
    system_info = {
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": round((psutil.disk_usage('/').used / psutil.disk_usage('/').total) * 100, 2),
        "active_connections": len(psutil.net_connections()),
        "boot_time": psutil.boot_time()
    }
    
    return {
        "timestamp": "2024-01-15T10:30:00Z",
        "application_metrics": metrics,
        "system_metrics": system_info
    }


@router.get("/audit/search")
async def search_audit_logs(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user_id: Optional[int] = None,
    event_type: Optional[str] = None,
    limit: int = 100,
    user: User = Depends(current_active_user)
):
    """Search audit logs for compliance reporting"""
    
    # Check permission
    context = AccessContext(user_id=user.id)
    has_permission = await rbac_manager.check_permission(context, Permission.ADMIN_LOGS)
    
    if not has_permission:
        raise HTTPException(status_code=403, detail="Insufficient permissions for audit log access")
    
    # Parse dates
    from datetime import datetime
    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None
    
    # Search logs
    logs = await audit_logger.search_audit_logs(
        start_date=start_dt,
        end_date=end_dt,
        user_id=user_id,
        event_types=[event_type] if event_type else None,
        limit=limit
    )
    
    # Convert to dict
    results = []
    for log in logs:
        results.append({
            "event_id": log.event_id,
            "event_type": log.event_type,
            "timestamp": log.timestamp.isoformat(),
            "user_id": log.user_id,
            "user_email": log.user_email,
            "ip_address": log.ip_address,
            "message": log.message,
            "details": log.details
        })
    
    return {
        "total_results": len(results),
        "limit": limit,
        "logs": results
    }


@router.get("/compliance/report")
async def generate_compliance_report(
    start_date: str,
    end_date: str,
    report_type: str = "gdpr",
    user: User = Depends(current_active_user)
):
    """Generate compliance report for auditors"""
    
    # Check permission
    context = AccessContext(user_id=user.id)
    has_permission = await rbac_manager.check_permission(context, Permission.ADMIN_LOGS)
    
    if not has_permission:
        raise HTTPException(status_code=403, detail="Insufficient permissions for compliance reporting")
    
    # Parse dates
    from datetime import datetime
    start_dt = datetime.fromisoformat(start_date)
    end_dt = datetime.fromisoformat(end_date)
    
    # Generate report
    report = await audit_logger.generate_compliance_report(start_dt, end_dt, report_type)
    
    # Log report generation
    audit_context = AuditContext(
        user_id=user.id,
        user_email=user.email,
        endpoint="/enterprise/compliance/report",
        method="GET"
    )
    
    await audit_logger.log(
        AuditEventType.DATA_EXPORT,
        f"Compliance report generated ({report_type})",
        audit_context,
        AuditSeverity.HIGH,
        {"report_type": report_type, "start_date": start_date, "end_date": end_date}
    )
    
    return report
