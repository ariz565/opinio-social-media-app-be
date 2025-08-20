import os
import logging
import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from jinja2 import Environment, FileSystemLoader

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_host = settings.get("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = settings.get("SMTP_PORT", 587)
        self.email = settings.get("EMAIL", "")
        self.password = settings.get("EMAIL_PASSWORD", "")
        
        # Use absolute path for templates directory
        import os
        current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.templates_dir = os.path.join(current_dir, "templates")
        
        # Setup Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(self.templates_dir)
        )
    
    async def send_email(self, to_email, subject, html_content, attachments=None):
        """Send email with HTML content"""
        try:
            # Create message
            message = MIMEMultipart("related")
            message["From"] = self.email
            message["To"] = to_email
            message["Subject"] = subject
            
            # Add HTML content
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)
            
            # Add logo as inline attachment
            current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            logo_path = os.path.join(current_dir, "static", "gulf_return_logo.jpg")
            if os.path.exists(logo_path):
                with open(logo_path, "rb") as f:
                    logo_data = f.read()
                
                logo_image = MIMEImage(logo_data)
                logo_image.add_header("Content-ID", "<logo>")
                logo_image.add_header("Content-Disposition", "inline", filename="gulf_return_logo.jpg")
                message.attach(logo_image)
            
            # Send email
            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                start_tls=True,
                username=self.email,
                password=self.password,
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Email sending failed: {str(e)}")
            return False
    
    async def send_verification_email(self, to_email, full_name, otp_code):
        """Send email verification OTP"""
        try:
            template = self.jinja_env.get_template("email_verification.html")
            
            # Generate verification link (for backup)
            verification_link = f"{settings.get('FRONTEND_URL', 'http://localhost:3000')}/verify-email?email={to_email}&otp={otp_code}"
            
            html_content = template.render(
                full_name=full_name,
                otp_code=otp_code,
                verification_link=verification_link
            )
            
            subject = "Verify Your Gulf Return Account"
            
            result = await self.send_email(to_email, subject, html_content)
            return result
        
        except Exception as e:
            logger.error(f"Verification email failed: {str(e)}")
            return False
    
    async def send_password_reset_email(self, to_email, full_name, reset_code, reset_link):
        """Send password reset email with template"""
        try:
            template = self.jinja_env.get_template("password_reset.html")
            
            html_content = template.render(
                full_name=full_name,
                reset_code=reset_code,
                reset_link=reset_link
            )
            
            subject = "Reset Your Gulf Return Password"
            
            result = await self.send_email(to_email, subject, html_content)
            return result
        
        except Exception as e:
            logger.error(f"Password reset email failed: {str(e)}")
            return False

# Create email service instance
email_service = EmailService()
