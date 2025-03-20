import os
import aiohttp
import discord
import random
from discord import app_commands, SelectOption, ui

# Base URL cho các API
HENRIK_API_BASE = "https://api.henrikdev.xyz/valorant"
VALORANT_API_BASE = "https://valorant-api.com/v1"
VLR_GG_API_BASE = "https://vlrggapi.vercel.app/api/v1"

# Lấy API Key từ biến môi trường
API_KEY = os.getenv("VALORANT_API_KEY")


# Class SelectView cho agent
class AgentSelectView(ui.View):

    def __init__(self, agents):
        super().__init__(timeout=60)
        self.add_item(AgentSelectMenu(agents))


class AgentSelectMenu(ui.Select):

    def __init__(self, agents):
        options = [
            SelectOption(label=agent.get("displayName", "Unknown"),
                         value=agent.get("uuid", ""),
                         description=agent.get("role",
                                               {}).get("displayName", ""),
                         emoji="🎮") for agent in agents[:25]
        ]
        super().__init__(placeholder="Chọn một đặc vụ...",
                         options=options,
                         min_values=1,
                         max_values=1)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        agent_id = self.values[0]
        # Tìm agent từ danh sách
        for agent in interaction.client._agents:
            if agent.get("uuid") == agent_id:
                embed = create_agent_embed(agent)
                await interaction.followup.send(embed=embed)
                break


# Class SelectView cho map
class MapSelectView(ui.View):

    def __init__(self, maps):
        super().__init__(timeout=60)
        self.add_item(MapSelectMenu(maps))


class MapSelectMenu(ui.Select):

    def __init__(self, maps):
        options = [
            SelectOption(label=map_data.get("displayName", "Unknown"),
                         value=map_data.get("uuid", ""),
                         emoji="🗺️") for map_data in maps[:25]
        ]
        super().__init__(placeholder="Chọn một bản đồ...",
                         options=options,
                         min_values=1,
                         max_values=1)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        map_id = self.values[0]
        # Tìm map từ danh sách
        for map_data in interaction.client._maps:
            if map_data.get("uuid") == map_id:
                embed = create_map_embed(map_data)
                await interaction.followup.send(embed=embed)
                break


# Hàm xem thông tin rank
async def get_rank(interaction: discord.Interaction, name: str, tag: str):
    await interaction.response.defer()
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{HENRIK_API_BASE}/v2/mmr/ap/{name}/{tag}"
            headers = {
                'Authorization': f'Bearer {API_KEY}',
                'X-Riot-Token': f'{API_KEY}'
            }
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    await interaction.followup.send(
                        f"❌ Lỗi: Không thể tìm thấy thông tin người chơi. Vui lòng kiểm tra lại tên và tag."
                    )
                    return

                data = await response.json()
                if data["status"] != 200:
                    await interaction.followup.send(
                        f"❌ Lỗi: {data.get('message', 'Không thể lấy thông tin rank.')}"
                    )
                    return

                player_data = data["data"]

                # Tạo embed để hiển thị thông tin
                embed = discord.Embed(title=f"Thông tin Rank của {name}#{tag}",
                                      color=0xFD4554)

                current_rank = player_data.get("currenttierpatched",
                                               "Chưa xếp hạng")
                rank_image = player_data.get("images", {}).get("large", "")
                elo = player_data.get("elo", "N/A")
                embed.add_field(name="Rank hiện tại",
                                value=current_rank,
                                inline=False)
                embed.add_field(name="ELO", value=str(elo), inline=True)

                if rank_image:
                    embed.set_thumbnail(url=rank_image)

                # Thêm thông tin về lịch sử xếp hạng
                mmr_history = player_data.get("mmr_change_to_last_game", "N/A")
                embed.add_field(name="Thay đổi ELO trận gần nhất",
                                value=str(mmr_history),
                                inline=True)

                await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Đã xảy ra lỗi: {str(e)}")


