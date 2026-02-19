"""
=============================================================================
 Script de Migration : Bases de données NoSQL → MongoDB
=============================================================================
 Auteur  : Olouwashègun Sylvère Akambi
 INE    : Février 2026
 Projet  : Migration NoSQL - Base de données e-commerce
 SGBD    : MongoDB (famille Document)
 
 Description :
   Ce script migre les données d'un schéma relationnel (6 tables) vers
   un modèle documentaire MongoDB optimisé avec dénormalisation.
   
 Modèle cible (3 collections) :
   - products   : produits avec catégorie et département embarqués
   - customers  : clients avec adresse embarquée
   - orders     : commandes avec items et infos produits/client embarqués
=============================================================================
"""

import json
import os
import sys
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from pymongo import MongoClient, errors
from pymongo.collection import Collection
from pymongo.database import Database

from capture import OutputCapture, save_output_as_image

# ═══════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════

# Connexion MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:admin123@localhost:27017/")
DATABASE_NAME = os.getenv("MONGO_DB", "ecommerce")

# Répertoire des données sources
DATA_DIR = Path(__file__).parent / "data"

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Classe principale de migration
# ═══════════════════════════════════════════════════════════════════════════

class EcommerceMigration:
    """
    Gère la migration complète des données relationnelles e-commerce
    vers MongoDB avec dénormalisation et embedding.
    
    Stratégie de modélisation :
    ─────────────────────────
    1. Collection 'products' :
       - Embarque la catégorie et le département directement
       - Évite les jointures pour le catalogue produits
       
    2. Collection 'customers' :
       - Embarque l'adresse comme sous-document
       - Structure plate pour les infos personnelles
       
    3. Collection 'orders' :
       - Embarque les order_items comme tableau de sous-documents
       - Chaque item embarque les infos produit (nom, prix)
       - Embarque les infos client (nom, email) pour accès rapide
       - Pattern "Extended Reference" pour éviter les lookups
    """

    def __init__(self, mongo_uri: str, db_name: str, data_dir: Path):
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        self.data_dir = data_dir
        self.client: MongoClient | None = None
        self.db: Database | None = None
        self.stats: dict[str, Any] = {
            "start_time": None,
            "end_time": None,
            "tables_read": {},
            "collections_created": {},
            "errors": [],
        }

    # ───────────────────────────────────────────────────────────────────
    # Connexion
    # ───────────────────────────────────────────────────────────────────

    def connect(self) -> None:
        """Établit la connexion à MongoDB et vérifie la disponibilité."""
        logger.info("Connexion à MongoDB : %s", self.mongo_uri)
        try:
            self.client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
            # Vérifie que le serveur est accessible
            self.client.admin.command("ping")
            self.db = self.client[self.db_name]
            logger.info("✅ Connexion réussie à la base '%s'", self.db_name)
        except errors.ServerSelectionTimeoutError as e:
            logger.error("❌ Impossible de se connecter à MongoDB : %s", e)
            raise SystemExit(
                "Assurez-vous que MongoDB est démarré (docker-compose up -d)"
            ) from e

    def disconnect(self) -> None:
        """Ferme proprement la connexion."""
        if self.client:
            self.client.close()
            logger.info("Connexion MongoDB fermée.")

    # ───────────────────────────────────────────────────────────────────
    # Lecture des données sources (JSON)
    # ───────────────────────────────────────────────────────────────────

    def load_json(self, filename: str) -> list[dict]:
        """
        Charge un fichier JSON depuis le répertoire data/.
        
        Args:
            filename: Nom du fichier JSON (ex: 'products.json')
            
        Returns:
            Liste de dictionnaires représentant les enregistrements.
            
        Raises:
            FileNotFoundError: Si le fichier n'existe pas.
            json.JSONDecodeError: Si le JSON est invalide.
        """
        filepath = self.data_dir / filename
        logger.info("📂 Lecture de %s ...", filepath)

        if not filepath.exists():
            error_msg = f"Fichier introuvable : {filepath}"
            self.stats["errors"].append(error_msg)
            raise FileNotFoundError(error_msg)

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            self.stats["tables_read"][filename] = len(data)
            logger.info("   → %d enregistrements chargés", len(data))
            return data

        except json.JSONDecodeError as e:
            error_msg = f"Erreur JSON dans {filepath} : {e}"
            self.stats["errors"].append(error_msg)
            raise

    # ───────────────────────────────────────────────────────────────────
    # Nettoyage de la base cible
    # ───────────────────────────────────────────────────────────────────

    def clean_database(self) -> None:
        """Supprime les collections existantes pour une migration propre."""
        logger.info("🧹 Nettoyage de la base '%s' ...", self.db_name)
        collections = ["products", "customers", "orders"]
        for col_name in collections:
            self.db[col_name].drop()
            logger.info("   → Collection '%s' supprimée", col_name)

    # ───────────────────────────────────────────────────────────────────
    # Migration : Collection 'products'
    # ───────────────────────────────────────────────────────────────────

    def migrate_products(
        self,
        departments: list[dict],
        categories: list[dict],
        products: list[dict],
    ) -> None:
        """
        Migre les produits avec dénormalisation catégorie + département.
        
        Modèle cible :
        {
            "_id": <product_id>,
            "name": "Tecno Camon 20 Pro",
            "description": "...",
            "price": 299.99,
            "image": "tecnocamon20.jpg",
            "category": {
                "id": 1,
                "name": "Smartphones"
            },
            "department": {
                "id": 1,
                "name": "Électronique"
            }
        }
        """
        logger.info("📦 Migration des produits (avec dénormalisation) ...")

        # Créer des dictionnaires de lookup pour la dénormalisation
        dept_lookup = {d["department_id"]: d for d in departments}
        cat_lookup = {c["category_id"]: c for c in categories}

        documents = []
        for p in products:
            cat_id = p["product_category_id"]
            category = cat_lookup.get(cat_id, {})
            dept_id = category.get("category_department_id")
            department = dept_lookup.get(dept_id, {})

            doc = {
                "_id": p["product_id"],
                "name": p["product_name"],
                "description": p.get("product_description", ""),
                "price": p["product_price"],
                "image": p.get("product_image", ""),
                "category": {
                    "id": cat_id,
                    "name": category.get("category_name", "Inconnue"),
                },
                "department": {
                    "id": dept_id,
                    "name": department.get("department_name", "Inconnu"),
                },
            }
            documents.append(doc)

        result = self.db.products.insert_many(documents)
        count = len(result.inserted_ids)
        self.stats["collections_created"]["products"] = count
        logger.info("   ✅ %d produits migrés", count)

    # ───────────────────────────────────────────────────────────────────
    # Migration : Collection 'customers'
    # ───────────────────────────────────────────────────────────────────

    def migrate_customers(self, customers: list[dict]) -> None:
        """
        Migre les clients avec adresse embarquée comme sous-document.
        
        Modèle cible :
        {
            "_id": <customer_id>,
            "first_name": "Awa",
            "last_name": "Diallo",
            "email": "awa.diallo@email.sn",
            "password": "hashed_pwd_001",
            "address": {
                "street": "23 Avenue Cheikh Anta Diop",
                "city": "Dakar",
                "state": "Sénégal",
                "zipcode": 10200
            }
        }
        """
        logger.info("👥 Migration des clients ...")

        documents = []
        for c in customers:
            doc = {
                "_id": c["customer_id"],
                "first_name": c["customer_fname"],
                "last_name": c["customer_lname"],
                "email": c["customer_email"],
                "password": c["customer_password"],
                "address": {
                    "street": c["customer_street"],
                    "city": c["customer_city"],
                    "state": c["customer_state"],
                    "zipcode": c["customer_zipcode"],
                },
            }
            documents.append(doc)

        result = self.db.customers.insert_many(documents)
        count = len(result.inserted_ids)
        self.stats["collections_created"]["customers"] = count
        logger.info("   ✅ %d clients migrés", count)

    # ───────────────────────────────────────────────────────────────────
    # Migration : Collection 'orders'
    # ───────────────────────────────────────────────────────────────────

    def migrate_orders(
        self,
        orders: list[dict],
        order_items: list[dict],
        products: list[dict],
        customers: list[dict],
    ) -> None:
        """
        Migre les commandes avec embedding des items, infos produit et client.
        
        Pattern "Extended Reference" :
          On embarque les infos essentielles du client et des produits
          directement dans la commande pour éviter les $lookup coûteux.
        
        Modèle cible :
        {
            "_id": <order_id>,
            "date": ISODate("2025-12-01T10:30:00"),
            "status": "COMPLETE",
            "customer": {
                "id": 1,
                "first_name": "Awa",
                "last_name": "Diallo",
                "email": "awa.diallo@email.sn"
            },
            "items": [
                {
                    "item_id": 1,
                    "product": {
                        "id": 1,
                        "name": "Tecno Camon 20 Pro",
                        "price": 299.99
                    },
                    "quantity": 1,
                    "subtotal": 299.99,
                    "unit_price": 299.99
                }
            ],
            "total": 1579.97
        }
        """
        logger.info("🛒 Migration des commandes (avec embedding items) ...")

        # Lookups
        product_lookup = {p["product_id"]: p for p in products}
        customer_lookup = {c["customer_id"]: c for c in customers}

        # Grouper les items par order_id
        items_by_order: dict[int, list[dict]] = {}
        for item in order_items:
            oid = item["order_item_order_id"]
            items_by_order.setdefault(oid, []).append(item)

        documents = []
        for o in orders:
            order_id = o["order_id"]
            customer_id = o["order_customer_id"]
            customer = customer_lookup.get(customer_id, {})

            # Transformer les items de cette commande
            embedded_items = []
            order_total = 0.0

            for item in items_by_order.get(order_id, []):
                product_id = item["order_item_product_id"]
                product = product_lookup.get(product_id, {})

                embedded_item = {
                    "item_id": item["order_item_id"],
                    "product": {
                        "id": product_id,
                        "name": product.get("product_name", "Produit inconnu"),
                        "price": product.get("product_price", 0.0),
                    },
                    "quantity": item["order_item_quantity"],
                    "subtotal": item["order_item_subtotal"],
                    "unit_price": item["order_item_product_price"],
                }
                embedded_items.append(embedded_item)
                order_total += item["order_item_subtotal"]

            doc = {
                "_id": order_id,
                "date": datetime.fromisoformat(o["order_date"]),
                "status": o["order_status"],
                "customer": {
                    "id": customer_id,
                    "first_name": customer.get("customer_fname", ""),
                    "last_name": customer.get("customer_lname", ""),
                    "email": customer.get("customer_email", ""),
                },
                "items": embedded_items,
                "total": round(order_total, 2),
            }
            documents.append(doc)

        result = self.db.orders.insert_many(documents)
        count = len(result.inserted_ids)
        self.stats["collections_created"]["orders"] = count
        logger.info("   ✅ %d commandes migrées", count)

    # ───────────────────────────────────────────────────────────────────
    # Création des index
    # ───────────────────────────────────────────────────────────────────

    def create_indexes(self) -> None:
        """
        Crée les index nécessaires pour optimiser les 10 requêtes du projet.
        
        Index créés :
        ─────────────
        products:
          - category.id         → R1 (produits par catégorie)
          - category.name       → R1 (recherche par nom de catégorie)
          - department.id       → R3 (CA par département)
          - name (text)         → Recherche textuelle
          
        customers:
          - address.city        → R5 (recherche par ville)
          - address.state       → R5 (recherche par état)
          - email (unique)      → Lookup par email
          
        orders:
          - customer.id         → R2, R7 (commandes d'un client)
          - status              → R9 (commandes en attente)
          - date                → R9 (filtrage temporel)
          - items.product.id    → R4, R10 (produits vendus)
          - status + date       → R9 (index composé)
        """
        logger.info("🔑 Création des index ...")

        # Index sur products
        self.db.products.create_index("category.id", name="idx_category_id")
        self.db.products.create_index("category.name", name="idx_category_name")
        self.db.products.create_index("department.id", name="idx_department_id")
        self.db.products.create_index("department.name", name="idx_department_name")
        self.db.products.create_index(
            [("name", "text"), ("description", "text")],
            name="idx_product_text_search",
            default_language="french",
        )
        logger.info("   → 5 index créés sur 'products'")

        # Index sur customers
        self.db.customers.create_index("address.city", name="idx_customer_city")
        self.db.customers.create_index("address.state", name="idx_customer_state")
        self.db.customers.create_index(
            "email", name="idx_customer_email", unique=True
        )
        logger.info("   → 3 index créés sur 'customers'")

        # Index sur orders
        self.db.orders.create_index("customer.id", name="idx_order_customer_id")
        self.db.orders.create_index("status", name="idx_order_status")
        self.db.orders.create_index("date", name="idx_order_date")
        self.db.orders.create_index("items.product.id", name="idx_order_product_id")
        self.db.orders.create_index(
            [("status", 1), ("date", 1)],
            name="idx_order_status_date",
        )
        logger.info("   → 5 index créés sur 'orders'")
        logger.info("   ✅ Total : 13 index créés")

    # ───────────────────────────────────────────────────────────────────
    # Statistiques de migration
    # ───────────────────────────────────────────────────────────────────

    def print_stats(self) -> None:
        """Affiche un récapitulatif détaillé de la migration."""
        duration = self.stats["end_time"] - self.stats["start_time"]

        print("\n" + "=" * 65)
        print("           RAPPORT DE MIGRATION E-COMMERCE → MongoDB")
        print("=" * 65)
        print(f"  Début    : {self.stats['start_time']:.4f}s")
        print(f"  Fin      : {self.stats['end_time']:.4f}s")
        print(f"  Durée    : {duration:.4f} secondes")
        print("-" * 65)

        print("\n  📂 DONNÉES SOURCES (fichiers JSON lus) :")
        total_source = 0
        for filename, count in self.stats["tables_read"].items():
            print(f"     {filename:<25} : {count:>5} enregistrements")
            total_source += count
        print(f"     {'TOTAL':<25} : {total_source:>5} enregistrements")

        print("\n  📦 COLLECTIONS MONGODB CRÉÉES :")
        total_target = 0
        for col_name, count in self.stats["collections_created"].items():
            print(f"     {col_name:<25} : {count:>5} documents")
            total_target += count
        print(f"     {'TOTAL':<25} : {total_target:>5} documents")

        if self.stats["errors"]:
            print(f"\n  ⚠️  ERREURS ({len(self.stats['errors'])}) :")
            for err in self.stats["errors"]:
                print(f"     - {err}")
        else:
            print("\n  ✅ AUCUNE ERREUR")

        print("\n" + "=" * 65)
        print("  Migration terminée avec succès !")
        print("=" * 65 + "\n")

    # ───────────────────────────────────────────────────────────────────
    # Exécution principale
    # ───────────────────────────────────────────────────────────────────

    def run(self) -> None:
        """
        Point d'entrée principal : exécute la migration complète.
        
        Étapes :
        1. Connexion à MongoDB
        2. Lecture des 6 fichiers JSON sources
        3. Nettoyage de la base cible
        4. Migration des 3 collections (avec dénormalisation)
        5. Création des index
        6. Affichage des statistiques
        """
        self.stats["start_time"] = time.time()
        
        try:
            # 1. Connexion
            self.connect()

            # 2. Chargement des données sources
            logger.info("=" * 50)
            logger.info("ÉTAPE 1 : Chargement des données sources")
            logger.info("=" * 50)
            departments = self.load_json("departments.json")
            categories = self.load_json("categories.json")
            products = self.load_json("products.json")
            customers = self.load_json("customers.json")
            orders = self.load_json("orders.json")
            order_items = self.load_json("order_items.json")

            # 3. Nettoyage
            logger.info("=" * 50)
            logger.info("ÉTAPE 2 : Nettoyage de la base cible")
            logger.info("=" * 50)
            self.clean_database()

            # 4. Migration des collections
            logger.info("=" * 50)
            logger.info("ÉTAPE 3 : Migration et dénormalisation")
            logger.info("=" * 50)
            self.migrate_products(departments, categories, products)
            self.migrate_customers(customers)
            self.migrate_orders(orders, order_items, products, customers)

            # 5. Création des index
            logger.info("=" * 50)
            logger.info("ÉTAPE 4 : Création des index")
            logger.info("=" * 50)
            self.create_indexes()

        except Exception as e:
            self.stats["errors"].append(f"Erreur fatale : {e}")
            logger.error("❌ Erreur fatale : %s", e)
            raise

        finally:
            self.stats["end_time"] = time.time()
            self.print_stats()
            self.disconnect()


# ═══════════════════════════════════════════════════════════════════════════
# Point d'entrée
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    migration = EcommerceMigration(
        mongo_uri=MONGO_URI,
        db_name=DATABASE_NAME,
        data_dir=DATA_DIR,
    )

    # Capturer la sortie et générer une image PNG
    cap = OutputCapture()
    cap.start()
    migration.run()
    output_text = cap.stop()
    save_output_as_image(
        output_text,
        filename="migration",
        title="Migration E-Commerce → MongoDB",
    )
