"""
Enhanced Pydantic schemas with enterprise-grade validation
Security-focused input validation and sanitization
"""
from pydantic import BaseModel, Field, field_validator, EmailStr
from typing import Optional, List, Union
from datetime import datetime
import re
from src.core.security import InputSanitizer


class SecureBaseModel(BaseModel):
    """
    Base model with enhanced security validation
    """
    
    class Config:
        # Prevent arbitrary class attributes
        populate_by_name = True  # Updated for Pydantic v2
        validate_assignment = True
        
    @field_validator("*", mode="before")
    @classmethod
    def sanitize_strings(cls, value):
        """
        Global string sanitization for all string fields
        """
        if isinstance(value, str):
            return InputSanitizer.sanitize_string(value)
        return value


class SecureUserCreate(SecureBaseModel):
    """
    Enhanced user creation schema with security validation
    """
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(
        ...,
        min_length=12,
        max_length=128,
        description="Password must be 12-128 characters"
    )
    first_name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=50,
        description="First name with Turkish character support"
    )
    last_name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=50,
        description="Last name with Turkish character support"
    )
    
    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, password):
        """
        Enterprise password policy validation
        """
        if len(password) < 12:
            raise ValueError("Password must be at least 12 characters long")
        
        # Check for character diversity
        has_upper = bool(re.search(r"[A-Z]", password))
        has_lower = bool(re.search(r"[a-z]", password))
        has_digit = bool(re.search(r"\d", password))
        has_special = bool(re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", password))
        
        if not (has_upper and has_lower and has_digit and has_special):
            raise ValueError(
                "Password must contain uppercase, lowercase, digit, and special character"
            )
        
        # Check for common patterns
        common_patterns = [
            r"12345", r"password", r"admin", r"qwerty", r"abc",
            r"(.)\1{2,}",  # Repeated characters
        ]
        
        for pattern in common_patterns:
            if re.search(pattern, password.lower()):
                raise ValueError("Password contains common patterns")
        
        return password
    
    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name_fields(cls, name):
        """
        Validate first and last name fields with Turkish character support
        """
        if name is None:
            return name
        
        name = InputSanitizer.sanitize_string(name)
        
        # Allow Turkish characters and common name patterns
        if not re.match(r"^[a-zA-ZğüşöçıĞÜŞÖÇİ\s\-'\.]+$", name):
            raise ValueError("Name contains invalid characters")
        
        return name.strip()
    
    @field_validator("email")
    @classmethod
    def validate_email_security(cls, email):
        """
        Enhanced email validation
        """
        email = InputSanitizer.sanitize_email(email)
        
        # Check for disposable email domains (basic list)
        disposable_domains = [
            "10minutemail.com", "guerrillamail.com", "mailinator.com",
            "tempmail.org", "temp-mail.org", "throwaway.email"
        ]
        
        domain = email.split("@")[1].lower()
        if domain in disposable_domains:
            raise ValueError("Disposable email addresses are not allowed")
        
        return email


class SecureJobCreate(SecureBaseModel):
    """
    Enhanced job creation schema
    """
    title: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Job title"
    )
    description: Optional[str] = Field(
        None,
        max_length=10000,
        description="Job description"
    )
    extra_questions: Optional[str] = Field(
        None,
        max_length=5000,
        description="Additional interview questions"
    )
    default_invite_expiry_days: int = Field(
        7,
        ge=1,
        le=365,
        description="Invite expiry in days (1-365)"
    )
    
    @field_validator("title")
    @classmethod
    def validate_title(cls, title):
        """
        Job title validation
        """
        # Remove potential HTML/script tags
        title = InputSanitizer.sanitize_string(title, 200)
        
        # Ensure professional format
        if not re.match(r"^[a-zA-Z0-9\s\-/&.,()]+$", title):
            raise ValueError("Job title contains invalid characters")
        
        return title.strip()
    
    @field_validator("description")
    @classmethod
    def validate_description(cls, description):
        """
        Job description validation
        """
        if description is None:
            return description
        
        description = InputSanitizer.sanitize_string(description, 10000)
        
        # Check for excessive capitalization (spam indicator)
        if len(re.findall(r"[A-Z]", description)) > len(description) * 0.3:
            raise ValueError("Excessive capitalization in job description")
        
        return description.strip()


