from flask import Flask, request, jsonify, render_template, redirect, url_for, make_response, send_from_directory, session, flash, Response
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from datetime import datetime, date, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import csv
import io
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from urllib.parse import urlparse, urljoin
from collections import Counter
from math import ceil
import re
import requests

app = Flask(__name__)
app.secret_key = "change_this_secret_key"
csrf = CSRFProtect(app)
app.permanent_session_lifetime = timedelta(minutes=30)

ADMIN_PASSWORD = "tonmotdepasse"

RECAPTCHA_SITE_KEY = "VOTRE_SITE_KEY"
RECAPTCHA_SECRET_KEY = "VOTRE_SECRET_KEY"
RECAPTCHA_THRESHOLD = 3  # nombre d'échecs avant captcha

def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

@app.before_request
def make_session_permanent():
    if session.get('admin_logged_in'):
        session.permanent = True

@app.route('/login', methods=['GET', 'POST'])
def login():
    config = Configuration.query.first()
    next_url = request.args.get('next') or request.form.get('next') or url_for('configuration')
    message = request.args.get('message')
    # Utilisation dynamique de la config captcha
    captcha_enabled = bool(getattr(config, 'captcha_enabled', False))
    captcha_threshold = getattr(config, 'captcha_threshold', 3)
    recaptcha_site_key = getattr(config, 'recaptcha_site_key', '')
    recaptcha_secret_key = getattr(config, 'recaptcha_secret_key', '')
    show_captcha = captcha_enabled and session.get('login_failures', 0) >= captcha_threshold

    if request.method == 'POST':
        password = request.form.get('password')
        stay_logged = request.form.get('stay_logged') == 'on'
        # Vérification du captcha si nécessaire
        if show_captcha:
            recaptcha_response = request.form.get('g-recaptcha-response')
            if not recaptcha_response:
                flash("Veuillez valider le captcha.", "danger")
                return render_template('login.html', config=config, next=next_url, message=message, show_captcha=show_captcha, recaptcha_site_key=recaptcha_site_key)
            # Vérification côté Google
            r = requests.post(
                'https://www.google.com/recaptcha/api/siteverify',
                data={'secret': recaptcha_secret_key, 'response': recaptcha_response}
            )
            if not r.json().get('success'):
                flash("Captcha invalide.", "danger")
                return render_template('login.html', config=config, next=next_url, message=message, show_captcha=show_captcha, recaptcha_site_key=recaptcha_site_key)
        if config and check_password_hash(config.admin_password_hash, password):
            session['admin_logged_in'] = True
            session['login_failures'] = 0  # reset uniquement après succès
            if stay_logged:
                app.permanent_session_lifetime = timedelta(days=7)
            else:
                app.permanent_session_lifetime = timedelta(minutes=30)
            session.permanent = True
            return redirect(next_url)
        else:
            session['login_failures'] = session.get('login_failures', 0) + 1
            flash("Mot de passe incorrect", "danger")
    # Ne pas reset login_failures sur GET

    return render_template('login.html', config=config, next=next_url, message=message, show_captcha=show_captcha, recaptcha_site_key=recaptcha_site_key)

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    flash("Vous avez été déconnecté avec succès.", "success")
    return redirect(url_for('login'))

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['SQLALCHEMY_BINDS'] = {
    'config_db': 'sqlite:///config.db'
}

UPLOAD_FOLDER_PDF = 'uploads_pdf'
app.config['UPLOAD_FOLDER_PDF'] = UPLOAD_FOLDER_PDF
if not os.path.exists(UPLOAD_FOLDER_PDF):
    os.makedirs(UPLOAD_FOLDER_PDF)

FAVICON_FOLDER = os.path.join(app.static_folder, 'favicons')
app.config['FAVICON_FOLDER'] = FAVICON_FOLDER
if not os.path.exists(FAVICON_FOLDER):
    os.makedirs(FAVICON_FOLDER)

ALLOWED_EXTENSIONS_LOGO = {'png', 'jpg', 'jpeg', 'gif', 'svg'}
LOGO_FOLDER = os.path.join(app.static_folder, 'logos')
app.config['LOGO_FOLDER'] = LOGO_FOLDER
if not os.path.exists(LOGO_FOLDER):
    os.makedirs(LOGO_FOLDER)

ALLOWED_EXTENSIONS_PDF = {'pdf'}
ALLOWED_EXTENSIONS_FAVICON = {'png', 'ico', 'svg', 'jpg', 'jpeg', 'gif'}

db = SQLAlchemy(app)

class Visitor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    entreprise = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    date_enregistrement = db.Column(db.DateTime, default=datetime.utcnow)
    signature_data = db.Column(db.Text, nullable=True)
    person_to_visit_id = db.Column(db.Integer, db.ForeignKey('person_to_visit.id'), nullable=True)
    person_to_visit = db.relationship('PersonToVisit', backref=db.backref('visitors', lazy=True))
    heure_depart = db.Column(db.DateTime, nullable=True)
    def __repr__(self):
        return f"Visitor('{self.nom}', '{self.prenom}', Visited: {self.person_to_visit.name if self.person_to_visit else 'N/A'})"

