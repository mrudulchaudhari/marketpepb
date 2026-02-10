import smtplib
import os
import datetime
from email.mime.text import MIMEText
from core import get_report_message, update_nifty_data, SYMBOLS, CSV_FILES, CSV_HISTORICAL


def send_email(subject, html_body):
    email = os.environ["EMAIL_ADDRESS"]
    password = os.environ["EMAIL_PASSWORD"]
    to_email = os.environ.get("TO_EMAIL", email)

    msg = MIMEText(html_body, "html")
    msg["Subject"] = subject
    msg["From"] = email
    msg["To"] = to_email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(email, password)
        server.send_message(msg)
    print(f"Email sent to {to_email}")


def text_to_html(report_text):
    """Convert plain text report to styled HTML email."""
    now = datetime.datetime.now().strftime("%d %B %Y, %I:%M %p")

    sections = report_text.split("\n\n")
    cards = []

    for section in sections:
        lines = section.strip().split("\n")
        if not lines:
            continue

        rows = ""
        title = ""
        subtitle = ""
        pepb_line = ""

        for line in lines:
            line = line.strip()
            if not line:
                continue
            if "Analysis Report" in line:
                title = line
            elif line.startswith("📅"):
                subtitle = line
            elif line.startswith("Today's PE*PB"):
                pepb_line = line
            elif "Days:" in line or "All time" in line:
                parts = line.split(":")
                label = parts[0].strip()
                value = ":".join(parts[1:]).strip()
                color = "#ccc"
                if "(" in value and "%" in value:
                    pct_str = value[value.index("(") + 1 : value.index(")")]
                    try:
                        pct_val = float(pct_str.replace("%", ""))
                        color = "#ff4d4d" if pct_val > 0 else "#4dff88"
                    except ValueError:
                        pass
                rows += f'<tr><td style="padding:6px 12px;color:#aaa;">{label}</td><td style="padding:6px 12px;color:{color};font-weight:bold;">{value}</td></tr>'

        card = f"""
        <div style="background:#1a1a2e;border-radius:10px;padding:20px;margin-bottom:16px;border:1px solid #333;">
            <div style="color:#00d4ff;font-size:17px;font-weight:bold;margin-bottom:4px;">{title}</div>
            <div style="color:#888;font-size:13px;margin-bottom:12px;">{subtitle}</div>
            <div style="color:#fff;font-size:15px;margin-bottom:14px;">{pepb_line}</div>
            <table style="width:100%;border-collapse:collapse;font-size:14px;font-family:monospace;">
                {rows}
            </table>
        </div>"""
        cards.append(card)

    return f"""
    <html>
    <body style="background:#0f0f23;padding:20px;font-family:Arial,sans-serif;">
        <h1 style="color:#fff;text-align:center;">📊 NSE PE*PB Daily Report</h1>
        <p style="color:#888;text-align:center;">Generated: {now}</p>
        {"".join(cards)}
        <p style="color:#555;text-align:center;font-size:12px;margin-top:20px;">Auto-generated via GitHub Actions</p>
    </body>
    </html>"""


if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)

    # Step 1: Update data
    print("Updating NSE data...")
    for symbol, csv_file, csv_hist in zip(SYMBOLS, CSV_FILES, CSV_HISTORICAL):
        success = update_nifty_data(symbol, csv_file, csv_hist)
        print(f"  {symbol}: {'done' if success else 'failed'}")

    # Step 2: Generate report
    print("Generating report...")
    report = get_report_message()
    print(report)

    # Step 3: Send email
    today = datetime.datetime.now().strftime("%d %b %Y")
    send_email(
        subject=f"NSE PE*PB Report - {today}",
        html_body=text_to_html(report),
    )