# Hàm xem thông tin tài khoản
async def get_account(interaction: discord.Interaction, name: str, tag: str):
    await interaction.response.defer()
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{HENRIK_API_BASE}/v1/account/{name}/{tag}"
            headers = {
                'Authorization': f'Bearer {API_KEY}',
                'X-Riot-Token': f'{API_KEY}'
            }
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    await interaction.followup.send(
                        f"❌ Lỗi: Không thể tìm thấy thông tin người chơi. Vui lòng kiểm tra lại tên và tag."
                    )
                    return

                data = await response.json()
                if data["status"] != 200:
                    await interaction.followup.send(
                        f"❌ Lỗi: {data.get('message', 'Không thể lấy thông tin tài khoản.')}"
                    )
                    return

                player_data = data["data"]

                # Tạo embed để hiển thị thông tin
                embed = discord.Embed(
                    title=f"Thông tin tài khoản của {name}#{tag}",
                    color=0xFD4554)

                account_level = player_data.get("account_level", "N/A")
                region = player_data.get("region", "N/A").upper()
                last_update = player_data.get("last_update", "N/A")
                embed.add_field(name="Cấp độ tài khoản",
                                value=str(account_level),
                                inline=True)
                embed.add_field(name="Khu vực", value=region, inline=True)
                embed.add_field(name="Cập nhật lần cuối",
                                value=last_update,
                                inline=False)

                # Thêm avatar nếu có
                card_small = player_data.get("card", {}).get("small", "")
                if card_small:
                    embed.set_thumbnail(url=card_small)

                await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Đã xảy ra lỗi: {str(e)}")


# Hàm xem thông tin agents
async def get_agents(interaction: discord.Interaction, agent_name: str = None):
    await interaction.response.defer()
    try:
        async with aiohttp.ClientSession() as session:
            if agent_name:
                # Tìm kiếm agent cụ thể
                url = f"{VALORANT_API_BASE}/agents?language=vi-VN&isPlayableCharacter=true"
                headers = {
                    'Authorization': f'Bearer {API_KEY}',
                    'X-Riot-Token': f'{API_KEY}'
                }
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        await interaction.followup.send(
                            "❌ Không thể lấy thông tin đặc vụ. Vui lòng thử lại sau."
                        )
                        return

                    data = await response.json()
                    agents = data.get("data", [])

                    # Tìm agent theo tên
                    found_agent = None
                    for agent in agents:
                        if agent_name.lower() in agent.get("displayName",
                                                           "").lower():
                            found_agent = agent
                            break

                    if not found_agent:
                        await interaction.followup.send(
                            f"❌ Không tìm thấy đặc vụ có tên '{agent_name}'.")
                        return

                    # Hiển thị thông tin agent
                    embed = create_agent_embed(found_agent)
                    await interaction.followup.send(embed=embed)
            else:
                # Lấy tất cả agent và hiển thị select menu
                url = f"{VALORANT_API_BASE}/agents?language=vi-VN&isPlayableCharacter=true"
                headers = {
                    'Authorization': f'Bearer {API_KEY}',
                    'X-Riot-Token': f'{API_KEY}'
                }
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        await interaction.followup.send(
                            "❌ Không thể lấy thông tin đặc vụ. Vui lòng thử lại sau."
                        )
                        return

                    data = await response.json()
                    agents = data.get("data", [])

                    if not agents:
                        await interaction.followup.send(
                            "❌ Không tìm thấy dữ liệu đặc vụ.")
                        return

                    # Lưu danh sách agent vào client để sử dụng sau
                    interaction.client._agents = agents

                    # Tạo select menu cho agent
                    view = AgentSelectView(agents)
                    await interaction.followup.send(
                        "Chọn một đặc vụ để xem thông tin:", view=view)
    except Exception as e:
        await interaction.followup.send(f"❌ Đã xảy ra lỗi: {str(e)}")