class PersonToVisit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    def __repr__(self):
        return f"PersonToVisit('{self.name}', '{self.email}')"

class Configuration(db.Model):
    __bind_key__ = 'config_db'
    id = db.Column(db.Integer, primary_key=True)
    smtp_server = db.Column(db.String(100), nullable=False, default='smtp.example.com')
    smtp_port = db.Column(db.Integer, nullable=False, default=587)
    smtp_user = db.Column(db.String(100), nullable=False, default='user@example.com')
    smtp_password = db.Column(db.String(100), nullable=False, default='password')
    sender_email = db.Column(db.String(120), nullable=False, default='sender@example.com')
    pdf_filename = db.Column(db.String(255), nullable=True)
    logo_filename = db.Column(db.String(255), nullable=True)
    admin_password_hash = db.Column(
        db.String(255),
        nullable=False,
        default=generate_password_hash('admin', method='pbkdf2:sha256')
    )
    site_name = db.Column(db.String(100), default='Mon Site')
    primary_color = db.Column(db.String(7), default='#0C2E45')
    primary_dark = db.Column(db.String(7), default='#257C88')
    secondary_color = db.Column(db.String(7), default='#A4D9E1')
    secondary_dark = db.Column(db.String(7), default='#87C1CB')
    success_color = db.Column(db.String(7), default='#28a745')
    success_dark = db.Column(db.String(7), default='#218838')
    danger_color = db.Column(db.String(7), default='#dc3545')
    danger_dark = db.Column(db.String(7), default='#c82333')
    background_color = db.Column(db.String(7), default='#FAFAFA')
    surface_color = db.Column(db.String(7), default='#FFFFFF')
    text_color = db.Column(db.String(7), default='#0C2E45')
    text_color_light = db.Column(db.String(7), default='#257C88')
    border_color = db.Column(db.String(7), default='#ced4da')
    divider_color = db.Column(db.String(7), default='#e9ecef')
    # Champs pour captcha
    captcha_enabled = db.Column(db.Boolean, default=False)
    captcha_threshold = db.Column(db.Integer, default=3)
    recaptcha_site_key = db.Column(db.String(120), nullable=True)
    recaptcha_secret_key = db.Column(db.String(120), nullable=True)
    def __repr__(self):
        return f"Configuration(SMTP Server: '{self.smtp_server}', PDF: '{self.pdf_filename}', Favicon: '{self.favicon_filename}')"

class NotificationEmail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    def __repr__(self):
        return f"NotificationEmail('{self.email}')"

def allowed_file(filename, allowed_extensions_set):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions_set

def send_email(recipient_email, subject, body, attach_pdf=False, html=False):
    config = Configuration.query.first()
    print("[LOG] Début send_email")
    if not config:
        print("[LOG] Erreur : Configuration SMTP non trouvée.")
        return False
    print(f"[LOG] SMTP config utilisée : serveur={config.smtp_server}, port={config.smtp_port}, user={config.smtp_user}, sender={config.sender_email}")
    if not all([config.smtp_server, config.smtp_port, config.smtp_user, config.smtp_password, config.sender_email]):
        print("[LOG] Erreur : Paramètres SMTP incomplets.")
        return False
    # Création du message
    if html:
        msg = MIMEText(body, 'html')
    else:
        msg = MIMEText(body, 'plain')
    msg['Subject'] = subject
    msg['From'] = config.sender_email
    msg['To'] = recipient_email
    try:
        print("[LOG] Connexion au serveur SMTP...")
        with smtplib.SMTP(config.smtp_server, int(config.smtp_port)) as server:
            print("[LOG] Démarrage TLS...")
            server.starttls()
            print("[LOG] Login SMTP...")
            server.login(config.smtp_user, config.smtp_password)
            print(f"[LOG] Envoi du mail à {recipient_email}...")
            server.sendmail(config.sender_email, recipient_email, msg.as_string())
        print(f"[LOG] Email envoyé à {recipient_email} avec succès.")
        return True
    except smtplib.SMTPException as e:
        print(f"[LOG] Erreur SMTP lors de l'envoi de l'email à {recipient_email} : {e}")
        return False
    except Exception as e:
        print(f"[LOG] Erreur lors de l'envoi de l'email à {recipient_email} : {e}")
        return False

@app.route('/')
def index():
    people_to_visit = PersonToVisit.query.all()
    config = Configuration.query.first()
    pdf_filename_for_template = None
    if config and config.pdf_filename and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER_PDF'], config.pdf_filename)):
        pdf_filename_for_template = config.pdf_filename
    return render_template('index.html', people_to_visit=people_to_visit, pdf_filename=pdf_filename_for_template, config=config)

@app.route('/configuration', methods=['GET'])
def configuration():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login', next=request.url, message='Session expirée, veuillez vous reconnecter.'))
    config = Configuration.query.first()
    people_to_visit = PersonToVisit.query.all()
    pdf_uploaded_status = False
    current_pdf_filename = None
    if config and config.pdf_filename and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER_PDF'], config.pdf_filename)):
        pdf_uploaded_status = True
        current_pdf_filename = config.pdf_filename
    notification_emails = NotificationEmail.query.all()
    return render_template('configuration.html', 
                           config=config, 
                           people_to_visit=people_to_visit, 
                           pdf_uploaded=pdf_uploaded_status, 
                           pdf_filename=current_pdf_filename,
                           notification_emails=notification_emails)

