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
    KeyboardButton,
    ReplyKeyboardMarkup,
)

# Cấu hình thông tin bot và Admin
TOKEN = "8335633183:AAHR1eKsNI6e6FQc345ymAIM-vbRPxNtGXM"
ADMIN_ID = (
    8985238179
)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- DATABASE TẠM THỜI TRONG BỘ NHỚ ---
# Lưu thông tin user: {user_id: {"balance": float, "total_topup": float, "referred_by": int, "invited_count": int}}
users_db = {}
# Kho tài nguyên tài khoản: { "srv_1_1": [acc1, acc2...], "srv_1_2": [...], ... "mail_new": [...], "mail_month": [...], "mail_year": [...] }
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
# Lịch sử đơn hàng: {user_id: [ {id, product, details, time}, ... ]}
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


# Bộ nhớ tạm lưu state tùy chỉnh cho từng user
user_temp_data = {}


def get_user(user_id: int):
    if user_id not in users_db:
        users_db[user_id] = {
            "balance": 0.0,
            "total_topup": 0.0,
            "referred_by": None,
            "invited_count": 0,
        }
    return users_db[user_id]


# --- BÀN PHÍM CHÍNH (MENU) ---
def main_menu_kb(user_id):
    keyboard = [
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
                text="5. Nạp Tiền Tự Động 💳", callback_data="topup_menu"
            ),
            InlineKeyboardButton(
                text="6. Lịch sử đơn hàng 📦", callback_data="history_orders"
            ),
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
            InlineKeyboardButton(text="11. Cookie 🍪", callback_data="cookie_menu"),
            InlineKeyboardButton(text="12. Top Nạp 🏆", callback_data="top_recharge"),
        ],
        [
            InlineKeyboardButton(text="13. Mua Mail 📨", callback_data="buy_mail_menu"),
            InlineKeyboardButton(
                text="14. Kick thiết bị 🦿", callback_data="kick_device_menu"
            ),
        ],
        [
            InlineKeyboardButton(
                text="Kiếm tiền 💵", callback_data="make_money_menu"
            )
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

    # Xử lý giới thiệu bạn bè (nếu có ref_id trong lệnh start)
    if len(args) > 1 and args[1].isdigit():
        ref_id = int(args[1])
        if ref_id != user_id and user["referred_by"] is None:
            ref_user = get_user(ref_id)
            user["referred_by"] = ref_id
            ref_user["invited_count"] += 1
            ref_user["balance"] += 3000.0  # Thưởng 3000đ khi mời thành công
            try:
                await bot.send_message(
                    ref_id,
                    f"🎉 Chúc mừng! Bạn vừa mời thành công 1 người dùng mới tham gia bot và nhận được +3,000đ vào số dư.",
                )
            except:
                pass

    welcome_text = (
        f"👋 Chào mừng **{message.from_user.full_name}** đến với Source Media 88 Agency!\n\n"
        f"💰 Số dư hiện tại của bạn: **{user['balance']:,.0f}đ**\n"
        f"Vui lòng chọn dịch vụ bên dưới:"
    )
    await message.answer(
        welcome_text, parse_mode="Markdown", reply_markup=main_menu_kb(user_id)
    )


# Nút Quay lại Menu
@dp.callback_query(F.data == "back_to_menu")
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
# 1 & 2. MUA TICK XANH FB & IG (CÓ HIỆN GIÁ VÀ HƯỚNG DẪN CHECK LỊCH SỬ)
# ==========================================
@dp.callback_query(F.data == "buy_fb_tick_menu")
async def cb_buy_fb_tick_menu(callback: types.CallbackQuery):
    kb = [
        [
            InlineKeyboardButton(
                text="1. FB Tick Pay sẵn (150,000đ)",
                callback_data="buy_item_srv_1_1",
            )
        ],
        [
            InlineKeyboardButton(
                text="2. FB Tick xanh sẵn dùng ngay (300,000đ)",
                callback_data="buy_item_srv_1_2",
            )
        ],
        [
            InlineKeyboardButton(
                text="3. Tick FB Theo tên & Avatar (500,000đ)",
                callback_data="buy_item_srv_1_3",
            )
        ],
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
        [
            InlineKeyboardButton(
                text="1. IG Tick Pay sẵn (180,000đ)",
                callback_data="buy_item_srv_2_1",
            )
        ],
        [
            InlineKeyboardButton(
                text="2. IG Tick xanh sẵn dùng ngay (350,000đ)",
                callback_data="buy_item_srv_2_2",
            )
        ],
        [
            InlineKeyboardButton(
                text="3. Tick IG Theo tên & Avatar (550,000đ)",
                callback_data="buy_item_srv_2_3",
            )
        ],
        [InlineKeyboardButton(text="« Quay lại Menu", callback_data="back_to_menu")],
    ]
    await callback.message.edit_text(
        "🟣 **BÁN TICK XANH INSTAGRAM**\nVui lòng chọn mục mua bên dưới:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
    )
    await callback.answer()


# Xử lý mua tài khoản chung (FB & IG Tick)
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
            f"❌ Số dư không đủ! Bạn cần {price:,.0f}đ nhưng chỉ có {user['balance']:,.0f}đ. Vui lòng nạp thêm!",
            show_alert=True,
        )

    # Kiểm tra kho
    if not stock_db.get(key) or len(stock_db[key]) == 0:
        return await callback.answer(
            "⚠️ Kho tài nguyên mục này đang tạm hết, vui lòng liên hệ admin!",
            show_alert=True,
        )

    # Lấy tài khoản từ kho
    acc_data = stock_db[key].pop(0)
    user["balance"] -= price

    # Lưu vào lịch sử đơn hàng
    if user_id not in orders_db:
        orders_db[user_id] = []
    order_id = "".join(random.choices("0123456789ABCDEF", k=8))
    orders_db[user_id].append(
        {
            "id": order_id,
            "product": name,
            "details": acc_data,
            "time": "Hôm nay",
        }
    )

    await callback.message.edit_text(
        f"✅ **MUA HÀNG THÀNH CÔNG!**\n\n"
        f"📦 Sản phẩm: {name}\n"
        f"💵 Đã trừ: {price:,.0f}đ\n"
        f"🔑 Mã đơn hàng: `{order_id}`\n\n"
        f"👉 **HƯỚNG DẪN:** Vui lòng vào mục **Lịch sử đơn hàng 📦** ở menu chính để check Tài khoản, Mật khẩu, Mã 2FA và Cookie chi tiết!",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📦 Lịch sử đơn hàng", callback_data="history_orders"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="« Quay lại Menu", callback_data="back_to_menu"
                    )
                ],
            ]
        ),
    )
    await callback.answer("Mua thành công!")


