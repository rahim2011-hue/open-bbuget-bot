import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

TOKEN = "8826766716:AAEpCHzAz-J8MRwbUZ6-jfaIX88cz6Yelrc"
ADMIN_ID = 6682139161  # O'z Telegram ID raqamingiz

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- BAZA ---
def db_start():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0, referred_by INTEGER DEFAULT 0)")
    cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS withdraws (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER, method TEXT, details TEXT)")
    conn.commit()
    
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('budget_link', '')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('vote_price', '5000')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('ref_bonus', '2000')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('min_withdraw', '50000')")
    conn.commit()
    conn.close()

db_start()

def get_setting(key):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else ""

def update_setting(key, value):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE settings SET value = ? WHERE key = ?", (value, key))
    conn.commit()
    conn.close()

# --- HOLATLAR ---
class UserStates(StatesGroup):
    waiting_for_phone = State()
    waiting_for_code = State()
    waiting_for_withdraw_details = State()

class AdminStates(StatesGroup):
    waiting_for_link = State()
    waiting_for_min_withdraw = State()
    waiting_for_vote_price = State()
    waiting_for_broadcast = State()

# --- MENYULAR ---
def main_menu(user_id):
    kb = [
        [KeyboardButton(text="🗳 Ovoz berish"), KeyboardButton(text="💰 Balans")],
        [KeyboardButton(text="💸 Pul yechish"), KeyboardButton(text="🔗 Referal ssilka")]
    ]
    if user_id == ADMIN_ID:
        kb.append([KeyboardButton(text="👑 Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")]
])

# --- START ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    args = message.text.split()
    
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        ref_id = 0
        if len(args) > 1 and args[1].isdigit():
            ref_id = int(args[1])
            if ref_id != user_id:
                ref_bonus = int(get_setting("ref_bonus"))
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (ref_bonus, ref_id))
        cursor.execute("INSERT INTO users (user_id, referred_by) VALUES (?, ?)", (user_id, ref_id))
        conn.commit()
    conn.close()

    text = (
        "👋 Botga xush kelibsiz!\n\n"
        "📦 OPEN BUDGET BOSHLANDI! 🚀\n\n"
        "✨ Ovoz bering — mukofot oling 🎁\n"
        "🤝 Do'stlaringizni taklif qiling — qo'shimcha daromad toping 💸\n\n"
        "‼ UNUTMANG, OVOZ UCHUN TO'LVNI FAQAT BIZNING BOT QILMOQDA. 🛡️"
    )
    await message.answer(text, reply_markup=main_menu(user_id))

@dp.callback_query(F.data == "cancel")
async def cancel_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.edit_text("❌ Amaliyot bekor qilindi.")
    except:
        pass
    await callback.message.answer("Asosiy menyu:", reply_markup=main_menu(callback.from_user.id))
    await callback.answer()

