"""Zoho SMTP email service — stdlib only (smtplib)."""
from __future__ import annotations

import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SMTP_HOST = os.environ.get("ZOHO_SMTP_HOST", "smtp.zoho.com")
SMTP_PORT = int(os.environ.get("ZOHO_SMTP_PORT", "587"))
SMTP_USER = os.environ.get("ZOHO_SMTP_USER", "foundryai@getfoundryai.com")
SMTP_PASS = os.environ.get("ZOHO_SMTP_PASSWORD", "")
FROM_NAME = os.environ.get("EMAIL_FROM_NAME", "Foundry Legal")
ENABLED   = bool(SMTP_PASS)


def _send(to: str, subject: str, html: str, plain: str) -> None:
    """Send an email via Zoho SMTP. Silently skips if ZOHO_SMTP_PASSWORD not set."""
    if not ENABLED:
        return
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"{FROM_NAME} <{SMTP_USER}>"
    msg["To"]      = to
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html,  "html"))
    ctx = ssl.create_default_context()
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls(context=ctx)
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, to, msg.as_string())


# ── Email templates ─────────────────────────────────────────────────────────

def send_welcome(to: str, display_name: str) -> None:
    subject = "Welcome to Foundry Legal"
    plain = (
        f"Hi {display_name},\n\n"
        "Your account is ready. Sign in at http://127.0.0.1:8000 to create your first matter, "
        "generate compliance calendars, and review contracts.\n\n"
        "— Foundry Legal Team"
    )
    html = f"""
    <div style="font-family:sans-serif;max-width:560px;margin:auto">
      <h2 style="color:#1a3a2a">Welcome to Foundry Legal, {display_name}!</h2>
      <p>Your account is ready. Here's what you can do:</p>
      <ul>
        <li><strong>New Matter</strong> — register your business step-by-step</li>
        <li><strong>Compliance Calendar</strong> — track every FIRS, CAC and PENCOM deadline</li>
        <li><strong>Document Generator</strong> — produce Nigerian-law contracts in minutes</li>
        <li><strong>Legal Q&amp;A</strong> — get cited answers reviewed by a real lawyer</li>
      </ul>
      <p><a href="http://127.0.0.1:8000" style="background:#1a6b3a;color:#fff;padding:10px 20px;
         border-radius:6px;text-decoration:none;display:inline-block">Open Foundry Legal →</a></p>
      <p style="color:#777;font-size:12px">Foundry Legal · Nigeria-first legal operations</p>
    </div>"""
    _send(to, subject, html, plain)


def send_matter_created(to: str, display_name: str, business_name: str, matter_id: str) -> None:
    subject = f"Matter created: {business_name}"
    plain = (
        f"Hi {display_name},\n\n"
        f"Your matter for '{business_name}' has been created (ID: {matter_id}).\n"
        "A compliance calendar has been auto-generated. Sign in to view your tasks and deadlines.\n\n"
        "— Foundry Legal Team"
    )
    html = f"""
    <div style="font-family:sans-serif;max-width:560px;margin:auto">
      <h2 style="color:#1a3a2a">Matter created: {business_name}</h2>
      <p>Hi {display_name}, your new matter is live.</p>
      <table style="border-collapse:collapse;width:100%">
        <tr><td style="padding:8px;color:#777">Business</td><td style="padding:8px"><strong>{business_name}</strong></td></tr>
        <tr><td style="padding:8px;color:#777">Matter ID</td><td style="padding:8px;font-size:12px">{matter_id}</td></tr>
      </table>
      <p>Your <strong>compliance calendar</strong> has been auto-generated with Nigerian statutory deadlines.</p>
      <p><a href="http://127.0.0.1:8000" style="background:#1a6b3a;color:#fff;padding:10px 20px;
         border-radius:6px;text-decoration:none;display:inline-block">View Dashboard →</a></p>
    </div>"""
    _send(to, subject, html, plain)