# ==========================================
# 3. CHECK UID
# ==========================================
@dp.callback_query(F.data == "check_uid")
async def cb_check_uid(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    price = 2000

    if user["balance"] < price:
        return await callback.answer(
            "❌ Số dư của bạn không đủ 2,000đ để Check UID!", show_alert=True
        )

    user["balance"] -= price
    status = random.choice(["Live ✅", "Die 🚫"])
    await callback.message.edit_text(
        f"🔍 **KẾT QUẢ CHECK UID**\n\n"
        f"💵 Phí dịch vụ: 2,000đ (Đã trừ)\n"
        f"📊 Tình trạng: **{status}**\n\n"
        f"💰 Số dư còn lại: {user['balance']:,.0f}đ",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="« Quay lại Menu", callback_data="back_to_menu"
                    )
                ]
            ]
        ),
    )
    await callback.answer()


# ==========================================
# 4. PROXY (CÓ THÊM MỤC CHẶN IP)
# ==========================================
@dp.callback_query(F.data == "proxy_menu")
async def cb_proxy_menu(callback: types.CallbackQuery):
    kb = [
        [
            InlineKeyboardButton(
                text="Proxy Việt Nam 🇻🇳", callback_data="proxy_vn"
            )
        ],
        [
            InlineKeyboardButton(
                text="Proxy Ngoại Quốc 🌍", callback_data="proxy_foreign"
            )
        ],
        [
            InlineKeyboardButton(
                text="Chặn IP - Giá: 300,000đ 🛡️", callback_data="block_ip"
            )
        ],
        [InlineKeyboardButton(text="« Quay lại Menu", callback_data="back_to_menu")],
    ]
    await callback.message.edit_text(
        "🌐 **HỆ THỐNG PROXY & BẢO MẬT IP**\nVui lòng chọn dịch vụ:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
    )
    await callback.answer()


@dp.callback_query(F.data == "proxy_vn")
async def cb_proxy_vn(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🌐 **Proxy Việt Nam**: Đang hoạt động ổn định, tốc độ cao.\nGiá: 50,000đ/tháng.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="« Quay lại", callback_data="proxy_menu"
                    )
                ]
            ]
        ),
    )


@dp.callback_query(F.data == "proxy_foreign")
async def cb_proxy_foreign(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🌍 **Proxy Ngoại Quốc**: US/UK sạch sẽ, ẩn danh tuyệt đối.\nGiá: 80,000đ/tháng.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="« Quay lại", callback_data="proxy_menu"
                    )
                ]
            ]
        ),
    )


@dp.callback_query(F.data == "block_ip")
async def cb_block_ip(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(Form.waiting_for_ip_address)
    await callback.message.edit_text(
        "🛡️ **DỊCH VỤ CHẶN IP**\n"
        "Mô tả: Chặn IP giúp máy ổn định và không bị nhảy IP đồng thời có thể giúp bạn chặn IP mà bạn muốn kick.\n"
        "Giá: **300,000đ**\n\n"
        "Vui lòng nhập địa chỉ IP của bạn vào khung chat để tiếp tục:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="« Quay lại", callback_data="proxy_menu"
                    )
                ]
            ]
        ),
    )
    await callback.answer()


@dp.message(Form.waiting_for_ip_address)
async def process_ip_address(message: types.Message, state: FSMContext):
    ip_text = message.text.strip()
    user_id = message.from_user.id
    user = get_user(user_id)
    price = 300000

    if user["balance"] < price:
        return await message.answer(
            f"❌ Số dư không đủ! Bạn cần {price:,.0f}đ nhưng chỉ có {user['balance']:,.0f}đ. Vui lòng nạp thêm để sử dụng!"
        )

    user["balance"] -= price
    await state.clear()

    await message.answer(
        f"IP: {ip_text}\n"
        f"Tình trạng: Thành Công ✅\n\n"
        f"💰 Số dư còn lại: {user['balance']:,.0f}đ",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="« Quay lại Menu", callback_data="back_to_menu"
                    )
                ]
            ]
        ),
    )


# ==========================================
# 5. NẠP TIỀN TỰ ĐỘNG QR
# ==========================================
@dp.callback_query(F.data == "topup_menu")
async def cb_topup_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(Form.waiting_for_topup_amount)
    await callback.message.edit_text(
        "💳 **NẠP TIỀN TỰ ĐỘNG QUA QR**\n\n"
        "Vui lòng nhập số tiền bạn muốn nạp (Ví dụ: `50000`):",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="« Quay lại Menu", callback_data="back_to_menu"
                    )
                ]
            ]
        ),
    )
    await callback.answer()