# --- ASOSIY MENYUGA QAYTISH ---
@dp.message(F.text.in_(["🗳 Ovoz berish", "💰 Balans", "💸 Pul yechish", "🔗 Referal ssilka", "👑 Admin Panel", "🔙 Asosiy menyu"]))
async def global_menu_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text
    
    await state.clear()
    
    if text == "🗳 Ovoz berish":
        link = get_setting("budget_link")
        if not link:
            await message.answer("⚠️ Hozirda ovoz berish uchun loyiha havolasi admin tomonidan qo'yilmagan!")
            return
        await message.answer("📞 Tasdiqlash uchun telefon raqamingizni kiriting:\nNa'muna: 991234567", reply_markup=cancel_kb)
        await state.set_state(UserStates.waiting_for_phone)
        
    elif text == "💰 Balans":
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        bal = cursor.fetchone()[0]
        conn.close()
        await message.answer(f"💰 Sizning hisobingiz: {bal} so'm", reply_markup=main_menu(user_id))
        
    elif text == "💸 Pul yechish":
        kb_reply = ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text="📞 Paynet"), KeyboardButton(text="💳 Karta")],
            [KeyboardButton(text="🔙 Asosiy menyu")]
        ], resize_keyboard=True)
        await message.answer("Pul yechish usulini tanlang:", reply_markup=kb_reply)
        
    elif text == "🔗 Referal ssilka":
        bot_info = await bot.get_me()
        link = f"https://t.me/{bot_info.username}?start={user_id}"
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,))
        ref_count = cursor.fetchone()[0]
        conn.close()
        await message.answer(f"🔗 Sizning taklif ssilkangiz:\n{link}\n\n👥 Taklif qilgan do'stlaringiz: {ref_count} ta", reply_markup=main_menu(user_id))
        
    elif text == "👑 Admin Panel":
        if user_id == ADMIN_ID:
            kb = [
                [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="🔗 Loyiha havolasi")],
                [KeyboardButton(text="⚙️ Minimal summani o'zgartirish"), KeyboardButton(text="💵 Ovoz narxini o'zgartirish")],
                [KeyboardButton(text="📢 Barchaga xabar yuborish"), KeyboardButton(text="🔙 Asosiy menyu")]
            ]
            await message.answer("👑 Admin Panel:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
        else:
            await message.answer("Sizda admin huquqi yo'q.")
            
    elif text in ["🔙 Asosiy menyu", "Asosiy menyu"]:
        await message.answer("Asosiy menyu:", reply_markup=main_menu(user_id))

# --- OVOZ BERISH JARAYONI ---
@dp.message(UserStates.waiting_for_phone)
async def get_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    if len(phone) < 7:
        await message.answer("❌ Noto'g'ri raqam. Qaytadan kiriting (Na'muna: 991234567):", reply_markup=cancel_kb)
        return

    await state.update_data(phone=phone)
    await message.answer("🔄 Telefon raqamingizga SMS xabar yuborilyapti...", reply_markup=cancel_kb)
    await asyncio.sleep(2)
    await message.answer("✉️ Tasdiqlash uchun **6 xonali SMS kodni** kiriting:", reply_markup=cancel_kb)
    await state.set_state(UserStates.waiting_for_code)

@dp.message(UserStates.waiting_for_code)
async def get_code(message: types.Message, state: FSMContext):
    code = message.text.strip()
    
    if not code.isdigit() or len(code) != 6:
        await message.answer("❌ Iltimos, to'g'ri kodni kiriting! Kod faqat **6 ta raqamdan** iborat bo'lishi kerak:", reply_markup=cancel_kb)
        return

    price = int(get_setting("vote_price"))
    user_id = message.from_user.id
    
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (price, user_id))
    conn.commit()
    conn.close()
    
    await state.clear()
    await message.answer(f"✅ Ovoz muvaffaqiyatli qabul qilindi! Hisobingizga {price} so'm qo'shildi.", reply_markup=main_menu(user_id))

# --- PUL YECHISH TAFSILOTLARI ---
@dp.message(F.text.in_(["📞 Paynet", "💳 Karta"]))
async def choose_method(message: types.Message, state: FSMContext):
    await state.update_data(method=message.text)
    cancel_reply = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔙 Asosiy menyu")]], resize_keyboard=True)
    await message.answer("💳 Karta raqamingizni yoki Paynet telefon raqamingizni kiriting:", reply_markup=cancel_reply)
    await state.set_state(UserStates.waiting_for_withdraw_details)

@dp.message(UserStates.waiting_for_withdraw_details)
async def get_withdraw_details(message: types.Message, state: FSMContext):
    details = message.text
    data = await state.get_data()
    user_id = message.from_user.id
    min_w = int(get_setting("min_withdraw"))
    
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    bal = cursor.fetchone()[0]
    
    if bal < min_w:
        await message.answer(f"❌ Kechirasiz, minimal pul yechish miqdori: {min_w} so'm. Balansingiz yetarli emas.", reply_markup=main_menu(user_id))
        await state.clear()
        conn.close()
        return
        
    cursor.execute("UPDATE users SET balance = 0 WHERE user_id = ?", (user_id,))
    cursor.execute("INSERT INTO withdraws (user_id, amount, method, details) VALUES (?, ?, ?, ?)", (user_id, bal, data.get("method"), details))
    conn.commit()
    conn.close()
    
    await state.clear()
    await message.answer("✅ Pul yechish so'rovingiz adminga yuborildi!", reply_markup=main_menu(user_id))
    await bot.send_message(ADMIN_ID, f"🔔 **Yangi pul yechish so'rovi!**\n\n👤 ID: {user_id}\n💰 Summa: {bal} so'm\n🛠 Usul: {data.get('method')}\n📱 Ma'lumot: {details}")

# --- ADMIN PANEL FUNKSIYALARI ---
@dp.message(F.text == "📊 Statistika", F.from_user.id == ADMIN_ID)
async def admin_stats(message: types.Message):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    conn.close()
    await message.answer(f"📊 Jami foydalanuvchilar: {total_users} ta")

