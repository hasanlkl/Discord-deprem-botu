import discord
from discord import app_commands
import asyncio
import requests
import json
import os

# API
API_URL = "https://api.orhanaydogdu.com.tr/deprem/kandilli/live?limit=1"

TOKEN = "DISCORDBOTTOKENINIZ"

# Kullanıcı ayarları
user_settings = {
    "channel_id": None,
    "notifications": True,
    "min_magnitude": 3.0,
    "last_hash": None
}

# Kullanıcı ayarlarını kaydetme ve yükleme
def save_settings(): 
    with open("settings.json", "w") as file:
        json.dump(user_settings, file)

def load_settings():
    global user_settings
    if os.path.exists("settings.json"):
        with open("settings.json", "r") as file:
            loaded = json.load(file)
            user_settings.update(loaded)

    if "min_magnitude" not in user_settings:
        user_settings["min_magnitude"] = 3.0
    if "last_hash" not in user_settings:
        user_settings["last_hash"] = None

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True

# Botu başlatma
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# Deprem bilgileri
class EarthquakeData:
    def __init__(self, magnitude=None, date=None, title=None):
        self.magnitude = magnitude
        self.date = date
        self.title = title

# API'den deprem verisini çekme
def get_earthquake_info():
    try:
        response = requests.get(API_URL)
        if response.status_code != 200:
            return None
        data = response.json()

        if "result" not in data or not data["result"]:
            return None

        earthquake_info = data['result'][0]

        print(f"✅ {earthquake_info['title']} - {earthquake_info['mag']} Mw - {earthquake_info['date']}")

        return EarthquakeData(
            magnitude=float(earthquake_info['mag']),
            date=earthquake_info['date'],
            title=earthquake_info['title']
        )
    except Exception as e:
        print(f"⚠ Bir hata meydana geldi: {e}")
        return None

@bot.event 
async def on_ready():
    load_settings() 
    print(f"✅ Bot is online! Logged in as {bot.user}")
    await tree.sync()
    print("✅ Slash komutları yüklendi!")

    if user_settings["channel_id"] is None:
        print("⚠ Kanal ID'si ayarlanmamış! `/kanalsec #kanal_adı` komutunu kullan.")
        return

    print(f"ℹ Mesaj gönderilecek kanal ID: {user_settings['channel_id']}")

    channel = bot.get_channel(user_settings["channel_id"])
    if channel is None:
        print("⚠ Kanal bulunamadı! ID yanlış olabilir veya botun yetkisi eksik.")
        return

    print(f"✅ Mesaj gönderilecek kanal: {channel.name} (ID: {channel.id})")

    delay = 60

    while True:
        if not user_settings["notifications"] or user_settings["channel_id"] is None:
            await asyncio.sleep(delay)
            continue
        
        eq_data = get_earthquake_info()

        if eq_data is None:
            print("⚠ API'den deprem verisi alınamadı.")
            await asyncio.sleep(delay)
            continue
        
        if eq_data.magnitude < user_settings["min_magnitude"]:
            print(f"⚠ Deprem büyüklüğü {eq_data.magnitude} Mw, belirlenen minimum değerin altında.")
            await asyncio.sleep(delay)
            continue

        if user_settings["last_hash"] == eq_data.date:
            print("⚠ Aynı deprem tekrar algılandı, mesaj gönderilmiyor.")
            await asyncio.sleep(delay)
            continue

        user_settings["last_hash"] = eq_data.date
        save_settings()

        print(f"🌍 {eq_data.title} | 💥 {eq_data.magnitude} Mw | 📅 {eq_data.date}")

        try:
            await channel.send(
                f"**# ⚠️ DEPREM UYARISI **\n"                
                f" 📌**Lokasyon:** {eq_data.title}\n"
                f"💥 **Büyüklük:** {eq_data.magnitude} Mw\n"
                f"📅 **Tarih ve saat:** {eq_data.date}"
            )
            print("✅ Deprem bildirimi başarıyla gönderildi!")
        except Exception as e:
            print(f"⚠ Mesaj gönderilirken hata oluştu: {e}")

        await asyncio.sleep(delay)

# Slash komutları
@tree.command(name="sondepremler", description="Belirtilen sayıda son depremleri listeler. (Min: 1, Max: 10)") 
async def sondepremler(interaction: discord.Interaction, adet: int):
    if adet < 1 or adet > 10:
        await interaction.response.send_message("⚠ Lütfen 1 ile 10 arasında bir değer girin.", ephemeral=True)
        return

    url = f'https://api.orhanaydogdu.com.tr/deprem/kandilli/live?limit={adet}'

    try:
        response = requests.get(url)
        if response.status_code != 200:
            await interaction.response.send_message("⚠ API bağlantı hatası! Lütfen daha sonra tekrar deneyin.", ephemeral=True)
            return

        data = response.json()
        print(f"API Yanıtı: {data}")

        if "result" not in data or not data["result"]:
            await interaction.response.send_message("⚠ Son depremler bilgisi alınamadı.", ephemeral=True)
            return

        message = f"**# Son {adet} Deprem **\n"
        for eq in data["result"]:
            magnitude = eq.get("mag", "0.0")  
            title = eq.get("title", "Bilinmeyen Konum")  
            date = eq.get("date", "Tarih bilgisi yok")

            message += f"📌 **{title}** \n 💥 **Büyüklük:** {magnitude} Mw \n 📅 **Tarih ve saat**: {date}\n \n"

        await interaction.response.send_message(message, ephemeral=False)

    except Exception as e:
        await interaction.response.send_message(f"⚠ Bir hata oluştu: {e}", ephemeral=True)

