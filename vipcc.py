import asyncio
import datetime
import logging
import random
import uvicorn
from fastapi import FastAPI
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Cấu hình thông tin bot và Admin
TOKEN = "8335633183:AAFurIszsH3hqW4fTa4SHYM4GZfCWEMDTe4"          # Bot chính (Bán hàng)
TOKEN_STOCK = "8770561467:AAFz1TLotmgJlL8N--sPWP rUR8XsZMPxzx4"   # Bot phụ (Nhét tài nguyên)
ADMIN_ID = 8312903264                                             # ID Admin của bạn

logging.basicConfig(level=logging.INFO)

# Khởi tạo 2 bot và 2 Dispatcher chạy song song
bot = Bot(token=TOKEN)
stock_bot = Bot(token=TOKEN_STOCK)

dp = Dispatcher()          # Router cho bot chính
stock_dp = Dispatcher()    # Router cho bot phụ

# Tạo web server FastAPI giữ cổng chống sleep trên Render
app = FastAPI()

@app.get("/")
def index():
    return {"status": "Both Bots are running!"}

# --- DATABASE TẠM THỜI TRONG BỘ NHỚ ---
users_db = {}
stock_db = {
    "srv_1_1": [], "srv_1_2": [], "srv_1_3": [],
    "srv_2_1": [], "srv_2_2": [], "srv_2_3": [],
    "mail_new": [], "mail_month": [], "mail_year": [],
}
orders_db = {}

# --- FSM CHO CÁC LUỒNG NHẬP LIỆU ---
class Form(StatesGroup):
    waiting_for_topup_amount = State()
    waiting_for_buff_link = State()
    waiting_for_buff_qty = State()
    waiting_for_kick_platform_id = State()
    waiting_for_kick_credentials = State()
    waiting_for_ip_address = State()
    waiting_for_fix_ip = State()
    waiting_for_cookie = State()
    waiting_for_add_stock = State()

def get_user(user_id: int):
    if user_id not in users_db:
        users_db[user_id] = {
            "balance": 0.0,
            "total_topup": 0.0,
            "referred_by": None,
            "invited_count": 0,
            "cookies": [],
            "username": "",
        }
    return users_db[user_id]

# --- BÀN PHÍM CHÍNH (MENU) ---
def main_menu_kb(user_id):
    keyboard = [
        [
            InlineKeyboardButton(text="👤 Tài khoản của tôi", callback_data="my_account"),
            InlineKeyboardButton(text="💳 Nạp tiền QR Tự Động", callback_data="topup_qr"),
        ],
        [
            InlineKeyboardButton(text="1. Mua Tick Xanh FB ✅", callback_data="buy_fb_tick_menu"),
            InlineKeyboardButton(text="2. Mua Tick Xanh IG ✅", callback_data="buy_ig_tick_menu"),
        ],
        [
            InlineKeyboardButton(text="3. Check UID 🔍", callback_data="check_uid"),
            InlineKeyboardButton(text="4. Proxy 🌐", callback_data="proxy_menu"),
        ],
        [
            InlineKeyboardButton(text="5. Lịch sử đơn hàng 📦", callback_data="history_orders"),
            InlineKeyboardButton(text="6. Top Nạp 🏆", callback_data="top_recharge"),
        ],
        [
            InlineKeyboardButton(text="7. Buff TikTok 🎵", callback_data="buff_tk"),
            InlineKeyboardButton(text="8. Buff Facebook 💙", callback_data="buff_fb"),
        ],
        [
            InlineKeyboardButton(text="9. Buff Instagram 🎀", callback_data="buff_ig"),
            InlineKeyboardButton(text="10. Sửa Giấy Tờ 📄", callback_data="fix_docs"),
        ],
        [
            InlineKeyboardButton(text="11. Cookie 🍪", callback_data="manage_cookies"),
            InlineKeyboardButton(text="12. Mua Mail 📨", callback_data="buy_mail_menu"),
        ],
        [
            InlineKeyboardButton(text="13. Kick thiết bị 🦿", callback_data="kick_device_menu"),
            InlineKeyboardButton(text="Kiếm tiền 💵", callback_data="make_money_menu"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    args = message.text.split()
    user = get_user(user_id)
    user["username"] = message.from_user.username or message.from_user.first_name

    if len(args) > 1 and args[1].isdigit():
        ref_id = int(args[1])
        if ref_id != user_id and user["referred_by"] is None:
            ref_user = get_user(ref_id)
            user["referred_by"] = ref_id
            ref_user["invited_count"] += 1
            ref_user["balance"] += 3000.0
            try:
                await bot.send_message(ref_id, "🎉 Chúc mừng! Bạn vừa mời thành công 1 người dùng mới và nhận được +3,000đ.")
            except:
                pass

    welcome_text = (
        f"👋 Chào mừng **{user['username']}** đến với hệ thống dịch vụ Agency!\n\n"
        f"💰 Số dư hiện tại: **{user['balance']:,.0f}đ**\n"
        f"💡 Hướng dẫn nạp tiền nhanh: Gõ `/naptien [số_tiền]` (Ví dụ: `/naptien 100000`)\n\n"
        f"Vui lòng chọn chức năng bên dưới:"
    )
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=main_menu_kb(user_id))

@dp.message(Command("sd"))
async def cmd_check_balance(message: types.Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    text = (
        f"💳 **THÔNG TIN SỐ DƯ**\n\n"
        f"🆔 ID: `{user_id}`\n"
        f"💰 Số dư hiện tại: **{user['balance']:,.0f}đ**"
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("naptien"))
async def cmd_naptien_fast(message: types.Message):
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        return await message.answer(
            "⚠️ Vui lòng nhập đúng cú pháp!\n"
            "Ví dụ nạp 100,000đ: `/naptien 100000`",
            parse_mode="Markdown"
        )
    
    amount = float(args[1])
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    transfer_content = f"NAP {user_id}"
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    qr_url = f"https://img.vietqr.io/image/MB-2105200999999-compact2.png?amount={int(amount)}&addInfo={transfer_content}&accountName=KHONG%20QUOC%20BAO"

    text = (
        f"💳 **HƯỚNG DẪN NẠP TIỀN TỰ ĐỘNG**\n\n"
        f"• Số tiền: **{amount:,.0f}đ**\n"
        f"• Ngân hàng: `MB Bank`\n"
        f"• Số tài khoản: `2105200999999`\n"
        f"• Chủ tài khoản: `KHONG QUOC BAO`\n"
        f"• Nội dung chuyển khoản: `{transfer_content}`\n\n"
        f"⚠️ Vui lòng quét mã QR hoặc chuyển đúng số tiền kèm nội dung trên. Hệ thống sẽ tự động duyệt hoặc gửi yêu cầu cho Admin."
    )
    
    admin_text = (
        f"🔔 **CÓ YÊU CẦU NẠP TIỀN MỚI**\n\n"
        f"👤 Tên: @{username} ({message.from_user.full_name})\n"
        f"🆔 ID khách: `{user_id}`\n"
        f"💵 Số tiền: **{amount:,.0f}đ**\n"
        f"⏰ Thời gian: {current_time}"
    )
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Duyệt", callback_data=f"approve_topup_{user_id}_{int(amount)}"),
            InlineKeyboardButton(text="❌ Từ chối", callback_data=f"reject_topup_{user_id}")
        ]
    ])

    try:
        await message.answer_photo(photo=qr_url, caption=text, parse_mode="Markdown")
    except Exception:
        await message.answer(text, parse_mode="Markdown")

    try:
        await bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown", reply_markup=admin_kb)
    except Exception:
        pass

