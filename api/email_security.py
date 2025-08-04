"""
Email security and rate limiting service
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
from api.db_models import EmailSend

class EmailSecurityService:
    
    @staticmethod
    def check_rate_limits(db: Session, client_ip: str, email_address: str) -> tuple[bool, str]:
        """
        Check email sending rate limits for security
        
        Returns:
            (is_allowed: bool, error_message: str)
        """
        if not client_ip:
            # Allow if we can't get IP (shouldn't happen but don't block)
            return True, ""
        
        # Check 1: Rate limit - max 3 emails per minute per IP
        one_minute_ago = datetime.utcnow() - timedelta(minutes=1)
        recent_sends = db.query(EmailSend).filter(
            EmailSend.client_ip == client_ip,
            EmailSend.sent_at >= one_minute_ago
        ).count()
        
        if recent_sends >= 3:
            return False, "Rate limit exceeded: Maximum of 3 emails per minute allowed"
        
        # Check 2: Lifetime limit - max 20 unique email addresses per IP
        unique_emails_count = db.query(
            func.count(distinct(EmailSend.email_address))
        ).filter(
            EmailSend.client_ip == client_ip
        ).scalar()
        
        # If they've already sent to 20 different emails, check if this is a new one
        if unique_emails_count >= 20:
            # Check if this email address was already used by this IP
            existing_send = db.query(EmailSend).filter(
                EmailSend.client_ip == client_ip,
                EmailSend.email_address == email_address
            ).first()
            
            if not existing_send:
                return False, "Email limit exceeded: Maximum of 20 unique email addresses allowed per user"
        
        return True, ""

# Global instance
email_security = EmailSecurityService()