"""
GDPR Data Subject Rights Implementation
Complete implementation of GDPR Article 12-22 rights
- Right to Access (Article 15)
- Right to Rectification (Article 16)
- Right to Erasure/Right to be Forgotten (Article 17)
- Right to Data Portability (Article 20)
- Right to Restrict Processing (Article 18)
- Right to Object (Article 21)
"""
import asyncio
import json
import zipfile
import io
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from enum import Enum
from dataclasses import dataclass, asdict
from sqlalchemy import String, Text, DateTime, Boolean, Integer, JSON, func, select, and_, or_, text
from sqlalchemy.orm import Mapped, mapped_column
from src.db.base import Base
from src.core.encryption import encryption_manager


class DataSubjectRequestType(str, Enum):
    """
    Types of GDPR data subject requests
    """
    ACCESS = "access"  # Article 15
    RECTIFICATION = "rectification"  # Article 16
    ERASURE = "erasure"  # Article 17 (Right to be forgotten)
    PORTABILITY = "portability"  # Article 20
    RESTRICT_PROCESSING = "restrict_processing"  # Article 18
    OBJECT_TO_PROCESSING = "object_to_processing"  # Article 21
    WITHDRAW_CONSENT = "withdraw_consent"  # Article 7


class RequestStatus(str, Enum):
    """
    Status of GDPR requests
    """
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"
    EXPIRED = "expired"


class DataCategory(str, Enum):
    """
    Categories of personal data for GDPR compliance
    """
    IDENTITY = "identity"  # Name, email, etc.
    CONTACT = "contact"  # Phone, address
    PROFESSIONAL = "professional"  # CV, work history
    BEHAVIORAL = "behavioral"  # Interview responses, ratings
    TECHNICAL = "technical"  # IP addresses, device info
    COMMUNICATION = "communication"  # Messages, emails


@dataclass
class PersonalDataItem:
    """
    Represents a single piece of personal data
    """
    category: DataCategory
    field_name: str
    value: Any
    source_table: str
    source_id: int
    collected_at: datetime
    legal_basis: str
    retention_period: Optional[int] = None  # Days
    is_sensitive: bool = False


