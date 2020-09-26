"""Mock SMTP class to patch internal class.

Prevents email being sent during testing and instead logs
them to be used in assertions
"""
import smtplib


class MockSMTP(smtplib.SMTP_SSL):
    """Mock SMTP server for testing."""

    def sendmail(self, **kwargs):
        """Overload sendmail to prevent email sending."""
        self.received_messages.append({'from:': kwargs.get('from_addr', '')})