class SecureCandidateCreate(SecureBaseModel):
    """
    Enhanced candidate creation schema
    """
    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Candidate full name"
    )
    email: EmailStr = Field(..., description="Candidate email")
    phone: Optional[str] = Field(
        None,
        description="Phone number in international format"
    )
    linkedin_url: Optional[str] = Field(
        None,
        max_length=500,
        description="LinkedIn profile URL"
    )
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, name):
        """
        Name validation with Turkish character support
        """
        name = InputSanitizer.sanitize_string(name, 100)
        
        # Allow Turkish characters and common name patterns
        if not re.match(r"^[a-zA-ZğüşöçıĞÜŞÖÇİ\s\-'\.]+$", name):
            raise ValueError("Name contains invalid characters")
        
        # Check for reasonable name structure
        parts = name.split()
        if len(parts) < 2 or any(len(part) < 2 for part in parts):
            raise ValueError("Please provide a valid full name")
        
        return name.strip()
    
    @field_validator("phone")
    @classmethod
    def validate_phone(cls, phone):
        """
        Phone number validation
        """
        if phone is None:
            return phone
        
        # Sanitize and normalize
        phone = re.sub(r"[^\d+]", "", phone)
        
        # International format validation
        if not re.match(r"^\+?[1-9]\d{1,14}$", phone):
            raise ValueError("Invalid phone number format")
        
        return phone
    
    @field_validator("linkedin_url")
    @classmethod
    def validate_linkedin_url(cls, url):
        """
        LinkedIn URL validation
        """
        if url is None:
            return url
        
        url = InputSanitizer.sanitize_string(url, 500)
        
        # Basic LinkedIn URL pattern
        linkedin_pattern = r"^https?://(www\.)?linkedin\.com/(in|pub)/[a-zA-Z0-9\-]+/?$"
        if not re.match(linkedin_pattern, url, re.IGNORECASE):
            raise ValueError("Invalid LinkedIn URL format")
        
        return url.lower()


class SecureInterviewCreate(SecureBaseModel):
    """
    Enhanced interview creation schema
    """
    job_id: int = Field(..., gt=0, description="Job ID")
    candidate_id: int = Field(..., gt=0, description="Candidate ID")
    
    @field_validator("job_id", "candidate_id")
    @classmethod
    def validate_positive_ids(cls, value):
        """
        Ensure IDs are positive integers
        """
        if value <= 0:
            raise ValueError("ID must be a positive integer")
        return value


class SecureConversationMessage(SecureBaseModel):
    """
    Enhanced conversation message schema
    """
    role: str = Field(..., description="Message role: user or assistant")
    text: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Message content"
    )
    
    @field_validator("text")
    @classmethod
    def validate_message_content(cls, text):
        """
        Message content validation
        """
        text = InputSanitizer.sanitize_string(text, 5000)
        
        # Check for spam patterns
        spam_indicators = [
            r"\b(buy|click|free|urgent|limited)\b.*\b(now|today|call)\b",
            r"https?://[^\s]+",  # URLs in messages
            r"\$\d+",  # Money amounts
        ]
        
        for pattern in spam_indicators:
            if re.search(pattern, text, re.IGNORECASE):
                raise ValueError("Message content flagged as potential spam")
        
        return text.strip()
    
    @field_validator("role")
    @classmethod
    def validate_role(cls, role):
        """
        Validate message role
        """
        if role not in ["user", "assistant"]:
            raise ValueError("Role must be either 'user' or 'assistant'")
        return role


class SecureTokenRequest(SecureBaseModel):
    """
    Enhanced token request schema
    """
    token: str = Field(
        ...,
        min_length=32,
        max_length=128,
        description="Secure token"
    )
    
    @field_validator("token")
    @classmethod
    def validate_token_format(cls, token):
        """
        Token format validation
        """
        # Ensure hexadecimal format
        if not re.match(r"^[a-fA-F0-9]+$", token):
            raise ValueError("Invalid token format")
        
        return token.lower()


class SecureFileUpload(SecureBaseModel):
    """
    Enhanced file upload schema
    """
    filename: str = Field(..., max_length=255)
    content_type: str = Field(..., max_length=100)
    file_size: int = Field(..., gt=0, le=50_000_000)  # 50MB limit
    
    @field_validator("filename")
    @classmethod
    def validate_filename(cls, filename):
        """
        Secure filename validation
        """
        filename = InputSanitizer.sanitize_string(filename, 255)
        
        # Check for dangerous file extensions
        dangerous_extensions = [
            ".exe", ".bat", ".cmd", ".com", ".scr", ".vbs", ".js",
            ".jar", ".php", ".asp", ".jsp", ".sh", ".ps1"
        ]
        
        file_ext = filename.lower().split(".")[-1] if "." in filename else ""
        if f".{file_ext}" in dangerous_extensions:
            raise ValueError("File type not allowed")
        
        # Allowed file types for resumes/documents
        allowed_extensions = ["pdf", "doc", "docx", "txt", "rtf"]
        if file_ext not in allowed_extensions:
            raise ValueError("Only PDF, DOC, DOCX, TXT, RTF files are allowed")
        
        # Check for path traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            raise ValueError("Invalid filename - path traversal detected")
        
        return filename
    
    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, content_type):
        """
        Content type validation
        """
        allowed_types = [
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain",
            "application/rtf"
        ]
        
        if content_type not in allowed_types:
            raise ValueError("File type not allowed")
        
        return content_type


class EnhancedErrorResponse(BaseModel):
    """
    Standardized error response format
    """
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[dict] = Field(None, description="Additional error details")
    request_id: Optional[str] = Field(None, description="Request tracking ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "validation_error",
                "message": "Input validation failed",
                "details": {"field": "email", "issue": "Invalid format"},
                "request_id": "req_123456789",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }
