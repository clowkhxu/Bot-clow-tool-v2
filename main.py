import os
import logging
import discord
import asyncio
import aiohttp
from discord.ext import commands, tasks
from discord import app_commands
from utils import get_random_user, generate_cards_from_bin, COUNTRY_MAP, COUNTRY_EMOJI
from web_server import start_server
from spammer import run
from utils import get_random_user, generate_cards_from_bin, COUNTRY_MAP, COUNTRY_EMOJI, check_bin_info
import vlr_api

# Cấu hình logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)
logger = logging.getLogger(__name__)

# Lấy token bot từ biến môi trường
TOKEN = os.environ.get("DISCORD_BOT_TOKEN")

# Lấy URL của ứng dụng Render
RENDER_URL = os.environ.get("RENDER_URL")

# Khởi tạo bot với intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# Thêm vào phần import
import vlr_api


# Thêm vào hàm on_ready
@bot.event
async def on_ready():
    logger.info(f"Bot đã đăng nhập với tên {bot.user}")
    try:
        # Đăng ký các lệnh Valorant
        vlr_api.setup_commands(bot)

        # Đồng bộ tất cả các lệnh slash
        synced = await bot.tree.sync()
        logger.info(f"Đã đồng bộ {len(synced)} lệnh slash")
    except Exception as e:
        logger.error(f"Lỗi khi đồng bộ lệnh: {e}")

    # Bắt đầu task ping server
    if RENDER_URL:
        keep_alive.start()
    else:
        logger.warning(
            "RENDER_URL không được cấu hình. Không thể bắt đầu task ping server."
        )


# Task tự động ping server mỗi 14 phút để giữ cho Render không tắt
@tasks.loop(minutes=14)
async def keep_alive():
    if not RENDER_URL:
        return

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(RENDER_URL) as response:
                logger.info(f"Ping server tại {RENDER_URL}: {response.status}")
    except Exception as e:
        logger.error(f"Lỗi khi ping server: {e}")


# Các lệnh slash
@bot.tree.command(name="start",
                  description="Hiển thị thông tin giới thiệu về bot")
async def start(interaction: discord.Interaction):
    await interaction.response.send_message(
        "🤖 **Chào mừng bạn đến với Bot Đa Năng!**\n\n"
        "👉 Dùng `/fake` để tạo thông tin giả.\n"
        "👉 Dùng `/gen` để tạo số thẻ tín dụng.\n"
        "👉 Dùng `/spam` để spam SMS.\n\n"
        "Xem danh sách quốc gia: `/help_fake`")


@bot.tree.command(name="fake", description="Tạo thông tin người dùng giả")
@app_commands.describe(country_code="Mã quốc gia (vd: us, gb, fr)")
async def fake_command(interaction: discord.Interaction, country_code: str):
    country_code = country_code.lower()
    if country_code not in COUNTRY_MAP:
        await interaction.response.send_message(
            "Mã quốc gia không hỗ trợ. Xem `/help_fake`.")
        return

    user_data = get_random_user(country_code)
    if not user_data or "results" not in user_data or not user_data["results"]:
        await interaction.response.send_message(
            "Không thể lấy thông tin người dùng. Thử lại sau.")
        return

    user = user_data["results"][0]
    emoji = COUNTRY_EMOJI.get(country_code, "")
    response = f'✅ **Info Generated:**\n\n'
    response += f"**Full Name**: {user['name']['title']} {user['name']['first']} {user['name']['last']}\n"
    response += f"**Email**: {user['email']}\n"
    response += f"**State**: {user['location']['state']}\n"
    response += f"**City**: {user['location']['city']}\n"
    response += f"**Street**: {user['location']['street']['number']} {user['location']['street']['name']}\n"
    response += f"**Zip Code**: {user['location']['postcode']}\n"
    response += f"**Country**: {user['location']['country']} {emoji}\n"
    response += f"**Gender**: {user['gender']}\n"
    response += f"**Phone**: {user['phone']}\n\n"
    response += f"**Requester**: <@{interaction.user.id}>\n"
    response += f"**Bot by**: @clowkhxu"

    await interaction.response.send_message(response)


@bot.tree.command(
    name="gen",
    description="Tạo số thẻ tín dụng dựa trên BIN và kiểm tra thông tin")
@app_commands.describe(bin_code="Mã BIN (số lượng bất kỳ)",
                       count="Số lượng thẻ (tối đa 20)")