@app.route('/save-configuration', methods=['POST'])
def save_configuration():
    smtp_server = request.form.get('smtp_server')
    smtp_port = request.form.get('smtp_port', type=int)
    smtp_user = request.form.get('smtp_user')
    smtp_password = request.form.get('smtp_password')
    sender_email = request.form.get('sender_email')
    primary_color = request.form.get('primary_color')
    primary_dark = request.form.get('primary_dark')
    secondary_color = request.form.get('secondary_color')
    secondary_dark = request.form.get('secondary_dark')
    success_color = request.form.get('success_color')
    success_dark = request.form.get('success_dark')
    danger_color = request.form.get('danger_color')
    danger_dark = request.form.get('danger_dark')
    background_color = request.form.get('background_color')
    surface_color = request.form.get('surface_color')
    text_color = request.form.get('text_color')
    text_color_light = request.form.get('text_color_light')
    border_color = request.form.get('border_color')
    divider_color = request.form.get('divider_color')
    site_name = request.form.get('site_name')
    if not all([smtp_server, smtp_port, smtp_user, smtp_password, sender_email]):
         print("Erreur : Tous les champs de configuration SMTP sont requis.")
         return redirect(url_for('configuration'))
    config = Configuration.query.first()
    if not config:
        config = Configuration()
        db.session.add(config)
    config.smtp_server = smtp_server
    config.smtp_port = smtp_port
    config.smtp_user = smtp_user
    config.smtp_password = smtp_password
    config.sender_email = sender_email
    config.primary_color = primary_color
    config.primary_dark = primary_dark
    config.secondary_color = secondary_color
    config.secondary_dark = secondary_dark
    config.success_color = success_color
    config.success_dark = success_dark
    config.danger_color = danger_color
    config.danger_dark = danger_dark
    config.background_color = background_color
    config.surface_color = surface_color
    config.text_color = text_color
    config.text_color_light = text_color_light
    config.border_color = border_color
    config.divider_color = divider_color
    config.site_name = site_name
    if 'pdf_file' in request.files:
        file = request.files['pdf_file']
        if file.filename != '':
            if file and allowed_file(file.filename, ALLOWED_EXTENSIONS_PDF):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER_PDF'], filename)
                file.save(filepath)
                config.pdf_filename = filename
                print(f"Fichier PDF '{filename}' sauvegardé.")
            else:
                print("Erreur : Type de fichier PDF non autorisé.")
    if 'favicon_file' in request.files:
        file = request.files['favicon_file']
        if file.filename != '':
            if file and allowed_file(file.filename, ALLOWED_EXTENSIONS_FAVICON):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['FAVICON_FOLDER'], filename)
                file.save(filepath)
                config.favicon_filename = filename 
                print(f"Favicon '{filename}' sauvegardé.")
            else:
                print("Erreur : Type de fichier Favicon non autorisé.")
    if 'logo_file' in request.files:
        file = request.files['logo_file']
        if file.filename != '':
            if file and allowed_file(file.filename, ALLOWED_EXTENSIONS_LOGO):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['LOGO_FOLDER'], filename)
                file.save(filepath)
                config.logo_filename = filename
                print(f"Logo '{filename}' sauvegardé.")
            else:
                print("Erreur : Type de fichier Logo non autorisé.")
    try:
        db.session.commit()
        print("Configuration sauvegardée avec succès.")
    except Exception as e:
        db.session.rollback()
        print(f"Erreur lors de la sauvegarde de la configuration : {e}")
    return redirect(url_for('configuration', tab='tab-form-pdf'))

@app.route('/save_smtp', methods=['POST'])
def save_smtp():
    config = Configuration.query.first()
    smtp_server = request.form.get('smtp_server', '').strip()
    smtp_port = request.form.get('smtp_port', '').strip()
    smtp_user = request.form.get('smtp_user', '').strip()
    smtp_password = request.form.get('smtp_password', '').strip()
    sender_email = request.form.get('sender_email', '').strip()
    # Validation email expéditeur
    if not sender_email or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", sender_email):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': 'Email expéditeur invalide.'}), 400
        flash("Email expéditeur invalide.", "danger")
        return redirect(url_for('configuration', tab='tab-smtp'))
    config.smtp_server = smtp_server
    config.smtp_port = smtp_port
    config.smtp_user = smtp_user
    config.smtp_password = smtp_password
    config.sender_email = sender_email
    db.session.commit()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True})
    return redirect(url_for('configuration', tab='tab-smtp'))

