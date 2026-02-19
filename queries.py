"""
=============================================================================
 Requêtes MongoDB — Projet Base de données NoSQL
=============================================================================
 Auteur  : Olouwashègun Sylvère Akambi
 Date    : Février 2026
 SGBD    : MongoDB 7.0 (famille Document)
 
 Description :
   Implémentation des 10 requêtes demandées avec le langage natif MongoDB
   (agrégation pipeline, find, etc.). Chaque requête est documentée avec :
   - Description fonctionnelle
   - Complexité
   - Pipeline/filtre utilisé
   - Index exploité
   - Exemple de résultat
=============================================================================
"""

import os
import sys
import json
from datetime import datetime, timedelta
from pymongo import MongoClient

from capture import OutputCapture, save_output_as_image

# ═══════════════════════════════════════════════════════════════════════════
# Connexion
# ═══════════════════════════════════════════════════════════════════════════

MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:admin123@localhost:27017/")
DATABASE_NAME = os.getenv("MONGO_DB", "ecommerce")

client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]


def print_separator(title: str, num: str) -> None:
    """Affiche un séparateur visuel pour chaque requête."""
    print(f"\n{'═' * 70}")
    print(f"  {num} — {title}")
    print(f"{'═' * 70}")


def print_results(results: list, limit: int = 5) -> None:
    """Affiche les résultats de manière formatée."""
    for i, doc in enumerate(results[:limit]):
        # Convertir les ObjectId et datetime pour l'affichage
        clean_doc = json.loads(json.dumps(doc, default=str, ensure_ascii=False))
        print(f"  {json.dumps(clean_doc, indent=4, ensure_ascii=False)}")
    if len(results) > limit:
        print(f"  ... et {len(results) - limit} résultats de plus")
    print(f"\n  → Total : {len(results)} résultat(s)")


# ═══════════════════════════════════════════════════════════════════════════
# R1 — Récupérer tous les produits d'une catégorie donnée
# ═══════════════════════════════════════════════════════════════════════════
# Complexité : Simple
# Index utilisé : idx_category_name
# ═══════════════════════════════════════════════════════════════════════════

def r1_products_by_category(category_name: str = "Smartphones") -> list:
    """
    Récupère tous les produits appartenant à une catégorie donnée.
    
    Requête MongoDB :
        db.products.find({"category.name": <category_name>})
    
    Args:
        category_name: Nom de la catégorie (ex: "Smartphones")
        
    Returns:
        Liste des produits de cette catégorie.
    """
    print_separator("Produits par catégorie", "R1")
    print(f"  Paramètre : category_name = '{category_name}'")
    print(f"  Requête   : db.products.find({{\"category.name\": \"{category_name}\"}})\n")

    results = list(
        db.products.find(
            {"category.name": category_name},
            {"name": 1, "price": 1, "category.name": 1, "department.name": 1},
        )
    )
    print_results(results)
    return results


# ═══════════════════════════════════════════════════════════════════════════
# R2 — Lister les commandes d'un client avec le détail des items
# ═══════════════════════════════════════════════════════════════════════════
# Complexité : Moyenne
# Index utilisé : idx_order_customer_id
# Avantage NoSQL : Pas de jointure, les items sont déjà embarqués !
# ═══════════════════════════════════════════════════════════════════════════

def r2_orders_by_customer(customer_id: int = 1) -> list:
    """
    Liste toutes les commandes d'un client avec le détail des items.
    
    Grâce à l'embedding, aucun $lookup n'est nécessaire : les items,
    les infos produit et le total sont déjà dans chaque document.
    
    Requête MongoDB :
        db.orders.find({"customer.id": <customer_id>})
    """
    print_separator("Commandes d'un client avec détail items", "R2")
    print(f"  Paramètre : customer_id = {customer_id}")
    print(f"  Requête   : db.orders.find({{\"customer.id\": {customer_id}}})\n")

    results = list(
        db.orders.find(
            {"customer.id": customer_id},
            {"date": 1, "status": 1, "customer": 1, "items": 1, "total": 1},
        ).sort("date", -1)
    )
    print_results(results)
    return results


# ═══════════════════════════════════════════════════════════════════════════
# R3 — Calculer le chiffre d'affaires par département
# ═══════════════════════════════════════════════════════════════════════════
# Complexité : Moyenne
# Pipeline d'agrégation : $unwind → $lookup → $group
# Index utilisé : idx_order_product_id, idx_department_id
# ═══════════════════════════════════════════════════════════════════════════