async def gen_command(interaction: discord.Interaction,
                      bin_code: str,
                      count: int = 5):
    # Kiểm tra BIN hợp lệ
    if not bin_code.isdigit():
        await interaction.response.send_message(
            'Mã BIN không hợp lệ. Vui lòng chỉ nhập số.')
        return

    # Kiểm tra BIN không dài hơn 15 số
    if len(bin_code) > 15:
        await interaction.response.send_message(
            'Mã BIN quá dài. Vui lòng nhập ít hơn 16 số.')
        return

    # Giới hạn số lượng thẻ
    count = min(count, 20)

    # Kiểm tra thông tin BIN
    bin_info = check_bin_info(
        bin_code[:6])  # Chỉ lấy 6 số đầu tiên để kiểm tra

    try:
        # Tạo số thẻ từ BIN
        cards = generate_cards_from_bin(bin_code, count)

        # Tạo danh sách thẻ theo định dạng mới
        card_list = ""
        for card in cards:
            card_list += f"{card['number']}|{card['expiry_month']}|{card['expiry_year']}|{card['cvv']}\n"

        # Tạo thông tin BIN
        bin_info_text = ""
        card_type = "UNKNOWN"
        card_brand = "UNKNOWN"
        card_category = "UNKNOWN"
        bank_name = "UNKNOWN"
        country_name = "Unknown"
        country_emoji = ""
        country_info = "Unknown"  # Khởi tạo country_info ở đây

        if "error" not in bin_info:
            card_type = bin_info.get(
                'type', 'UNKNOWN').upper() if 'type' in bin_info else "UNKNOWN"
            card_brand = bin_info.get(
                'scheme',
                'UNKNOWN').upper() if 'scheme' in bin_info else "UNKNOWN"
            card_category = bin_info.get(
                'brand',
                'UNKNOWN').upper() if 'brand' in bin_info else "UNKNOWN"

            if "country" in bin_info:
                country = bin_info["country"]
                country_emoji = country.get("emoji", "")
                country_name = country.get("name", "Unknown")
                country_code = country.get("alpha2", "")
                country_info = f"{country_name}({country_code}) {country_emoji}"

            if "bank" in bin_info:
                bank = bin_info["bank"]
                bank_name = bank.get('name', 'UNKNOWN')

        # Tạo response theo định dạng mới
        response = f"**Random Test Credit Card Numbers Generator**\n\n"
        response += f"{card_list}\n\n"
        response += f"𝗔𝗺𝗼𝘂𝗻𝘁 ⇾ {count}\n\n"
        response += f"**BIN**: {bin_code[:6]}\n"
        response += f"**INFO**: {card_type} - {card_brand} - {card_category}\n"
        response += f"**Bank**: {bank_name}\n"
        response += f"**Country**: {country_info}\n"
        response += f"**Requester**➟ <@{interaction.user.id}>\n"
        response += f"**Bot by**: @clowkhxu"

        await interaction.response.send_message(response)

    except Exception as e:
        await interaction.response.send_message(f'Lỗi: {str(e)}')


@bot.tree.command(name="spam", description="Thực hiện spam SMS")
@app_commands.describe(phone="Số điện thoại cần spam",
                       count="Số lần spam (tối đa 20)")
async def spam_command(interaction: discord.Interaction, phone: str,
                       count: int):
    # Kiểm tra số điện thoại hợp lệ
    if not phone.isdigit() or len(phone) < 9 or len(phone) > 11:
        await interaction.response.send_message(
            "Số điện thoại không hợp lệ! Vui lòng nhập số điện thoại đúng định dạng."
        )
        return

    # Kiểm tra số lần spam hợp lệ
    if count <= 0:
        await interaction.response.send_message(
            "Số lần spam không hợp lệ! Vui lòng nhập một số nguyên dương.")
        return

    count = min(count, 20)  # Giới hạn tối đa 20 lần spam

    # Chuẩn hóa số điện thoại
    if phone.startswith("0"):
        phone = phone[1:]

    user_name = interaction.user.display_name
    initial_message = f"┌──────⭓ Clow_Ponkey\n│ Spam: Đang thực hiện\n│ Người dùng: {user_name}\n│ Số Lần Spam: {count}\n│ Đang Tấn Công: {phone}\n└─────────────"

    await interaction.response.send_message(initial_message)
    progress_msg = await interaction.original_response()

    try:
        from spammer import run
        for i in range(1, min(count, 20) + 1):
            # Cập nhật thông báo tiến trình
            message = f"┌──────⭓ Clow_Ponkey\n│ Spam: Đang thực hiện\n│ Người dùng: {user_name}\n│ Số Lần Spam: {count} (lần {i}/{count})\n│ Đang Tấn Công: {phone}\n└─────────────"
            await progress_msg.edit(content=message)

            # Chạy hàm spam
            await bot.loop.run_in_executor(None, run, phone, i)

            if i < count:
                # Hiển thị thông báo đang chuẩn bị cho lần tiếp theo
                message = f"┌──────⭓ Clow_Ponkey\n│ Spam: Đang thực hiện\n│ Người dùng: {user_name}\n│ Số Lần Spam: {count} (lần {i}/{count})\n│ Đang Tấn Công: {phone}\n└─────────────\n⏳ Đang chuẩn bị cho lần tiếp theo..."
                await progress_msg.edit(content=message)
                await asyncio.sleep(3)

        # Hiển thị kết quả cuối cùng
        final_message = f"┌──────⭓ Clow_Ponkey\n│ Spam: Thành Công\n│ Người dùng: {user_name}\n│ Số Lần Spam: {count}\n│ Đang Tấn Công: {phone}\n└─────────────"
        await progress_msg.edit(content=final_message)
    except Exception as e:
        await interaction.followup.send(f"❌ Lỗi: {str(e)}")


@bot.tree.command(name="help_fake",
                  description="Hiển thị danh sách các quốc gia được hỗ trợ")
async def help_fake_command(interaction: discord.Interaction):
    response = '🌎 **Quốc gia hỗ trợ:**\n\n'
    for code, name in sorted(COUNTRY_MAP.items()):
        emoji = COUNTRY_EMOJI.get(code, '')
        response += f"{emoji} `{code}` - {name}\n"

    await interaction.response.send_message(response)


@bot.tree.command(name="help", description="Hiển thị danh sách lệnh")
async def help_command(interaction: discord.Interaction):
    await interaction.response.send_message(
        "/fake `country_code` - Tạo thông tin giả.\n"
        "/gen `bin_code` `count` - Tạo số thẻ tín dụng.\n"
        "/spam `phone` `count` - Spam SMS.\n\n"
        "Xem danh sách quốc gia: `/help_fake`")


# Khởi động bot
def main():
    # Khởi động web server
    start_server()
    # Chạy bot
    bot.run(TOKEN)


if __name__ == '__main__':
    main()
