# OnBoard - Gestion des Visiteurs

Ce projet est une application web Flask pour la gestion des visiteurs en entreprise. Il permet l'enregistrement, le suivi, les notifications, l'export CSV, et la personnalisation de l'interface.

## Fonctionnalités

- Enregistrement et désinscription des visiteurs
- Signature électronique et validation de consignes PDF
- Gestion des personnes à visiter
- Notifications par email (SMTP configurable)
- Export des visiteurs au format CSV
- Personnalisation des couleurs et du logo
- Authentification administrateur
- Protection des formulaires (CSRF possible avec Flask-WTF)
- Interface responsive

## Prérequis

- Python 3.8+
- pip
- Docker et Docker Compose (pour le déploiement)

## Installation

1. **Clone le dépôt :**
   ```bash
   git clone https://github.com/vagvom/beta-OnBoard
   cd beta-OnBoard
   ```

2. **Installe les dépendances :**
   ```bash
   pip install -r requirements.txt
   ```

3. **Lance l’application :**
   ```bash
   python app.py
   ```
   L’application sera accessible sur [http://localhost:5000](http://localhost:5000).

## Déploiement avec Docker

1. **Construis l’image :**
   ```bash
   docker build -t onboard-app .
   ```

2. **Lance le conteneur :**
   ```bash
   docker run -p 5000:5000 onboard-app
   ```

## Utilisation en production avec Gunicorn

Pour lancer l’application en production avec Gunicorn :

1. **Installe Gunicorn (si ce n’est pas déjà fait) :**
   ```bash
   pip install gunicorn
   ```

2. **Lance l’application avec Gunicorn :**
   ```bash
   gunicorn -b 0.0.0.0:5000 app:app
   ```

## Déploiement avec Docker Compose

1. **Crée un fichier `docker-compose.yml` à la racine du projet :**
   ```yaml
   version: '3.8'

   services:
     web:
       image: vomfive/onboard-app:latest
       ports:
         - "5000:5000"
       volumes:
         - ./uploads_pdf:/app/uploads_pdf
         - ./static:/app/static
         - ./templates:/app/templates
       environment:
         - FLASK_ENV=production
       restart: unless-stopped
   ```

2. **Lance l’application avec Docker Compose :**
   ```bash
   docker-compose up -d
   ```
   L’application sera accessible sur [http://localhost:5000](http://localhost:5000).

## Conseils de sécurité

- Change la clé secrète et le mot de passe admin par défaut avant la mise en production.
- Utilise un serveur WSGI comme Gunicorn pour la production.
- Mets à jour le fichier `.gitignore` pour ne pas versionner les fichiers sensibles.

## Auteur

Projet réalisé par vagvom.

---

**Licence** : CC BY-NC 4.0  
Vous pouvez utiliser, modifier et partager ce projet, mais **pas pour un usage commercial sans l’accord de l’auteur**.