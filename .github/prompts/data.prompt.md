---
agent: agent
---
# Sujet Projet NoSQL

## 1. Contexte du Projet

Vous êtes chargé(e) de migrer une base de données relationnelle e-commerce vers une solution NoSQL. Le schéma source contient 6 tables : departments, categories, products, customers, orders, order_items. Votre mission est de choisir la famille NoSQL la plus adaptée, de concevoir le modèle de données cible, et d'implémenter la migration ainsi qu'un ensemble de requêtes.

## 2. Objectifs Pédagogiques

- Comprendre les différentes familles de bases NoSQL et leurs cas d'usage
- Maîtriser la modélisation de données selon le paradigme NoSQL choisi
- Implémenter un script de migration en Python
- Écrire des requêtes optimisées pour le SGBD choisi

## 3. Travail Demandé

### 3.1 Choix de la Famille NoSQL et du SGBD

Choisissez UNE famille NoSQL parmi les quatre proposées et UN SGBD de cette famille :

| Famille   | SGBD Possibles                | Cas d'usage pour ce schéma                                      |
|-----------|-------------------------------|-----------------------------------------------------------------|
| Document  | MongoDB, CouchDB              | Commandes avec items imbriqués, catalogue produits flexible     |
| Clé-Valeur| Redis, DynamoDB               | Cache sessions/panier, lookups rapides par ID                   |
| Colonnes  | Cassandra, ScyllaDB           | Historique massif de commandes, analytics temps réel            |
| Graphe    | Neo4j, ArangoDB               | Recommandations produits, navigation catégories                 |

### 3.2 Modélisation des Données

Vous devez concevoir et documenter votre modèle de données NoSQL :

1. Justifier le choix de la famille NoSQL pour ce cas d'usage
2. Présenter le schéma/structure cible (collections, tables, nœuds...)
3. Expliquer les stratégies de dénormalisation ou d'imbrication
4. Décrire les index nécessaires pour optimiser les requêtes

### 3.3 Script de Migration Python

Développez un script Python qui :

1. Lit les données sources (fichiers JSON/CSV fournis ou connexion SQL)
2. Transforme les données selon le modèle cible
3. Insère les données dans le SGBD NoSQL choisi
4. Gère les erreurs et affiche des statistiques de migration

### 3.4 Requêtes à Implémenter

Implémentez les 10 requêtes suivantes dans le langage natif de votre SGBD :

| N°  | Description de la Requête                                      | Complexité |
|-----|----------------------------------------------------------------|------------|
| R1  | Récupérer tous les produits d'une catégorie donnée             | Simple     |
| R2  | Lister les commandes d'un client avec le détail des items      | Moyenne    |
| R3  | Calculer le chiffre d'affaires par département                 | Moyenne    |
| R4  | Trouver les 10 produits les plus vendus                        | Moyenne    |
| R5  | Rechercher les clients par ville ou état                       | Simple     |
| R6  | Obtenir l'historique complet d'une commande (avec produits)    | Moyenne    |
| R7  | Calculer le panier moyen par client                            | Complexe   |
| R8  | Lister les catégories avec leur nombre de produits             | Simple     |
| R9  | Trouver les commandes en attente depuis plus de 7 jours        | Moyenne    |
| R10 | Recommander des produits basés sur les achats similaires       | Complexe   |

## 4. Livrables Attendus

1. Rapport technique (PDF) : justification des choix, modèle de données, analyse de performance
2. Code source Python : script de migration complet et commenté
3. Fichier de requêtes : les 10 requêtes avec exemples de résultats
4. Instructions d'installation : README avec prérequis et étapes de déploiement

## 5. Critères d'Évaluation

| Critère                                      | Points | %    |
|----------------------------------------------|--------|------|
| Pertinence du choix NoSQL et justification   | 4      | 20%  |
| Qualité du modèle de données                 | 4      | 20%  |
| Fonctionnement du script de migration        | 5      | 25%  |
| Exactitude et optimisation des requêtes      | 5      | 25%  |
| Qualité du code et documentation             | 2      | 10%  |
| TOTAL                                        | 20     | 100% |

## 6. Schéma Source (Relationnel)

Le fichier schemas.json fourni contient la structure des 6 tables :

- **departments** (department_id, department_name)
- **categories** (category_id, category_department_id → departments, category_name)
- **products** (product_id, product_category_id → categories, product_name, description, price, image)
- **customers** (customer_id, fname, lname, email, password, street, city, state, zipcode)
- **orders** (order_id, order_date, order_customer_id → customers, order_status)
- **order_items** (order_item_id, order_id → orders, product_id → products, quantity, subtotal, product_price)

## 7. Ressources et Bibliothèques Python

| SGBD     | Bibliothèque Python   | Installation                 |
|----------|-----------------------|------------------------------|
| MongoDB  | pymongo               | pip install pymongo          |
| Redis    | redis-py              | pip install redis            |
| Cassandra| cassandra-driver      | pip install cassandra-driver |
| Neo4j    | neo4j                 | pip install neo4j            |
| CouchDB  | couchdb               | pip install couchdb          |
| ArangoDB | python-arango         | pip install python-arango    |

## 8. Conseils de Réalisation

- Commencez par installer le SGBD localement (Docker recommandé)
- Générez des données de test réalistes avant la migration finale
- Mesurez les performances des requêtes et documentez les optimisations
- Utilisez des environnements virtuels Python (venv)
- Versionnez votre code avec Git

**Bon courage !**