def r3_revenue_by_department() -> list:
    """
    Calcule le chiffre d'affaires total par département.
    
    Pipeline d'agrégation :
    1. $unwind : Éclate les items de chaque commande
    2. $lookup : Joint avec products pour obtenir le département
    3. $unwind : Éclate le résultat du lookup
    4. $group  : Agrège par département (somme des subtotals)
    5. $sort   : Trie par CA décroissant
    """
    print_separator("Chiffre d'affaires par département", "R3")

    pipeline = [
        # Éclater les items
        {"$unwind": "$items"},
        # Joindre avec products pour obtenir le département
        {
            "$lookup": {
                "from": "products",
                "localField": "items.product.id",
                "foreignField": "_id",
                "as": "product_info",
            }
        },
        {"$unwind": "$product_info"},
        # Grouper par département
        {
            "$group": {
                "_id": {
                    "department_id": "$product_info.department.id",
                    "department_name": "$product_info.department.name",
                },
                "chiffre_affaires": {"$sum": "$items.subtotal"},
                "nombre_articles_vendus": {"$sum": "$items.quantity"},
                "nombre_commandes": {"$addToSet": "$_id"},
            }
        },
        # Projeter proprement
        {
            "$project": {
                "_id": 0,
                "departement": "$_id.department_name",
                "department_id": "$_id.department_id",
                "chiffre_affaires": {"$round": ["$chiffre_affaires", 2]},
                "nombre_articles_vendus": 1,
                "nombre_commandes": {"$size": "$nombre_commandes"},
            }
        },
        # Trier par CA décroissant
        {"$sort": {"chiffre_affaires": -1}},
    ]

    print("  Pipeline  : $unwind → $lookup → $group → $project → $sort\n")
    results = list(db.orders.aggregate(pipeline))
    print_results(results, limit=10)
    return results


# ═══════════════════════════════════════════════════════════════════════════
# R4 — Trouver les 10 produits les plus vendus
# ═══════════════════════════════════════════════════════════════════════════
# Complexité : Moyenne
# Pipeline d'agrégation : $unwind → $group → $sort → $limit → $lookup
# ═══════════════════════════════════════════════════════════════════════════

def r4_top_10_products() -> list:
    """
    Trouve les 10 produits les plus vendus (par quantité totale).
    
    Pipeline d'agrégation :
    1. $unwind : Éclate les items
    2. $group  : Agrège par product_id (somme quantités + CA)
    3. $sort   : Trie par quantité décroissante
    4. $limit  : Garde les 10 premiers
    5. $lookup : Joint avec products pour le nom complet
    """
    print_separator("Top 10 produits les plus vendus", "R4")

    pipeline = [
        {"$unwind": "$items"},
        {
            "$group": {
                "_id": "$items.product.id",
                "product_name": {"$first": "$items.product.name"},
                "total_quantity": {"$sum": "$items.quantity"},
                "total_revenue": {"$sum": "$items.subtotal"},
                "times_ordered": {"$sum": 1},
            }
        },
        {"$sort": {"total_quantity": -1}},
        {"$limit": 10},
        {
            "$project": {
                "_id": 0,
                "product_id": "$_id",
                "product_name": 1,
                "total_quantity": 1,
                "total_revenue": {"$round": ["$total_revenue", 2]},
                "times_ordered": 1,
            }
        },
    ]

    print("  Pipeline  : $unwind → $group → $sort → $limit → $project\n")
    results = list(db.orders.aggregate(pipeline))
    print_results(results, limit=10)
    return results


# ═══════════════════════════════════════════════════════════════════════════
# R5 — Rechercher les clients par ville ou état
# ═══════════════════════════════════════════════════════════════════════════
# Complexité : Simple
# Index utilisé : idx_customer_city, idx_customer_state
# ═══════════════════════════════════════════════════════════════════════════

