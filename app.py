from flask import Flask, request, jsonify, render_template, redirect, url_for, make_response, send_from_directory, session, flash, Response
from flask_sqlalchemy import SQLAlchemy
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

app = Flask(__name__)
app.secret_key = "change_this_secret_key"
app.permanent_session_lifetime = timedelta(minutes=1)

ADMIN_PASSWORD = "tonmotdepasse"

def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

@app.route('/login', methods=['GET', 'POST'])
def login():
    config = Configuration.query.first()
    next_url = request.args.get('next') or request.form.get('next') or url_for('configuration')
    if request.method == 'POST':
        password = request.form.get('password')
        if config and check_password_hash(config.admin_password_hash, password):
            session['admin_logged_in'] = True
            return redirect(next_url)
        else:
            flash("Mot de passe incorrect", "danger")
    return render_template('login.html', config=config, next=next_url)

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
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
    if not config:
        print("Erreur : Configuration SMTP non trouvée.")
        return False
    if html:
        msg = MIMEMultipart()
        msg.attach(MIMEText(body, 'html'))
    else:
        msg = MIMEMultipart() if attach_pdf else MIMEText(body)
        if not attach_pdf:
            msg = MIMEText(body)
        else:
            msg.attach(MIMEText(body))
    msg['Subject'] = subject
    msg['From'] = config.sender_email
    msg['To'] = recipient_email
    try:
        with smtplib.SMTP(config.smtp_server, config.smtp_port) as server:
            server.starttls()
            server.login(config.smtp_user, config.smtp_password)
            server.sendmail(config.sender_email, recipient_email, msg.as_string())
        print(f"Email envoyé à {recipient_email} avec succès.")
        return True
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email à {recipient_email} : {e}")
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
        return redirect(url_for('login', next=request.url))
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
    config.smtp_server = request.form.get('smtp_server')
    config.smtp_port = request.form.get('smtp_port')
    config.smtp_user = request.form.get('smtp_user')
    config.smtp_password = request.form.get('smtp_password')
    config.sender_email = request.form.get('sender_email')
    db.session.commit()
    return redirect(url_for('configuration', tab='tab-smtp'))

@app.route('/save_appearance', methods=['POST'])
def save_appearance():
    print("DEBUG: save_appearance appelée !", request.form, request.files)
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
            file.save(os.path.join(app.config['LOGO_FOLDER'], filename))
            config.logo_filename = filename
    if 'favicon_file' in request.files:
        file = request.files['favicon_file']
        if file and file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['FAVICON_FOLDER'], filename))
            config.favicon_filename = filename
    db.session.commit()
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
            file.save(os.path.join(app.config['UPLOAD_FOLDER_PDF'], filename))
            config.pdf_filename = filename
    db.session.commit()
    return redirect(url_for('configuration', tab='tab-form'))

@app.route('/uploads_pdf/<filename>')
def uploaded_pdf_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER_PDF'], filename)

@app.route('/add-person-to-visit', methods=['POST'])
def add_person_to_visit():
    name = request.form.get('person_name')
    email = request.form.get('person_email')
    if not name or not email:
        return redirect(url_for('configuration', tab='tab-form'))
    new_person = PersonToVisit(name=name, email=email)
    db.session.add(new_person)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Erreur ajout personne: {e}")
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
        nom = data.get('nom')
        prenom = data.get('prenom')
        entreprise = data.get('entreprise')
        person_to_visit_id = data.get('person_to_visit')
        signature_data = data.get('signature_data')
        pdf_viewed = data.get('pdf_viewed') == 'true'
        if not all([nom, prenom, entreprise, person_to_visit_id]):
            return jsonify({"message": "Tous les champs sont requis."}, 400)
        config = Configuration.query.first()
        if config and config.pdf_filename:
            if not pdf_viewed or not signature_data:
                return jsonify({"message": "Veuillez lire les consignes et signer."}, 400)
        send_emails_flag = True
        if not config or not config.smtp_server or not config.smtp_user:
            print("Avertissement : Configuration SMTP incomplète. Emails non envoyés.")
            send_emails_flag = False
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
            if send_emails_flag:
                pass
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
    if filter_date_str:
        visitors_query = visitors_query.filter(db.func.date(Visitor.date_enregistrement) == filter_date_obj)
    visitors_list = visitors_query.all()
    config = Configuration.query.first()
    return render_template('visitors.html', visitors=visitors_list, selected_date=filter_date_str, config=config)

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
        return redirect(url_for('login'))
    new_password = request.form.get('new_admin_password')
    if not new_password:
        flash("Le mot de passe ne peut pas être vide.", "danger")
        return redirect(url_for('configuration', tab='tab-user'))
    config = Configuration.query.first()
    config.admin_password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
    db.session.commit()
    flash("Mot de passe administrateur modifié avec succès.", "success")
    return redirect(url_for('configuration', tab='tab-user'))

@app.route('/save-site-name', methods=['POST'])
def save_site_name():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login', next=request.url))
    site_name = request.form.get('site_name')
    config = Configuration.query.first()
    if config:
        config.site_name = site_name
        db.session.commit()
    return redirect(url_for('configuration', tab='tab-form'))

@app.route('/add-notification-email', methods=['POST'])
def add_notification_email():
    notif_email = request.form.get('notif_email')
    if notif_email and not NotificationEmail.query.filter_by(email=notif_email).first():
        db.session.add(NotificationEmail(email=notif_email))
        db.session.commit()
    return redirect(url_for('configuration', tab='tab-form'))

@app.route('/delete-notification-email/<int:notif_id>', methods=['POST'])
def delete_notification_email(notif_id):
    notif = NotificationEmail.query.get(notif_id)
    if notif:
        db.session.delete(notif)
        db.session.commit()
    return redirect(url_for('configuration', tab='tab-form'))

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