# Hàm xem thông tin bản đồ
async def get_map(interaction: discord.Interaction, map_name: str = None):
    await interaction.response.defer()
    try:
        async with aiohttp.ClientSession() as session:
            if map_name:
                # Tìm kiếm bản đồ cụ thể
                url = f"{VALORANT_API_BASE}/maps?language=vi-VN"
                headers = {
                    'Authorization': f'Bearer {API_KEY}',
                    'X-Riot-Token': f'{API_KEY}'
                }
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        await interaction.followup.send(
                            "❌ Không thể lấy thông tin bản đồ. Vui lòng thử lại sau."
                        )
                        return

                    data = await response.json()
                    maps = data.get("data", [])

                    # Tìm bản đồ theo tên
                    found_map = None
                    for map_data in maps:
                        if map_name.lower() in map_data.get("displayName",
                                                            "").lower():
                            found_map = map_data
                            break

                    if not found_map:
                        await interaction.followup.send(
                            f"❌ Không tìm thấy bản đồ có tên '{map_name}'.")
                        return

                    # Hiển thị thông tin bản đồ
                    embed = create_map_embed(found_map)
                    await interaction.followup.send(embed=embed)
            else:
                # Lấy tất cả bản đồ và hiển thị select menu
                url = f"{VALORANT_API_BASE}/maps?language=vi-VN"
                headers = {
                    'Authorization': f'Bearer {API_KEY}',
                    'X-Riot-Token': f'{API_KEY}'
                }
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        await interaction.followup.send(
                            "❌ Không thể lấy thông tin bản đồ. Vui lòng thử lại sau."
                        )
                        return

                    data = await response.json()
                    maps = data.get("data", [])

                    if not maps:
                        await interaction.followup.send(
                            "❌ Không tìm thấy dữ liệu bản đồ.")
                        return

                    # Lưu danh sách map vào client để sử dụng sau
                    interaction.client._maps = maps

                    # Tạo select menu cho map
                    view = MapSelectView(maps)
                    await interaction.followup.send(
                        "Chọn một bản đồ để xem thông tin:", view=view)
    except Exception as e:
        await interaction.followup.send(f"❌ Đã xảy ra lỗi: {str(e)}")


# Hàm xem thông tin người chơi
async def get_player(interaction: discord.Interaction, player_name: str):
    await interaction.response.defer()
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{VLR_GG_API_BASE}/player/{player_name}"
            headers = {
                'Authorization': f'Bearer {API_KEY}',
                'X-Riot-Token': f'{API_KEY}'
            }
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    await interaction.followup.send(
                        f"❌ Lỗi: Không thể tìm thấy thông tin người chơi. Vui lòng kiểm tra lại tên."
                    )
                    return

                data = await response.json()

                # Tạo embed để hiển thị thông tin
                embed = discord.Embed(
                    title=
                    f"Thông tin người chơi {data.get('name', 'Không có tên')}",
                    color=0xFD4554)

                # Thêm avatar nếu có
                if data.get('avatar'):
                    embed.set_thumbnail(url=data.get('avatar'))

                # Thêm thông tin cơ bản
                embed.add_field(name="Tên đầy đủ",
                                value=data.get('name', 'Không có'),
                                inline=True)
                embed.add_field(name="Tên thật",
                                value=data.get('real_name', 'Không có'),
                                inline=True)

                # Thêm thông tin về đội
                if data.get('team'):
                    embed.add_field(name="Đội hiện tại",
                                    value=data.get('team'),
                                    inline=False)

                # Thêm thông tin về quốc gia
                if data.get('country'):
                    embed.add_field(name="Quốc gia",
                                    value=data.get('country'),
                                    inline=True)

                # Thêm thông tin về vai trò
                if data.get('role'):
                    embed.add_field(name="Vai trò",
                                    value=data.get('role'),
                                    inline=True)

                # Thêm thông tin về đặc vụ
                if data.get('agents') and isinstance(data.get('agents'), list):
                    agents_str = ", ".join(data.get('agents'))
                    embed.add_field(name="Đặc vụ",
                                    value=agents_str,
                                    inline=False)

                # Thêm thông tin về thống kê
                if data.get('stats'):
                    stats = data.get('stats')
                    embed.add_field(name="ACS",
                                    value=stats.get('acs', 'N/A'),
                                    inline=True)
                    embed.add_field(name="K:D",
                                    value=stats.get('kd', 'N/A'),
                                    inline=True)
                    embed.add_field(name="HS%",
                                    value=stats.get('hs', 'N/A'),
                                    inline=True)

                await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Đã xảy ra lỗi: {str(e)}")