def r5_customers_by_location(city: str = None, state: str = None) -> list:
    """
    Recherche les clients par ville et/ou état.
    
    Utilise l'opérateur $or pour permettre la recherche par ville OU état.
    Les index sur address.city et address.state optimisent la requête.
    
    Requête MongoDB :
        db.customers.find({"$or": [
            {"address.city": <city>},
            {"address.state": <state>}
        ]})
    """
    print_separator("Clients par ville ou état", "R5")

    # Construction dynamique du filtre
    conditions = []
    if city:
        conditions.append({"address.city": city})
    if state:
        conditions.append({"address.state": state})

    if not conditions:
        # Valeurs par défaut pour la démonstration
        city = "Dakar"
        state = "Sénégal"
        conditions = [{"address.city": city}, {"address.state": state}]

    query = {"$or": conditions} if len(conditions) > 1 else conditions[0]

    print(f"  Paramètres : city = '{city}', state = '{state}'")
    print(f"  Requête    : db.customers.find({json.dumps(query, ensure_ascii=False)})\n")

    results = list(
        db.customers.find(
            query,
            {"first_name": 1, "last_name": 1, "email": 1, "address": 1},
        )
    )
    print_results(results, limit=10)
    return results


# ═══════════════════════════════════════════════════════════════════════════
# R6 — Obtenir l'historique complet d'une commande (avec produits)
# ═══════════════════════════════════════════════════════════════════════════
# Complexité : Moyenne
# Avantage NoSQL : Tout est déjà dans un seul document !
# ═══════════════════════════════════════════════════════════════════════════

def r6_order_full_details(order_id: int = 1) -> dict | None:
    """
    Récupère l'historique complet d'une commande avec tous les détails.
    
    Grâce à l'embedding, cette requête ne nécessite qu'un simple find
    au lieu de 3 JOINs en SQL (orders + order_items + products).
    
    Requête MongoDB :
        db.orders.findOne({"_id": <order_id>})
    """
    print_separator("Historique complet d'une commande", "R6")
    print(f"  Paramètre : order_id = {order_id}")
    print(f"  Requête   : db.orders.findOne({{\"_id\": {order_id}}})\n")

    result = db.orders.find_one({"_id": order_id})

    if result:
        print_results([result])
    else:
        print("  Aucune commande trouvée.")
    return result


# ═══════════════════════════════════════════════════════════════════════════
# R7 — Calculer le panier moyen par client
# ═══════════════════════════════════════════════════════════════════════════
# Complexité : Complexe
# Pipeline d'agrégation : $group (2 niveaux) → $project
# Index utilisé : idx_order_customer_id
# ═══════════════════════════════════════════════════════════════════════════

def r7_average_basket_per_customer() -> list:
    """
    Calcule le panier moyen (montant moyen par commande) pour chaque client.
    
    Pipeline d'agrégation :
    1. $group : Agrège par client (somme totale, nombre de commandes)
    2. $project : Calcule la moyenne (total / nb_commandes)
    3. $sort : Trie par panier moyen décroissant
    """
    print_separator("Panier moyen par client", "R7")

    pipeline = [
        # Grouper par client
        {
            "$group": {
                "_id": {
                    "customer_id": "$customer.id",
                    "first_name": "$customer.first_name",
                    "last_name": "$customer.last_name",
                    "email": "$customer.email",
                },
                "total_depense": {"$sum": "$total"},
                "nombre_commandes": {"$sum": 1},
                "montant_min": {"$min": "$total"},
                "montant_max": {"$max": "$total"},
            }
        },
        # Calculer le panier moyen
        {
            "$project": {
                "_id": 0,
                "client": {
                    "$concat": ["$_id.first_name", " ", "$_id.last_name"]
                },
                "email": "$_id.email",
                "nombre_commandes": 1,
                "total_depense": {"$round": ["$total_depense", 2]},
                "panier_moyen": {
                    "$round": [
                        {"$divide": ["$total_depense", "$nombre_commandes"]},
                        2,
                    ]
                },
                "commande_min": {"$round": ["$montant_min", 2]},
                "commande_max": {"$round": ["$montant_max", 2]},
            }
        },
        {"$sort": {"panier_moyen": -1}},
    ]

    print("  Pipeline  : $group → $project (calcul moyenne) → $sort\n")
    results = list(db.orders.aggregate(pipeline))
    print_results(results, limit=10)
    return results


# ═══════════════════════════════════════════════════════════════════════════
# R8 — Lister les catégories avec leur nombre de produits
# ═══════════════════════════════════════════════════════════════════════════
# Complexité : Simple
# Pipeline d'agrégation : $group → $sort
# Index utilisé : idx_category_name
# ═══════════════════════════════════════════════════════════════════════════