@dp.callback_query(F.data.in_(["back_to_menu", "back_home"]))
async def cb_back_to_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    user = get_user(user_id)
    text = f"🏠 **MENU CHÍNH**\n\n💰 Số dư: **{user['balance']:,.0f}đ**\nVui lòng chọn chức năng:"
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=main_menu_kb(user_id))
    await callback.answer()

# ==========================================
# TÀI KHOẢN & NẠP TIỀN QR (MB BANK)
# ==========================================
@dp.callback_query(F.data == "my_account")
async def process_my_account(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    text = (
        f"👤 *THÔNG TIN TÀI KHOẢN*\n\n"
        f"🆔 ID của bạn: `{user_id}`\n"
        f"📛 Tên: {callback.from_user.full_name}\n"
        f"💰 Số dư: *{user['balance']:,.0f} VNĐ*\n"
        f"🍪 Số lượng Cookie đang lưu: {len(user['cookies'])}\n"
        f"👥 Số bạn đã mời: {user['invited_count']} người\n"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Quay lại Menu", callback_data="back_to_menu")]])
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data == "topup_qr")
async def process_topup_qr(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    transfer_content = f"NAP {user_id}"
    qr_url = f"https://img.vietqr.io/image/MB-2105200999999-compact2.png?amount=0&addInfo={transfer_content}&accountName=KHONG%20QUOC%20BAO"

    text = (
        f"💳 *HƯỚNG DẪN NẠP TIỀN TỰ ĐỘNG*\n\n"
        f"Quét mã QR hoặc chuyển khoản theo thông tin:\n"
        f"• Ngân hàng: `MB Bank`\n"
        f"• Số tài khoản: `2105200999999`\n"
        f"• Chủ tài khoản: `KHONG QUOC BAO`\n"
        f"• Nội dung chuyển khoản: `{transfer_content}`\n\n"
        f"💡 Hoặc bạn có thể gõ nhanh: `/naptien [số_tiền]` (Ví dụ: `/naptien 100000`)\n\n"
        f"⚠️ Sau khi chuyển khoản xong, vui lòng nhấn nút bên dưới để gửi yêu cầu duyệt tiền cho Admin."
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Báo cáo đã chuyển khoản", callback_data="report_topup")],
        [InlineKeyboardButton(text="🔙 Quay lại Menu", callback_data="back_to_menu")],
    ])
    try:
        await callback.message.answer_photo(photo=qr_url, caption=text, parse_mode="Markdown", reply_markup=keyboard)
        await callback.message.delete()
    except Exception:
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data == "report_topup")
async def process_report_topup(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(Form.waiting_for_topup_amount)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Hủy", callback_data="back_to_menu")]])
    await callback.message.edit_text("💰 Vui lòng nhập số tiền bạn đã chuyển khoản (Ví dụ: `50000`):", parse_mode="Markdown", reply_markup=keyboard)
    await callback.answer()

@dp.message(Form.waiting_for_topup_amount)
async def process_topup_amount_input(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("Vui lòng nhập số tiền hợp lệ bằng số!")
    
    amount = float(message.text)
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    await state.clear()
    await message.answer("✅ Đã gửi yêu cầu nạp tiền tới Admin. Vui lòng chờ duyệt trong giây lát!")

    admin_text = (
        f"🔔 **CÓ YÊU CẦU NẠP TIỀN MỚI**\n\n"
        f"👤 Tên: @{username} ({message.from_user.full_name})\n"
        f"🆔 ID khách: `{user_id}`\n"
        f"💵 Số tiền: **{amount:,.0f}đ**\n"
        f"⏰ Thời gian: {current_time}"
    )
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Duyệt", callback_data=f"approve_topup_{user_id}_{int(amount)}"),
            InlineKeyboardButton(text="❌ Từ chối", callback_data=f"reject_topup_{user_id}")
        ]
    ])
    try:
        await bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown", reply_markup=admin_kb)
    except Exception:
        pass

