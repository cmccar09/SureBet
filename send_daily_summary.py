#!/usr/bin/env python3
"""
send_daily_summary.py - Send daily email summary of betting activity
Summarizes picks made, bets placed, and learning activity
"""

import os
import sys
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from pathlib import Path
import boto3
from decimal import Decimal

def load_today_selections():
    """Load today's generated selections"""
    today_slug = datetime.now().strftime("%Y%m%d")
    history_dir = Path(__file__).parent / "history"
    
    # Find today's selection files
    selection_files = list(history_dir.glob(f"selections_{today_slug}*.csv"))
    
    if not selection_files:
        return None, 0
    
    # Get the most recent one
    latest_file = max(selection_files, key=lambda p: p.stat().st_mtime)
    
    with open(latest_file, 'r') as f:
        lines = f.readlines()
        pick_count = len(lines) - 1  # Subtract header
    
    return latest_file, pick_count

def load_yesterday_performance():
    """Load yesterday's performance results"""
    yesterday_slug = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
    history_dir = Path(__file__).parent / "history"
    
    results_file = history_dir / f"results_{yesterday_slug}.json"
    performance_file = history_dir / f"performance_{yesterday_slug}.md"
    
    if not results_file.exists():
        return None
    
    with open(results_file, 'r') as f:
        results = json.load(f)
    
    # Extract win/place stats
    stats = {
        'total_races': len(results.get('races', [])),
        'wins': 0,
        'places': 0,
        'losses': 0
    }
    
    for race in results.get('races', []):
        result = race.get('result', '')
        if result == 'WON':
            stats['wins'] += 1
        elif result in ['PLACED_2ND', 'PLACED_3RD', 'PLACED_4TH']:
            stats['places'] += 1
        else:
            stats['losses'] += 1
    
    return stats

def get_bets_from_dynamodb():
    """Retrieve today's bets from DynamoDB"""
    try:
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.Table('SureBetBets')
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        response = table.scan(
            FilterExpression='begins_with(#pk, :today)',
            ExpressionAttributeNames={'#pk': 'pk'},
            ExpressionAttributeValues={':today': today}
        )
        
        return response.get('Items', [])
    except Exception as e:
        print(f"Error accessing DynamoDB: {e}")
        return []

def send_email_via_ses(subject, html_body, text_body, to_email):
    """Send email using AWS SES"""
    ses = boto3.client('ses', region_name='us-east-1')
    
    try:
        response = ses.send_email(
            Source='betting@futuregenai.com',  # Must be verified in SES
            Destination={'ToAddresses': [to_email]},
            Message={
                'Subject': {'Data': subject},
                'Body': {
                    'Text': {'Data': text_body},
                    'Html': {'Data': html_body}
                }
            }
        )
        print(f"✅ Email sent! Message ID: {response['MessageId']}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email via SES: {e}")
        return False

def send_email_via_smtp(subject, html_body, text_body, to_email):
    """Send email using SMTP (Gmail fallback)"""
    smtp_user = os.environ.get('SMTP_USER')
    smtp_password = os.environ.get('SMTP_PASSWORD')
    
    if not smtp_user or not smtp_password:
        print("❌ SMTP credentials not set (SMTP_USER, SMTP_PASSWORD)")
        return False
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = smtp_user
    msg['To'] = to_email
    
    msg.attach(MIMEText(text_body, 'plain'))
    msg.attach(MIMEText(html_body, 'html'))
    
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, [to_email], msg.as_string())
        server.quit()
        print("✅ Email sent via SMTP!")
        return True
    except Exception as e:
        print(f"❌ Failed to send email via SMTP: {e}")
        return False