def r8_categories_product_count() -> list:
    """
    Liste toutes les catégories avec le nombre de produits dans chacune.
    
    Pipeline d'agrégation :
    1. $group : Agrège par catégorie (comptage)
    2. $sort  : Trie par nombre décroissant
    """
    print_separator("Catégories avec nombre de produits", "R8")

    pipeline = [
        {
            "$group": {
                "_id": {
                    "category_id": "$category.id",
                    "category_name": "$category.name",
                    "department": "$department.name",
                },
                "nombre_produits": {"$sum": 1},
                "prix_moyen": {"$avg": "$price"},
                "prix_min": {"$min": "$price"},
                "prix_max": {"$max": "$price"},
            }
        },
        {
            "$project": {
                "_id": 0,
                "categorie": "$_id.category_name",
                "departement": "$_id.department",
                "nombre_produits": 1,
                "prix_moyen": {"$round": ["$prix_moyen", 2]},
                "prix_min": 1,
                "prix_max": 1,
            }
        },
        {"$sort": {"nombre_produits": -1, "categorie": 1}},
    ]

    print("  Pipeline  : $group → $project → $sort\n")
    results = list(db.products.aggregate(pipeline))
    print_results(results, limit=20)
    return results


# ═══════════════════════════════════════════════════════════════════════════
# R9 — Trouver les commandes en attente depuis plus de 7 jours
# ═══════════════════════════════════════════════════════════════════════════
# Complexité : Moyenne
# Index utilisé : idx_order_status_date (index composé)
# ═══════════════════════════════════════════════════════════════════════════

def r9_pending_orders_over_7_days() -> list:
    """
    Trouve les commandes avec statut PENDING datant de plus de 7 jours.
    
    Utilise l'index composé (status, date) pour un scan optimal.
    
    Requête MongoDB :
        db.orders.find({
            "status": "PENDING",
            "date": {"$lt": <date_il_y_a_7_jours>}
        })
    """
    print_separator("Commandes en attente > 7 jours", "R9")

    cutoff_date = datetime.now() - timedelta(days=7)

    query = {
        "status": "PENDING",
        "date": {"$lt": cutoff_date},
    }

    print(f"  Date seuil : {cutoff_date.isoformat()}")
    print(f"  Requête    : db.orders.find({{\"status\": \"PENDING\", \"date\": {{\"$lt\": \"{cutoff_date.isoformat()}\"}}}})\n")

    results = list(
        db.orders.find(query).sort("date", 1)
    )

    # Ajouter le nombre de jours en attente pour l'affichage
    enriched = []
    for order in results:
        order_copy = dict(order)
        days_pending = (datetime.now() - order["date"]).days
        order_copy["jours_en_attente"] = days_pending
        enriched.append(order_copy)

    print_results(enriched, limit=10)
    return enriched


# ═══════════════════════════════════════════════════════════════════════════
# R10 — Recommander des produits basés sur les achats similaires
# ═══════════════════════════════════════════════════════════════════════════
# Complexité : Complexe
# Pattern : "Clients qui ont acheté X ont aussi acheté Y"
# Pipeline : Plusieurs étapes d'agrégation avancées
# ═══════════════════════════════════════════════════════════════════════════