@dp.callback_query(F.data.startswith("approve_topup_"))
async def cb_approve_topup(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("Bạn không có quyền thực hiện thao tác này!", show_alert=True)
    
    _, _, user_id_str, amount_str = callback.data.split("_")
    user_id = int(user_id_str)
    amount = float(amount_str)

    user = get_user(user_id)
    user["balance"] += amount
    user["total_topup"] += amount

    await callback.message.edit_text(callback.message.text + f"\n\n✅ **ĐÃ DUYỆT (+{amount:,.0f}đ)**")
    await callback.answer("Đã duyệt nạp tiền thành công!")

    try:
        await bot.send_message(user_id, f"🎉 Tài khoản của bạn đã được Admin duyệt cộng **{amount:,.0f}đ** vào số dư!")
    except:
        pass

@dp.callback_query(F.data.startswith("reject_topup_"))
async def cb_reject_topup(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("Bạn không có quyền thực hiện thao tác này!", show_alert=True)
    
    _, _, user_id_str = callback.data.split("_")
    user_id = int(user_id_str)

    await callback.message.edit_text(callback.message.text + "\n\n❌ **ĐÃ TỪ CHỐI GIAO DỊCH**")
    await callback.answer("Đã từ chối giao dịch!")

    try:
        await bot.send_message(user_id, "❌ Yêu cầu nạp tiền của bạn đã bị từ chối bởi Admin. Vui lòng liên hệ hỗ trợ.")
    except:
        pass

# ==========================================
# QUẢN LÝ COOKIE
# ==========================================
@dp.callback_query(F.data == "manage_cookies")
async def process_manage_cookies(callback: types.CallbackQuery, state: FSMContext):
    user = get_user(callback.from_user.id)
    cookie_count = len(user["cookies"])
    text = (
        f"🍪 *QUẢN LÝ COOKIE*\n\n"
        f"Số lượng Cookie hiện đang lưu: *{cookie_count}*\n\n"
        f"Vui lòng chọn thao tác bên dưới:"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Thêm Cookie mới", callback_data="add_cookie")],
        [InlineKeyboardButton(text="🗑️ Xóa tất cả Cookie", callback_data="clear_cookies")],
        [InlineKeyboardButton(text="🔙 Quay lại Menu", callback_data="back_to_menu")],
    ])
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data == "add_cookie")
async def process_add_cookie_prompt(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(Form.waiting_for_cookie)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Hủy bỏ", callback_data="manage_cookies")]])
    await callback.message.edit_text("📥 Vui lòng gửi đoạn Cookie của bạn vào đây:", parse_mode="Markdown", reply_markup=keyboard)
    await callback.answer()

@dp.message(Form.waiting_for_cookie)
async def process_save_cookie(message: types.Message, state: FSMContext):
    user = get_user(message.from_user.id)
    user["cookies"].append(message.text.strip())
    await state.clear()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍪 Quản lý Cookie", callback_data="manage_cookies")],
        [InlineKeyboardButton(text="🏠 Về Menu chính", callback_data="back_to_menu")],
    ])
    await message.answer("✅ Đã lưu Cookie thành công!", reply_markup=keyboard)

@dp.callback_query(F.data == "clear_cookies")
async def process_clear_cookies(callback: types.CallbackQuery, state: FSMContext):
    user = get_user(callback.from_user.id)
    user["cookies"] = []
    await callback.answer("🗑️ Đã xóa toàn bộ cookie thành công!", show_alert=True)
    await process_manage_cookies(callback, state)