# Hàm tạo embed cho agent
def create_agent_embed(agent):
    embed = discord.Embed(title=agent.get("displayName", "Không có tên"),
                          description=agent.get("description",
                                                "Không có mô tả"),
                          color=0xFD4554)

    # Thêm hình ảnh
    embed.set_thumbnail(url=agent.get("displayIcon", ""))
    embed.set_image(url=agent.get("fullPortrait", ""))

    # Thêm thông tin về vai trò
    role = agent.get("role", {})
    embed.add_field(name="Vai trò",
                    value=role.get("displayName", "Không có"),
                    inline=True)

    # Thêm thông tin về kỹ năng
    abilities = agent.get("abilities", [])
    for ability in abilities:
        ability_name = ability.get("displayName", "Không có tên")
        ability_description = ability.get("description", "Không có mô tả")
        embed.add_field(name=ability_name,
                        value=ability_description,
                        inline=False)

    return embed


# Hàm tạo embed cho map
def create_map_embed(map_data):
    embed = discord.Embed(title=map_data.get("displayName", "Không có tên"),
                          description=map_data.get("narrativeDescription",
                                                   "Không có mô tả"),
                          color=0xFD4554)

    # Thêm hình ảnh
    embed.set_image(url=map_data.get("splash", ""))

    # Thêm hình ảnh nhỏ (nếu có)
    if map_data.get("displayIcon"):
        embed.set_thumbnail(url=map_data.get("displayIcon"))

    # Thêm thông tin về tọa độ
    coordinates = map_data.get("coordinates", "Không có thông tin")
    if coordinates:
        embed.add_field(name="Tọa độ", value=coordinates, inline=True)

    # Thêm thông tin về các vị trí đặt spike
    sites = []
    if map_data.get("bombsites"):
        for site in map_data.get("bombsites"):
            sites.append(site.get("site", ""))

    if sites:
        embed.add_field(name="Vị trí đặt Spike",
                        value=", ".join(sites),
                        inline=True)

    return embed


# Hàm đăng ký các lệnh slash
def setup_commands(bot):
    # Khởi tạo biến lưu trữ agents và maps
    bot._agents = []
    bot._maps = []

    @bot.tree.command(name="vlr_rank",
                      description="Xem thông tin rank của người chơi Valorant")
    @app_commands.describe(name="Tên người chơi (ví dụ: username)",
                           tag="Tag của người chơi (ví dụ: 1234)")
    async def vlr_rank(interaction: discord.Interaction, name: str, tag: str):
        await get_rank(interaction, name, tag)

    @bot.tree.command(
        name="vlr_account",
        description="Xem thông tin tài khoản của người chơi Valorant")
    @app_commands.describe(name="Tên người chơi (ví dụ: username)",
                           tag="Tag của người chơi (ví dụ: 1234)")
    async def vlr_account(interaction: discord.Interaction, name: str,
                          tag: str):
        await get_account(interaction, name, tag)

    @bot.tree.command(name="vlr_agents",
                      description="Xem thông tin về các đặc vụ trong Valorant")
    @app_commands.describe(
        agent_name="Tên đặc vụ (không bắt buộc, để trống để xem danh sách)")
    async def vlr_agents(interaction: discord.Interaction,
                         agent_name: str = None):
        await get_agents(interaction, agent_name)

    @bot.tree.command(name="vlr_map",
                      description="Xem thông tin về các bản đồ trong Valorant")
    @app_commands.describe(
        map_name="Tên bản đồ (không bắt buộc, để trống để xem danh sách)")
    async def vlr_map(interaction: discord.Interaction, map_name: str = None):
        await get_map(interaction, map_name)

    @bot.tree.command(
        name="vlr_player",
        description="Xem thông tin người chơi Valorant chuyên nghiệp")
    @app_commands.describe(player_name="Tên người chơi (ví dụ: TenZ, ScreaM)")
    async def vlr_player(interaction: discord.Interaction, player_name: str):
        await get_player(interaction, player_name)