@dp.message(Form.waiting_for_topup_amount)
async def process_topup_amount(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("Vui lòng nhập một con số hợp lệ!")

    amount = int(message.text)
    user_id = message.from_user.id
    await state.clear()

    # Gửi QR giả lập hoặc thông tin chuyển khoản kèm nút duyệt cho admin
    qr_caption = (
        f"🧾 **YÊU CẦU NẠP TIỀN**\n\n"
        f"👤 Khách: {message.from_user.full_name} (`{user_id}`)\n"
        f"💵 Số tiền: **{amount:,.0f}đ**\n"
        f"Nội dung chuyển khoản: `NAP {user_id}`\n\n"
        f"Admin vui lòng xác nhận:"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Duyệt", callback_data=f"approve_topup_{user_id}_{amount}"
                ),
                InlineKeyboardButton(text="❌ Từ chối", callback_data="reject_topup"),
            ]
        ]
    )

    try:
        await bot.send_message(
            ADMIN_ID, qr_caption, parse_mode="Markdown", reply_markup=kb
        )
    except:
        pass

    await message.answer(
        f"⏳ Đã tạo lệnh nạp **{amount:,.0f}đ**. Vui lòng chuyển khoản theo cú pháp:\n\n"
        f"STK: `190xxxxxx` (Techcombank)\n"
        f"Nội dung: `NAP {user_id}`\n\n"
        f"Hệ thống sẽ tự động cộng tiền sau 1-2 phút khi nhận được thanh toán.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="« Quay lại Menu", callback_data="back_to_menu"
                    )
                ]
            ]
        ),
    )


@dp.callback_query(F.data.startswith("approve_topup_"))
async def cb_approve_topup(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    target_user_id = int(parts[2])
    amount = float(parts[3])

    target_user = get_user(target_user_id)
    target_user["balance"] += amount
    target_user["total_topup"] += amount

    await callback.message.edit_text(
        callback.message.text
        + f"\n\n✅ **ĐÃ DUYỆT THÀNH CÔNG +{amount:,.0f}đ** cho user `{target_user_id}`",
        parse_mode="Markdown",
    )
    try:
        await bot.send_message(
            target_user_id,
            f"🎉 Tài khoản của bạn đã được cộng **{amount:,.0f}đ** từ giao dịch nạp tiền!",
            parse_mode="Markdown",
        )
    except:
        pass
    await callback.answer("Đã duyệt nạp tiền thành công!")


@dp.callback_query(F.data == "reject_topup")
async def cb_reject_topup(callback: types.CallbackQuery):
    await callback.message.edit_text(
        callback.message.text + "\n\n❌ **ĐÃ TỪ CHỐI GIAO DỊCH NẠP TIỀN**",
        parse_mode="Markdown",
    )
    await callback.answer("Đã từ chối!")


# ==========================================
# 6. LỊCH SỬ ĐƠN HÀNG
# ==========================================
@dp.callback_query(F.data == "history_orders")
async def cb_history_orders(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_orders = orders_db.get(user_id, [])

    if not user_orders:
        text = "📦 Bạn chưa có đơn hàng nào trong lịch sử."
    else:
        text = "📦 **LỊCH SỬ ĐƠN HÀNG CỦA BẠN**:\n\n"
        for ord in user_orders:
            text += (
                f"▪️ **Mã đơn:** `{ord['id']}`\n"
                f"🔹 **Sản phẩm:** {ord['product']}\n"
                f"🔑 **Thông tin/Acc:** `{ord['details']}`\n"
                f"----------------------------------\n"
            )

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="« Quay lại Menu", callback_data="back_to_menu"
                    )
                ]
            ]
        ),
    )
    await callback.answer()


# ==========================================
# 7, 8, 9. BUFF TIKTOK, FACEBOOK, INSTAGRAM
# ==========================================
@dp.callback_query(F.data.in_(["buff_tk", "buff_fb", "buff_ig"]))
async def cb_buff_menu(callback: types.CallbackQuery, state: FSMContext):
    platform_map = {
        "buff_tk": (
            "TikTok 🎵",
            [
                ("Tăng Tim ♥️ (15đ)", 15),
                ("Tăng Followers 🤖 (80đ)", 80),
                ("Tăng chia sẻ 🔁 (35đ)", 35),
            ],
        ),
        "buff_fb": (
            "Facebook 💙",
            [
                ("Tăng Followers 🤖 (10đ)", 10),
                ("Tăng Tim ♥️ (11đ)", 11),
                ("Tăng chia sẻ 🔁 (35đ)", 35),
            ],
        ),
        "buff_ig": (
            "Instagram 🎀",
            [
                ("Tăng Followers 🤖 (13đ)", 13),
                ("Tăng Tim ♥️ (11đ)", 11),
                ("Tăng chia sẻ 🔁 (35đ)", 35),
            ],
        ),
    }

    p_key = callback.data
    name, options = platform_map[p_key]

    kb = []
    for opt_name, price in options:
        kb.append(
            [
                InlineKeyboardButton(
                    text=opt_name, callback_data=f"buff_sel_{p_key}_{price}"
                )
            ]
        )
    kb.append([InlineKeyboardButton(text="« Quay lại Menu", callback_data="back_to_menu")])

    await callback.message.edit_text(
        f"🚀 **HỆ THỐNG BUFF {name}**\nVui lòng chọn dịch vụ:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("buff_sel_"))
async def cb_buff_select_service(callback: types.CallbackQuery, state: FSMContext):
    _, _, p_key, price_str = callback.data.split("_")
    price = int(price_str)

    await state.update_data(buff_price=price, buff_platform=p_key)
    await state.set_state(Form.waiting_for_buff_link)

    await callback.message.edit_text(
        "🔗 Vui lòng gửi **Link/URL** cần buff vào khung chat:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="« Quay lại", callback_data=p_key
                    )
                ]
            ]
        ),
    )
    await callback.answer()


@dp.message(Form.waiting_for_buff_link)
async def process_buff_link(message: types.Message, state: FSMContext):
    await state.update_data(buff_link=message.text.strip())
    await state.set_state(Form.waiting_for_buff_qty)
    await message.answer("🔢 Nhập **số lượng** cần buff (Ví dụ: `1000`):")