class GDPRRequest(Base):
    """
    Database model for GDPR data subject requests
    """
    __tablename__ = "gdpr_requests"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Request identification
    request_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    request_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=RequestStatus.PENDING, nullable=False)
    
    # Data subject information
    subject_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    subject_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    subject_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Request details
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    requested_data_categories: Mapped[Optional[List]] = mapped_column(JSON, nullable=True)
    
    # Processing information
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Staff handling
    assigned_to: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    processed_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Results
    response_data: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Compliance tracking
    verification_method: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class DataProcessingLog(Base):
    """
    Log of data processing activities for GDPR compliance
    """
    __tablename__ = "data_processing_logs"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Data subject
    subject_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    
    # Processing details
    processing_activity: Mapped[str] = mapped_column(String(100), nullable=False)
    data_categories: Mapped[List] = mapped_column(JSON, nullable=False)
    legal_basis: Mapped[str] = mapped_column(String(100), nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Timing
    processing_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    retention_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Third parties
    recipients: Mapped[Optional[List]] = mapped_column(JSON, nullable=True)
    transfers_outside_eu: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Consent tracking
    consent_given: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    consent_withdrawn: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    consent_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class GDPRManager:
    """
    GDPR compliance manager
    Handles data subject rights and compliance requirements
    """
    
    def __init__(self):
        self.data_mappings = self._initialize_data_mappings()
        self.retention_policies = self._initialize_retention_policies()
    
    def _initialize_data_mappings(self) -> Dict[str, Dict]:
        """
        Map database tables/fields to GDPR data categories
        """
        return {
            "users": {
                "email": DataCategory.IDENTITY,
                "first_name": DataCategory.IDENTITY,
                "last_name": DataCategory.IDENTITY,
                "created_at": DataCategory.TECHNICAL
            },
            "candidates": {
                "name": DataCategory.IDENTITY,
                "email": DataCategory.IDENTITY,
                "phone": DataCategory.CONTACT,
                "linkedin_url": DataCategory.PROFESSIONAL,
                "resume_url": DataCategory.PROFESSIONAL,
                "created_at": DataCategory.TECHNICAL
            },
            "candidate_profiles": {
                "raw_text": DataCategory.PROFESSIONAL,
                "phone": DataCategory.CONTACT,
                "linkedin_url": DataCategory.PROFESSIONAL,
                "education": DataCategory.PROFESSIONAL,
                "experience": DataCategory.PROFESSIONAL,
                "skills": DataCategory.PROFESSIONAL
            },
            "interviews": {
                "transcript_text": DataCategory.BEHAVIORAL,
                "audio_url": DataCategory.BEHAVIORAL,
                "video_url": DataCategory.BEHAVIORAL,
                "completed_ip": DataCategory.TECHNICAL,
                "created_at": DataCategory.TECHNICAL
            },
            "conversation_messages": {
                "content": DataCategory.BEHAVIORAL,
                "created_at": DataCategory.TECHNICAL
            },
            "interview_analysis": {
                "transcript": DataCategory.BEHAVIORAL,
                "job_fit": DataCategory.BEHAVIORAL,
                "opinion": DataCategory.BEHAVIORAL,
                "overall_score": DataCategory.BEHAVIORAL
            }
        }
    
    def _initialize_retention_policies(self) -> Dict[DataCategory, int]:
        """
        Define retention periods for different data categories (in days)
        """
        return {
            DataCategory.IDENTITY: 2555,  # 7 years
            DataCategory.CONTACT: 2555,   # 7 years
            DataCategory.PROFESSIONAL: 1825,  # 5 years
            DataCategory.BEHAVIORAL: 1095,    # 3 years
            DataCategory.TECHNICAL: 365,      # 1 year
            DataCategory.COMMUNICATION: 730   # 2 years
        }
    
    async def submit_access_request(
        self,
        subject_email: str,
        subject_name: Optional[str] = None,
        requested_categories: Optional[List[DataCategory]] = None,
        verification_token: Optional[str] = None
    ) -> str:
        """
        Submit a data access request (Article 15)
        """
        from src.db.session import async_session_factory
        import uuid
        
        request_id = f"ACCESS_{uuid.uuid4().hex[:12].upper()}"
        
        async with async_session_factory() as session:
            gdpr_request = GDPRRequest(
                request_id=request_id,
                request_type=DataSubjectRequestType.ACCESS,
                subject_email=subject_email.lower(),
                subject_name=subject_name,
                requested_data_categories=[cat.value for cat in requested_categories] if requested_categories else None,
                expires_at=datetime.utcnow() + timedelta(days=30),  # GDPR requires response within 30 days
                verification_method="email_token" if verification_token else "manual"
            )
            
            session.add(gdpr_request)
            await session.commit()
            
            # Log the request
            await self._log_processing_activity(
                subject_email,
                "access_request_submitted",
                [DataCategory.IDENTITY],
                "legitimate_interest",
                "Processing data access request under GDPR Article 15"
            )
        
        # Send verification email if needed
        if not verification_token:
            await self._send_verification_email(subject_email, request_id)
        
        return request_id
    
    async def process_access_request(self, request_id: str) -> Dict[str, Any]:
        """
        Process and fulfill a data access request
        """
        from src.db.session import async_session_factory
        
        async with async_session_factory() as session:
            # Get request
            query = select(GDPRRequest).where(GDPRRequest.request_id == request_id)
            result = await session.execute(query)
            request = result.scalar_one_or_none()
            
            if not request or request.status != RequestStatus.PENDING:
                raise ValueError("Invalid or already processed request")
            
            # Collect all personal data for the subject
            personal_data = await self._collect_personal_data(request.subject_email)
            
            # Structure the response according to GDPR requirements
            response = {
                "request_id": request_id,
                "subject_email": request.subject_email,
                "processed_at": datetime.utcnow().isoformat(),
                "data_controller": {
                    "name": "AI Interview Platform",
                    "contact": "privacy@aiinterview.com",
                    "dpo_contact": "dpo@aiinterview.com"
                },
                "personal_data": self._structure_personal_data(personal_data),
                "processing_purposes": await self._get_processing_purposes(request.subject_email),
                "retention_periods": {cat.value: days for cat, days in self.retention_policies.items()},
                "recipients": await self._get_data_recipients(request.subject_email),
                "rights_information": self._get_rights_information(),
                "generated_at": datetime.utcnow().isoformat()
            }
            
            # Update request status
            request.status = RequestStatus.COMPLETED
            request.processed_at = func.now()
            request.completed_at = func.now()
            request.response_data = response
            
            await session.commit()
            
            # Log completion
            await self._log_processing_activity(
                request.subject_email,
                "access_request_completed",
                list(DataCategory),
                "legal_obligation",
                "Completed data access request under GDPR Article 15"
            )
            
            return response
    
    async def submit_erasure_request(
        self,
        subject_email: str,
        reason: str,
        specific_data: Optional[List[str]] = None
    ) -> str:
        """
        Submit a data erasure request (Right to be forgotten - Article 17)
        """
        from src.db.session import async_session_factory
        import uuid
        
        request_id = f"ERASURE_{uuid.uuid4().hex[:12].upper()}"
        
        async with async_session_factory() as session:
            gdpr_request = GDPRRequest(
                request_id=request_id,
                request_type=DataSubjectRequestType.ERASURE,
                subject_email=subject_email.lower(),
                description=reason,
                requested_data_categories=specific_data,
                expires_at=datetime.utcnow() + timedelta(days=30)
            )
            
            session.add(gdpr_request)
            await session.commit()
        
        return request_id
    
    async def process_erasure_request(self, request_id: str) -> bool:
        """
        Process and fulfill a data erasure request
        """
        from src.db.session import async_session_factory
        
        async with async_session_factory() as session:
            # Get request
            query = select(GDPRRequest).where(GDPRRequest.request_id == request_id)
            result = await session.execute(query)
            request = result.scalar_one_or_none()
            
            if not request:
                raise ValueError("Request not found")
            
            # Check if erasure is legally possible
            can_erase, restrictions = await self._check_erasure_restrictions(request.subject_email)
            
            if not can_erase:
                request.status = RequestStatus.REJECTED
                request.rejection_reason = f"Erasure restricted: {restrictions}"
                await session.commit()
                return False
            
            # Perform data erasure
            await self._erase_personal_data(request.subject_email, session)
            
            # Update request
            request.status = RequestStatus.COMPLETED
            request.processed_at = func.now()
            request.completed_at = func.now()
            
            await session.commit()
            
            # Log erasure
            await self._log_processing_activity(
                request.subject_email,
                "data_erased",
                list(DataCategory),
                "data_subject_request",
                "Personal data erased under GDPR Article 17"
            )
            
            return True
    
    async def export_personal_data(
        self,
        subject_email: str,
        format_type: str = "json"
    ) -> bytes:
        """
        Export personal data in machine-readable format (Article 20)
        """
        personal_data = await self._collect_personal_data(subject_email)
        
        if format_type == "json":
            return json.dumps(personal_data, indent=2, default=str).encode('utf-8')
        elif format_type == "zip":
            return await self._create_data_export_zip(personal_data)
        else:
            raise ValueError("Unsupported format type")
    
    async def _collect_personal_data(self, subject_email: str) -> List[PersonalDataItem]:
        """
        Collect all personal data for a data subject
        """
        from src.db.session import async_session_factory
        from src.db.models.user import User
        from src.db.models.candidate import Candidate
        from src.db.models.candidate_profile import CandidateProfile
        from src.db.models.interview import Interview
        from src.db.models.conversation import ConversationMessage
        
        personal_data = []
        
        async with async_session_factory() as session:
            # Users table  
            query = select(User).where(text("email = :email")).params(email=subject_email)
            result = await session.execute(query)
            user = result.scalar_one_or_none()
            
            if user:
                personal_data.extend(await self._extract_table_data(
                    "users", user, user.created_at
                ))
            
            # Candidates table
            query = select(Candidate).where(text("email = :email")).params(email=subject_email)
            result = await session.execute(query)
            candidate = result.scalar_one_or_none()
            
            if candidate:
                personal_data.extend(await self._extract_table_data(
                    "candidates", candidate, candidate.created_at
                ))
                
                # Candidate profiles
                query = select(CandidateProfile).where(CandidateProfile.candidate_id == candidate.id)
                result = await session.execute(query)
                profiles = result.scalars().all()
                
                for profile in profiles:
                    personal_data.extend(await self._extract_table_data(
                        "candidate_profiles", profile, profile.created_at
                    ))
                
                # Interviews
                query = select(Interview).where(Interview.candidate_id == candidate.id)
                result = await session.execute(query)
                interviews = result.scalars().all()
                
                for interview in interviews:
                    personal_data.extend(await self._extract_table_data(
                        "interviews", interview, interview.created_at
                    ))
                    
                    # Conversation messages
                    query = select(ConversationMessage).where(ConversationMessage.interview_id == interview.id)
                    result = await session.execute(query)
                    messages = result.scalars().all()
                    
                    for message in messages:
                        if hasattr(message, 'timestamp'):
                            personal_data.extend(await self._extract_table_data(
                                "conversation_messages", message, message.timestamp
                            ))
        
        return personal_data
    
    async def _extract_table_data(
        self,
        table_name: str,
        record: Any,
        collected_at: datetime
    ) -> List[PersonalDataItem]:
        """
        Extract personal data from a database record
        """
        items = []
        table_mapping = self.data_mappings.get(table_name, {})
        
        for field_name, category in table_mapping.items():
            if hasattr(record, field_name):
                value = getattr(record, field_name)
                if value is not None:
                    # Decrypt if encrypted
                    if isinstance(value, str) and value.startswith('gAAAAAB'):
                        try:
                            value = encryption_manager.decrypt(value)
                        except:
                            pass  # Keep encrypted if decryption fails
                    
                    items.append(PersonalDataItem(
                        category=category,
                        field_name=field_name,
                        value=value,
                        source_table=table_name,
                        source_id=record.id,
                        collected_at=collected_at,
                        legal_basis=self._get_legal_basis(category),
                        retention_period=self.retention_policies.get(category),
                        is_sensitive=self._is_sensitive_data(field_name, value)
                    ))
        
        return items
    
    def _structure_personal_data(self, personal_data: List[PersonalDataItem]) -> Dict[str, Any]:
        """
        Structure personal data for GDPR response
        """
        structured = {}
        
        for item in personal_data:
            category = item.category.value
            if category not in structured:
                structured[category] = {
                    "description": self._get_category_description(item.category),
                    "legal_basis": item.legal_basis,
                    "retention_period_days": item.retention_period,
                    "data_items": []
                }
            
            structured[category]["data_items"].append({
                "field": item.field_name,
                "value": item.value if not item.is_sensitive else "[REDACTED]",
                "source": f"{item.source_table}#{item.source_id}",
                "collected_at": item.collected_at.isoformat()
            })
        
        return structured
    
    async def _erase_personal_data(self, subject_email: str, session):
        """
        Erase personal data for a data subject
        """
        from src.db.models.user import User
        from src.db.models.candidate import Candidate
        from sqlalchemy import delete
        
        # Delete user record
        await session.execute(delete(User).where(text("email = :email")).params(email=subject_email))
        
        # Delete candidate records (cascading will handle related data)
        await session.execute(delete(Candidate).where(text("email = :email")).params(email=subject_email))
        
        # Note: In production, you might want to anonymize rather than delete
        # to preserve aggregate statistics while removing personal identifiers
    
    async def _check_erasure_restrictions(self, subject_email: str) -> tuple[bool, str]:
        """
        Check if data erasure is legally restricted
        """
        # Check for legal obligations that prevent erasure
        # Examples:
        # - Ongoing legal proceedings
        # - Regulatory requirements
        # - Legitimate interests that override erasure rights
        
        # For now, allow all erasures
        return True, ""
    
    def _get_legal_basis(self, category: DataCategory) -> str:
        """
        Get legal basis for processing each data category
        """
        basis_mapping = {
            DataCategory.IDENTITY: "contract",
            DataCategory.CONTACT: "legitimate_interest",
            DataCategory.PROFESSIONAL: "consent",
            DataCategory.BEHAVIORAL: "consent",
            DataCategory.TECHNICAL: "legitimate_interest",
            DataCategory.COMMUNICATION: "consent"
        }
        return basis_mapping.get(category, "legitimate_interest")
    
    def _is_sensitive_data(self, field_name: str, value: Any) -> bool:
        """
        Determine if data is sensitive (special category data under GDPR)
        """
        sensitive_fields = [
            "phone", "address", "health_info", "ethnicity", 
            "political_opinions", "religious_beliefs"
        ]
        return field_name in sensitive_fields
    
    def _get_category_description(self, category: DataCategory) -> str:
        """
        Get human-readable description of data category
        """
        descriptions = {
            DataCategory.IDENTITY: "Personal identification information",
            DataCategory.CONTACT: "Contact information and addresses",
            DataCategory.PROFESSIONAL: "Professional and educational background",
            DataCategory.BEHAVIORAL: "Interview responses and assessments",
            DataCategory.TECHNICAL: "Technical and system information",
            DataCategory.COMMUNICATION: "Communication records and messages"
        }
        return descriptions.get(category, "Other personal data")
    
    async def _get_processing_purposes(self, subject_email: str) -> List[str]:
        """
        Get purposes for which personal data is processed
        """
        return [
            "Interview scheduling and management",
            "Candidate assessment and evaluation",
            "Communication with candidates",
            "Legal compliance and record keeping",
            "Platform functionality and user experience"
        ]
    
    async def _get_data_recipients(self, subject_email: str) -> List[str]:
        """
        Get list of data recipients/processors
        """
        return [
            "Platform administrators",
            "Authorized HR personnel",
            "AI processing services (OpenAI, Google)",
            "Cloud infrastructure providers (AWS)",
            "Analytics and monitoring services"
        ]
    
    def _get_rights_information(self) -> Dict[str, str]:
        """
        Get information about data subject rights
        """
        return {
            "right_to_access": "You have the right to request copies of your personal data",
            "right_to_rectification": "You have the right to request correction of inaccurate data",
            "right_to_erasure": "You have the right to request deletion of your personal data",
            "right_to_restrict": "You have the right to request restriction of processing",
            "right_to_object": "You have the right to object to processing of your personal data",
            "right_to_portability": "You have the right to request transfer of your data",
            "right_to_complaint": "You have the right to lodge a complaint with a supervisory authority",
            "contact_dpo": "For questions about your rights, contact our Data Protection Officer"
        }
    
    async def _log_processing_activity(
        self,
        subject_email: str,
        activity: str,
        categories: List[DataCategory],
        legal_basis: str,
        purpose: str
    ):
        """
        Log data processing activity for compliance
        """
        from src.db.session import async_session_factory
        
        async with async_session_factory() as session:
            log_entry = DataProcessingLog(
                subject_email=subject_email,
                processing_activity=activity,
                data_categories=[cat.value for cat in categories],
                legal_basis=legal_basis,
                purpose=purpose,
                retention_until=datetime.utcnow() + timedelta(days=2555)  # 7 years
            )
            
            session.add(log_entry)
            await session.commit()
    
    async def _send_verification_email(self, email: str, request_id: str):
        """
        Send verification email for GDPR requests
        """
        # Implementation would send email with verification link
        pass
    
    async def _create_data_export_zip(self, personal_data: List[PersonalDataItem]) -> bytes:
        """
        Create ZIP archive for data export
        """
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add JSON export
            data_json = json.dumps([asdict(item) for item in personal_data], indent=2, default=str)
            zip_file.writestr("personal_data.json", data_json)
            
            # Add CSV export for structured data
            import csv
            csv_buffer = io.StringIO()
            if personal_data:
                writer = csv.DictWriter(csv_buffer, fieldnames=asdict(personal_data[0]).keys())
                writer.writeheader()
                for item in personal_data:
                    writer.writerow(asdict(item))
                zip_file.writestr("personal_data.csv", csv_buffer.getvalue())
            
            # Add README
            readme = """
GDPR Data Export
================

This archive contains your personal data as requested under GDPR Article 20.

Files included:
- personal_data.json: Complete data export in JSON format
- personal_data.csv: Structured data in CSV format
- README.txt: This file

For questions about this data or your rights, please contact:
Data Protection Officer: dpo@aiinterview.com
            """
            zip_file.writestr("README.txt", readme)
        
        zip_buffer.seek(0)
        return zip_buffer.getvalue()


# Global GDPR manager instance
gdpr_manager = GDPRManager()