# ==========================================
# MUA TICK XANH FB & IG
# ==========================================
@dp.callback_query(F.data == "buy_fb_tick_menu")
async def cb_buy_fb_tick_menu(callback: types.CallbackQuery):
    kb = [
        [InlineKeyboardButton(text="1. FB Tick Pay sẵn (150,000đ)", callback_data="buy_item_srv_1_1")],
        [InlineKeyboardButton(text="2. FB Tick xanh sẵn dùng ngay (300,000đ)", callback_data="buy_item_srv_1_2")],
        [InlineKeyboardButton(text="3. Tick FB Theo tên & Avatar (500,000đ)", callback_data="buy_item_srv_1_3")],
        [InlineKeyboardButton(text="« Quay lại Menu", callback_data="back_to_menu")],
    ]
    await callback.message.edit_text("🔵 **BÁN TICK XANH FACEBOOK**\nVui lòng chọn mục mua bên dưới:", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(F.data == "buy_ig_tick_menu")
async def cb_buy_ig_tick_menu(callback: types.CallbackQuery):
    kb = [
        [InlineKeyboardButton(text="1. IG Tick Pay sẵn (180,000đ)", callback_data="buy_item_srv_2_1")],
        [InlineKeyboardButton(text="2. IG Tick xanh sẵn dùng ngay (350,000đ)", callback_data="buy_item_srv_2_2")],
        [InlineKeyboardButton(text="3. Tick IG Theo tên & Avatar (550,000đ)", callback_data="buy_item_srv_2_3")],
        [InlineKeyboardButton(text="« Quay lại Menu", callback_data="back_to_menu")],
    ]
    await callback.message.edit_text("🟣 **BÁN TICK XANH INSTAGRAM**\nVui lòng chọn mục mua bên dưới:", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

PRICES_TICK = {
    "srv_1_1": ("FB Tick Pay sẵn", 150000),
    "srv_1_2": ("FB Tick xanh sẵn dùng ngay", 300000),
    "srv_1_3": ("Tick FB Theo tên & Avatar", 500000),
    "srv_2_1": ("IG Tick Pay sẵn", 180000),
    "srv_2_2": ("IG Tick xanh sẵn dùng ngay", 350000),
    "srv_2_3": ("Tick IG Theo tên & Avatar", 550000),
}

@dp.callback_query(F.data.startswith("buy_item_"))
async def cb_buy_item(callback: types.CallbackQuery):
    key = callback.data.replace("buy_item_", "")
    user_id = callback.from_user.id
    user = get_user(user_id)

    if key not in PRICES_TICK:
        return await callback.answer("Sản phẩm không tồn tại!", show_alert=True)

    name, price = PRICES_TICK[key]
    if user["balance"] < price:
        return await callback.answer(f"❌ Số dư không đủ! Cần {price:,.0f}đ nhưng chỉ có {user['balance']:,.0f}đ.", show_alert=True)

    if not stock_db.get(key) or len(stock_db[key]) == 0:
        return await callback.answer("⚠️ Kho tài nguyên mục này đang tạm hết, vui lòng liên hệ admin!", show_alert=True)

    acc_data = stock_db[key].pop(0)
    user["balance"] -= price

    if user_id not in orders_db:
        orders_db[user_id] = []
    order_id = "".join(random.choices("0123456789ABCDEF", k=8))
    orders_db[user_id].append({"id": order_id, "product": name, "details": acc_data, "time": "Hôm nay"})

    await callback.message.edit_text(
        f"✅ **MUA HÀNG THÀNH CÔNG!**\n\n📦 Sản phẩm: {name}\n💵 Đã trừ: {price:,.0f}đ\n🔑 Mã đơn hàng: `{order_id}`\n\n👉 Kiểm tra chi tiết tại mục **Lịch sử đơn hàng 📦**.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📦 Lịch sử đơn hàng", callback_data="history_orders")],
            [InlineKeyboardButton(text="« Quay lại Menu", callback_data="back_to_menu")],
        ]),
    )
    await callback.answer("Mua thành công!")

# ==========================================
# CHECK UID
# ==========================================
@dp.callback_query(F.data == "check_uid")
async def cb_check_uid(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    price = 2000

    if user["balance"] < price:
        return await callback.answer("❌ Số dư không đủ 2,000đ!", show_alert=True)

    user["balance"] -= price
    status = random.choice(["Live ✅", "Die 🚫"])
    await callback.message.edit_text(
        f"🔍 **KẾT QUẢ CHECK UID**\n\n💵 Phí: 2,000đ\n📊 Tình trạng: **{status}**\n\n💰 Số dư còn lại: {user['balance']:,.0f}đ",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Quay lại Menu", callback_data="back_to_menu")]]),
    )
    await callback.answer()

# ==========================================
# PROXY & RỬA IP / FIX IP
# ==========================================
@dp.callback_query(F.data == "proxy_menu")
async def cb_proxy_menu(callback: types.CallbackQuery):
    kb = [
        [InlineKeyboardButton(text="Proxy Việt Nam 🇻🇳", callback_data="proxy_vn")],
        [InlineKeyboardButton(text="Proxy Ngoại Quốc 🌍", callback_data="proxy_foreign")],
        [InlineKeyboardButton(text="Chặn IP - 300,000đ 🛡️", callback_data="block_ip")],
        [InlineKeyboardButton(text="Rửa IP/Fix IP - 150,000đ 📱", callback_data="fix_ip_menu")],
        [InlineKeyboardButton(text="« Quay lại Menu", callback_data="back_to_menu")],
    ]
    await callback.message.edit_text(
        "🌐 **HỆ THỐNG PROXY & BẢO MẬT IP**\nVui lòng chọn:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
    )
    await callback.answer()

@dp.callback_query(F.data == "proxy_vn")
async def cb_proxy_vn(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🌐 **Proxy Việt Nam**: Tốc độ cao.\nGiá: 50,000đ/tháng.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Quay lại", callback_data="proxy_menu")]]),
    )

@dp.callback_query(F.data == "proxy_foreign")
async def cb_proxy_foreign(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🌍 **Proxy Ngoại Quốc**: US/UK sạch sẽ.\nGiá: 80,000đ/tháng.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Quay lại", callback_data="proxy_menu")]]),
    )

@dp.callback_query(F.data == "block_ip")
async def cb_block_ip(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(Form.waiting_for_ip_address)
    await callback.message.edit_text(
        "🛡️ **CHẶN IP**\nGiá: **300,000đ**\nVui lòng nhập địa chỉ IP cần thao tác:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Quay lại", callback_data="proxy_menu")]]),
    )
    await callback.answer()