@dp.message(Form.waiting_for_buff_qty)
async def process_buff_qty(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("Vui lòng nhập một số lượng hợp lệ (số nguyên)!")

    qty = int(message.text)
    data = await state.get_data()
    price = data["buff_price"]
    link = data["buff_link"]
    platform = data["buff_platform"]

    total_cost = qty * price
    user_id = message.from_user.id
    user = get_user(user_id)

    if user["balance"] < total_cost:
        await state.clear()
        return await message.answer(
            f"❌ Số dư không đủ! Tổng tiền là {total_cost:,.0f}đ nhưng bạn chỉ có {user['balance']:,.0f}đ. Vui lòng nạp thêm!"
        )

    user["balance"] -= total_cost
    await state.clear()

    order_id = "".join(random.choices("0123456789ABCDEF", k=8))

    # Gửi thông báo về cho Admin
    admin_text = (
        f"🚨 **CÓ ĐƠN BUFF MỚI!**\n\n"
        f"👤 Khách: {message.from_user.full_name} (`{user_id}`)\n"
        f"📱 Nền tảng: {platform.upper()}\n"
        f"🔗 Link: {link}\n"
        f"📊 Số lượng: {qty}\n"
        f"💵 Tổng tiền: {total_cost:,.0f}đ\n"
        f"🔖 Mã đơn: `{order_id}`"
    )
    try:
        await bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown")
    except:
        pass

    await message.answer(
        f"✅ **ĐẶT ĐƠN BUFF THÀNH CÔNG!**\n\n"
        f"🔗 Link: {link}\n"
        f"📊 Số lượng: {qty}\n"
        f"💵 Đã trừ: {total_cost:,.0f}đ\n"
        f"🔖 Mã đơn: `{order_id}`\n"
        f"Tình trạng: Đang xử lý hệ thống 🔄",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="« Quay lại Menu", callback_data="back_to_menu"
                    )
                ]
            ]
        ),
    )


# ==========================================
# 10, 11, 12. SỬA GIẤY TỜ, COOKIE, TOP NẠP
# ==========================================
@dp.callback_query(F.data == "fix_docs")
async def cb_fix_docs(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📄 **DỊCH VỤ SỬA GIẤY TỜ**\nLiên hệ admin trực tiếp qua @miutea88 để làm việc.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="« Quay lại Menu", callback_data="back_to_menu"
                    )
                ]
            ]
        ),
    )
    await callback.answer()


@dp.callback_query(F.data == "cookie_menu")
async def cb_cookie_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🍪 **KHO COOKIE & PROXY CHẤT LƯỢNG**\nĐã sẵn sàng kho nguyên liệu sạch.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="« Quay lại Menu", callback_data="back_to_menu"
                    )
                ]
            ]
        ),
    )
    await callback.answer()


@dp.callback_query(F.data == "top_recharge")
async def cb_top_recharge(callback: types.CallbackQuery):
    sorted_users = sorted(
        users_db.items(), key=lambda x: x[1]["total_topup"], reverse=True
    )[:10]

    text = "🏆 **TOP 10 TÀI KHOẢN NẠP NHIỀU NHẤT**\n\n"
    if not sorted_users or all(u[1]["total_topup"] == 0 for u in sorted_users):
        text += "Chưa có dữ liệu nạp tiền."
    else:
        for idx, (uid, u_data) in enumerate(sorted_users, 1):
            if u_data["total_topup"] <= 0:
                continue
            badge = (
                "🥇" if idx == 1 else ("🥈" if idx == 2 else ("🥉" if idx == 3 else f"#{idx}"))
            )
            text += f"{badge} User ID `{uid}` — Tổng nạp: **{u_data['total_topup']:,.0f}đ**\n"

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="« Quay lại Menu", callback_data="back_to_menu"
                    )
                ]
            ]
        ),
    )
    await callback.answer()


# ==========================================
# 13. MUA MAIL 📨
# ==========================================
@dp.callback_query(F.data == "buy_mail_menu")
async def cb_buy_mail_menu(callback: types.CallbackQuery):
    kb = [
        [
            InlineKeyboardButton(
                text="Mail New (Reg) - 25,000đ", callback_data="buy_mail_new"
            )
        ],
        [
            InlineKeyboardButton(
                text="Mail Tháng (Ổn) - 50,000đ", callback_data="buy_mail_month"
            )
        ],
        [
            InlineKeyboardButton(
                text="Mail Năm (Cứng) - 115,000đ", callback_data="buy_mail_year"
            )
        ],
        [InlineKeyboardButton(text="« Quay lại Menu", callback_data="back_to_menu")],
    ]
    await callback.message.edit_text(
        "📨 **KHO MUA MAIL CHẤT LƯỢNG**\nVui lòng chọn loại mail bạn cần mua:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
    )
    await callback.answer()


@dp.callback_query(
    F.data.in_(["buy_mail_new", "buy_mail_month", "buy_mail_year"])
)
async def cb_buy_mail_process(callback: types.CallbackQuery):
    mail_types = {
        "buy_mail_new": (
            "Mail New (Reg)",
            25000,
            "Mail mới tạo từ 1 - 7 ngày trắng thông tin.",
            "mail_new",
        ),
        "buy_mail_month": (
            "Mail Tháng (Ổn)",
            50000,
            "Mail tạo từ 1 - 11 tháng và trắng thông tin.",
            "mail_month",
        ),
        "buy_mail_year": (
            "Mail Năm (Cứng)",
            115000,
            "Mail tạo từ 12 tháng - vài năm cổ trắng thông tin",
            "mail_year",
        ),
    }

    name, price, desc, stock_key = mail_types[callback.data]
    user_id = callback.from_user.id
    user = get_user(user_id)

    if user["balance"] < price:
        return await callback.answer(
            f"❌ Số dư không đủ! Bạn cần {price:,.0f}đ nhưng chỉ có {user['balance']:,.0f}đ. Vui lòng nạp thêm!",
            show_alert=True,
        )

    if not stock_db.get(stock_key) or len(stock_db[stock_key]) == 0:
        return await callback.answer(
            "⚠️ Kho mail mục này đang tạm hết, vui lòng liên hệ admin!",
            show_alert=True,
        )

    acc_data = stock_db[stock_key].pop(0)
    user["balance"] -= price

    if user_id not in orders_db:
        orders_db[user_id] = []
    order_id = "".join(random.choices("0123456789ABCDEF", k=8))
    orders_db[user_id].append(
        {
            "id": order_id,
            "product": name,
            "details": acc_data,
            "time": "Hôm nay",
        }
    )

    await callback.message.edit_text(
        f"✅ **MUA MAIL THÀNH CÔNG!**\n\n"
        f"📦 Loại: {name}\n"
        f"📝 Mô tả: {desc}\n"
        f"🔑 Định dạng Tài khoản | Mật khẩu: `{acc_data}`\n"
        f"💵 Đã trừ: {price:,.0f}đ\n"
        f"🔖 Mã đơn: `{order_id}`",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="« Quay lại Menu", callback_data="back_to_menu"
                    )
                ]
            ]
        ),
    )
    await callback.answer("Mua mail thành công!")


