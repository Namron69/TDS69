from flask import Flask, request, redirect, render_template_string
import requests
import json
from user_agents import parse

app = Flask(__name__)

# Load routing rules from routes.json
with open('routes.json', 'r', encoding='utf-8') as f:
    RULES = json.load(f)

def get_country(ip):
    """Return country code for IP using ip-api.com"""
    try:
        resp = requests.get(f'http://ip-api.com/json/{ip}', timeout=3)
        data = resp.json()
        if data.get('status') == 'success':
            return data.get('countryCode')
    except Exception:
        pass
    return None

@app.route('/')
def index():
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    ua = parse(request.headers.get('User-Agent', ''))
    country = get_country(user_ip) or 'default'

    # Determine device type
    device = 'mobile' if ua.is_mobile or ua.is_tablet else 'desktop'

    # Determine target URL
    target = None
    if country in RULES:
        target = RULES[country].get(device) or RULES[country].get('default')
    if not target:
        target = RULES.get('default')

    if target:
        return redirect(target, code=302)
    return 'No redirect configured', 404


@app.route('/admin')
def admin():
    """Simple admin page displaying current rules."""
    table_rows = []
    for country, rules in RULES.items():
        if isinstance(rules, dict):
            row = f"<tr><td>{country}</td><td>{rules.get('mobile','-')}</td><td>{rules.get('desktop','-')}</td><td>{rules.get('default','-')}</td></tr>"
            table_rows.append(row)
    html = f"""
    <html>
    <head>
    <title>TDS Admin</title>
    <style>
        body {{ font-family: Arial, sans-serif; background: #f4f4f4; }}
        table {{ background: #fff; padding: 20px; border-collapse: collapse; width: 80%; margin:auto; }}
        th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
        th {{ background: #eee; }}
    </style>
    </head>
    <body>
    <h2 style='text-align:center;'>Routing Rules</h2>
    <table>
      <tr><th>Country</th><th>Mobile</th><th>Desktop</th><th>Default</th></tr>
      {''.join(table_rows)}
    </table>
    </body>
    </html>
    """
    return render_template_string(html)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
