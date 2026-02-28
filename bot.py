import sqlite3
import os
import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters


print("Telegram version:", telegram.__version__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [801355433, 309222693]  # Replace with your two admin Telegram USER IDs
MY_CHANNEL_ID = '@waliyahousecar'  # e.g., '@cars_ethiopia' or -1001234567890
FRIEND_CHANNEL_ID = '@bayracars'  # e.g., '@friend_cars' or -100xxxxxxxxxx
GROUP_ID = '@waliya_12'      # Same for group
# =========================

# Database
conn = sqlite3.connect('pending_posts.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS pending (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    photos TEXT,  -- Comma-separated file_ids
    make TEXT,
    model TEXT,
    year TEXT,
    condition TEXT,
    plate_code TEXT,
    transmission TEXT,
    mileage TEXT,
    color TEXT,
    price TEXT,
    description TEXT,
    negotiable TEXT,
    contact TEXT
)
''')
conn.commit()

# Conversation states
PHOTOS, MAKE, MODEL, YEAR, CONDITION, PLATE, TRANSMISSION, MILEAGE, COLOR, PRICE, DESCRIPTION, NEGOTIABLE, CONTACT = range(13)

async def start(update: Update, context):
    await update.message.reply_text(
        "🚗 Welcome to the Car Listing Bot!\n\n"
        "Send 3-10 photos of the car (you can send them all at once as an album).\n"
        "Then type /done to continue."
    )
    context.user_data['photos'] = []
    return PHOTOS

async def photos(update: Update, context):
    message = update.message
    if message.photo:
        context.user_data['photos'].append(message.photo[-1].file_id)
    elif message.document:
        await message.reply_text("Please send as photos, not documents.")
        return PHOTOS
    
    photo_count = len(context.user_data['photos'])
    if photo_count > 10:
        await message.reply_text("Max 10 photos. Starting over.")
        context.user_data['photos'] = []
        return PHOTOS
    
    await message.reply_text(f"✅ {photo_count} photos received. Send more or type /done to continue.")
    return PHOTOS

async def done_photos(update: Update, context):
    photo_count = len(context.user_data.get('photos', []))
    if photo_count < 3:
        await update.message.reply_text("❌ Need at least 3 photos. Send more and /done again.")
        return PHOTOS
    await update.message.reply_text(f"✅ {photo_count} photos saved! What's the make of the car? (e.g., Toyota)")
    return MAKE

async def make(update: Update, context):
    context.user_data['make'] = update.message.text.strip()
    await update.message.reply_text("Model? (e.g., Corolla)")
    return MODEL

async def model(update: Update, context):
    context.user_data['model'] = update.message.text.strip()
    await update.message.reply_text("Year of manufacture? (e.g., 2020)")
    return YEAR

async def year(update: Update, context):
    year = update.message.text.strip()
    if not year.isdigit() or not (1900 <= int(year) <= 2026):
        await update.message.reply_text("❌ Invalid year (1900-2026). Try again.")
        return YEAR
    context.user_data['year'] = year
    keyboard = [
        [InlineKeyboardButton("Used", callback_data="Used"), InlineKeyboardButton("Brand New", callback_data="Brand New")]
    ]
    await update.message.reply_text("Used or Brand New?", reply_markup=InlineKeyboardMarkup(keyboard))
    return CONDITION

async def condition(update: Update, context):
    query = update.callback_query
    await query.answer()
    context.user_data['condition'] = query.data
    await query.edit_message_text(f"✅ Selected: {query.data}\n\nPlate code? (usually 1, 2, or 3)")
    return PLATE

async def plate(update: Update, context):
    plate = update.message.text.strip()
    if not plate.isdigit() or not (1 <= int(plate) <= 3):
        await update.message.reply_text("❌ Plate code must be 1, 2, or 3. Try again.")
        return PLATE
    context.user_data['plate'] = plate
    keyboard = [
        [InlineKeyboardButton("Automatic", callback_data="Automatic"), InlineKeyboardButton("Manual", callback_data="Manual")]
    ]
    await update.message.reply_text("Transmission type?", reply_markup=InlineKeyboardMarkup(keyboard))
    return TRANSMISSION

async def transmission(update: Update, context):
    query = update.callback_query
    await query.answer()
    context.user_data['transmission'] = query.data
    await query.edit_message_text(f"✅ Selected: {query.data}\n\nMileage? (e.g., 50000 km)")
    return MILEAGE

async def mileage(update: Update, context):
    mileage = update.message.text.strip()
    if not mileage.replace(" km", "").replace(" ", "").isdigit():
        await update.message.reply_text("❌ Invalid mileage. Use numbers (e.g., 50000).")
        return MILEAGE
    context.user_data['mileage'] = mileage
    await update.message.reply_text("Color? (e.g., Red)")
    return COLOR

async def color(update: Update, context):
    context.user_data['color'] = update.message.text.strip()
    await update.message.reply_text("Price? (e.g., 100000 ETB)")
    return PRICE

async def price(update: Update, context):
    price = update.message.text.strip()
    if not price.replace(" ETB", "").replace(" ", "").isdigit():
        await update.message.reply_text("❌ Invalid price. Use numbers (e.g., 100000).")
        return PRICE
    context.user_data['price'] = price
    await update.message.reply_text("Description? (optional, max 500 chars). Type 'skip' to skip.")
    return DESCRIPTION

async def description(update: Update, context):
    desc = update.message.text.strip()
    if desc.lower() != 'skip' and len(desc) > 500:
        await update.message.reply_text("❌ Too long (max 500). Try again or 'skip'.")
        return DESCRIPTION
    context.user_data['description'] = desc if desc.lower() != 'skip' else ''
    keyboard = [
        [InlineKeyboardButton("Negotiable", callback_data="Negotiable"), InlineKeyboardButton("Fixed", callback_data="Fixed")]
    ]
    await update.message.reply_text("Is the price negotiable or fixed?", reply_markup=InlineKeyboardMarkup(keyboard))
    return NEGOTIABLE

async def negotiable(update: Update, context):
    query = update.callback_query
    await query.answer()
    context.user_data['negotiable'] = query.data
    await query.edit_message_text(f"✅ Selected: {query.data}\n\nPhone number or Telegram username?")
    return CONTACT

async def contact(update: Update, context):
    context.user_data['contact'] = update.message.text.strip()
    data = context.user_data
    photos_str = ','.join(data['photos'])
    cursor.execute('''
        INSERT INTO pending (user_id, photos, make, model, year, condition, plate_code, transmission, mileage, color, price, description, negotiable, contact)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (update.message.from_user.id, photos_str, data['make'], data['model'], data['year'], data['condition'], data['plate'], data['transmission'], data['mileage'], data['color'], data['price'], data['description'], data['negotiable'], data['contact']))
    conn.commit()
    post_id = cursor.lastrowid
    await update.message.reply_text("✅ Your listing is submitted and pending approval by admins!")
    
    # Send to BOTH admins
    post_text = format_post(data, is_pending=True)
    keyboard = [
        [InlineKeyboardButton("✅ Approve", callback_data=f"approve_{post_id}"), 
         InlineKeyboardButton("❌ Reject", callback_data=f"reject_{post_id}")]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(admin_id, post_text, reply_markup=markup)
        except Exception as e:
            print(f"Failed to notify admin {admin_id}: {e}")
    
    return ConversationHandler.END

def format_post(data, is_pending=False):
    desc = f"\n📝 Description: {data['description']}" if data['description'] else ''
    return (
        f"🚗 **{data['make']} {data['model']} ({data['year']})**\n"
        f"🔹 Condition: {data['condition']}\n"
        f"🔹 Plate Code: {data['plate']}\n"
        f"🔹 Transmission: {data['transmission']}\n"
        f"🔹 Mileage: {data['mileage']}\n"
        f"🔹 Color: {data['color']}\n"
        f"💰 Price: {data['price']} ({data['negotiable']})\n"
        f"{desc}\n"
        f"📞 Contact: {data['contact']}\n\n"
        f"{'🔄 *Pending Admin Approval*' if is_pending else ''}"
    )

async def approve_reject(update: Update, context):
    query = update.callback_query
    await query.answer()
    action, post_id = query.data.split('_')
    post_id = int(post_id)
    
    cursor.execute('SELECT * FROM pending WHERE id = ?', (post_id,))
    row = cursor.fetchone()
    if not row:
        await query.edit_message_text("❌ This post has already been processed by another admin.")
        return
    
    if action == 'reject':
        cursor.execute('DELETE FROM pending WHERE id = ?', (post_id,))
        conn.commit()
        await query.edit_message_text("❌ Rejected and removed.")
        return
    
    # Approve
    data = {
        'make': row[3], 'model': row[4], 'year': row[5], 'condition': row[6], 'plate': row[7],
        'transmission': row[8], 'mileage': row[9], 'color': row[10], 'price': row[11],
        'description': row[12], 'negotiable': row[13], 'contact': row[14]
    }
    post_text = format_post(data)
    photos = row[2].split(',') if row[2] else []
    
    # Post to both channels and the group
    targets = [MY_CHANNEL_ID, FRIEND_CHANNEL_ID, GROUP_ID]
    for target in targets:
        if photos:
            media = [InputMediaPhoto(photo_id) for photo_id in photos]
            media[0].caption = post_text
            media[0].parse_mode = 'Markdown'
            await context.bot.send_media_group(target, media)
        else:
            await context.bot.send_message(target, post_text, parse_mode='Markdown')
    
    cursor.execute('DELETE FROM pending WHERE id = ?', (post_id,))
    conn.commit()
    await query.edit_message_text("✅ Approved and posted to both channels & group!")

async def cancel(update: Update, context):
    await update.message.reply_text("❌ Listing cancelled.")
    return ConversationHandler.END

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            PHOTOS: [
                MessageHandler(filters.PHOTO | filters.Document.ALL, photos),
                CommandHandler('done', done_photos)
            ],
            MAKE: [MessageHandler(filters.TEXT & ~filters.COMMAND, make)],
            MODEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, model)],
            YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, year)],
            CONDITION: [CallbackQueryHandler(condition)],
            PLATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, plate)],
            TRANSMISSION: [CallbackQueryHandler(transmission)],
            MILEAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, mileage)],
            COLOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, color)],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, price)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, description)],
            NEGOTIABLE: [CallbackQueryHandler(negotiable)],
            CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, contact)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(approve_reject, pattern='^(approve|reject)_'))
    
    print("Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()