# ==========================================
# 14. KICK THIẾT BỊ 🦿
# ==========================================
KICK_PLATFORMS = {
    1: ("Facebook", 270000),
    2: ("Instagram", 250000),
    3: ("Tiktok", 200000),
    4: ("Threads", 230000),
    5: ("Spotify", 250000),
    6: ("Gmail", 550000),
    7: ("Youtube", 350000),
    8: ("Whatapps", 550000),
    9: ("Telegram", 150000),
    10: ("Zalo", 400000),
}


@dp.callback_query(F.data == "kick_device_menu")
async def cb_kick_device_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(Form.waiting_for_kick_platform_id)
    text = (
        "🦿 **DỊCH VỤ KICK THIẾT BỊ**\n"
        "Bot sẽ giúp kick All thiết bị đang đăng nhập trong nick cần kick.\n\n"
        "Danh sách nền tảng:\n"
    )
    for idx, (p_name, p_price) in KICK_PLATFORMS.items():
        text += f"{idx}. {p_name} — Giá: **{p_price:,.0f}đ**\n"

    text += "\nVui lòng nhập **số thứ tự** của nền tảng bạn cần kick:"
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="« Quay lại Menu", callback_data="back_to_menu"
                    )
                ]
            ]
        ),
    )
    await callback.answer()


@dp.message(Form.waiting_for_kick_platform_id)
async def process_kick_platform_choice(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("Vui lòng nhập số thứ tự hợp lệ (từ 1 đến 10)!")

    choice = int(message.text)
    if choice not in KICK_PLATFORMS:
        return await message.answer(
            "❌ Số thứ tự không nằm trong danh sách! Vui lòng nhập từ 1 đến 10:"
        )

    p_name, p_price = KICK_PLATFORMS[choice]
    await state.update_data(kick_platform=p_name, kick_price=p_price)
    await state.set_state(Form.waiting_for_kick_credentials)

    await message.answer(
        f"🎯 Bạn đã chọn: **{p_name}**\n"
        f"💵 Giá dịch vụ: **{p_price:,.0f}đ**\n\n"
        f"Vui lòng nhập **Tài khoản | Mật khẩu** của nền tảng cần kick vào khung chat:",
        parse_mode="Markdown",
    )


@dp.message(Form.waiting_for_kick_credentials)
async def process_kick_credentials(message: types.Message, state: FSMContext):
    creds = message.text.strip()
    data = await state.get_data()
    p_name = data["kick_platform"]
    price = data["kick_price"]

    user_id = message.from_user.id
    user = get_user(user_id)

    if user["balance"] < price:
        await state.clear()
        return await message.answer(
            f"❌ Số dư không đủ! Dịch vụ Kick {p_name} có giá {price:,.0f}đ nhưng bạn chỉ có {user['balance']:,.0f}đ. Vui lòng nạp thêm để sử dụng!"
        )

    user["balance"] -= price
    await state.clear()

    await message.answer(
        f"✅ **KICK THIẾT BỊ THÀNH CÔNG!**\n\n"
        f"📱 Nền tảng: {p_name}\n"
        f"🔑 Tài khoản: `{creds}`\n"
        f"💵 Đã trừ: {price:,.0f}đ\n"
        f"📊 Tình trạng: Đã đăng xuất toàn bộ thiết bị khác thành công ✅\n\n"
        f"💰 Số dư còn lại: {user['balance']:,.0f}đ",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="« Quay lại Menu", callback_data="back_to_menu"
                    )
                ]
            ]
        ),
    )


# ==========================================
# 15. KIẾM TIỀN 💵 (TRÒ CHƠI TÀI XỈU, BOWLING & GIỚI THIỆU BOT)
# ==========================================
@dp.callback_query(F.data == "make_money_menu")
async def cb_make_money_menu(callback: types.CallbackQuery):
    kb = [
        [InlineKeyboardButton(text="Trò chơi 🍀", callback_data="games_menu")],
        [
            InlineKeyboardButton(
                text="Giới thiệu bot 👾", callback_data="invite_friends_menu"
            )
        ],
        [InlineKeyboardButton(text="« Quay lại Menu", callback_data="back_to_menu")],
    ]
    await callback.message.edit_text(
        "💵 **KHU VỰC KIẾM TIỀN & GIẢI TRÍ**\nVui lòng chọn:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
    )
    await callback.answer()


@dp.callback_query(F.data == "games_menu")
async def cb_games_menu(callback: types.CallbackQuery):
    kb = [
        [InlineKeyboardButton(text="🎲 Tài Xỉu 🎲", callback_data="game_taixiu")],
        [InlineKeyboardButton(text="🎳 Bowling 🎳", callback_data="game_bowling")],
        [
            InlineKeyboardButton(
                text="« Quay lại", callback_data="make_money_menu"
            )
        ],
    ]
    await callback.message.edit_text(
        "🍀 **KHO TRÒ CHƠI GIẢI TRÍ**\nChọn trò chơi bạn muốn tham gia:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
    )
    await callback.answer()