@app.route('/save_appearance', methods=['POST'])
def save_appearance():
    config = Configuration.query.first()
    if not config:
        config = Configuration()
        db.session.add(config)
    config.primary_color = request.form.get('primary_color')
    config.primary_dark = request.form.get('primary_dark')
    config.secondary_color = request.form.get('secondary_color')
    config.secondary_dark = request.form.get('secondary_dark')
    config.success_color = request.form.get('success_color')
    config.success_dark = request.form.get('success_dark')
    config.danger_color = request.form.get('danger_color')
    config.danger_dark = request.form.get('danger_dark')
    config.background_color = request.form.get('background_color')
    config.surface_color = request.form.get('surface_color')
    config.text_color = request.form.get('text_color')
    config.text_color_light = request.form.get('text_color_light')
    config.border_color = request.form.get('border_color')
    config.divider_color = request.form.get('divider_color')
    if 'logo_file' in request.files:
        file = request.files['logo_file']
        if file and file.filename:
            filename = secure_filename(file.filename)
            if not allowed_file(filename, ALLOWED_EXTENSIONS_LOGO):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'error': 'Type de fichier logo non autorisé.'}), 400
                flash("Type de fichier logo non autorisé.", "danger")
                return redirect(url_for('configuration', tab='tab-appearance'))
            file.seek(0, os.SEEK_END)
            size = file.tell()
            file.seek(0)
            if size > 2 * 1024 * 1024:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'error': 'Le logo est trop volumineux (max 2 Mo).'}), 400
                flash("Le logo est trop volumineux (max 2 Mo).", "danger")
                return redirect(url_for('configuration', tab='tab-appearance'))
            file.save(os.path.join(app.config['LOGO_FOLDER'], filename))
            config.logo_filename = filename
    if 'favicon_file' in request.files:
        file = request.files['favicon_file']
        if file and file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['FAVICON_FOLDER'], filename))
            config.favicon_filename = filename
    db.session.commit()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True})
    return redirect(url_for('configuration', tab='tab-appearance'))

@app.route('/save_pdf', methods=['POST'])
def save_pdf():
    config = Configuration.query.first()
    if not config:
        config = Configuration()
        db.session.add(config)
    if 'pdf_file' in request.files:
        file = request.files['pdf_file']
        if file and file.filename:
            filename = secure_filename(file.filename)
            # Vérification extension
            if not allowed_file(filename, ALLOWED_EXTENSIONS_PDF):
                flash("Type de fichier PDF non autorisé.", "danger")
                return redirect(url_for('configuration', tab='tab-form'))
            # Limite de taille (ex: 5 Mo)
            file.seek(0, os.SEEK_END)
            size = file.tell()
            file.seek(0)
            if size > 5 * 1024 * 1024:
                flash("Le PDF est trop volumineux (max 5 Mo).", "danger")
                return redirect(url_for('configuration', tab='tab-form'))
            file.save(os.path.join(app.config['UPLOAD_FOLDER_PDF'], filename))
            config.pdf_filename = filename
    db.session.commit()
    return redirect(url_for('configuration', tab='tab-form'))

@app.route('/uploads_pdf/<filename>')
def uploaded_pdf_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER_PDF'], filename)

@app.route('/add-person-to-visit', methods=['POST'])
def add_person_to_visit():
    name = request.form.get('person_name', '').strip()
    email = request.form.get('person_email', '').strip()
    # Validation nom : longueur, caractères autorisés (lettres, espaces, tirets)
    if not name or len(name) > 100 or not re.match(r"^[A-Za-zÀ-ÿ\-\s']+$", name):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': 'Nom invalide (caractères non autorisés ou trop long)'}), 400
        flash("Nom invalide (caractères non autorisés ou trop long)", "danger")
        return redirect(url_for('configuration', tab='tab-form'))
    # Validation email basique
    if not email or len(email) > 120 or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': 'Email invalide'}), 400
        flash("Email invalide", "danger")
        return redirect(url_for('configuration', tab='tab-form'))
    new_person = PersonToVisit(name=name, email=email)
    db.session.add(new_person)
    try:
        db.session.commit()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            people = PersonToVisit.query.all()
            people_list = [{'id': p.id, 'name': p.name, 'email': p.email} for p in people]
            return jsonify({'success': True, 'people': people_list})
    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': "Erreur lors de l'ajout de la personne."}), 500
        flash("Erreur lors de l'ajout de la personne.", "danger")
    return redirect(url_for('configuration', tab='tab-form'))

@app.route('/delete-person-to-visit/<int:person_id>', methods=['POST'])
def delete_person_to_visit(person_id):
    person = PersonToVisit.query.get(person_id)
    if person:
        db.session.delete(person)
        db.session.commit()
    return redirect(url_for('configuration', tab='tab-form'))