def r10_product_recommendations(product_id: int = 1, limit: int = 5) -> list:
    """
    Recommande des produits basés sur les achats similaires.
    
    Algorithme "Collaborative Filtering" simplifié :
    1. Trouver toutes les commandes contenant le produit donné
    2. Extraire tous les AUTRES produits de ces commandes
    3. Compter la fréquence de co-achat de chaque produit
    4. Retourner les produits les plus fréquemment co-achetés
    
    Logique : "Les clients qui ont acheté le produit X ont aussi acheté Y"
    
    Pipeline :
    1. $match   : Commandes contenant le produit cible
    2. $unwind  : Éclater les items
    3. $match   : Exclure le produit cible lui-même
    4. $group   : Compter les co-achats par produit
    5. $sort    : Trier par score de co-achat décroissant
    6. $limit   : Garder les N meilleurs
    7. $lookup  : Enrichir avec les infos produit complètes
    """
    print_separator("Recommandations produits (co-achats)", "R10")

    # Récupérer le nom du produit pour l'affichage
    product = db.products.find_one({"_id": product_id})
    product_name = product["name"] if product else f"Produit #{product_id}"
    print(f"  Produit source : {product_name} (id={product_id})")
    print(f"  Algorithme     : Co-achat (Collaborative Filtering)\n")

    pipeline = [
        # 1. Trouver les commandes contenant ce produit
        {"$match": {"items.product.id": product_id}},
        # 2. Éclater les items
        {"$unwind": "$items"},
        # 3. Exclure le produit source
        {"$match": {"items.product.id": {"$ne": product_id}}},
        # 4. Compter les co-achats
        {
            "$group": {
                "_id": "$items.product.id",
                "product_name": {"$first": "$items.product.name"},
                "co_purchase_count": {"$sum": 1},
                "avg_quantity": {"$avg": "$items.quantity"},
            }
        },
        # 5. Trier par pertinence
        {"$sort": {"co_purchase_count": -1}},
        # 6. Limiter les résultats
        {"$limit": limit},
        # 7. Enrichir avec infos complètes du produit
        {
            "$lookup": {
                "from": "products",
                "localField": "_id",
                "foreignField": "_id",
                "as": "product_details",
            }
        },
        {"$unwind": {"path": "$product_details", "preserveNullAndEmptyArrays": True}},
        # Projection finale
        {
            "$project": {
                "_id": 0,
                "product_id": "$_id",
                "product_name": 1,
                "category": "$product_details.category.name",
                "department": "$product_details.department.name",
                "price": "$product_details.price",
                "co_purchase_count": 1,
                "score_recommandation": {
                    "$round": [
                        {"$multiply": ["$co_purchase_count", "$avg_quantity"]},
                        2,
                    ]
                },
            }
        },
    ]

    print("  Pipeline  : $match → $unwind → $match → $group → $sort → $limit → $lookup\n")
    results = list(db.orders.aggregate(pipeline))

    if results:
        print(f"  📌 \"Les clients qui ont acheté '{product_name}' ont aussi acheté :\"")
        print_results(results, limit=limit)
    else:
        print("  Aucune recommandation trouvée (produit jamais commandé ou toujours seul).")

    return results


# ═══════════════════════════════════════════════════════════════════════════
# Exécution de toutes les requêtes
# ═══════════════════════════════════════════════════════════════════════════

def run_all_queries() -> None:
    """Exécute les 10 requêtes avec des exemples de paramètres et sauvegarde en images."""
    print("\n" + "🚀" * 35)
    print("  EXÉCUTION DES 10 REQUÊTES MongoDB — Projet E-Commerce NoSQL")
    print("🚀" * 35)

    try:
        # Vérifier la connexion
        client.admin.command("ping")
        print(f"\n  ✅ Connecté à MongoDB ({MONGO_URI})")
        print(f"  📁 Base de données : {DATABASE_NAME}")
        
        # Statistiques de la base
        print(f"\n  Collections :")
        for col in ["products", "customers", "orders"]:
            count = db[col].count_documents({})
            print(f"    - {col}: {count} documents")

    except Exception as e:
        print(f"\n  ❌ Erreur de connexion : {e}")
        print("  Assurez-vous que MongoDB est démarré (docker-compose up -d)")
        sys.exit(1)

    # Définir chaque requête avec ses infos pour la capture
    queries = [
        ("R01", "R1 — Produits par catégorie",
         lambda: r1_products_by_category("Smartphones")),
        ("R02", "R2 — Commandes d'un client + items",
         lambda: r2_orders_by_customer(1)),
        ("R03", "R3 — Chiffre d'affaires par département",
         lambda: r3_revenue_by_department()),
        ("R04", "R4 — Top 10 produits les plus vendus",
         lambda: r4_top_10_products()),
        ("R05", "R5 — Clients par ville ou état",
         lambda: r5_customers_by_location(city="Dakar", state="Sénégal")),
        ("R06", "R6 — Historique complet d'une commande",
         lambda: r6_order_full_details(1)),
        ("R07", "R7 — Panier moyen par client",
         lambda: r7_average_basket_per_customer()),
        ("R08", "R8 — Catégories avec nombre de produits",
         lambda: r8_categories_product_count()),
        ("R09", "R9 — Commandes PENDING > 7 jours",
         lambda: r9_pending_orders_over_7_days()),
        ("R10", "R10 — Recommandations co-achats",
         lambda: r10_product_recommendations(product_id=1, limit=5)),
    ]

    # Exécuter et capturer chaque requête individuellement
    for filename, title, query_fn in queries:
        cap = OutputCapture()
        cap.start()
        query_fn()
        output_text = cap.stop()
        save_output_as_image(output_text, filename=filename, title=title)

    print(f"\n{'═' * 70}")
    print("  ✅ Toutes les requêtes ont été exécutées avec succès !")
    print(f"  📸 Images sauvegardées dans le dossier outputs/")
    print(f"{'═' * 70}\n")

    client.close()


if __name__ == "__main__":
    run_all_queries()