# Hướng dẫn Tài Xỉu
@dp.callback_query(F.data == "game_taixiu")
async def cb_game_taixiu(callback: types.CallbackQuery):
    desc = (
        "🎲 **HƯỚNG DẪN CHƠI TÀI XỈU** 🎲\n\n"
        "• **Tài:** Tổng 3 xúc xắc cộng lại được từ **11 - 18 điểm**\n"
        "• **Xỉu:** Tổng 3 xúc xắc cộng lại được từ **3 - 10 điểm**\n\n"
        "📌 **Lệnh cược (Tối thiểu 20,000đ):**\n"
        "- Đặt Tài: `/Tai (số tiền)` (Ví dụ: `/Tai 100000`)\n"
        "- Đặt Xỉu: `/Xiu (số tiền)` (Ví dụ: `/Xiu 100000`)\n\n"
        "💎 Thắng nhận thưởng **x1.95** số tiền cược!\n"
        "💳 Tiền cược sẽ được trừ thẳng vào số dư của bạn.\n\n"
        "💸 **Lệnh rút tiền:** `/rut (số tiền)` (Tối thiểu 150,000đ và phải mời đủ 6 bạn)"
    )
    await callback.message.edit_text(
        desc,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="« Quay lại trò chơi", callback_data="games_menu"
                    )
                ]
            ]
        ),
    )
    await callback.answer()


# Hướng dẫn Bowling
@dp.callback_query(F.data == "game_bowling")
async def cb_game_bowling(callback: types.CallbackQuery):
    desc = (
        "🎳 **HƯỚNG DẪN CHƠI BOWLING** 🎳\n\n"
        "Bowling 🎳 là trò chơi tung bóng lăn ăn điểm.\n"
        "• **Chẵn:** Tổng số chai hạ gục là: **2, 4, 6**\n"
        "• **Lẻ:** Tổng số chai hạ gục là: **1, 3, 5**\n\n"
        "📌 **Lệnh cược (Tối thiểu 20,000đ):**\n"
        "- Đặt Chẵn: `/Chan (số tiền)` (Ví dụ: `/Chan 50000`)\n"
        "- Đặt Lẻ: `/Le (số tiền)` (Ví dụ: `/Le 50000`)\n\n"
        "💎 Thắng nhận thưởng **x1.85** số tiền cược!\n"
        "💳 Tiền cược sẽ được trừ thẳng vào số dư của bạn.\n\n"
        "💸 **Lệnh rút tiền:** `/rut (số tiền)` (Tối thiểu 150,000đ và phải mời đủ 6 bạn)"
    )
    await callback.message.edit_text(
        desc,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="« Quay lại trò chơi", callback_data="games_menu"
                    )
                ]
            ]
        ),
    )
    await callback.answer()


# --- LỆNH ĐẶT CƯỢC TÀI XỈU (/Tai & /Xiu) ---
@dp.message(Command(commands=["Tai", "tai"]))
async def cmd_bet_tai(message: types.Message):
    await process_dice_bet(message, "TAI")


@dp.message(Command(commands=["Xiu", "xiu"]))
async def cmd_bet_xiu(message: types.Message):
    await process_dice_bet(message, "XIU")


async def process_dice_bet(message: types.Message, choice: str):
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        return await message.answer(
            "❌ Sai cú pháp! Vui lòng dùng: `/Tai (số tiền)` hoặc `/Xiu (số tiền)` (VD: `/Tai 50000`)"
        )

    amount = int(args[1])
    if amount < 20000:
        return await message.answer(
            "⚠️ Mức cược tối thiểu là **20,000đ**!", parse_mode="Markdown"
        )

    user_id = message.from_user.id
    user = get_user(user_id)

    if user["balance"] < amount:
        return await message.answer(
            f"❌ Số dư không đủ! Bạn muốn cược {amount:,.0f}đ nhưng chỉ có {user['balance']:,.0f}đ trong tài khoản."
        )

    user["balance"] -= amount

    # Thông báo cho admin nếu cược to > 30,000đ
    if amount > 30000:
        try:
            await bot.send_message(
                ADMIN_ID,
                f"🚨 **CÓ KHÁCH CƯỢC TO TÀI XỈU!**\n"
                f"👤 Khách: {message.from_user.full_name} (`{user_id}`)\n"
                f"🎯 Cửa: {choice}\n"
                f"💵 Số tiền cược: **{amount:,.0f}đ**",
                parse_mode="Markdown",
            )
        except:
            pass

    # Tung 3 xúc xắc bằng xúc xắc Telegram
    msg_dice1 = await message.answer_dice(emoji="🎲")
    v1 = msg_dice1.dice.value
    await asyncio.sleep(0.5)

    msg_dice2 = await message.answer_dice(emoji="🎲")
    v2 = msg_dice2.dice.value
    await asyncio.sleep(0.5)

    msg_dice3 = await message.answer_dice(emoji="🎲")
    v3 = msg_dice3.dice.value

    total_score = v1 + v2 + v3
    is_tai = 11 <= total_score <= 18
    result_str = "TÀI" if is_tai else "XỈU"

    win = (choice == "TAI" and is_tai) or (choice == "XIU" and not is_tai)

    result_text = (
        f"🎲 **KẾT QUẢ TÀI XỈU** 🎲\n\n"
        f"🎯 Bạn đặt: **{choice}** ({amount:,.0f}đ)\n"
        f"🎲 Xúc xắc: {v1} - {v2} - {v3} (Tổng: **{total_score} điểm** - **{result_str}**)\n\n"
    )

    if win:
        payout = amount * 1.95
        user["balance"] += payout
        result_text += f"🎉 **THẮNG!** Bạn nhận được **+{payout:,.0f}đ** (x1.95)"
    else:
        result_text += f"😢 **THUA!** Chúc bạn may mắn lần sau."

    result_text += f"\n💰 Số dư hiện tại: {user['balance']:,.0f}đ"
    await message.answer(result_text, parse_mode="Markdown")