def generate_summary_email():
    """Generate daily summary email content"""
    today = datetime.now().strftime("%A, %B %d, %Y")
    
    # Load data
    selections_file, pick_count = load_today_selections()
    yesterday_stats = load_yesterday_performance()
    db_bets = get_bets_from_dynamodb()
    
    # Check if betting is enabled
    auto_betting_enabled = os.environ.get('ENABLE_AUTO_BETTING', 'false').lower() == 'true'
    
    # Count actual bets placed
    actual_bets_placed = len([b for b in db_bets if b.get('bet_placed', False)])
    
    # Build email content
    html_parts = []
    text_parts = []
    
    # Header
    html_parts.append(f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .header {{ background-color: #2c3e50; color: white; padding: 20px; }}
            .section {{ padding: 15px; margin: 10px 0; background-color: #f8f9fa; border-radius: 5px; }}
            .stat {{ font-size: 24px; font-weight: bold; color: #27ae60; }}
            .warning {{ color: #e74c3c; font-weight: bold; }}
            .info {{ color: #3498db; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🏇 Daily Betting Summary - {today}</h1>
        </div>
    """)
    
    text_parts.append(f"=" * 60)
    text_parts.append(f"DAILY BETTING SUMMARY - {today}")
    text_parts.append(f"=" * 60)
    
    # Today's Activity
    html_parts.append('<div class="section">')
    html_parts.append('<h2>📊 Today\'s Activity</h2>')
    
    if pick_count > 0:
        html_parts.append(f'<p>✅ Generated <span class="stat">{pick_count}</span> picks</p>')
        text_parts.append(f"\n✅ Generated {pick_count} picks")
    else:
        html_parts.append('<p class="warning">⚠️ No picks generated today</p>')
        html_parts.append('<p>Possible reasons: No races met ROI threshold, Betfair API error, or no races scheduled</p>')
        text_parts.append("\n⚠️ No picks generated today")
    
    # Betting Status
    if auto_betting_enabled:
        if actual_bets_placed > 0:
            html_parts.append(f'<p>💰 <span class="stat">{actual_bets_placed}</span> bets placed automatically</p>')
            text_parts.append(f"💰 {actual_bets_placed} bets placed automatically")
        else:
            html_parts.append('<p class="warning">⚠️ Auto-betting enabled but NO bets placed</p>')
            html_parts.append('<p>Check: Betfair account balance, API connectivity, selection criteria</p>')
            text_parts.append("\n⚠️ Auto-betting enabled but NO bets placed")
    else:
        html_parts.append('<p class="info">ℹ️ Auto-betting is DISABLED (dry-run mode)</p>')
        html_parts.append('<p>Set ENABLE_AUTO_BETTING=true to place real bets</p>')
        text_parts.append("\nℹ️ Auto-betting is DISABLED (dry-run mode)")
    
    html_parts.append('</div>')
    
    # Yesterday's Performance
    if yesterday_stats:
        html_parts.append('<div class="section">')
        html_parts.append('<h2>📈 Yesterday\'s Results</h2>')
        html_parts.append(f'<p>Races: {yesterday_stats["total_races"]}</p>')
        html_parts.append(f'<p>🏆 Wins: {yesterday_stats["wins"]}</p>')
        html_parts.append(f'<p>🥈 Places: {yesterday_stats["places"]}</p>')
        html_parts.append(f'<p>❌ Losses: {yesterday_stats["losses"]}</p>')
        
        win_rate = (yesterday_stats["wins"] / yesterday_stats["total_races"] * 100) if yesterday_stats["total_races"] > 0 else 0
        html_parts.append(f'<p>Win Rate: {win_rate:.1f}%</p>')
        html_parts.append('</div>')
        
        text_parts.append(f"\n📈 Yesterday's Results:")
        text_parts.append(f"  Races: {yesterday_stats['total_races']}")
        text_parts.append(f"  Wins: {yesterday_stats['wins']}")
        text_parts.append(f"  Places: {yesterday_stats['places']}")
        text_parts.append(f"  Win Rate: {win_rate:.1f}%")
    
    # Learning Status
    html_parts.append('<div class="section">')
    html_parts.append('<h2>🧠 Learning System</h2>')
    html_parts.append('<p>✅ Learning from past results: ENABLED</p>')
    html_parts.append('<p>Prompt adjustments are applied automatically based on performance</p>')
    html_parts.append('</div>')
    
    text_parts.append("\n🧠 Learning System: ENABLED")
    
    # Footer
    html_parts.append("""
        <div class="section">
            <p style="font-size: 12px; color: #7f8c8d;">
                This is an automated summary from your betting workflow.<br>
                View logs: C:\\Users\\charl\\OneDrive\\futuregenAI\\Betting\\logs<br>
                View history: C:\\Users\\charl\\OneDrive\\futuregenAI\\Betting\\history
            </p>
        </div>
    </body>
    </html>
    """)
    
    text_parts.append("\n" + "=" * 60)
    text_parts.append("This is an automated summary from your betting workflow")
    
    html_body = ''.join(html_parts)
    text_body = '\n'.join(text_parts)
    
    return html_body, text_body

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Send daily betting summary email")
    parser.add_argument("--to", type=str, required=True, help="Recipient email address")
    parser.add_argument("--use-smtp", action="store_true", help="Use SMTP instead of AWS SES")
    args = parser.parse_args()
    
    print("Generating daily summary email...")
    
    html_body, text_body = generate_summary_email()
    subject = f"🏇 Daily Betting Summary - {datetime.now().strftime('%Y-%m-%d')}"
    
    # Try to send email
    if args.use_smtp:
        success = send_email_via_smtp(subject, html_body, text_body, args.to)
    else:
        success = send_email_via_ses(subject, html_body, text_body, args.to)
    
    if not success:
        print("\n📧 Email preview:")
        print("=" * 60)
        print(text_body)
        print("=" * 60)
        print("\nTo enable email sending:")
        print("  Option 1 (AWS SES): Verify email in AWS SES console")
        print("  Option 2 (SMTP): Set SMTP_USER and SMTP_PASSWORD environment variables")
        sys.exit(1)
    
    sys.exit(0)

if __name__ == "__main__":
    main()