@app.route('/enregistrer-visiteur', methods=['POST'])
def enregistrer_visiteur():
    if request.method == 'POST':
        data = request.form
        nom = data.get('nom', '').strip()
        prenom = data.get('prenom', '').strip()
        entreprise = data.get('entreprise', '').strip()
        person_to_visit_id = data.get('person_to_visit')
        signature_data = data.get('signature_data')
        pdf_viewed = data.get('pdf_viewed') == 'true'
        autre_nom = data.get('autre_nom', '').strip()
        autre_prenom = data.get('autre_prenom', '').strip()
        # Validation nom/prenom/entreprise
        if not nom or len(nom) > 100 or not re.match(r"^[A-Za-zÀ-ÿ\-\s']+$", nom):
            return jsonify({"message": "Nom invalide."}), 400
        if not prenom or len(prenom) > 100 or not re.match(r"^[A-Za-zÀ-ÿ\-\s']+$", prenom):
            return jsonify({"message": "Prénom invalide."}), 400
        if not entreprise or len(entreprise) > 100 or not re.match(r"^[A-Za-zÀ-ÿ0-9\-\s'.,]+$", entreprise):
            return jsonify({"message": "Entreprise invalide."}), 400
        if not all([nom, prenom, entreprise, person_to_visit_id]):
            return jsonify({"message": "Tous les champs sont requis."}, 400)
        config = Configuration.query.first()
        if config and config.pdf_filename:
            if not pdf_viewed or not signature_data:
                return jsonify({"message": "Veuillez lire les consignes et signer."}, 400)
        send_emails_flag = bool(config and config.smtp_server and config.smtp_user and config.smtp_password and config.sender_email and config.smtp_port)
        if not send_emails_flag:
            print("[LOG] Avertissement : Configuration SMTP incomplète. Emails non envoyés.")
        # Gestion du cas 'autre'
        if person_to_visit_id == 'autre':
            if not autre_nom or not autre_prenom:
                return jsonify({"message": "Veuillez renseigner le nom et prénom de la personne à visiter."}, 400)
            personne_a_visiter = f"Autre : {autre_prenom} {autre_nom}"
            nouveau_visiteur = Visitor(
                nom=nom, prenom=prenom, entreprise=entreprise,
                person_to_visit=None, signature_data=signature_data
            )
            nouveau_visiteur.email = personne_a_visiter
            person_to_visit = None  # Pour la suite
        else:
            person_to_visit = PersonToVisit.query.get(person_to_visit_id)
            if not person_to_visit:
                return jsonify({"message": "Personne à visiter invalide."}, 400)
            nouveau_visiteur = Visitor(
                nom=nom, prenom=prenom, entreprise=entreprise,
                person_to_visit=person_to_visit, signature_data=signature_data
            )
        db.session.add(nouveau_visiteur)
        try:
            db.session.commit()
            message = (
                "Votre enregistrement a bien été pris en compte. Merci de patienter, quelqu'un va venir vous accueillir.<br>"
                "N'oubliez pas de venir vous désinscrire avant votre départ !"
            )
            if send_emails_flag and person_to_visit:
                # Préparation du logo (logo config ou logo par défaut sans accent)
                logo_filename = config.logo_filename if config and config.logo_filename else 'default-logo.png'
                logo_url = url_for('static', filename=f'logos/{logo_filename}', _external=True)
                logo_html_top = f'<div style="text-align:center;margin-bottom:18px;"><img src="{logo_url}" alt="Logo" style="max-width:240px;max-height:100px;"></div>'
                onboard_text_bottom = '<div style="text-align:right;color:#257C88;font-size:15px;font-weight:bold;margin-top:24px;">OnBoard</div>'
                # Message pour la personne visitée (HTML design)
                heure_str = datetime.now().strftime('%d/%m/%Y %H:%M')
                site_name = config.site_name if config and config.site_name else "le site"
                sujet_visited = f"[OnBoard] {prenom} {nom} est arrivé"
                body_visited = f'''
                <div style="max-width:500px;margin:0 auto;padding:24px;background:#f7fafd;border-radius:8px;border:1px solid #e3e8ee;font-family:Arial,sans-serif;">
                  {logo_html_top}
                  <h2 style="color:#257C88;margin-top:0;">Arrivée d'un visiteur</h2>
                  <p style="font-size:16px;">Pour information, <span style="font-weight:bold;color:#0C2E45;">{prenom} {nom}</span> de l'entreprise <span style="font-weight:bold;color:#0C2E45;">{entreprise}</span> est arrivé sur le site de <span style="color:#257C88;">{site_name}</span>.</p>
                  <p style="font-size:15px;margin:18px 0 8px 0;">Heure d'enregistrement :</p>
                  <div style="font-size:18px;font-weight:bold;color:#28a745;margin-bottom:18px;">{heure_str}</div>
                  {onboard_text_bottom}
                </div>
                '''
                print(f"[LOG] Appel send_email avec : dest={person_to_visit.email}, sujet={sujet_visited}, body={body_visited}")
                if send_email(person_to_visit.email, sujet_visited, body_visited, html=True):
                    print("[LOG] Email envoyé avec succès (retour True).")
                else:
                    print("[LOG] L'envoi de l'email a échoué (retour False).")
                # Message pour les personnes toujours notifiées (HTML design)
                sujet_notif = f"[OnBoard] Nouvel enregistrement sur le site de {site_name}"
                body_notif = f'''
                <div style="max-width:500px;margin:0 auto;padding:24px;background:#f7fafd;border-radius:8px;border:1px solid #e3e8ee;font-family:Arial,sans-serif;">
                  {logo_html_top}
                  <h2 style="color:#257C88;margin-top:0;">Nouvel enregistrement visiteur</h2>
                  <p style="font-size:16px;">Une nouvelle personne vient de s'enregistrer pour voir <span style="font-weight:bold;color:#0C2E45;">{person_to_visit.name}</span>.</p>
                  <div style="margin:18px 0 8px 0;">
                    <div><b>Nom :</b> <span style="color:#0C2E45;">{nom}</span></div>
                    <div><b>Prénom :</b> <span style="color:#0C2E45;">{prenom}</span></div>
                    <div><b>Entreprise :</b> <span style="color:#0C2E45;">{entreprise}</span></div>
                    <div><b>Heure et date d'enregistrement :</b> <span style="color:#28a745;">{heure_str}</span></div>
                  </div>
                  <div style="margin:18px 0 8px 0;">
                    <a href="http://127.0.0.1:5000/visitors" style="color:#257C88;text-decoration:underline;font-weight:bold;">Voir la liste des visiteurs</a>
                  </div>
                  {onboard_text_bottom}
                </div>
                '''
                notification_emails = NotificationEmail.query.all()
                for notif in notification_emails:
                    print(f"[LOG] Appel send_email pour notification : dest={notif.email}, sujet={sujet_notif}, body={body_notif}")
                    if send_email(notif.email, sujet_notif, body_notif, html=True):
                        print(f"[LOG] Email de notification envoyé à {notif.email} (retour True).")
                    else:
                        print(f"[LOG] L'envoi de l'email de notification à {notif.email} a échoué (retour False).")
            status_code = 200
        except Exception as e:
            db.session.rollback()
            message = f"Erreur lors de l'enregistrement : {str(e)}"
            status_code = 500
        return jsonify({"message": message}), status_code

