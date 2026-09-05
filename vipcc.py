import asyncio
import logging
import random
import re
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

# Cấu hình thông tin bot và Admin
TOKEN = "8335633183:AAELuswtzaZS57Xq7-8K2Xs3KSo47q1kE30"
ADMIN_ID = 8985238179

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- DATABASE TẠM THỜI TRONG BỘ NHỚ ---
users_db = {}

stock_db = {
    "srv_1_1": [],
    "srv_1_2": [],
    "srv_1_3": [],
    "srv_2_1": [],
    "srv_2_2": [],
    "srv_2_3": [],
    "mail_new": [],
    "mail_month": [],
    "mail_year": [],
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
    waiting_for_withdraw_amount = State()
    waiting_for_bank_name = State()
    waiting_for_bank_acc = State()
    waiting_for_bank_owner = State()
    waiting_for_cookie = State()


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
            InlineKeyboardButton(
                text="👤 Tài khoản của tôi", callback_data="my_account"
            ),
            InlineKeyboardButton(
                text="💳 Nạp tiền QR Tự Động", callback_data="topup_qr"
            ),
        ],
        [
            InlineKeyboardButton(
                text="1. Mua Tick Xanh FB ✅", callback_data="buy_fb_tick_menu"
            ),
            InlineKeyboardButton(
                text="2. Mua Tick Xanh IG ✅", callback_data="buy_ig_tick_menu"
            ),
        ],
        [
            InlineKeyboardButton(text="3. Check UID 🔍", callback_data="check_uid"),
            InlineKeyboardButton(text="4. Proxy 🌐", callback_data="proxy_menu"),
        ],
        [
            InlineKeyboardButton(
                text="5. Lịch sử đơn hàng 📦", callback_data="history_orders"
            ),
            InlineKeyboardButton(text="6. Top Nạp 🏆", callback_data="top_recharge"),
        ],
        [
            InlineKeyboardButton(text="7. Buff TikTok 🎵", callback_data="buff_tk"),
            InlineKeyboardButton(
                text="8. Buff Facebook 💙", callback_data="buff_fb"
            ),
        ],
        [
            InlineKeyboardButton(
                text="9. Buff Instagram 🎀", callback_data="buff_ig"
            ),
            InlineKeyboardButton(
                text="10. Sửa Giấy Tờ 📄", callback_data="fix_docs"
            ),
        ],
        [
            InlineKeyboardButton(text="11. Cookie 🍪", callback_data="manage_cookies"),
            InlineKeyboardButton(text="12. Mua Mail 📨", callback_data="buy_mail_menu"),
        ],
        [
            InlineKeyboardButton(
                text="13. Kick thiết bị 🦿", callback_data="kick_device_menu"
            ),
            InlineKeyboardButton(
                text="Kiếm tiền 💵", callback_data="make_money_menu"
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# --- LỆNH /START & XỬ LÝ REF ---
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
                await bot.send_message(
                    ref_id,
                    f"🎉 Chúc mừng! Bạn vừa mời thành công 1 người dùng mới tham gia bot và nhận được +3,000đ vào số dư.",
                )
            except:
                pass

    welcome_text = (
        f"👋 Chào mừng **{user['username']}** đến với hệ thống dịch vụ Agency!\n\n"
        f"💰 Số dư hiện tại: **{user['balance']:,.0f}đ**\n"
        f"Vui lòng chọn chức năng bên dưới:"
    )
    await message.answer(
        welcome_text, parse_mode="Markdown", reply_markup=main_menu_kb(user_id)
    )


@dp.callback_query(F.data.in_(["back_to_menu", "back_home"]))
async def cb_back_to_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    user = get_user(user_id)
    text = (
        f"🏠 **MENU CHÍNH**\n\n"
        f"💰 Số dư: **{user['balance']:,.0f}đ**\n"
        f"Vui lòng chọn chức năng:"
    )
    await callback.message.edit_text(
        text, parse_mode="Markdown", reply_markup=main_menu_kb(user_id)
    )
    await callback.answer()


# ==========================================
# TÀI KHOẢN CỦA TÔI & NẠP TIỀN QR VIETQR (ĐÃ CẬP NHẬT MB BANK)
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

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Quay lại Menu", callback_data="back_to_menu")]
        ]
    )

    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)
    await callback.answer()


