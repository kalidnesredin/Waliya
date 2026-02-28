import sqlite3
import os
import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters

print("Telegram version:", telegram.__version__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [801355433, 309222693]
MY_CHANNEL_ID = '@waliyahousecar'
FRIEND_CHANNEL_ID = '@Bayracars'
GROUP_ID = '@waliya_12'

# Database
conn = sqlite3.connect('pending_posts.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS pending (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    photos TEXT,  
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

# ----------------------- BOT LOGIC -----------------------

async def start(update: Update, context):
    if update.message:
        await update.message.reply_text(
            "🚗 Welcome to the Car Listing Bot!\n\n"
            "Send 3-10 photos of the car (you can send them all at once as an album)."
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
        await update.message.reply_text("Max 10 photos. Starting over.")
        context.user_data['photos'] = []
        return PHOTOS
    
    # Inline Done button
    keyboard = [[InlineKeyboardButton("✅ Done", callback_data="done_photos")]]
    await update.message.reply_text(f"✅ {photo_count} photos received. Send more or click Done.", 
                                    reply_markup=InlineKeyboardMarkup(keyboard))
    return PHOTOS

async def done_photos_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    photo_count = len(context.user_data.get('photos', []))
    if photo_count < 3:
        await query.edit_message_text("❌ Need at least 3 photos. Send more and click Done again.")
        return PHOTOS
    await query.edit_message_text(f"✅ {photo_count} photos saved! What's the make of the car? (e.g., Toyota)")
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
        [
            InlineKeyboardButton("1", callback_data="plate_1"),
            InlineKeyboardButton("2", callback_data="plate_2"),
            InlineKeyboardButton("3", callback_data="plate_3"),
            InlineKeyboardButton("Brand New", callback_data="plate_brandnew")
        ]
    ]
    await update.message.reply_text("Select plate code or Brand New:", reply_markup=InlineKeyboardMarkup(keyboard))
    return PLATE

async def plate_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    context.user_data['plate'] = query.data.replace("plate_", "")
    keyboard = [
        [InlineKeyboardButton("Automatic", callback_data="Automatic"), InlineKeyboardButton("Manual", callback_data="Manual")]
    ]
    await query.edit_message_text("Transmission type?", reply_markup=InlineKeyboardMarkup(keyboard))
    return TRANSMISSION

async def transmission(update: Update, context):
    query = update.callback_query
    await query.answer()
    context.user_data['transmission'] = query.data
    await query.edit_message_text("Mileage? (e.g., 50,000 km)")
    return MILEAGE

async def mileage(update: Update, context):
    mileage = update.message.text.strip()
    if not mileage.replace(" km", "").replace(",", "").replace(" ", "").isdigit():
        await update.message.reply_text("❌ Invalid mileage. Use numbers (e.g., 50,000).")
        return MILEAGE
    context.user_data['mileage'] = mileage
    await update.message.reply_text("Color? (e.g., Red)")
    return COLOR

async def color(update: Update, context):
    context.user_data['color'] = update.message.text.strip()
    await update.message.reply_text("Price? (e.g., 2,894,000 ETB)")
    return PRICE

async def price(update: Update, context):
    price = update.message.text.strip()
    numeric_price = ''.join(filter(str.isdigit, price))
    if not numeric_price.isdigit():
        await update.message.reply_text("❌ Invalid price. Use numbers like 2,894,000.")
        return PRICE
    formatted_price = "{:,}".format(int(numeric_price))
    context.user_data['price'] = formatted_price + " ETB"
    await update.message.reply_text(f"Price recorded: {context.user_data['price']}\nDescription? (optional, max 500 chars). Type 'skip' to skip.")
    return DESCRIPTION

async def description(update: Update, context):
    desc = update.message.text.strip()
    if desc.lower() != 'skip' and len(desc) > 500:
        await update.message.reply_text("❌ Too long (max 500). Try again or 'skip'.")
        return DESCRIPTION
    context.user_data['description'] = desc if desc.lower() != 'skip' else ''
    keyboard = [[InlineKeyboardButton("Negotiable", callback_data="Negotiable"), InlineKeyboardButton("Fixed", callback_data="Fixed")]]
    await update.message.reply_text("Is the price negotiable or fixed?", reply_markup=InlineKeyboardMarkup(keyboard))
    return NEGOTIABLE

async def negotiable(update: Update, context):
    query = update.callback_query
    await query.answer()
    context.user_data['negotiable'] = query.data
    await query.edit_message_text("Phone number or Telegram username?")
    return CONTACT

async def contact(update: Update, context):
    context.user_data['contact'] = update.message.text.strip()
    data = context.user_data
    photos_str = ','.join(data['photos'])
    
    cursor.execute('''
        INSERT INTO pending (user_id, photos, make, model, year, condition, plate_code, transmission, mileage, color, price, description, negotiable, contact)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (update.message.from_user.id, photos_str, data['make'], data['model'], data['year'], data.get('condition', ''), data.get('plate', ''), data.get('transmission', ''), data['mileage'], data['color'], data['price'], data['description'], data['negotiable'], data['contact']))
    conn.commit()
    post_id = cursor.lastrowid
    
    await update.message.reply_text("✅ Your listing is submitted and pending approval by admins!")
    
    # User confirmation + post another car button
    keyboard_user = [[InlineKeyboardButton("🚗 Post Another Car", callback_data="post_another")]]
    await update.message.reply_text(
        "✅ Your listing is submitted and pending approval by admins!\n"
        "You can post another car if you want.",
        reply_markup=InlineKeyboardMarkup(keyboard_user)
    )

    # Send to admins
    post_text = format_post(data, is_pending=True)
    keyboard = [[InlineKeyboardButton("✅ Approve", callback_data=f"approve_{post_id}"),
                 InlineKeyboardButton("❌ Reject", callback_data=f"reject_{post_id}")]]
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
        f"🔹 Condition: {data.get('condition','')}\n"
        f"🔹 Plate Code: {data.get('plate','')}\n"
        f"🔹 Transmission: {data.get('transmission','')}\n"
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
    
    # Admin prompt to post another car
    keyboard = [[InlineKeyboardButton("Post Another Car", callback_data="post_another")]]
    await context.bot.send_message(query.from_user.id, "✅ Approved and posted.\nWould you like to post another car?", 
                                   reply_markup=InlineKeyboardMarkup(keyboard))
    
    await query.edit_message_text("✅ Approved and posted to channels & group!")

async def post_another_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    return await start(update, context)

async def cancel(update: Update, context):
    await update.message.reply_text("❌ Listing cancelled.")
    return ConversationHandler.END

# ----------------------- MAIN -----------------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            PHOTOS: [MessageHandler(filters.PHOTO | filters.Document.ALL, photos),
                     CallbackQueryHandler(done_photos_callback, pattern="^done_photos$")],
            MAKE: [MessageHandler(filters.TEXT & ~filters.COMMAND, make)],
            MODEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, model)],
            YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, year)],
            PLATE: [CallbackQueryHandler(plate_callback, pattern="^plate_")],
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
    app.add_handler(CallbackQueryHandler(post_another_callback, pattern='^post_another$'))
    
    print("Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()