@app.route('/visitors', methods=['GET'])
def visitors():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login', next=request.url))
    filter_date_str = request.args.get('filter_date')
    entreprise = request.args.get('entreprise', '').strip()
    person_id = request.args.get('person_id', '').strip()
    statut = request.args.get('statut', '').strip()
    page = int(request.args.get('page', 1))
    per_page = 20  # Nombre de visiteurs par page

    if not filter_date_str:
        filter_date_obj = date.today()
        filter_date_str = filter_date_obj.strftime('%Y-%m-%d')
    else:
        try:
            filter_date_obj = datetime.strptime(filter_date_str, '%Y-%m-%d').date()
        except ValueError:
            filter_date_obj = date.today()
            filter_date_str = filter_date_obj.strftime('%Y-%m-%d')

    visitors_query = Visitor.query.order_by(Visitor.date_enregistrement.desc())
    visitors_query = visitors_query.filter(db.func.date(Visitor.date_enregistrement) == filter_date_obj)

    if entreprise:
        visitors_query = visitors_query.filter(Visitor.entreprise.ilike(f'%{entreprise}%'))
    if person_id:
        visitors_query = visitors_query.filter(Visitor.person_to_visit_id == int(person_id))
    if statut == "present":
        visitors_query = visitors_query.filter(Visitor.heure_depart == None)
    elif statut == "sorti":
        visitors_query = visitors_query.filter(Visitor.heure_depart != None)

    total_visitors = visitors_query.count()
    total_pages = ceil(total_visitors / per_page)
    visitors_list = visitors_query.offset((page-1)*per_page).limit(per_page).all()

    config = Configuration.query.first()
    presents = [v for v in visitors_list if v.heure_depart is None]
    presents_count = len([v for v in visitors_query.filter(Visitor.heure_depart == None).all()])
    sortis_count = total_visitors - presents_count

    heures = [v.date_enregistrement.strftime('%H:00') for v in visitors_list if v.date_enregistrement]
    if heures:
        heure_pic, nb_pic = Counter(heures).most_common(1)[0]
    else:
        heure_pic, nb_pic = None, 0

    personnes = PersonToVisit.query.all()
    # Après avoir filtré visitors_list
    heures = [v.date_enregistrement.strftime('%H') for v in visitors_list if v.date_enregistrement]
    compteur_heures = Counter(heures)
    # Pour chaque heure de 0 à 23, on met 0 si aucune visite
    visites_par_heure = [compteur_heures.get(f"{h:02d}", 0) for h in range(24)]

    return render_template(
        'visitors.html',
        visitors=visitors_list,
        total_visitors=total_visitors,
        presents_count=presents_count,
        sortis_count=sortis_count,
        heure_pic=heure_pic,
        nb_pic=nb_pic,
        config=config,
        selected_date=filter_date_str,
        entreprise=entreprise,
        person_id=person_id,
        statut=statut,
        page=page,
        total_pages=total_pages,
        visites_par_heure=visites_par_heure,
        personnes=personnes
    )

