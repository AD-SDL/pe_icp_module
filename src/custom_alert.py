import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class CustomAlert:  # SMTP server alerts
    def __init__(self):
        self.when = 1  # 0 - always, 1 - only if there are problems
        self.server = "mailgateway.anl.gov"
        self.port = 25  # Common ports are 587 for TLS and 465 for SSL
        self.instrument = "ICP-AARL200@anl.gov"
        self.to = "shkrob@anl.gov"  # comma separated list

    def alert(self, subject="ALERT", body=None, importance=None):
        self.message = MIMEMultipart()
        self.message["From"] = self.instrument
        self.message["To"] = self.to
        self.message["Subject"] = subject

        if body:
            body_part = MIMEText(str(body), "plain")  # 'plain' for plain text
            self.message.attach(body_part)

        if importance:
            self.message["Importance"] = importance

        try:
            server = smtplib.SMTP(self.server, self.port)
            server.sendmail(self.instrument, self.to, self.message.as_string())
            server.quit()
        except Exception as e:
            print(">> Cannot send smtp e-mail, error = %s" % e)