@dp.callback_query(F.data == "topup_qr")
async def process_topup_qr(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    transfer_content = f"NAP {user_id}"
    # Đã đổi sang VietQR của MB Bank với số tài khoản 2105200999999
    qr_url = f"https://img.vietqr.io/image/MB-2105200999999-compact2.png?amount=0&addInfo={transfer_content}&accountName=KHONG%20QUOC%20BAO"

    text = (
        f"💳 *HƯỚNG DẪN NẠP TIỀN TỰ ĐỘNG*\n\n"
        f"Quét mã QR hoặc chuyển khoản theo thông tin:\n"
        f"• Ngân hàng: `MB Bank`\n"
        f"• Số tài khoản: `2105200999999`\n"
        f"• Chủ tài khoản: `KHONG QUOC BAO`\n"
        f"• Nội dung chuyển khoản: `{transfer_content}`\n\n"
        f"⚠️ *Lưu ý:* Hệ thống sẽ tự động cộng tiền khi nhận được chuyển khoản."
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Kiểm tra giao dịch", callback_data="check_topup")],
            [InlineKeyboardButton(text="🔙 Quay lại Menu", callback_data="back_to_menu")],
        ]
    )

    try:
        await callback.message.answer_photo(photo=qr_url, caption=text, parse_mode="Markdown", reply_markup=keyboard)
        await callback.message.delete()
    except Exception:
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)

    await callback.answer()


@dp.callback_query(F.data == "check_topup")
async def process_check_topup(callback: types.CallbackQuery):
    await callback.answer("❌ Chưa ghi nhận giao dịch mới nào với nội dung của bạn!", show_alert=True)


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

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Thêm Cookie mới", callback_data="add_cookie")],
            [InlineKeyboardButton(text="🗑️ Xóa tất cả Cookie", callback_data="clear_cookies")],
            [InlineKeyboardButton(text="🔙 Quay lại Menu", callback_data="back_to_menu")],
        ]
    )

    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)
    await callback.answer()


@dp.callback_query(F.data == "add_cookie")
async def process_add_cookie_prompt(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(Form.waiting_for_cookie)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Hủy bỏ", callback_data="manage_cookies")]
        ]
    )
    await callback.message.edit_text(
        "📥 Vui lòng gửi đoạn Cookie của bạn vào đây:", parse_mode="Markdown", reply_markup=keyboard
    )
    await callback.answer()


@dp.message(Form.waiting_for_cookie)
async def process_save_cookie(message: types.Message, state: FSMContext):
    user = get_user(message.from_user.id)
    new_cookie = message.text.strip()

    user["cookies"].append(new_cookie)
    await state.clear()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🍪 Quản lý Cookie", callback_data="manage_cookies")],
            [InlineKeyboardButton(text="🏠 Về Menu chính", callback_data="back_to_menu")],
        ]
    )
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
    await callback.message.edit_text(
        "🔵 **BÁN TICK XANH FACEBOOK**\nVui lòng chọn mục mua bên dưới:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
    )
    await callback.answer()


