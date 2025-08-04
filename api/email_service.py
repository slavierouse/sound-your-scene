"""
Email service for sending playlist links
"""
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.orm import Session

class EmailService:
    
    def __init__(self):
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER')
        self.smtp_pass = os.getenv('SMTP_PASS')
        self.from_email = os.getenv('FROM_EMAIL')
        
        if not all([self.smtp_user, self.smtp_pass, self.from_email]):
            raise ValueError("Email configuration missing. Check SMTP_USER, SMTP_PASS, and FROM_EMAIL environment variables.")
    
    def send_playlist_email(self, db: Session, playlist_id: str, to_email: str, playlist_url: str, client_ip: str = None) -> bool:
        """Send playlist link via email and record in database"""
        from api.db_models import EmailSend
        
        success = False
        error_message = None
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = "Your Sound Your Scene Playlist"
            
            # Email body
            body = f"""Thanks for using Sound Your Scene!

The playlist you requested us to email you is available at:
{playlist_url}

Enjoy your music!

- The Sound Your Scene Team

PS How are you liking Sound Your Scene? Send back some feedback or submit anonymous feedback here: https://forms.gle/vtFnqH4F8oLQVrxi7.
"""
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
            
            success = True
            
        except Exception as e:
            error_message = str(e)
            print(f"Failed to send email: {e}")
        
        # Record the email send attempt in database
        try:
            email_record = EmailSend(
                playlist_id=playlist_id,
                email_address=to_email,
                client_ip=client_ip,
                success=success,
                error_message=error_message
            )
            db.add(email_record)
            db.commit()
        except Exception as db_error:
            print(f"Failed to record email send: {db_error}")
            # Don't fail the whole operation if database recording fails
        
        return success

# Global instance
email_service = EmailService()