@dp.message(Form.waiting_for_ip_address)
async def process_ip_address(message: types.Message, state: FSMContext):
    ip_text = message.text.strip()
    user_id = message.from_user.id
    user = get_user(user_id)
    price = 300000

    if user["balance"] < price:
        return await message.answer(f"❌ Số dư không đủ {price:,.0f}đ!")

    user["balance"] -= price
    await state.clear()

    await message.answer(
        f"IP: {ip_text}\nTình trạng: Thành Công ✅\n💰 Số dư còn lại: {user['balance']:,.0f}đ",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Quay lại Menu", callback_data="back_to_menu")]]),
    )

@dp.callback_query(F.data == "fix_ip_menu")
async def cb_fix_ip_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(Form.waiting_for_fix_ip)
    await callback.message.edit_text(
        "📱 **RỬA IP / FIX IP**\nGiá: **150,000đ**\n\nVui lòng nhập địa chỉ IP của bạn:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Quay lại", callback_data="proxy_menu")]]),
    )
    await callback.answer()

@dp.message(Form.waiting_for_fix_ip)
async def process_fix_ip_input(message: types.Message, state: FSMContext):
    ip_text = message.text.strip()
    user_id = message.from_user.id
    user = get_user(user_id)
    price = 150000

    if user["balance"] < price:
        await state.clear()
        return await message.answer(f"❌ Số dư không đủ {price:,.0f}đ để thực hiện Rửa IP!")

    user["balance"] -= price
    await state.clear()

    await message.answer(
        f"IP: {ip_text}\nTình trạng: Thành Công ✅\n💰 Số dư còn lại: {user['balance']:,.0f}đ",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Quay lại Menu", callback_data="back_to_menu")]]),
    )

# ==========================================
# LỊCH SỬ ĐƠN HÀNG
# ==========================================
@dp.callback_query(F.data == "history_orders")
async def cb_history_orders(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_orders = orders_db.get(user_id, [])

    if not user_orders:
        text = "📦 Bạn chưa có đơn hàng nào."
    else:
        text = "📦 **LỊCH SỬ ĐƠN HÀNG**:\n\n"
        for ord in user_orders:
            text += f"▪️ **Mã đơn:** `{ord['id']}`\n🔹 **Sản phẩm:** {ord['product']}\n🔑 **Thông tin:** `{ord['details']}`\n------------------\n"

    await callback.message.edit_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Quay lại Menu", callback_data="back_to_menu")]]),
    )
    await callback.answer()

# ==========================================
# BUFF TIKTOK, FACEBOOK, INSTAGRAM
# ==========================================
@dp.callback_query(F.data.in_(["buff_tk", "buff_fb", "buff_ig"]))
async def cb_buff_menu(callback: types.CallbackQuery, state: FSMContext):
    platform_map = {
        "buff_tk": ("TikTok 🎵", [("Tăng Tim ♥️ (15đ)", 15), ("Tăng Followers 🤖 (80đ)", 80)]),
        "buff_fb": ("Facebook 💙", [("Tăng Followers 🤖 (10đ)", 10), ("Tăng Tim ♥️ (11đ)", 11)]),
        "buff_ig": ("Instagram 🎀", [("Tăng Followers 🤖 (13đ)", 13), ("Tăng Tim ♥️ (11đ)", 11)]),
    }
    p_key = callback.data
    name, options = platform_map[p_key]
    kb = [[InlineKeyboardButton(text=opt_name, callback_data=f"buff_sel_{p_key}_{price}")] for opt_name, price in options]
    kb.append([InlineKeyboardButton(text="« Quay lại Menu", callback_data="back_to_menu")])

    await callback.message.edit_text(f"🚀 **BUFF {name}**\nChọn dịch vụ:", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(F.data.startswith("buff_sel_"))
async def cb_buff_select_service(callback: types.CallbackQuery, state: FSMContext):
    _, _, p_key, price_str = callback.data.split("_")
    await state.update_data(buff_price=int(price_str), buff_platform=p_key)
    await state.set_state(Form.waiting_for_buff_link)
    await callback.message.edit_text("🔗 Gửi **Link/URL** cần buff:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Quay lại", callback_data=p_key)]]))
    await callback.answer()