@dp.message(F.text == "🔗 Loyiha havolasi", F.from_user.id == ADMIN_ID)
async def manage_link(message: types.Message):
    link = get_setting("budget_link")
    if link:
        text = f"🔗 Hozirgi loyiha havolasi:\n{link}"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ O'zgartirish", callback_data="change_link")],
            [InlineKeyboardButton(text="🗑 Olib tashlash", callback_data="delete_link")]
        ])
    else:
        text = "🔗 Hozircha loyiha havolasi qo'yilmagan."
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Havola qo'shish", callback_data="change_link")]
        ])
    await message.answer(text, reply_markup=kb)

@dp.callback_query(F.data == "change_link", F.from_user.id == ADMIN_ID)
async def callback_change_link(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Yangi loyiha havolasini yuboring (faqat 1 ta havola bo'ladi):", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔙 Asosiy menyu")]], resize_keyboard=True))
    await state.set_state(AdminStates.waiting_for_link)
    await callback.answer()

@dp.message(AdminStates.waiting_for_link, F.from_user.id == ADMIN_ID)
async def save_new_link(message: types.Message, state: FSMContext):
    update_setting("budget_link", message.text.strip())
    await state.clear()
    await message.answer("✅ Loyiha havolasi muvaffaqiyatli saqlandi!", reply_markup=main_menu(message.from_user.id))

@dp.callback_query(F.data == "delete_link", F.from_user.id == ADMIN_ID)
async def callback_delete_link(callback: types.CallbackQuery):
    update_setting("budget_link", "")
    try:
        await callback.message.edit_text("🗑 Loyiha havolasi olib tashlandi. Endi yangi havola qo'shishingiz mumkin.")
    except:
        pass
    await callback.answer()

@dp.message(F.text == "⚙️ Minimal summani o'zgartirish", F.from_user.id == ADMIN_ID)
async def change_min_w(message: types.Message, state: FSMContext):
    await message.answer("Yangi minimal pul yechish summasini kiriting (masalan: 50000):", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔙 Asosiy menyu")]], resize_keyboard=True))
    await state.set_state(AdminStates.waiting_for_min_withdraw)

@dp.message(AdminStates.waiting_for_min_withdraw, F.from_user.id == ADMIN_ID)
async def save_min_w(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Faqat raqam kiriting:")
        return
    update_setting("min_withdraw", message.text)
    await state.clear()
    await message.answer(f"✅ Minimal summa {message.text} so'm qilib o'zgartirildi!", reply_markup=main_menu(message.from_user.id))

@dp.message(F.text == "💵 Ovoz narxini o'zgartirish", F.from_user.id == ADMIN_ID)
async def change_vote_price(message: types.Message, state: FSMContext):
    await message.answer("Har bir ovoz uchun yangi narxni kiriting (masalan: 5000):", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔙 Asosiy menyu")]], resize_keyboard=True))
    await state.set_state(AdminStates.waiting_for_vote_price)

@dp.message(AdminStates.waiting_for_vote_price, F.from_user.id == ADMIN_ID)
async def save_vote_price(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Faqat raqam kiriting:")
        return
    update_setting("vote_price", message.text)
    await state.clear()
    await message.answer(f"✅ Ovoz narxi {message.text} so'm qilib o'zgartirildi!", reply_markup=main_menu(message.from_user.id))

@dp.message(F.text == "📢 Barchaga xabar yuborish", F.from_user.id == ADMIN_ID)
async def broadcast_cmd(message: types.Message, state: FSMContext):
    await message.answer("Barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yuboring:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔙 Asosiy menyu")]], resize_keyboard=True))
    await state.set_state(AdminStates.waiting_for_broadcast)

@dp.message(AdminStates.waiting_for_broadcast, F.from_user.id == ADMIN_ID)
async def send_broadcast(message: types.Message, state: FSMContext):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()
    
    await state.clear()
    sent_count = 0
    await message.answer("⏳ Xabar yuborish boshlandi...")
    
    for row in users:
        u_id = row[0]
        try:
            await message.send_copy(chat_id=u_id)
            sent_count += 1
            await asyncio.sleep(0.05)
        except:
            pass
            
    await message.answer(f"✅ Xabar muvaffaqiyatli **{sent_count} ta** foydalanuvchiga yuborildi!", reply_markup=main_menu(message.from_user.id))

# --- ISHGA TUSHIRISH ---
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())