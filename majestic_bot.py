import os
import json
import secrets
import asyncio
import threading
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = "8951797894:AAH8mj6ky_mlj3XCHmEviEmHcmjSdpz8P-U"
ADMIN_ID = 8102854834
KEYS_FILE = "keys_data.json"
HWID_FILE = "hwid_data.json"

def load_json(path, default=None):
    if default is None:
        default = {}
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def generate_key():
    hex_chars = '0123456789ABCDEF'
    part1 = ''.join(secrets.choice(hex_chars) for _ in range(4))
    part2 = ''.join(secrets.choice(hex_chars) for _ in range(4))
    return f"MAJ-{part1}-{part2}"

DURATIONS = {'1': 1, '3': 3, '7': 7, '30': 30, '90': 90, '365': 365}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Нет доступа")
        return
    await update.message.reply_text(
        "MAJESTIC KEY MANAGER\n\n"
        "/create 7 - создать ключ\n"
        "/revoke MAJ-XXXX-XXXX - отозвать\n"
        "/keys - список ключей\n"
        "/stats - статистика\n"
        "/hwid MAJ-XXXX-XXXX - HWID ключа\n"
        "/unbind MAJ-XXXX-XXXX - отвязать HWID"
    )

async def create_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("Укажи срок: /create 7")
        return
    days = context.args[0]
    if days not in DURATIONS:
        await update.message.reply_text(f"Доступные сроки: {', '.join(DURATIONS.keys())} дней")
        return
    keys = load_json(KEYS_FILE)
    new_key = generate_key()
    while new_key in keys:
        new_key = generate_key()
    duration = DURATIONS[days]
    keys[new_key] = {
        "duration_days": duration,
        "created": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "activated": None,
        "active": True
    }
    save_json(KEYS_FILE, keys)
    await update.message.reply_text(f"Ключ создан: {new_key}\nСрок: {duration} дн.")

async def revoke_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("Укажи ключ: /revoke MAJ-XXXX-XXXX")
        return
    key_to_revoke = context.args[0].upper()
    keys = load_json(KEYS_FILE)
    if key_to_revoke not in keys:
        await update.message.reply_text("Ключ не найден")
        return
    keys[key_to_revoke]['active'] = False
    save_json(KEYS_FILE, keys)
    hwids = load_json(HWID_FILE)
    if key_to_revoke in hwids:
        del hwids[key_to_revoke]
        save_json(HWID_FILE, hwids)
    await update.message.reply_text(f"Ключ отозван: {key_to_revoke}")

async def list_keys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    keys = load_json(KEYS_FILE)
    hwids = load_json(HWID_FILE)
    if not keys:
        await update.message.reply_text("Нет ключей")
        return
    msg = "Ключи:\n\n"
    for key, data in keys.items():
        status = "Активен" if data['active'] else "Отозван"
        activated = "Активирован" if data['activated'] else "Не активирован"
        bound = "Привязан" if key in hwids else "Не привязан"
        msg += f"{key} - {data['duration_days']}д - {status} - {activated} - {bound}\n"
    await update.message.reply_text(msg)

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    keys = load_json(KEYS_FILE)
    hwids = load_json(HWID_FILE)
    total = len(keys)
    active = sum(1 for k in keys.values() if k['active'])
    activated = sum(1 for k in keys.values() if k['activated'])
    bound = len(hwids)
    await update.message.reply_text(f"Статистика\nВсего: {total}\nАктивных: {active}\nАктивировано: {activated}\nПривязано: {bound}")

async def show_hwid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("Укажи ключ: /hwid MAJ-XXXX-XXXX")
        return
    key = context.args[0].upper()
    hwids = load_json(HWID_FILE)
    keys = load_json(KEYS_FILE)
    if key not in keys:
        await update.message.reply_text("Ключ не найден")
        return
    if key in hwids:
        await update.message.reply_text(f"HWID: {hwids[key]}")
    else:
        await update.message.reply_text("Ключ не активирован")

async def unbind_hwid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("Укажи ключ: /unbind MAJ-XXXX-XXXX")
        return
    key = context.args[0].upper()
    hwids = load_json(HWID_FILE)
    if key in hwids:
        del hwids[key]
        save_json(HWID_FILE, hwids)
        keys = load_json(KEYS_FILE)
        if key in keys:
            keys[key]['activated'] = None
            save_json(KEYS_FILE, keys)
        await update.message.reply_text(f"HWID отвязан: {key}")
    else:
        await update.message.reply_text("Ключ не был привязан")

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"service": "Majestic Key Server", "status": "running"})

@app.route('/check', methods=['POST'])
def check_key():
    data = request.json
    key = data.get('key', '').upper()
    hwid = data.get('hwid', '')
    
    keys = load_json(KEYS_FILE)
    hwids = load_json(HWID_FILE)
    
    if key not in keys:
        return jsonify({"valid": False, "message": "Неверный ключ", "code": "INVALID"})
    
    key_data = keys[key]
    
    if not key_data.get('active', False):
        return jsonify({"valid": False, "message": "Ключ отозван", "code": "REVOKED"})
    
    if key in hwids:
        if hwids[key] != hwid:
            return jsonify({"valid": False, "message": "Ключ привязан к другому устройству", "code": "HWID_MISMATCH"})
    else:
        hwids[key] = hwid
        save_json(HWID_FILE, hwids)
    
    if key_data.get('activated'):
        activated_date = datetime.strptime(key_data['activated'], '%Y-%m-%d %H:%M:%S')
    else:
        activated_date = datetime.now()
        key_data['activated'] = activated_date.strftime('%Y-%m-%d %H:%M:%S')
        save_json(KEYS_FILE, keys)
    
    duration = key_data['duration_days']
    expire_date = activated_date + timedelta(days=duration)
    
    if datetime.now() > expire_date:
        return jsonify({"valid": False, "message": "Ключ истёк", "code": "EXPIRED"})
    
    return jsonify({
        "valid": True,
        "message": f"Доступ до {expire_date.strftime('%Y-%m-%d %H:%M:%S')}",
        "expire_date": expire_date.strftime('%Y-%m-%d %H:%M:%S'),
        "code": "OK"
    })

@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({"status": "ok"})

def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("create", create_key))
    application.add_handler(CommandHandler("revoke", revoke_key))
    application.add_handler(CommandHandler("keys", list_keys))
    application.add_handler(CommandHandler("stats", show_stats))
    application.add_handler(CommandHandler("hwid", show_hwid))
    application.add_handler(CommandHandler("unbind", unbind_hwid))
    
    print("Bot started")
    application.run_polling()

if __name__ == '__main__':
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
