# OnBoard - Gestion des Visiteurs

Application web Flask pour la gestion des visiteurs en entreprise : enregistrement, suivi, notifications, export CSV, personnalisation de l’interface, etc.

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

## Installation

1. **Clone le dépôt :**
   ```bash
   git clone https://github.com/vagvom/beta-OnBoard
   cd projet01
   ```

2. **Installe les dépendances :**
   ```bash
   pip install -r requirements.txt
   ```

3. **Lance l’application :**
   ```bash
   python app.py
   ```
   L’application sera accessible sur [http://localhost:5000](http://localhost:5000)

## Utilisation

- Accède à `/login` pour te connecter en tant qu’administrateur (mot de passe par défaut : `admin`).
- Configure le SMTP, les couleurs, le logo, etc. dans la page de configuration.
- Les visiteurs peuvent s’enregistrer via la page d’accueil.

## Utilisation en production avec Gunicorn

Pour lancer l’application en production avec Gunicorn :

1. **Installe Gunicorn** (si ce n’est pas déjà fait) :
   ```bash
   pip install gunicorn
   ```

2. **Lance l’application avec Gunicorn** :
   ```bash
   gunicorn -b 0.0.0.0:5000 app:app
   ```
   - Le premier `app` correspond au nom de ton fichier Python (`app.py` sans l’extension).
   - Le second `app` correspond à la variable Flask (`app = Flask(__name__)`).

3. **Avec Docker**  
   Si tu utilises Docker, ajoute dans ton `Dockerfile` :
   ```
   CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
   ```

**Astuce** : Pour de meilleures performances, tu peux ajouter l’option `-w 4` pour utiliser 4 workers (processus) :
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

---

**N’oublie pas** :  
- En production, désactive le mode debug (`debug=False`).
- Utilise un proxy (Nginx, Apache) devant Gunicorn pour la sécurité et le HTTPS (optionnel mais recommandé).

## Déploiement avec Docker

1. **Construis l’image :**
   ```bash
   docker build -t onboard-app .
   ```
2. **Lance le conteneur :**
   ```bash
   docker run -p 5000:5000 onboard-app
   ```
   
## Structure du projet

```
beta-OnBoard/
│
├── app.py
├── requirements.txt
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

## Conseils de sécurité

- Change la clé secrète et le mot de passe admin par défaut avant la mise en production.
- Utilise un serveur WSGI comme Gunicorn pour la production.
- Mets à jour le fichier `.gitignore` pour ne pas versionner les fichiers sensibles.

## Auteur

Projet réalisé par vagvom.

---

**Licence** : CC BY-NC 4.0  
Vous pouvez utiliser, modifier et partager ce projet, mais **pas pour un usage commercial sans l’accord de l’auteur**.