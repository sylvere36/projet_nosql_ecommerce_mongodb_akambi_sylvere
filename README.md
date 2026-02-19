# 🛒 Projet NoSQL — Migration E-Commerce vers MongoDB

**Projet NoSQL — Base de données E-Commerce**  
**Auteur** : Olouwashègun Sylvère AKAMBI  
**INE** : ET5337424
**SGBD choisi** : MongoDB 7.0 (famille Document)

> Migration d'une base relationnelle e-commerce (6 tables) vers MongoDB avec dénormalisation, script Python et 10 requêtes optimisées.

---

## 📋 Table des matières

- [Prérequis](#-prérequis)
- [Installation rapide](#-installation-rapide)
- [Structure du projet](#-structure-du-projet)
- [Modèle de données](#-modèle-de-données)
- [Utilisation](#-utilisation)
- [Les 10 requêtes](#-les-10-requêtes)
- [Rapport technique](#-rapport-technique)

---

## 🔧 Prérequis

| Outil | Version | Installation |
|-------|---------|-------------|
| **Docker** + Docker Compose | ≥ 24.0 | [docker.com](https://docs.docker.com/get-docker/) |
| **Python** | ≥ 3.10 | [python.org](https://www.python.org/downloads/) |
| **pip** | ≥ 22.0 | Inclus avec Python |

---

## 🚀 Installation rapide

### 1. Cloner le projet

```bash
git clone https://github.com/sylvere36/projet_nosql_ecommerce_mongodb_akambi_sylvere.git projet_nosql_akambi_sylvere
cd projet_nosql_akambi_sylvere
```

### 2. Démarrer MongoDB avec Docker

```bash
docker-compose up -d
```

Cela démarre :
- **MongoDB 7.0** sur le port `27017` (user: `admin`, password: `admin123`)
- **Mongo Express** (interface web) sur [http://localhost:8081](http://localhost:8081)

### 3. Créer l'environnement Python

```bash
python3 -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows
pip install -r requirements.txt
```

### 4. Lancer la migration

```bash
python migration.py
```

Sortie attendue :
```
✅ Connexion réussie à la base 'ecommerce'
📂 Lecture de data/departments.json ... → 7 enregistrements
📂 Lecture de data/categories.json ...  → 18 enregistrements
📂 Lecture de data/products.json ...    → 40 enregistrements
📂 Lecture de data/customers.json ...   → 15 enregistrements
📂 Lecture de data/orders.json ...      → 32 enregistrements
📂 Lecture de data/order_items.json ... → 69 enregistrements
📦 40 produits migrés
👥 15 clients migrés
🛒 32 commandes migrées
🔑 13 index créés
✅ Migration terminée avec succès !
```

### 5. Exécuter les requêtes

```bash
python queries.py
```

> 📸 **Captures automatiques** : Les deux scripts génèrent automatiquement des images PNG dans le dossier `outputs/` — style terminal sombre, prêtes à intégrer dans un rapport.

---

## 📸 Sorties visuelles

Chaque exécution produit des captures au format **image PNG** (style terminal) :

| Image | Contenu |
|-------|--------|
| `outputs/migration.png` | Rapport complet de la migration |
| `outputs/R01.png` à `outputs/R10.png` | Résultat de chaque requête |

Ces images sont générées par le module `capture.py` qui utilise **matplotlib** pour rendre le texte console en image avec un thème sombre.

---

## 📁 Structure du projet

```
NoSql/
├── README.md                  # Ce fichier
├── rapport.md                 # Rapport technique complet
├── docker-compose.yml         # Configuration MongoDB + Mongo Express
├── requirements.txt           # Dépendances Python
├── schemas.json               # Schéma relationnel source
├── migration.py               # Script de migration (Python → MongoDB)
├── queries.py                 # 10 requêtes MongoDB implémentées
├── capture.py                 # Utilitaire de capture console → image PNG
├── .gitignore                 # Fichiers à ignorer par Git
├── data/                      # Données sources (JSON)
│   ├── departments.json       # 7 départements
│   ├── categories.json        # 18 catégories
│   ├── products.json          # 40 produits
│   ├── customers.json         # 15 clients
│   ├── orders.json            # 32 commandes
│   └── order_items.json       # 69 items de commande
└── outputs/                   # 📸 Captures d'écran générées automatiquement
    ├── migration.png          # Résultat de la migration
    ├── R01.png                # R1 — Produits par catégorie
    ├── R02.png                # R2 — Commandes d'un client
    ├── R03.png                # R3 — CA par département
    ├── R04.png                # R4 — Top 10 produits
    ├── R05.png                # R5 — Clients par ville/état
    ├── R06.png                # R6 — Historique commande
    ├── R07.png                # R7 — Panier moyen
    ├── R08.png                # R8 — Catégories + nb produits
    ├── R09.png                # R9 — Commandes PENDING > 7j
    └── R10.png                # R10 — Recommandations co-achats
```

---

## 🗃️ Modèle de données

### Transformation : 6 tables SQL → 3 collections MongoDB

```
SQL (Relationnel)                    MongoDB (Document)
══════════════════                   ══════════════════
departments ─┐
categories  ─┼──→ 📦 products      (catégorie + département embarqués)
products    ─┘

customers   ────→ 👥 customers     (adresse comme sous-document)

orders      ─┐
order_items ─┼──→ 🛒 orders        (items + infos client/produit embarqués)
(+ refs)    ─┘
```

### Stratégies de dénormalisation

| Pattern | Appliqué à | Avantage |
|---------|-----------|----------|
| Embedded Document | Adresse → Customer | 0 JOIN pour l'adresse |
| Embedded Array | Items → Order | 0 JOIN pour les détails commande |
| Extended Reference | Client → Order | Nom/email sans lookup |
| Extended Reference | Produit → Order Items | Snapshot prix historique |
| Pre-computed | Total → Order | Pas de recalcul en lecture |

---

## 💻 Utilisation

### Migration seule

```bash
python migration.py
```

### Requêtes seules

```bash
python queries.py
```

### Variables d'environnement (optionnel)

```bash
export MONGO_URI="mongodb://admin:admin123@localhost:27017/"
export MONGO_DB="ecommerce"
```

### Interface web Mongo Express

Ouvrir [http://localhost:8081](http://localhost:8081) pour explorer la base visuellement.

### Arrêter MongoDB

```bash
docker-compose down           # Arrêter (données conservées)
docker-compose down -v        # Arrêter + supprimer les données
```

---

## 📊 Les 10 requêtes

| N° | Description | Complexité | Type MongoDB |
|----|------------|------------|-------------|
| R1 | Produits par catégorie | Simple | `find()` |
| R2 | Commandes d'un client + items | Moyenne | `find()` + `sort()` |
| R3 | CA par département | Moyenne | `aggregate()` |
| R4 | Top 10 produits vendus | Moyenne | `aggregate()` |
| R5 | Clients par ville/état | Simple | `find()` + `$or` |
| R6 | Historique complet commande | Moyenne | `findOne()` |
| R7 | Panier moyen par client | Complexe | `aggregate()` |
| R8 | Catégories + nb produits | Simple | `aggregate()` |
| R9 | Commandes PENDING > 7 jours | Moyenne | `find()` + index composé |
| R10 | Recommandations co-achats | Complexe | `aggregate()` (8 étapes) |

Chaque requête est documentée dans [queries.py](queries.py) avec :
- Description fonctionnelle
- Requête MongoDB native
- Index exploité
- Exemple de résultat

---

## 📄 Rapport technique

Le rapport complet est disponible dans [rapport.md](rapport.md) et couvre :

1. **Justification du choix** MongoDB vs Redis/Cassandra/Neo4j
2. **Modèle de données** avec schémas détaillés
3. **Stratégies de dénormalisation** et patterns MongoDB
4. **13 index** documentés avec leur justification
5. **Analyse de performance** SQL vs MongoDB
6. **Limites et perspectives** de scalabilité

---

## 🛠️ Technologies

- **SGBD** : MongoDB 7.0 (famille Document)
- **Langage** : Python 3.10+
- **Driver** : PyMongo 4.x
- **Visualisation** : Matplotlib (captures console → PNG)
- **Conteneurisation** : Docker + Docker Compose
- **Interface** : Mongo Express

---

**Bon courage pour la correction ! 🎓**
