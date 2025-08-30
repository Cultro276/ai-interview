"""
Enterprise Health Check System
Comprehensive monitoring for all application components
Kubernetes/Docker ready health checks
"""
import asyncio
import time
import psutil
import httpx
from typing import Dict, List, Any, Optional, Union, cast
from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging


class HealthStatus(str, Enum):
    """Health check status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


class ComponentType(str, Enum):
    """Types of components to monitor"""
    DATABASE = "database"
    EXTERNAL_API = "external_api"
    STORAGE = "storage"
    CACHE = "cache"
    QUEUE = "queue"
    SYSTEM_RESOURCE = "system_resource"
    APPLICATION = "application"


@dataclass
class HealthCheckResult:
    """Result of a health check"""
    component: str
    component_type: ComponentType
    status: HealthStatus
    response_time_ms: float
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    error: Optional[str] = None


class BaseHealthCheck:
    """Base class for health checks"""
    
    def __init__(self, name: str, component_type: ComponentType, timeout: float = 5.0):
        self.name = name
        self.component_type = component_type
        self.timeout = timeout
        self.logger = logging.getLogger(f"health.{name}")
    
    async def check(self) -> HealthCheckResult:
        """Perform the health check"""
        start_time = time.time()
        
        try:
            # Perform the actual check with timeout
            result = await asyncio.wait_for(
                self._perform_check(),
                timeout=self.timeout
            )
            
            response_time = round((time.time() - start_time) * 1000, 2)
            
            return HealthCheckResult(
                component=self.name,
                component_type=self.component_type,
                status=result["status"],
                response_time_ms=response_time,
                message=result["message"],
                details=result.get("details", {}),
                timestamp=datetime.utcnow(),
                error=result.get("error")
            )
            
        except asyncio.TimeoutError:
            response_time = round((time.time() - start_time) * 1000, 2)
            return HealthCheckResult(
                component=self.name,
                component_type=self.component_type,
                status=HealthStatus.CRITICAL,
                response_time_ms=response_time,
                message=f"Health check timed out after {self.timeout}s",
                details={},
                timestamp=datetime.utcnow(),
                error="timeout"
            )
            
        except Exception as e:
            response_time = round((time.time() - start_time) * 1000, 2)
            self.logger.error(f"Health check failed: {e}")
            
            return HealthCheckResult(
                component=self.name,
                component_type=self.component_type,
                status=HealthStatus.CRITICAL,
                response_time_ms=response_time,
                message=f"Health check failed: {str(e)}",
                details={},
                timestamp=datetime.utcnow(),
                error=str(e)
            )
    
    async def _perform_check(self) -> Dict[str, Any]:
        """Override this method to implement specific health check logic"""
        raise NotImplementedError


class DatabaseHealthCheck(BaseHealthCheck):
    """Health check for database connectivity and performance"""
    
    def __init__(self):
        super().__init__("database", ComponentType.DATABASE, timeout=10.0)
    
    async def _perform_check(self) -> Dict[str, Any]:
        from src.db.session import async_session_factory
        from sqlalchemy import text
        
        async with async_session_factory() as session:
            # Test basic connectivity
            start_time = time.time()
            result = await session.execute(text("SELECT 1"))
            query_time = round((time.time() - start_time) * 1000, 2)
            
            # Test table access
            result = await session.execute(text("SELECT COUNT(*) FROM users"))
            user_count = result.scalar()
            
            # Database health details
            details = {
                "query_response_time_ms": query_time,
                "user_count": user_count,
                "connection_info": "database connection successful"
            }
            
            # Determine status based on performance
            if query_time > 1000:  # 1 second
                status = HealthStatus.DEGRADED
                message = f"Database responding slowly ({query_time}ms)"
            elif query_time > 5000:  # 5 seconds
                status = HealthStatus.UNHEALTHY
                message = f"Database very slow ({query_time}ms)"
            else:
                status = HealthStatus.HEALTHY
                message = f"Database healthy ({query_time}ms)"
            
            return {
                "status": status,
                "message": message,
                "details": details
            }


class ExternalAPIHealthCheck(BaseHealthCheck):
    """Health check for external API dependencies"""
    
    def __init__(self, name: str, url: str, expected_status: int = 200):
        super().__init__(f"external_api_{name}", ComponentType.EXTERNAL_API, timeout=15.0)
        self.url = url
        self.expected_status = expected_status
    
    async def _perform_check(self) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(self.url)
            
            details = {
                "url": self.url,
                "status_code": response.status_code,
                "response_time_ms": round(response.elapsed.total_seconds() * 1000, 2),
                "expected_status": self.expected_status
            }
            
            if response.status_code == self.expected_status:
                status = HealthStatus.HEALTHY
                message = f"API responding normally (HTTP {response.status_code})"
            elif 200 <= response.status_code < 300:
                status = HealthStatus.HEALTHY
                message = f"API responding with different success code (HTTP {response.status_code})"
            elif 400 <= response.status_code < 500:
                status = HealthStatus.DEGRADED
                message = f"API client error (HTTP {response.status_code})"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"API server error (HTTP {response.status_code})"
            
            return {
                "status": status,
                "message": message,
                "details": details
            }


class SystemResourceHealthCheck(BaseHealthCheck):
    """Health check for system resources (CPU, Memory, Disk)"""
    
    def __init__(self):
        super().__init__("system_resources", ComponentType.SYSTEM_RESOURCE, timeout=5.0)
    
    async def _perform_check(self) -> Dict[str, Any]:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_available_gb = round(memory.available / (1024**3), 2)
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_percent = round((disk.used / disk.total) * 100, 2)
        disk_free_gb = round(disk.free / (1024**3), 2)
        
        # Network I/O
        network = psutil.net_io_counters()
        
        # Process info
        process = psutil.Process()
        process_memory_mb = round(process.memory_info().rss / (1024**2), 2)
        process_cpu_percent = process.cpu_percent()
        
        details = {
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
            "memory_available_gb": memory_available_gb,
            "disk_percent": disk_percent,
            "disk_free_gb": disk_free_gb,
            "network_bytes_sent": network.bytes_sent,
            "network_bytes_recv": network.bytes_recv,
            "process_memory_mb": process_memory_mb,
            "process_cpu_percent": process_cpu_percent,
            "load_average": list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else None
        }
        
        # Determine overall status
        issues = []
        
        if cpu_percent > 90:
            issues.append(f"High CPU usage ({cpu_percent}%)")
        if memory_percent > 90:
            issues.append(f"High memory usage ({memory_percent}%)")
        if disk_percent > 90:
            issues.append(f"High disk usage ({disk_percent}%)")
        if disk_free_gb < 1:
            issues.append(f"Low disk space ({disk_free_gb}GB free)")
        
        if issues:
            if cpu_percent > 95 or memory_percent > 95 or disk_percent > 95:
                status = HealthStatus.CRITICAL
            else:
                status = HealthStatus.DEGRADED
            message = f"Resource issues: {', '.join(issues)}"
        else:
            status = HealthStatus.HEALTHY
            message = f"Resources healthy (CPU: {cpu_percent}%, Mem: {memory_percent}%, Disk: {disk_percent}%)"
        
        return {
            "status": status,
            "message": message,
            "details": details
        }


class ApplicationHealthCheck(BaseHealthCheck):
    """Health check for application-specific metrics"""
    
    def __init__(self):
        super().__init__("application", ComponentType.APPLICATION, timeout=5.0)
    
    async def _perform_check(self) -> Dict[str, Any]:
        from src.core.metrics import collector
        
        # Get application metrics
        metrics = collector.snapshot()
        
        # Check recent activity
        now = datetime.utcnow()
        recent_threshold = now - timedelta(minutes=5)
        
        details = {
            "metrics": metrics,
            "uptime_seconds": time.time() - self._get_start_time(),
            "active_sessions": await self._count_active_sessions(),
            "recent_interviews": await self._count_recent_interviews(recent_threshold),
            "error_rate": metrics.get("error_rate", 0)
        }
        
        # Determine status
        error_rate = metrics.get("error_rate", 0)
        
        if error_rate > 0.1:  # 10% error rate
            status = HealthStatus.CRITICAL
            message = f"High error rate ({error_rate:.1%})"
        elif error_rate > 0.05:  # 5% error rate
            status = HealthStatus.DEGRADED
            message = f"Elevated error rate ({error_rate:.1%})"
        else:
            status = HealthStatus.HEALTHY
            message = f"Application healthy (error rate: {error_rate:.1%})"
        
        return {
            "status": status,
            "message": message,
            "details": details
        }
    
    def _get_start_time(self) -> float:
        """Get application start time"""
        # In production, this would be tracked properly
        return time.time() - 3600  # Mock: 1 hour ago
    
    async def _count_active_sessions(self) -> int:
        """Count active user sessions"""
        # Implementation would query session store
        return 42  # Mock value
    
    async def _count_recent_interviews(self, since: datetime) -> int:
        """Count recent interviews"""
        from src.db.session import async_session_factory
        from src.db.models.interview import Interview
        from sqlalchemy import select, func
        
        try:
            async with async_session_factory() as session:
                query = select(func.count(Interview.id)).where(
                    Interview.created_at >= since
                )
                result = await session.execute(query)
                return result.scalar() or 0
        except:
            return 0


class HealthCheckManager:
    """Manages all health checks and provides aggregated status"""
    
    def __init__(self):
        self.checks: List[BaseHealthCheck] = []
        self.logger = logging.getLogger("health.manager")
        self._setup_checks()
    
    def _setup_checks(self):
        """Setup all health checks"""
        # Core checks
        self.checks.append(DatabaseHealthCheck())
        self.checks.append(SystemResourceHealthCheck())
        self.checks.append(ApplicationHealthCheck())
        
        # External API checks
        self.checks.append(ExternalAPIHealthCheck(
            "openai", 
            "https://api.openai.com/v1/models",
            expected_status=200
        ))
        
        # Add more checks as needed
        # self.checks.append(ExternalAPIHealthCheck("gemini", "https://generativelanguage.googleapis.com/"))
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks and return aggregated results"""
        start_time = time.time()
        
        # Run all checks concurrently
        tasks = [check.check() for check in self.checks]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        check_results = []
        status_counts = {status: 0 for status in HealthStatus}
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Handle check that failed with exception
                check_results.append(HealthCheckResult(
                    component=self.checks[i].name,
                    component_type=self.checks[i].component_type,
                    status=HealthStatus.CRITICAL,
                    response_time_ms=0,
                    message=f"Check failed with exception: {str(result)}",
                    details={},
                    timestamp=datetime.utcnow(),
                    error=str(result)
                ))
                status_counts[HealthStatus.CRITICAL] += 1
            else:
                # result is a HealthCheckResult
                health_result = cast(HealthCheckResult, result)
                check_results.append(health_result)
                status_counts[health_result.status] += 1
        
        # Determine overall status
        overall_status = self._calculate_overall_status(status_counts)
        
        # Calculate total response time
        total_time = round((time.time() - start_time) * 1000, 2)
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "total_checks": len(check_results),
            "total_response_time_ms": total_time,
            "status_summary": status_counts,
            "checks": [asdict(result) for result in check_results],
            "version": "1.0.0",
            "environment": "production"
        }
    
    def _calculate_overall_status(self, status_counts: Dict[HealthStatus, int]) -> HealthStatus:
        """Calculate overall system status from individual check results"""
        if status_counts[HealthStatus.CRITICAL] > 0:
            return HealthStatus.CRITICAL
        elif status_counts[HealthStatus.UNHEALTHY] > 0:
            return HealthStatus.UNHEALTHY
        elif status_counts[HealthStatus.DEGRADED] > 0:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY
    
    async def run_readiness_check(self) -> Dict[str, Any]:
        """Simplified readiness check for Kubernetes"""
        # Only run critical checks for readiness
        critical_checks = [
            check for check in self.checks 
            if check.component_type in [ComponentType.DATABASE, ComponentType.APPLICATION]
        ]
        
        start_time = time.time()
        tasks = [check.check() for check in critical_checks]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check if any critical component is unhealthy
        ready = True
        issues = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                ready = False
                issues.append(f"{critical_checks[i].name}: exception")
            elif cast(HealthCheckResult, result).status in [HealthStatus.CRITICAL, HealthStatus.UNHEALTHY]:
                ready = False
                issues.append(f"{critical_checks[i].name}: {cast(HealthCheckResult, result).status}")
        
        total_time = round((time.time() - start_time) * 1000, 2)
        
        return {
            "ready": ready,
            "timestamp": datetime.utcnow().isoformat(),
            "response_time_ms": total_time,
            "issues": issues
        }
    
    async def run_liveness_check(self) -> Dict[str, Any]:
        """Simplified liveness check for Kubernetes"""
        # Basic application liveness check
        start_time = time.time()
        
        try:
            # Check if the application is responsive
            await asyncio.sleep(0.001)  # Minimal check
            
            alive = True
            message = "Application is alive"
        except Exception as e:
            alive = False
            message = f"Application not responding: {str(e)}"
        
        total_time = round((time.time() - start_time) * 1000, 2)
        
        return {
            "alive": alive,
            "timestamp": datetime.utcnow().isoformat(),
            "response_time_ms": total_time,
            "message": message
        }


# Global health check manager
health_manager = HealthCheckManager()


# Helper functions for FastAPI endpoints
async def get_health_status() -> Dict[str, Any]:
    """Get comprehensive health status"""
    return await health_manager.run_all_checks()


async def get_readiness_status() -> Dict[str, Any]:
    """Get readiness status for Kubernetes"""
    return await health_manager.run_readiness_check()


async def get_liveness_status() -> Dict[str, Any]:
    """Get liveness status for Kubernetes"""
    return await health_manager.run_liveness_check()
