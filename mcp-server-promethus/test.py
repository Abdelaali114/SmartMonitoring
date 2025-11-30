import smtplib
from email.mime.text import MIMEText

# ==== Your Gmail SMTP Configuration ====
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USER = "abdellaalimohamad4321@gmail.com"         # your Gmail address
EMAIL_PASS = "grhy xrpf npbq adkq"       # the 16-character App Password
ALERT_EMAIL_TO = "naitpublicstore2001@gmail.com"  # where to send test email


def send_test_email():
    subject = "✅ Test Email from FastAPI Alert System"
    message = "This is a test email to confirm SMTP setup works properly."

    try:
        # Build the email
        msg = MIMEText(message)
        msg["Subject"] = subject
        msg["From"] = EMAIL_USER
        msg["To"] = ALERT_EMAIL_TO

        # Connect to Gmail SMTP
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()  # upgrade to secure connection
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)

        print("📧 Test email sent successfully!")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")


# Run the test
if __name__ == "__main__":
    send_test_email()
