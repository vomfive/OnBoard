
---

<div align="center">
  <img src="./static/logos/default-logo.png" width="250" alt="OnBoard Logo" />
</div>

# OnBoard

**OnBoard** est une application web de **SVM – Système de Management des Visiteurs**, conçue pour gérer simplement et efficacement l’émargement, la traçabilité et l’accueil des visiteurs, prestataires et intervenants dans un établissement.

[![Docker Pulls](https://img.shields.io/docker/pulls/vomfive/onboard-app)](https://hub.docker.com/r/vomfive/onboard-app)
[![Licence](https://img.shields.io/badge/Licence-CC%20BY--NC%204.0-blue)](https://creativecommons.org/licenses/by-nc/4.0/)

---

## 📌 Qu’est-ce qu’un SVM ?

Un **SVM (Système de Management des Visiteurs)** est une solution numérique qui centralise les processus d'accueil, de contrôle d’accès, de notifications internes, et d’émargement de tous les visiteurs d’un site.
**OnBoard** est un SVM simple à mettre en place, mais complet, adapté aux exigences de sécurité, de conformité et d’organisation des entreprises modernes.

---

## ✨ Fonctionnalités principales

* 💬 **Accueil simplifié des visiteurs** avec formulaire d’enregistrement
* 🔍 **Recherche intelligente** : saisie assistée du nom pour retrouver un profil existant
* 📝 **Signature électronique** d’un règlement (PDF personnalisé)
* 📧 **Notifications automatiques** à la personne visitée (et autres si besoin)
* 🚪 **Désinscription des visiteurs** en fin de passage
* 📊 **Tableau de bord des visites du jour** (présents/absents)
* ⬇️ **Export CSV** pour archivage ou analyse
* 🔐 **Portail administrateur sécurisé** avec :

  * Gestion des personnes pouvant être visitées
  * Configuration des consignes et notifications
  * Personnalisation graphique (logo, couleurs)
  * Paramétrage du serveur SMTP
  * Changement du mot de passe admin

---

## 🛠️ Cas d’usage

* Entreprises industrielles ou tertiaires
* Établissements publics ou privés
* Chantiers, usines, laboratoires
* Locaux avec protocole de sécurité ou accès restreint
* Accueil de prestataires techniques ou visiteurs ponctuels

---

## 🚀 Lancer l'application avec Docker

```bash
docker run -d -p 5000:5000 --name onboard-app vomfive/onboard-app:latest
```

Accédez à l’interface via : [http://localhost:5000](http://localhost:5000)

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

Lancement :

```bash
docker-compose up -d
```

---

## 🧑‍💻 Installation manuelle (développeur)

```bash
git clone https://github.com/vomfive/beta-OnBoard
cd beta-OnBoard
pip3 install Flask Flask_SQLAlchemy Werkzeug
python app.py
```

---

## 🔐 Accès administrateur

* Accédez à : `/login`
* Mot de passe par défaut : **admin**

---

## 📁 Arborescence du projet

```
onboard-app/
├── app.py
├── static/
│   ├── style.css
│   └── logos/
│       └── default-logo.png
├── templates/
│   ├── index.html
│   ├── login.html
│   ├── configuration.html
│   └── visitors.html
├── uploads_pdf/
└── data/
```

---

## 🛡️ Licence

**CC BY-NC 4.0**
Ce projet est librement utilisable à des fins non commerciales. Pour un usage professionnel ou commercial, merci de contacter l’auteur.
[Consultez la licence complète](https://creativecommons.org/licenses/by-nc/4.0/)

---