# --- LỆNH ĐẶT CƯỢC BOWLING (/Chan & /Le) ---
@dp.message(Command(commands=["Chan", "chan"]))
async def cmd_bet_chan(message: types.Message):
    await process_bowling_bet(message, "CHAN")


@dp.message(Command(commands=["Le", "le"]))
async def cmd_bet_le(message: types.Message):
    await process_bowling_bet(message, "LE")


async def process_bowling_bet(message: types.Message, choice: str):
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        return await message.answer(
            "❌ Sai cú pháp! Vui lòng dùng: `/Chan (số tiền)` hoặc `/Le (số tiền)` (VD: `/Chan 50000`)"
        )

    amount = int(args.get("args", args)[1] if isinstance(args, dict) else args[1])
    amount = int(args[1])
    if amount < 20000:
        return await message.answer(
            "⚠️ Mức cược tối thiểu là **20,000đ**!", parse_mode="Markdown"
        )

    user_id = message.from_user.id
    user = get_user(user_id)

    if user["balance"] < amount:
        return await message.answer(
            f"❌ Số dư không đủ! Bạn muốn cược {amount:,.0f}đ nhưng chỉ có {user['balance']:,.0f}đ."
        )

    user["balance"] -= amount

    if amount > 30000:
        try:
            await bot.send_message(
                ADMIN_ID,
                f"🚨 **CÓ KHÁCH CƯỢC TO BOWLING!**\n"
                f"👤 Khách: {message.from_user.full_name} (`{user_id}`)\n"
                f"🎳 Cửa: {choice}\n"
                f"💵 Số tiền cược: **{amount:,.0f}đ**",
                parse_mode="Markdown",
            )
        except:
            pass

    # Tung icon 🎳 (Bowling)
    msg_bowl = await message.answer_dice(emoji="🎳")
    # Giá trị value của bowling dice từ 1 đến 6 (số chai bị đổ)
    pins_down = msg_bowl.dice.value

    is_even = pins_down in [2, 4, 6]
    result_str = "CHẴN" if is_even else "LẺ"

    win = (choice == "CHAN" and is_even) or (choice == "LE" and not is_even)

    result_text = (
        f"🎳 **KẾT QUẢ BOWLING** 🎳\n\n"
        f"🎯 Bạn đặt: **{choice}** ({amount:,.0f}đ)\n"
        f"🎳 Số chai đổ: **{pins_down}** ({result_str})\n\n"
    )

    if win:
        payout = amount * 1.85
        user["balance"] += payout
        result_text += f"🎉 **THẮNG!** Bạn nhận được **+{payout:,.0f}đ** (x1.85)"
    else:
        result_text += f"😢 **THUA!** Chúc bạn may mắn lần sau."

    result_text += f"\n💰 Số dư hiện tại: {user['balance']:,.0f}đ"
    await message.answer(result_text, parse_mode="Markdown")


# ==========================================
# LỆNH RÚT TIỀN (/rut) & FSM NHẬP THÔNG TIN NGÂN HÀNG
# ==========================================
@dp.message(Command(commands=["rut", "Rut"]))
async def cmd_withdraw(message: types.Message, state: FSMContext):
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        return await message.answer(
            "❌ Sai cú pháp! Vui lòng dùng: `/rut (số tiền)` (Ví dụ: `/rut 200000`)"
        )

    amount = int(args[1])
    user_id = message.from_user.id
    user = get_user(user_id)

    if amount < 150000:
        return await message.answer(
            "⚠️ Yêu cầu rút tiền tối thiểu là **150,000đ**!", parse_mode="Markdown"
        )

    if user["invited_count"] < 6:
        return await message.answer(
            f"❌ Bạn chưa đủ điều kiện rút tiền!\n"
            f"📌 Yêu cầu: Phải mời đủ **6 bạn** tham gia bot.\n"
            f"📊 Số bạn bạn đã mời: **{user['invited_count']}/6**",
            parse_mode="Markdown",
        )

    if user["balance"] < amount:
        return await message.answer(
            f"❌ Số dư không đủ! Số dư hiện tại của bạn là {user['balance']:,.0f}đ."
        )

    await state.update_data(withdraw_amount=amount)
    await state.set_state(Form.waiting_for_bank_name)
    await message.answer(
        "🏦 **YÊU CẦU RÚT TIỀN**\nVui lòng nhập **Tên Ngân Hàng** của bạn (Ví dụ: Vietcombank, Techcombank,...):"
    )


@dp.message(Form.waiting_for_bank_name)
async def process_bank_name(message: types.Message, state: FSMContext):
    await state.update_data(bank_name=message.text.strip())
    await state.set_state(Form.waiting_for_bank_acc)
    await message.answer("🔢 Vui lòng nhập **Số tài khoản ngân hàng** của bạn:")


@dp.message(Form.waiting_for_bank_acc)
async def process_bank_acc(message: types.Message, state: FSMContext):
    await state.update_data(bank_acc=message.text.strip())
    await state.set_state(Form.waiting_for_bank_owner)
    await message.answer("👤 Vui lòng nhập **Họ và tên chủ tài khoản** (viết hoa không dấu):")