@app.route('/export-visitors-csv')
def export_visitors_csv():
    filter_date_str = request.args.get('filter_date')
    if not filter_date_str:
        filter_date_obj = date.today()
    else:
        try:
            filter_date_obj = datetime.strptime(filter_date_str, '%Y-%m-%d').date()
        except ValueError:
            filter_date_obj = date.today()
    visitors_query = Visitor.query.order_by(Visitor.date_enregistrement.desc())
    if filter_date_str:
        visitors_query = visitors_query.filter(db.func.date(Visitor.date_enregistrement) == filter_date_obj)
    visitors = visitors_query.all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Nom', 'Prénom', 'Entreprise', 'Date entrée', 'Date sortie',
        'Statut', 'Signature', 'Consignes lues'
    ])
    for visitor in visitors:
        statut = "Présent" if not visitor.heure_depart else "Sorti"
        signature = "Signé" if visitor.signature_data else "Non signé"
        consignes = "Oui" if getattr(visitor, 'pdf_viewed', True) else "Non"
        date_sortie = visitor.heure_depart.strftime('%Y-%m-%d %H:%M:%S') if visitor.heure_depart else ""
        writer.writerow([
            visitor.nom,
            visitor.prenom,
            visitor.entreprise,
            visitor.date_enregistrement.strftime('%Y-%m-%d %H:%M:%S'),
            date_sortie,
            statut,
            signature,
            consignes
        ])
    output.seek(0)
    return Response(output, mimetype="text/csv", headers={"Content-Disposition":"attachment;filename=visiteurs.csv"})

@app.route('/search-visitors', methods=['GET'])
def search_visitors():
    query_name = request.args.get('name', '').strip()
    if not query_name: return jsonify([])
    today = date.today()
    visitors_found = Visitor.query.filter(
        ((Visitor.nom.ilike(f'{query_name}%')) | (Visitor.prenom.ilike(f'{query_name}%'))) &
        (db.func.date(Visitor.date_enregistrement) == today) &
        (Visitor.heure_depart == None)
    ).limit(10).all()
    results = [{'id': v.id, 'nom': v.nom, 'prenom': v.prenom, 'entreprise': v.entreprise, 'email': v.email, 'enregistrement_actif': True} for v in visitors_found]
    return jsonify(results)

@app.route('/autocomplete-visitor', methods=['GET'])
def autocomplete_visitor():
    query_name = request.args.get('name', '').strip()
    if not query_name:
        return jsonify([])
    subquery = db.session.query(
        db.func.lower(Visitor.nom).label('nom'),
        db.func.lower(Visitor.prenom).label('prenom'),
        db.func.lower(Visitor.entreprise).label('entreprise'),
        db.func.max(Visitor.id).label('latest_id')
    ).filter(
        (db.func.lower(Visitor.nom).like(f'{query_name.lower()}%')) |
        (db.func.lower(Visitor.prenom).like(f'{query_name.lower()}%'))
    ).group_by(
        db.func.lower(Visitor.nom),
        db.func.lower(Visitor.prenom),
        db.func.lower(Visitor.entreprise)
    ).subquery()
    visitors_found = Visitor.query.join(subquery, Visitor.id == subquery.c.latest_id).all()
    results = [{
        'id': v.id,
        'nom': v.nom,
        'prenom': v.prenom,
        'entreprise': v.entreprise,
        'person_to_visit_id': v.person_to_visit_id,
        'enregistrement_actif': v.heure_depart is None and v.date_enregistrement.date() == date.today()
    } for v in visitors_found]
    return jsonify(results)

@app.route('/sign-out-visitor', methods=['POST'])
def sign_out_visitor():
    visitor_id = request.form.get('visitor_id')
    visitor_obj = Visitor.query.get(visitor_id)
    if not visitor_obj or visitor_obj.heure_depart is not None:
        return jsonify({'message': 'Aucun enregistrement actif trouvé pour ce visiteur.'}), 404
    visitor_obj.heure_depart = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Heure de départ enregistrée avec succès. Merci pour votre visite et à bientôt.'})

@app.route('/delete-favicon', methods=['POST'])
def delete_favicon():
    config = Configuration.query.first()
    if config and config.favicon_filename:
        favicon_path = os.path.join(app.config['FAVICON_FOLDER'], config.favicon_filename)
        if os.path.exists(favicon_path):
            os.remove(favicon_path)
        config.favicon_filename = None
        db.session.commit()
    return redirect(url_for('configuration'))

@app.route('/delete-logo', methods=['POST'])
def delete_logo():
    config = Configuration.query.first()
    if config and config.logo_filename:
        logo_path = os.path.join(app.config['LOGO_FOLDER'], config.logo_filename)
        if os.path.exists(logo_path):
            os.remove(logo_path)
        config.logo_filename = None
        db.session.commit()
    return redirect(url_for('configuration'))

@app.route('/change-admin-password', methods=['POST'])
def change_admin_password():
    if not session.get('admin_logged_in'):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': 'Non autorisé'}), 401
        return redirect(url_for('login'))
    new_password = request.form.get('new_admin_password')
    confirm_password = request.form.get('confirm_admin_password')
    if new_password != confirm_password:
        msg = 'Les deux mots de passe ne correspondent pas.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': msg}), 400
        flash(msg, "danger")
        return redirect(url_for('configuration', tab='tab-user'))
    # Règles de sécurité du mot de passe
    password_errors = []
    if not new_password or len(new_password) < 8:
        password_errors.append('Au moins 8 caractères')
    if not any(c.islower() for c in new_password or ''):
        password_errors.append('Une minuscule')
    if not any(c.isupper() for c in new_password or ''):
        password_errors.append('Une majuscule')
    if not any(c.isdigit() for c in new_password or ''):
        password_errors.append('Un chiffre')
    if not any(c in '!@#$%^&*()-_=+[]{};:,.?/\\|<>~' for c in new_password or ''):
        password_errors.append('Un caractère spécial')
    if password_errors:
        msg = 'Le mot de passe doit contenir : ' + ', '.join(password_errors) + '.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': msg}), 400
        flash(msg, "danger")
        return redirect(url_for('configuration', tab='tab-user'))
    config = Configuration.query.first()
    config.admin_password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
    db.session.commit()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True})
    flash("Mot de passe administrateur modifié avec succès.", "success")
    return redirect(url_for('configuration', tab='tab-user'))