@dp.message(Form.waiting_for_buff_link)
async def process_buff_link(message: types.Message, state: FSMContext):
    await state.update_data(buff_link=message.text.strip())
    await state.set_state(Form.waiting_for_buff_qty)
    await message.answer("🔢 Nhập **số lượng** cần buff:")

@dp.message(Form.waiting_for_buff_qty)
async def process_buff_qty(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("Vui lòng nhập số lượng hợp lệ!")

    qty = int(message.text)
    data = await state.get_data()
    total_cost = qty * data["buff_price"]
    user = get_user(message.from_user.id)

    if user["balance"] < total_cost:
        await state.clear()
        return await message.answer(f"❌ Số dư không đủ {total_cost:,.0f}đ!")

    user["balance"] -= total_cost
    await state.clear()
    await message.answer(
        f"✅ **ĐẶT ĐƠN BUFF THÀNH CÔNG!**\n📊 Số lượng: {qty}\n💵 Đã trừ: {total_cost:,.0f}đ",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Quay lại Menu", callback_data="back_to_menu")]]),
    )

# ==========================================
# SỬA GIẤY TỜ, TOP NẠP
# ==========================================
@dp.callback_query(F.data == "fix_docs")
async def cb_fix_docs(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📄 **SỬA GIẤY TỜ**\nLiên hệ admin qua @miutea88.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Quay lại Menu", callback_data="back_to_menu")]]),
    )
    await callback.answer()

@dp.callback_query(F.data == "top_recharge")
async def cb_top_recharge(callback: types.CallbackQuery):
    sorted_users = sorted(users_db.items(), key=lambda x: x[1]["total_topup"], reverse=True)[:10]
    text = "🏆 **TOP 10 NẠP NHIỀU NHẤT**\n\n"
    if not sorted_users or all(u[1]["total_topup"] == 0 for u in sorted_users):
        text += "Chưa có dữ liệu."
    else:
        for idx, (uid, u_data) in enumerate(sorted_users, 1):
            if u_data["total_topup"] > 0:
                text += f"#{idx} - UID `{uid}`: **{u_data['total_topup']:,.0f}đ**\n"

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Quay lại Menu", callback_data="back_to_menu")]]))
    await callback.answer()

# ==========================================
# MUA MAIL 📨
# ==========================================
@dp.callback_query(F.data == "buy_mail_menu")
async def cb_buy_mail_menu(callback: types.CallbackQuery):
    kb = [
        [InlineKeyboardButton(text="Mail New - 25,000đ", callback_data="buy_mail_new")],
        [InlineKeyboardButton(text="Mail Tháng - 50,000đ", callback_data="buy_mail_month")],
        [InlineKeyboardButton(text="Mail Năm - 115,000đ", callback_data="buy_mail_year")],
        [InlineKeyboardButton(text="« Quay lại Menu", callback_data="back_to_menu")],
    ]
    await callback.message.edit_text("📨 **KHO MAIL**\nChọn loại mail:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(F.data.in_(["buy_mail_new", "buy_mail_month", "buy_mail_year"]))
async def cb_buy_mail_process(callback: types.CallbackQuery):
    mail_types = {
        "buy_mail_new": ("Mail New", 25000, "mail_new"),
        "buy_mail_month": ("Mail Tháng", 50000, "mail_month"),
        "buy_mail_year": ("Mail Năm", 115000, "mail_year"),
    }
    name, price, stock_key = mail_types[callback.data]
    user = get_user(callback.from_user.id)

    if user["balance"] < price:
        return await callback.answer("❌ Số dư không đủ!", show_alert=True)
    if not stock_db.get(stock_key) or len(stock_db[stock_key]) == 0:
        return await callback.answer("⚠️ Kho tạm hết!", show_alert=True)

    acc = stock_db[stock_key].pop(0)
    user["balance"] -= price
    await callback.message.edit_text(
        f"✅ **MUA THÀNH CÔNG!**\nAcc: `{acc}`",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Quay lại Menu", callback_data="back_to_menu")]]),
    )
    await callback.answer()

# ==========================================
# KICK THIẾT BỊ 🦿
# ==========================================
KICK_PLATFORMS = {1: ("Facebook", 270000), 2: ("Instagram", 250000), 3: ("Tiktok", 200000)}

@dp.callback_query(F.data == "kick_device_menu")
async def cb_kick_device_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(Form.waiting_for_kick_platform_id)
    text = "🦿 **KICK THIẾT BỊ**\nNhập số thứ tự nền tảng:\n"
    for idx, (p_name, p_price) in KICK_PLATFORMS.items():
        text += f"{idx}. {p_name} — {p_price:,.0f}đ\n"
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Quay lại", callback_data="back_to_menu")]]))
    await callback.answer()

@dp.message(Form.waiting_for_kick_platform_id)
async def process_kick_choice(message: types.Message, state: FSMContext):
    if not message.text.isdigit() or int(message.text) not in KICK_PLATFORMS:
        return await message.answer("Vui lòng nhập đúng số thứ tự hợp lệ!")
    p_name, p_price = KICK_PLATFORMS[int(message.text)]
    await state.update_data(kick_platform=p_name, kick_price=p_price)
    await state.set_state(Form.waiting_for_kick_credentials)
    await message.answer(f"Nhập **Tài khoản | Mật khẩu** của {p_name}:")

@dp.message(Form.waiting_for_kick_credentials)
async def process_kick_creds(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user = get_user(message.from_user.id)
    if user["balance"] < data["kick_price"]:
        await state.clear()
        return await message.answer("❌ Số dư không đủ!")
    user["balance"] -= data["kick_price"]
    await state.clear()
    await message.answer("✅ Đã đăng xuất toàn bộ thiết bị thành công!")

# ==========================================
# KIẾM TIỀN (TÀI XỈU & BOWLING)
# ==========================================
@dp.callback_query(F.data == "make_money_menu")
async def cb_make_money_menu(callback: types.CallbackQuery):
    kb = [
        [InlineKeyboardButton(text="🎲 Tài Xỉu 🎲", callback_data="game_taixiu")],
        [InlineKeyboardButton(text="🎳 Bowling 🎳", callback_data="game_bowling")],
        [InlineKeyboardButton(text="« Quay lại Menu", callback_data="back_to_menu")],
    ]
    await callback.message.edit_text("💵 **KHU VỰC GIẢI TRÍ KIẾM TIỀN**", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(F.data == "game_taixiu")
async def cb_game_taixiu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🎲 **TÀI XỈU**\nLệnh cược: `/Tai (số tiền)` hoặc `/Xiu (số tiền)` (Tối thiểu 20k, Thưởng x1.95)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Quay lại", callback_data="make_money_menu")]]),
    )
    await callback.answer()

@dp.callback_query(F.data == "game_bowling")
async def cb_game_bowling(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🎳 **BOWLING**\nLệnh cược: `/Chan (số tiền)` hoặc `/Le (số tiền)` (Tối thiểu 20k, Thưởng x1.85)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Quay lại", callback_data="make_money_menu")]]),
    )
    await callback.answer()

@dp.message(Command(commands=["Tai", "tai"]))
async def cmd_bet_tai(message: types.Message):
    await process_dice_bet(message, "TAI")

@dp.message(Command(commands=["Xiu", "xiu"]))
async def cmd_bet_xiu(message: types.Message):
    await process_dice_bet(message, "XIU")

async def process_dice_bet(message: types.Message, choice: str):
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        return await message.answer("Sai cú pháp! Dùng: `/Tai 50000` hoặc `/Xiu 50000`")
    amount = int(args[1])
    user = get_user(message.from_user.id)
    if amount < 20000 or user["balance"] < amount:
        return await message.answer("❌ Không đủ số dư hoặc mức cược tối thiểu là 20,000đ!")

    user["balance"] -= amount
    v1 = (await message.answer_dice(emoji="🎲")).dice.value
    v2 = (await message.answer_dice(emoji="🎲")).dice.value
    v3 = (await message.answer_dice(emoji="🎲")).dice.value
    total = v1 + v2 + v3
    is_tai = 11 <= total <= 18
    win = (choice == "TAI" and is_tai) or (choice == "XIU" and not is_tai)

    if win:
        payout = amount * 1.95
        user["balance"] += payout
        await message.answer(f"🎉 THẮNG! Tổng điểm: {total}. Nhận được +{payout:,.0f}đ")
    else:
        await message.answer(f"😢 THUA! Tổng điểm: {total}. Chúc bạn may mắn lần sau.")

@dp.message(Command(commands=["Chan", "chan"]))
async def cmd_bet_chan(message: types.Message):
    await process_bowling_bet(message, "CHAN")

@dp.message(Command(commands=["Le", "le"]))
async def cmd_bet_le(message: types.Message):
    await process_bowling_bet(message, "LE")

async def process_bowling_bet(message: types.Message, choice: str):
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        return await message.answer("Sai cú pháp! Dùng: `/Chan 50000` hoặc `/Le 50000`")
    amount = int(args[1])
    user = get_user(message.from_user.id)
    if amount < 20000 or user["balance"] < amount:
        return await message.answer("❌ Không đủ số dư hoặc mức cược tối thiểu là 20,000đ!")

    user["balance"] -= amount
    msg_dice = await message.answer_dice(emoji="🎳")
    value = msg_dice.dice.value
    is_even = (value % 2 == 0)
    win = (choice == "CHAN" and is_even) or (choice == "LE" and not is_even)

    if win:
        payout = amount * 1.85
        user["balance"] += payout
        await message.answer(f"🎉 THẮNG BOWLING! Kết quả: {value} (được {'Chẵn' if is_even else 'Lẻ'}). Nhận được +{payout:,.0f}đ")
    else:
        await message.answer(f"😢 THUA BOWLING! Kết quả: {value} (được {'Chẵn' if is_even else 'Lẻ'}).")

# ==========================================
# ADMIN COMMANDS (THÊM TIỀN, KHO, THÔNG BÁO)
# ==========================================
@dp.message(Command("addtien"))
async def cmd_addtien(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    args = message.text.split()
    if len(args) < 3:
        return await message.answer("Cú pháp: `/addtien (user_id) (số_tiền)`", parse_mode="Markdown")
    user_id = int(args[1])
    amount = float(args[2])
    get_user(user_id)["balance"] += amount
    await message.answer(f"✅ Đã cộng {amount:,.0f}đ cho user `{user_id}`", parse_mode="Markdown")

@dp.message(Command("addstock"))
async def cmd_addstock(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        return await message.answer(
            "⚠️ Cú pháp không đúng!\n"
            "Dùng: `/addstock (mã_kho) (nội_dung_tài_nguyên)`\n\n"
            "Danh sách mã kho:\n"
            "• `srv_1_1` (FB Pay sẵn)\n"
            "• `srv_1_2` (FB Xanh sẵn)\n"
            "• `srv_1_3` (FB Tên & Avatar)\n"
            "• `srv_2_1` (IG Pay sẵn)\n"
            "• `srv_2_2` (IG Xanh sẵn)\n"
            "• `srv_2_3` (IG Tên & Avatar)\n"
            "• `mail_new` | `mail_month` | `mail_year`",
            parse_mode="Markdown"
        )
    
    stock_key = args[1]
    content = args[2]

    if stock_key not in stock_db:
        return await message.answer(f"❌ Mã kho `{stock_key}` không tồn tại!", parse_mode="Markdown")

    stock_db[stock_key].append(content)
    await message.answer(f"✅ Đã thêm tài nguyên thành công vào kho `{stock_key}`!\n📦 Tổng tồn kho hiện tại: {len(stock_db[stock_key])} mục.", parse_mode="Markdown")

@dp.message(Command("thongbao"))
async def cmd_thongbao(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    content = message.text.replace("/thongbao", "", 1).strip()
    if not content:
        return await message.answer("⚠️ Vui lòng nhập nội dung thông báo!\nCú pháp: `/thongbao (nội dung)`", parse_mode="Markdown")

    success_count = 0
    fail_count = 0

    status_msg = await message.answer("📢 Đang gửi thông báo đến toàn bộ người dùng...")

    for user_id in users_db.keys():
        try:
            await bot.send_message(user_id, f"📢 **THÔNG BÁO TỪ HỆ THỐNG**\n\n{content}", parse_mode="Markdown")
            success_count += 1
            await asyncio.sleep(0.05)
        except Exception:
            fail_count += 1

    await status_msg.edit_text(
        f"✅ **GỬI THÔNG BÁO HOÀN TẤT**\n\n"
        f"• Thành công: `{success_count}` người dùng\n"
        f"• Thất bại: `{fail_count}` người dùng",
        parse_mode="Markdown"
    )


# ==========================================
# 🤖 CODE TÍCH HỢP CON BOT PHỤ (NHẬT KÝ KHO HÀNG)
# ==========================================
@stock_dp.message(Command("them"))
async def stock_bot_add(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("Bạn không có quyền sử dụng bot này!")

    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        return await message.answer(
            "⚠️ Sai cú pháp!\n"
            "Dùng: `/them [mã_kho] [nội_dung]`\n\n"
            "💡 Các mã kho hợp lệ:\n"
            "• `srv_1_1`, `srv_1_2`, `srv_1_3` (Tick FB)\n"
            "• `srv_2_1`, `srv_2_2`, `srv_2_3` (Tick IG)\n"
            "• `mail_new`, `mail_month`, `mail_year`",
            parse_mode="Markdown"
        )

    skey = args[1]
    content = args[2]

    if skey not in stock_db:
        return await message.answer(f"❌ Mã kho `{skey}` không tồn tại!")

    stock_db[skey].append(content)
    await message.answer(f"✅ Đã nhét thành công vào kho `{skey}`!\n📦 Tồn kho hiện tại: {len(stock_db[skey])} mục.")

@stock_dp.message(Command("start"))
async def stock_bot_start(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("Bot này dùng riêng cho Admin.")
    await message.answer(
        "🤖 **BOT QUẢN LÝ KHO TÀI NGUYÊN**\n\n"
        "Nhắn tin trực tiếp để nhét hàng vào kho chính:\n"
        "`/them [mã_kho] [nội_dung]`",
        parse_mode="Markdown"
    )


# --- KHỞI CHẠY SONG SONG 2 CON BOT & WEB SERVER ---
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await stock_bot.delete_webhook(drop_pending_updates=True)

    config = uvicorn.Config(app, host="0.0.0.0", port=10000, log_level="info")
    server = uvicorn.Server(config)
    
    print("Starting Web Server & Both Telegram Bots simultaneously...")
    await asyncio.gather(
        server.serve(),
        dp.start_polling(bot),
        stock_dp.start_polling(stock_bot)
    )

if __name__ == "__main__":
    asyncio.run(main())