@tree.command(name="kanalsec", description="Deprem bildirimlerinin gönderileceği kanalı seç.") 
async def kanalsec(interaction: discord.Interaction, kanal: discord.TextChannel):
    user_settings["channel_id"] = kanal.id
    save_settings()
    await interaction.response.send_message(f"✅ Deprem bildirimleri artık {kanal.mention} kanalına gönderilecek.")

@tree.command(name="bildirimler", description="Deprem bildirimlerini aç/kapat ve mevcut durumunu gösterir.") 
async def bildirimler(interaction: discord.Interaction, durum: str = None):
    if durum is None:
        status = "✅ Açık" if user_settings["notifications"] else "❌ Kapalı"
        await interaction.response.send_message(f"📢 Bildirimler şu anda: {status}")
        return

    if durum.lower() == "aç":
        if user_settings["notifications"]:
            await interaction.response.send_message("⚠ **Bildirimler zaten açık!**")
        else:
            user_settings["notifications"] = True
            save_settings()
            await interaction.response.send_message("✅ **Deprem bildirimleri açıldı!**")

    elif durum.lower() == "kapat":
        if not user_settings["notifications"]:
            await interaction.response.send_message("⚠ **Bildirimler zaten kapalı!**")
        else:
            user_settings["notifications"] = False
            save_settings()
            await interaction.response.send_message("❌ **Deprem bildirimleri kapatıldı!**")

    else:
        await interaction.response.send_message("⚠ Geçerli bir seçenek girin: `aç` veya `kapat`")

@tree.command(name="minbuyukluk", description="Bildirim almak için minimum deprem büyüklüğünü belirle.") 
async def minbuyukluk(interaction: discord.Interaction, buyukluk: float):
    if buyukluk < 0:
        await interaction.response.send_message("⚠ Geçerli bir büyüklük giriniz (0'dan büyük olmalı).", ephemeral=True )
        return

    user_settings["min_magnitude"] = buyukluk
    save_settings()  

    await interaction.response.send_message(f"✅ Minimum deprem büyüklüğü {buyukluk} olarak ayarlandı.")

@tree.command(name="ayarlar", description="Botun mevcut bildirim ayarlarını gösterir.") 
async def ayarlar(interaction: discord.Interaction):
    settings_text = (
        f"📌 Mevcut Ayarlar 📌\n"
        f"📢 Bildirimler: {'✅ Açık' if user_settings['notifications'] else '❌ Kapalı'}\n"
        f"📊 Min Büyüklük: {user_settings['min_magnitude']} Mw\n"
        f"📩 Bildirim Kanalı: <#{user_settings['channel_id']}>\n"
    )
    await interaction.response.send_message(settings_text)

@tree.command(name="yardım", description="Botun tüm komutlarını ve açıklamalarını gösterir.") 
async def yardım(interaction: discord.Interaction):
    bot_avatar = interaction.client.user.avatar.url if interaction.client.user.avatar else ""
    bot_name = interaction.client.user.name

    embed = discord.Embed(
        title=f"📌 {bot_name} - Yardım Menüsü",
        description="Bu bot Türkiye'deki depremleri takip etmenizi sağlar. Aşağıda tüm komutları ve açıklamalarını bulabilirsiniz:",
        color=discord.Color.blue()
    )

    if bot_avatar:
        embed.set_thumbnail(url=bot_avatar)

    embed.add_field(name="🔹 /kanalsec [kanal]", value="Deprem bildirimlerinin gönderileceği kanalı ayarlar.", inline=False)
    embed.add_field(name="🔹 /bildirimler", value="Deprem bildirimlerini açar veya kapatır.", inline=False)
    embed.add_field(name="🔹 /minbuyukluk [büyüklük]", value="Bildirim almak için minimum deprem büyüklüğünü belirler.", inline=False)
    embed.add_field(name="🔹 /sondepremler [adet]", value="Son x depremi listeler (1 ile 10 arasında seçim yapabilirsiniz).", inline=False)
    embed.add_field(name="🔹 /yardım", value="Botun tüm komutlarını ve açıklamalarını gösterir.", inline=False)
    embed.add_field(name="🔹 /ayarlar", value="Botun mevcut ayarlarını gösterir.", inline=False)

    embed.set_footer(text="📡 Deprem Bilgi Botu - Anlık Deprem Takibi")

    await interaction.response.send_message(embed=embed)

# Botu çalıştır
bot.run(TOKEN)