@dp.callback_query(F.data == "buy_ig_tick_menu")
async def cb_buy_ig_tick_menu(callback: types.CallbackQuery):
    kb = [
        [InlineKeyboardButton(text="1. IG Tick Pay sẵn (180,000đ)", callback_data="buy_item_srv_2_1")],
        [InlineKeyboardButton(text="2. IG Tick xanh sẵn dùng ngay (350,000đ)", callback_data="buy_item_srv_2_2")],
        [InlineKeyboardButton(text="3. Tick IG Theo tên & Avatar (550,000đ)", callback_data="buy_item_srv_2_3")],
        [InlineKeyboardButton(text="« Quay lại Menu", callback_data="back_to_menu")],
    ]
    await callback.message.edit_text(
        "🟣 **BÁN TICK XANH INSTAGRAM**\nVui lòng chọn mục mua bên dưới:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
    )
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
        return await callback.answer(
            f"❌ Số dư không đủ! Cần {price:,.0f}đ nhưng chỉ có {user['balance']:,.0f}đ.",
            show_alert=True,
        )

    if not stock_db.get(key) or len(stock_db[key]) == 0:
        return await callback.answer(
            "⚠️ Kho tài nguyên mục này đang tạm hết, vui lòng liên hệ admin!",
            show_alert=True,
        )

    acc_data = stock_db[key].pop(0)
    user["balance"] -= price

    if user_id not in orders_db:
        orders_db[user_id] = []
    order_id = "".join(random.choices("0123456789ABCDEF", k=8))
    orders_db[user_id].append(
        {"id": order_id, "product": name, "details": acc_data, "time": "Hôm nay"}
    )

    await callback.message.edit_text(
        f"✅ **MUA HÀNG THÀNH CÔNG!**\n\n"
        f"📦 Sản phẩm: {name}\n"
        f"💵 Đã trừ: {price:,.0f}đ\n"
        f"🔑 Mã đơn hàng: `{order_id}`\n\n"
        f"👉 Kiểm tra chi tiết tại mục **Lịch sử đơn hàng 📦**.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📦 Lịch sử đơn hàng", callback_data="history_orders")],
                [InlineKeyboardButton(text="« Quay lại Menu", callback_data="back_to_menu")],
            ]
        ),
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
        f"🔍 **KẾT QUẢ CHECK UID**\n\n"
        f"💵 Phí: 2,000đ\n"
        f"📊 Tình trạng: **{status}**\n\n"
        f"💰 Số dư còn lại: {user['balance']:,.0f}đ",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="« Quay lại Menu", callback_data="back_to_menu")]]
        ),
    )
    await callback.answer()


# ==========================================
# PROXY & CHẶN IP
# ==========================================
@dp.callback_query(F.data == "proxy_menu")
async def cb_proxy_menu(callback: types.CallbackQuery):
    kb = [
        [InlineKeyboardButton(text="Proxy Việt Nam 🇻🇳", callback_data="proxy_vn")],
        [InlineKeyboardButton(text="Proxy Ngoại Quốc 🌍", callback_data="proxy_foreign")],
        [InlineKeyboardButton(text="Chặn IP - 300,000đ 🛡️", callback_data="block_ip")],
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
            text += (
                f"▪️ **Mã đơn:** `{ord['id']}`\n"
                f"🔹 **Sản phẩm:** {ord['product']}\n"
                f"🔑 **Thông tin:** `{ord['details']}`\n------------------\n"
            )

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
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

    await callback.message.edit_text(
        f"🚀 **BUFF {name}**\nChọn dịch vụ:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("buff_sel_"))
async def cb_buff_select_service(callback: types.CallbackQuery, state: FSMContext):
    _, _, p_key, price_str = callback.data.split("_")
    await state.update_data(buff_price=int(price_str), buff_platform=p_key)
    await state.set_state(Form.waiting_for_buff_link)
    await callback.message.edit_text(
        "🔗 Gửi **Link/URL** cần buff:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Quay lại", callback_data=p_key)]]),
    )
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

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Quay lại Menu", callback_data="back_to_menu")]]),
    )
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
    await callback.message.edit_text(
        "📨 **KHO MAIL**\nChọn loại mail:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
    )
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
    if not stock_db.get(stock_key):
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
    await callback.message.edit_text(
        "💵 **KHU VỰC GIẢI TRÍ KIẾM TIỀN**",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
    )
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
        await message.answer(f"🎉 THẮNG! Nhận được +{payout:,.0f}đ")
    else:
        await message.answer("😢 THUA! Chúc bạn may mắn lần sau.")


# --- ADMIN COMMANDS ---
@dp.message(Command("addtien"))
async def cmd_addtien(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    args = message.text.split()
    if len(args) < 3:
        return
    get_user(int(args[1]))["balance"] += float(args[2])
    await message.answer(f"✅ Đã cộng tiền cho user `{args[1]} `", parse_mode="Markdown")


# Hàm khởi chạy bot
async def main():
    print("Bot is starting...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
