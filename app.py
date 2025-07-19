from flask import Flask, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user,
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import requests
import os
import random
import string
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-me')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tds.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)

class Campaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(64), unique=True, nullable=False)
    url = db.Column(db.String(255), nullable=False)
    extra_urls = db.Column(db.Text)
    fallback_url = db.Column(db.String(255))
    hits = db.Column(db.Integer, default=0)
    countries = db.Column(db.String(255))  # comma separated country codes
    redirect_type = db.Column(
        db.String(10), default='302'
    )  # 302, meta, js, refresh, iframe
    delay = db.Column(db.Integer, default=0)  # seconds

class Click(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'))
    ip = db.Column(db.String(45))
    country = db.Column(db.String(2))
    ua = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', password=generate_password_hash('admin'))
            db.session.add(admin)
            db.session.commit()

def is_safe_url(target):
    # Basic check for external urls
    return target.startswith('http://') or target.startswith('https://')

def generate_slug():
    letters = string.ascii_lowercase + string.digits
    while True:
        slug = ''.join(random.choices(letters, k=6))
        if not Campaign.query.filter_by(slug=slug).first():
            return slug

def replace_macros(url, ip, country, ua):
    return (
        url.replace('{ip}', ip or '')
        .replace('{country}', (country or ''))
        .replace('{ua}', ua or '')
    )

def get_country(ip):
    try:
        r = requests.get(f"https://ipapi.co/{ip}/json/", timeout=3)
        if r.ok:
            return r.json().get('country')
    except Exception:
        pass
    return None

@app.route('/')
@login_required
def index():
    campaigns = Campaign.query.all()
    return render_template('admin.html', campaigns=campaigns)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/campaign/create', methods=['POST'])
@login_required
def create_campaign():
    name = request.form['name']
    slug = request.form.get('slug', '').strip() or generate_slug()
    url = request.form['url']
    extra_urls = request.form.get('extra_urls', '')
    fallback_url = request.form.get('fallback_url') or None
    countries = request.form.get('countries', '')
    redirect_type = request.form.get('redirect_type', '302')
    delay = int(request.form.get('delay', '0') or 0)
    if not is_safe_url(url):
        return 'Invalid URL', 400
    if fallback_url and not is_safe_url(fallback_url):
        return 'Invalid fallback URL', 400
    if slug and not re.match(r'^[a-zA-Z0-9_-]+$', slug):
        return 'Invalid slug', 400
    if Campaign.query.filter_by(slug=slug).first():
        return 'Slug taken', 400
    campaign = Campaign(
        name=name,
        slug=slug,
        url=url,
        extra_urls=extra_urls,
        fallback_url=fallback_url,
        countries=countries,
        redirect_type=redirect_type,
        delay=delay,
    )
    db.session.add(campaign)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/campaign/<int:cid>/delete', methods=['POST'])
@login_required
def delete_campaign(cid):
    campaign = Campaign.query.get_or_404(cid)
    db.session.delete(campaign)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/campaign/<int:cid>/edit', methods=['GET'])
@login_required
def edit_campaign_get(cid):
    campaign = Campaign.query.get_or_404(cid)
    return render_template('edit.html', campaign=campaign)

@app.route('/campaign/<int:cid>/edit', methods=['POST'])
@login_required
def edit_campaign(cid):
    campaign = Campaign.query.get_or_404(cid)
    name = request.form['name']
    slug = request.form.get('slug', '').strip() or campaign.slug
    url = request.form['url']
    extra_urls = request.form.get('extra_urls', '')
    fallback_url = request.form.get('fallback_url') or None
    countries = request.form.get('countries', '')
    redirect_type = request.form.get('redirect_type', '302')
    delay = int(request.form.get('delay', '0') or 0)
    if not is_safe_url(url):
        return 'Invalid URL', 400
    if fallback_url and not is_safe_url(fallback_url):
        return 'Invalid fallback URL', 400
    if slug and not re.match(r'^[a-zA-Z0-9_-]+$', slug):
        return 'Invalid slug', 400
    if slug != campaign.slug and Campaign.query.filter_by(slug=slug).first():
        return 'Slug taken', 400
    campaign.name = name
    campaign.slug = slug
    campaign.url = url
    campaign.extra_urls = extra_urls
    campaign.fallback_url = fallback_url
    campaign.countries = countries
    campaign.redirect_type = redirect_type
    campaign.delay = delay
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/campaign/<int:cid>/stats')
@login_required
def campaign_stats(cid):
    campaign = Campaign.query.get_or_404(cid)
    clicks = Click.query.filter_by(campaign_id=cid).order_by(Click.timestamp.desc()).all()
    return render_template('stats.html', campaign=campaign, clicks=clicks)

@app.route('/t/<int:cid>')
def track(cid):
    campaign = Campaign.query.get_or_404(cid)
    return handle_redirect(campaign)

@app.route('/s/<slug>')
def track_slug(slug):
    campaign = Campaign.query.filter_by(slug=slug).first_or_404()
    return handle_redirect(campaign)

def handle_redirect(campaign):
    if not is_safe_url(campaign.url):
        return 'Invalid target', 400

    ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    country = get_country(ip)
    click = Click(campaign_id=campaign.id, ip=ip, country=country, ua=request.headers.get('User-Agent'))
    db.session.add(click)

    allowed = True
    if campaign.countries:
        codes = [c.strip().upper() for c in campaign.countries.split(',') if c.strip()]
        if country and country.upper() not in codes:
            allowed = False

    if allowed:
        campaign.hits += 1
        targets = []
        targets.extend([campaign.url])
        if campaign.extra_urls:
            for line in campaign.extra_urls.splitlines():
                if not line.strip():
                    continue
                if '|' in line:
                    url_line, weight = line.split('|', 1)
                    weight = int(weight) if weight.isdigit() else 1
                else:
                    url_line, weight = line, 1
                targets.extend([url_line.strip()] * weight)
        target = random.choice(targets)
        target = replace_macros(target, ip, country, request.headers.get('User-Agent'))

        if request.query_string:
            target += ("&" if "?" in target else "?") + request.query_string.decode()
        db.session.commit()

        if campaign.redirect_type == '302':
            return redirect(target)
        if campaign.redirect_type == 'refresh':
            resp = app.make_response('')
            resp.headers['Refresh'] = f"{campaign.delay}; url={target}"
            return resp
        if campaign.redirect_type == 'iframe':
            return render_template('iframe.html', url=target, delay=campaign.delay)
        return render_template(
            'redirect.html',
            url=target,
            redirect_type=campaign.redirect_type,
            delay=campaign.delay,
        )

    db.session.commit()
    if campaign.fallback_url and is_safe_url(campaign.fallback_url):
        fb = replace_macros(campaign.fallback_url, ip, country, request.headers.get('User-Agent'))
        return redirect(fb)
    return 'Geo not allowed', 403

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
