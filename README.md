<div align="center">
  <img src="./static/logos/default-logo.png" width="120" alt="OnBoard Logo" />
</div>

# OnBoard

**OnBoard** est une application web de gestion des visiteurs pour entreprises, simple à installer et à personnaliser.

[![Docker Pulls](https://img.shields.io/docker/pulls/vomfive/onboard-app)](https://hub.docker.com/r/vomfive/onboard-app)
[![Licence](https://img.shields.io/badge/Licence-CC%20BY--NC%204.0-blue)](https://creativecommons.org/licenses/by-nc/4.0/)

---

## 🚀 Démo rapide

```bash
docker run -d -p 5000:5000 --name onboard-app vomfive/onboard-app:latest
```

Accédez à [http://localhost:5000](http://localhost:5000)

---

## ✨ Fonctionnalités

- Enregistrement et désinscription des visiteurs
- Signature électronique et validation de consignes PDF
- Gestion des personnes à visiter
- Notifications par email (SMTP configurable)
- Export CSV des visiteurs
- Personnalisation des couleurs et du logo
- Authentification administrateur
- Interface responsive

---

## 🐳 Déploiement avec Docker Compose

Créez un fichier `docker-compose.yml` :

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
    environment:
      - FLASK_ENV=production
    restart: unless-stopped
```

Lancez :

```bash
docker-compose up -d
```

---

## ⚡ Installation manuelle (développeur)

```bash
git clone https://github.com/vomfive/beta-OnBoard
cd beta-OnBoard
pip install -r requirements.txt
python app.py
```

---

## 🔑 Connexion administrateur

- Accédez à `/login`
- Mot de passe par défaut : **admin**

---

## 📁 Structure du projet

```
onboard-app/
├── app.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── static/
│   ├── style.css
│   └── logos/
│       └── default-logo.png
├── templates/
│   ├── index.html
│   ├── login.html
│   ├── configuration.html
│   └── visitors.html
└── uploads_pdf/
```

---

## 🛡️ Licence

**CC BY-NC 4.0**  
Vous pouvez utiliser, modifier et partager ce projet, mais **pas pour un usage commercial sans l’accord de l’auteur**.  
[Voir la licence complète](https://creativecommons.org/licenses/by-nc/4.0/)

---