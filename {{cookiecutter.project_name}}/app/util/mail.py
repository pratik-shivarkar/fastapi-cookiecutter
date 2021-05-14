"""
Copyright (C) Pratik Shivarkar - All Rights Reserved

This source code is protected under international copyright law.  All rights
reserved and protected by the copyright holders.
This file is confidential and only available to authorized individuals with the
permission of the copyright holders.  If you encounter this file and do not have
permission, please contact the copyright holders and delete this file.
"""


import os
import ssl
import smtplib
from pydantic import BaseModel, Field
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class Mail(BaseModel):
    sender_email: str = Field(default=os.getenv('SENDER_EMAIL'))
    recipient_email: str
    subject: str
    body_text: str
    body_html: str
    smtp_server: str = Field(default=os.getenv('SMTP_SERVER'))
    smtp_port: int = Field(default=int(os.getenv('SMTP_PORT')))
    smtp_username: str = Field(default=os.getenv('SMTP_USERNAME'))
    smtp_password: str = Field(default=os.getenv('SMTP_PASSWORD'))


def send_mail(mail: Mail):
    message = MIMEMultipart("alternative")
    message["Subject"] = mail.subject
    message["From"] = mail.sender_email
    message["To"] = mail.recipient_email

    # Turn these into plain/html MIMEText objects
    part1 = MIMEText(mail.body_text, "plain")
    part2 = MIMEText(mail.body_html, "html")

    # Add HTML/plain-text parts to MIMEMultipart message
    # The email client will try to render the last part first
    message.attach(part1)
    message.attach(part2)

    # Create secure connection with server and send email
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(mail.smtp_server, mail.smtp_port, context=context) as server:
        server.login(mail.sender_email, mail.smtp_password)
        server.sendmail(
            mail.sender_email, mail.recipient_email, message.as_string()
        )
