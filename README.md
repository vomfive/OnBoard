
<div align="center">
  <img src="./static/logos/default-logo.png" width="250" alt="OnBoard Logo" />
</div>

# OnBoard

**OnBoard** est une application web de **SVM – Système de Management des Visiteurs**, conçue pour gérer simplement et efficacement l’émargement, la traçabilité et l’accueil des visiteurs, prestataires et intervenants dans un établissement.

[![Docker Pulls](https://img.shields.io/docker/pulls/vomfive/onboard-app)](https://hub.docker.com/r/vomfive/onboard-app)
[![Licence](https://img.shields.io/badge/Licence-CC%20BY--NC%204.0-blue)](https://creativecommons.org/licenses/by-nc/4.0/)

---

## 📌 Qu’est-ce qu’un SVM ?

Un **SVM (Système de Management des Visiteurs)** est une solution numérique qui centralise les processus d'accueil, de contrôle d’accès, de notifications internes, et d’émargement.  
**OnBoard** est un SVM moderne, personnalisable et conforme aux exigences de sécurité des entreprises et établissements recevant du public.

---

## ✨ Fonctionnalités principales

### 🧾 Gestion des visiteurs (via `/visitors`)

| Fonctionnalité          | Description                                              |
|-------------------------|----------------------------------------------------------|
| 🔍 Recherche avancée   | Par entreprise, date, personne visitée                   |
| 🧰 Filtres dynamiques  | Présents / Sortis / Plages horaires                      |
| 📊 Tableau de bord     | Statistiques globales : volume, pics horaires, etc.      |
| 📁 Export CSV          | Téléchargement de la liste des visiteurs                 |

### 🎨 Personnalisation (via `/configuration`)

| Fonctionnalité                 | Description                                                  |
|--------------------------------|--------------------------------------------------------------|
| 🖼️ Upload de logo            | Depuis l’onglet « Personnalisation »                        |
| 🎨 Personnalisation des couleurs | Choix des couleurs principales pour l'application      |

### ✉️ Configuration SMTP (via `/configuration`)

| Fonctionnalité         | Description              |
|------------------------|--------------------------|
| 📧 Test SMTP intégré  | Envoi + retour visuel    |

### 🧪 Formulaires & visiteurs (via `/configuration`)

| Fonctionnalité                                       | Description                                              |
|------------------------------------------------------|----------------------------------------------------------|
| 📄 Ajout des consignes PDF                           | Téléversement d’un fichier PDF à signer                  |
| 👥 Gestion des personnes à visiter                   | Ajout, suppression        |
| 📬 Mails automatiques permanents                     | Ajout, suppression de destinataires systématiques                    |
| 🏷️ Nom du site                                      | Personnalisation le nom du site             |

### 🔐 Authentification (via `/configuration`)

| Fonctionnalité                 | Description                                              |
|--------------------------------|----------------------------------------------------------|
| 🔑 Changement mot de passe    | Par défaut : `admin`                                     |
| 🤖 Activation du reCAPTCHA    | Option activable pour sécuriser la connexion       |

### 🔐 Sécurité & Sessions

| Fonctionnalité                  | Description                                              |
|--------------------------------|----------------------------------------------------------|
| ⏳ Session étendue             | 30 min ou 7 jours avec « Rester connecté »              |
| 🤖 Google reCAPTCHA           | Sur l’écran de connexion admin (option activable)       |
| 🛡️ CSRF protection           | Flask-WTF sur tous les formulaires                      |
| 🧼 Validation des entrées     | Anti-injection XSS/SQL, etc.                            |
| 🧱 Critères de sécurité       | Longueur, majuscule, chiffre, caractère spécial         |
| 📉 Feedback clair             | Messages d’erreur stylés et explicites                  |

### 🧭 Ergonomie & Accessibilité

| Fonctionnalité                 | Description                                              |
|-------------------------------|----------------------------------------------------------|
| ⌨️ Navigation clavier         | Entrée = valider ou étape suivante                      |
| ✍️ Autocomplete              | Suggestions dans le formulaire visiteur                |
| 🔔 Messages homogènes        | Erreurs / succès uniformes dans toute l’interface       |

---

## 🛠️ Cas d’usage

* Sites industriels ou tertiaires  
* Établissements recevant du public  
* Chantiers, usines, zones sensibles  
* Accueil de visiteurs internes ou externes  

---

## 🚀 Lancer l'application avec Docker

```bash
docker run -d -p 5000:5000 --name onboard-app vomfive/onboard-app:latest
```

> Interface accessible via : [http://localhost:5000](http://localhost:5000)

---

## 🐳 Déploiement avec Docker Compose

```yaml
version: '3.8'

services:
  web:
    image: vomfive/onboard-app:latest
    ports:
      - "5000:5000"
    volumes:
      - ./data:/app/data
      - ./uploads_pdf:/app/uploads_pdf
      - ./static/logos:/app/static/logos
    environment:
      - FLASK_ENV=production
    restart: unless-stopped
```

```bash
docker-compose up -d
```

---

## 🧑‍💻 Installation manuelle (développeur)

```bash
git clone https://github.com/vomfive/OnBoard
cd OnBoard
pip3 install Flask Flask_SQLAlchemy Werkzeug Flask-WTF requests
python3 app.py
```

---

## 📁 Arborescence du projet

```
onboard-app/
├── app.py
├── static/
│   ├── style.css
│   ├── favicon.ico
│   └── logos/
│       └── default-logo.png
├── templates/
│   ├── index.html
│   ├── login.html
│   ├── configuration.html
│   └── visitors.html
├── uploads_pdf/
```

---

## 🛡️ Licence

**CC BY-NC 4.0**  
Ce projet est librement utilisable à des fins **non commerciales**.  
Pour un usage professionnel ou commercial, merci de contacter l’auteur.  
[Consulter la licence complète](https://creativecommons.org/licenses/by-nc/4.0/)
