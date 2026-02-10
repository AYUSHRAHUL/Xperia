import os
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def send_email(to_email, subject, html_content):
    """
    Sends an email using SendGrid. 
    If SENDGRID_API_KEY is not set, simulates sending by logging to console.
    """
    api_key = os.getenv("SENDGRID_API_KEY")
    sender_email = os.getenv("EMAIL_SENDER", "noreply@urbanpulse.local")
    
    if not api_key:
        print(f"\n📨 [EMAIL SIMULATION] To: {to_email} | Subject: {subject}")
        # print(f"Body: {html_content[:100]}...")
        return True
        
    try:
        message = Mail(
            from_email=sender_email,
            to_emails=to_email,
            subject=subject,
            html_content=html_content
        )
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        print(f"✅ Email sent to {to_email}: Status {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ Email sending failed: {str(e)}")
        return False