def send_compliance_alert(to: str, display_name: str, obligations: list[dict]) -> None:
    if not obligations:
        return
    subject = f"Compliance alert: {len(obligations)} deadline(s) need attention"
    items_plain = "\n".join(
        f"  • {o['description']} — due {o['due_date']} [{o['status'].upper()}]"
        for o in obligations
    )
    items_html = "".join(
        f"<tr><td style='padding:8px'>{o['description']}</td>"
        f"<td style='padding:8px'>{o['due_date']}</td>"
        f"<td style='padding:8px;color:{'#c0392b' if o['status']=='overdue' else '#e67e22'}'>"
        f"{o['status'].upper()}</td></tr>"
        for o in obligations
    )
    plain = f"Hi {display_name},\n\nThe following compliance obligations need attention:\n{items_plain}\n\n— Foundry Legal Team"
    html = f"""
    <div style="font-family:sans-serif;max-width:560px;margin:auto">
      <h2 style="color:#c0392b">Compliance Alert</h2>
      <p>Hi {display_name}, the following deadlines need your attention:</p>
      <table style="border-collapse:collapse;width:100%;border:1px solid #eee">
        <thead><tr style="background:#f5f5f5">
          <th style="padding:8px;text-align:left">Obligation</th>
          <th style="padding:8px;text-align:left">Due Date</th>
          <th style="padding:8px;text-align:left">Status</th>
        </tr></thead>
        <tbody>{items_html}</tbody>
      </table>
      <p><a href="http://127.0.0.1:8000" style="background:#1a6b3a;color:#fff;padding:10px 20px;
         border-radius:6px;text-decoration:none;display:inline-block">View Calendar →</a></p>
    </div>"""
    _send(to, subject, html, plain)


def send_contract_approved(to: str, display_name: str, filename: str) -> None:
    subject = f"Contract approved: {filename}"
    plain = f"Hi {display_name},\n\nYour contract '{filename}' has been reviewed and approved by a lawyer.\n\n— Foundry Legal Team"
    html = f"""
    <div style="font-family:sans-serif;max-width:560px;margin:auto">
      <h2 style="color:#1a3a2a">Contract Approved ✓</h2>
      <p>Hi {display_name}, your contract <strong>{filename}</strong> has been reviewed and approved by a lawyer.</p>
      <p><a href="http://127.0.0.1:8000" style="background:#1a6b3a;color:#fff;padding:10px 20px;
         border-radius:6px;text-decoration:none;display:inline-block">View Contract →</a></p>
    </div>"""
    _send(to, subject, html, plain)


def send_payment_receipt(to: str, display_name: str, tier: str, amount_ngn: float, reference: str) -> None:
    subject = f"Payment confirmed — {tier.title()} plan"
    plain = (
        f"Hi {display_name},\n\n"
        f"Payment of ₦{amount_ngn:,.0f} for the {tier.title()} plan has been confirmed.\n"
        f"Reference: {reference}\n\n"
        "— Foundry Legal Team"
    )
    html = f"""
    <div style="font-family:sans-serif;max-width:560px;margin:auto">
      <h2 style="color:#1a3a2a">Payment Confirmed</h2>
      <p>Hi {display_name}, thank you for your payment.</p>
      <table style="border-collapse:collapse;width:100%">
        <tr><td style="padding:8px;color:#777">Plan</td><td style="padding:8px"><strong>{tier.title()}</strong></td></tr>
        <tr><td style="padding:8px;color:#777">Amount</td><td style="padding:8px"><strong>₦{amount_ngn:,.0f}</strong></td></tr>
        <tr><td style="padding:8px;color:#777">Reference</td><td style="padding:8px;font-size:12px">{reference}</td></tr>
      </table>
      <p><a href="http://127.0.0.1:8000" style="background:#1a6b3a;color:#fff;padding:10px 20px;
         border-radius:6px;text-decoration:none;display:inline-block">Go to Dashboard →</a></p>
    </div>"""
    _send(to, subject, html, plain)