@dp.message(Form.waiting_for_bank_owner)
async def process_bank_owner(message: types.Message, state: FSMContext):
    owner_name = message.text.strip()
    data = await state.get_data()
    amount = data["withdraw_amount"]
    bank_name = data["bank_name"]
    bank_acc = data["bank_acc"]

    user_id = message.from_user.id
    user = get_user(user_id)

    if user["balance"] < amount:
        await state.clear()
        return await message.answer("❌ Số dư không đủ thực hiện giao dịch rút tiền.")

    user["balance"] -= amount
    await state.clear()

    # Gửi thông báo cho Admin
    admin_notice = (
        f"💸 **CÓ YÊU CẦU RÚT TIỀN MỚI!**\n\n"
        f"👤 Khách: {message.from_user.full_name} (`{user_id}`)\n"
        f"💵 Số tiền rút: **{amount:,.0f}đ**\n"
        f"🏦 Ngân hàng: {bank_name}\n"
        f"🔢 STK: `{bank_acc}`\n"
        f"🏷️ Chủ tài khoản: {owner_name}"
    )
    try:
        await bot.send_message(ADMIN_ID, admin_notice, parse_mode="Markdown")
    except:
        pass

    await message.answer(
        f"✅ **GỬI YÊU CẦU RÚT TIỀN THÀNH CÔNG!**\n\n"
        f"💵 Số tiền: {amount:,.0f}đ\n"
        f"🏦 Ngân hàng: {bank_name} - STK: `{bank_acc}`\n"
        f"🏷️ Chủ TK: {owner_name}\n\n"
        f"⏳ Yêu cầu của bạn đã được chuyển đến Admin, tiền sẽ về tài khoản sau ít phút.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="« Quay lại Menu", callback_data="back_to_menu"
                    )
                ]
            ]
        ),
    )


# ==========================================
# GIỚI THIỆU BOT 👾 & TOP MỜI BẠN BÈ
# ==========================================
@dp.callback_query(F.data == "invite_friends_menu")
async def cb_invite_friends_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)

    bot_info = await bot.get_me()
    bot_username = bot_info.username
    ref_link = f"https://t.me/{bot_username}?start={user_id}"

    # Sắp xếp top mời bạn bè nhiều nhất
    sorted_invite = sorted(
        users_db.items(), key=lambda x: x[1]["invited_count"], reverse=True
    )[:3]

    top_text = "\n\n🏆 **TOP MỜI BẠN BÈ NHIỀU NHẤT:**\n"
    if not sorted_invite or all(u[1]["invited_count"] == 0 for u in sorted_invite):
        top_text += "Chưa có dữ liệu."
    else:
        medals = ["🥇", "🥈", "🥉"]
        for idx, (uid, u_data) in enumerate(sorted_invite):
            if u_data["invited_count"] <= 0:
                continue
            medal = medals[idx] if idx < 3 else f"#{idx+1}"
            top_text += f"{medal} User ID `{uid}` — Mời được: **{u_data['invited_count']} người**\n"

    text = (
        f"👾 **GIỚI THIỆU BẠN BÈ - NHẬN THƯỞNG 3,000Đ**\n\n"
        f"🔗 Link giới thiệu của bạn:\n`{ref_link}`\n\n"
        f"👥 Số bạn bè bạn đã mời được: **{user['invited_count']} người**\n"
        f"💰 Thưởng nhận ngay: +3,000đ/1 lượt mời thành công."
        f"{top_text}"
    )

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="« Quay lại Menu", callback_data="back_to_menu"
                    )
                ]
            ]
        ),
    )
    await callback.answer()


# ==========================================
# LỆNH ADMIN QUẢN LÝ
# ==========================================
@dp.message(Command("addtien"))
async def cmd_addtien(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    args = message.text.split()
    if len(args) < 3:
        return await message.answer("Sai cú pháp! Dùng: `/addtien (id) (số_tiền)`")

    target_id = int(args[1])
    amount = float(args[2])
    target_user = get_user(target_id)
    target_user["balance"] += amount
    target_user["total_topup"] += amount
    await message.answer(
        f"✅ Đã cộng thành công {amount:,.0f}đ cho user `{target_id}`",
        parse_mode="Markdown",
    )


@dp.message(Command("trutien"))
async def cmd_trutien(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    args = message.text.split()
    if len(args) < 3:
        return await message.answer("Sai cú pháp! Dùng: `/trutien (id) (số_tiền)`")

    target_id = int(args[1])
    amount = float(args[2])
    target_user = get_user(target_id)
    target_user["balance"] -= amount
    await message.answer(
        f"✅ Đã trừ {amount:,.0f}đ của user `{target_id}`", parse_mode="Markdown"
    )


@dp.message(Command("tbao"))
async def cmd_tbao(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    content = message.text.replace("/tbao", "").strip()
    if not content:
        return await message.answer("Vui lòng nhập nội dung thông báo!")

    success_count = 0
    fail_count = 0
    for uid in users_db.keys():
        try:
            await bot.send_message(
                uid,
                f"📢 **THÔNG BÁO TỪ HỆ THỐNG**\n\n{content}",
                parse_mode="Markdown",
            )
            success_count += 1
            await asyncio.sleep(0.05)
        except:
            fail_count += 1

    await message.answer(
        f"✅ Đã gửi thông báo đến {success_count} người dùng ({fail_count} lỗi)."
    )


@dp.message(Command("addtainguyen"))
async def cmd_addtainguyen(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    # Cú pháp: /addtainguyen srv_1_1 acc|pass|2fa
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        return await message.answer(
            "Sai cú pháp! Dùng: `/addtainguyen (mã_kho) (thông_tin_acc)`\n"
            "Mã kho gồm: `srv_1_1`, `srv_1_2`, `srv_1_3`, `srv_2_1`, `srv_2_2`, `srv_2_3`, `mail_new`, `mail_month`, `mail_year`"
        )

    key = parts[1]
    acc_content = parts[2]

    if key not in stock_db:
        return await message.answer(
            f"❌ Mã kho `{key}` không tồn tại trong hệ thống!", parse_mode="Markdown"
        )

    stock_db[key].append(acc_content)
    total_stock = len(stock_db[key])
    await message.answer(
        f"✅ Đã thêm tài nguyên thành công vào kho `{key}`!\nTổng kho hiện tại: {total_stock} tài nguyên.",
        parse_mode="Markdown",
    )


# Khởi chạy bot
async def main():
    print("Bot is starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
	◦	