@app.route('/save-site-name', methods=['POST'])
def save_site_name():
    if not session.get('admin_logged_in'):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': 'Non autorisé'}), 401
        return redirect(url_for('login', next=request.url))
    site_name = request.form.get('site_name', '').strip()
    if not site_name or len(site_name) > 100:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': 'Nom du site invalide.'}), 400
        flash("Nom du site invalide.", "danger")
        return redirect(url_for('configuration', tab='tab-form'))
    config = Configuration.query.first()
    if config:
        config.site_name = site_name
        db.session.commit()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'site_name': site_name})
    return redirect(url_for('configuration', tab='tab-form'))

@app.route('/add-notification-email', methods=['POST'])
def add_notification_email():
    notif_email = request.form.get('notif_email', '').strip()
    # Validation email basique
    if not notif_email or len(notif_email) > 120 or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", notif_email):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': 'Email de notification invalide'}), 400
        flash("Email de notification invalide", "danger")
        return redirect(url_for('configuration', tab='tab-form'))
    if NotificationEmail.query.filter_by(email=notif_email).first():
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': 'Cet email est déjà enregistré.'}), 400
        flash("Cet email est déjà enregistré.", "warning")
        return redirect(url_for('configuration', tab='tab-form'))
    db.session.add(NotificationEmail(email=notif_email))
    try:
        db.session.commit()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            emails = NotificationEmail.query.all()
            emails_list = [{'id': e.id, 'email': e.email} for e in emails]
            return jsonify({'success': True, 'emails': emails_list})
    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': "Erreur lors de l'ajout de l'email."}), 500
        flash("Erreur lors de l'ajout de l'email.", "danger")
    return redirect(url_for('configuration', tab='tab-form'))

@app.route('/delete-notification-email/<int:notif_id>', methods=['POST'])
def delete_notification_email(notif_id):
    notif = NotificationEmail.query.get(notif_id)
    if notif:
        db.session.delete(notif)
        db.session.commit()
    return redirect(url_for('configuration', tab='tab-form'))

@app.route('/delete-pdf', methods=['POST'])
def delete_pdf():
    config = Configuration.query.first()
    if config and config.pdf_filename:
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER_PDF'], config.pdf_filename)
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        config.pdf_filename = None
        db.session.commit()
        flash("Le PDF a été supprimé.", "success")
    else:
        flash("Aucun PDF à supprimer.", "warning")
    return redirect(url_for('configuration', tab='tab-form'))

@app.route('/test-smtp', methods=['POST'])
def test_smtp():
    if not request.is_json:
        return jsonify({'success': False, 'error': 'Requête invalide.'}), 400
    data = request.get_json()
    test_email = data.get('test_email', '').strip()
    if not test_email or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", test_email):
        return jsonify({'success': False, 'error': 'Email de test invalide.'}), 400
    config = Configuration.query.first()
    if not config or not all([config.smtp_server, config.smtp_port, config.smtp_user, config.smtp_password, config.sender_email]):
        return jsonify({'success': False, 'error': 'Configuration SMTP incomplète.'}), 400
    try:
        subject = "Test SMTP OnBoard"
        body = "Ceci est un mail de test envoyé depuis la configuration OnBoard."
        if send_email(test_email, subject, body, html=False):
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Échec de l\'envoi du mail. Vérifiez la configuration SMTP.'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/save-auth-settings', methods=['POST'])
def save_auth_settings():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login', next=request.url))
    config = Configuration.query.first()
    captcha_enabled = request.form.get('captcha_enabled') == '1'
    captcha_threshold = request.form.get('captcha_threshold', type=int) or 3
    recaptcha_site_key = request.form.get('recaptcha_site_key', '').strip()
    recaptcha_secret_key = request.form.get('recaptcha_secret_key', '').strip()
    config.captcha_enabled = captcha_enabled
    config.captcha_threshold = captcha_threshold
    config.recaptcha_site_key = recaptcha_site_key
    config.recaptcha_secret_key = recaptcha_secret_key
    db.session.commit()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True})
    flash("Paramètres Captcha enregistrés.", "success")
    return redirect(url_for('configuration', tab='tab-user'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not Configuration.query.first():
            config = Configuration()
            db.session.add(config)
            db.session.commit()
            print("Configuration par défaut créée (mot de passe admin = 'admin').")
        print("Bases de données et tables créées/vérifiées.")
    app.run(debug=True)

