import os
import discord
from discord.ext import commands
import google.generativeai as genai
from dotenv import load_dotenv

# Wczytanie zmiennych środowiskowych z pliku .env
load_dotenv()
# Słownik na wczytane klucze
config_keys = {}

# Wczytywanie kluczy z pliku kody.txt
config_path = "kody.txt"
if os.path.exists(config_path):
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    config_keys[k.strip().lower()] = v.strip()
    except Exception as e:
        print(f"Błąd podczas odczytu pliku kody.txt: {e}")

DISCORD_TOKEN = config_keys.get("token")
GEMINI_API_KEY = config_keys.get("api")

# Konfiguracja Google Gemini API
genai.configure(api_key=GEMINI_API_KEY)
# Używamy modelu gemini-2.5-flash (poprzednie wersje zostały wycofane z darmowego API)
model = genai.GenerativeModel('gemini-2.5-flash')

# Konfiguracja uprawnień bota (Intents)
intents = discord.Intents.default()
intents.message_content = True  # Pozwala czytać treść wiadomości
intents.guilds = True           # Pozwala zarządzać serwerem (kanałami)

# Inicjalizacja bota z prefiksem komend
bot = commands.Bot(command_prefix="!", intents=intents)

# Słownik przechowujący historię czatu dla każdego kanału w celu zachowania kontekstu rozmowy
chat_sessions = {}

@bot.event
async def on_ready():
    print(f"Zalogowano pomyślnie jako bot: {bot.user.name} (ID: {bot.user.id})")
    # Ustawienie statusu bota na Discordzie
    await bot.change_presence(activity=discord.Game(name="Rozmowa z Gemini AI | Napisz coś!"))

@bot.event
async def on_message(message):
    # Ignoruj wiadomości wysyłane przez samego bota
    if message.author == bot.user:
        return

    # Sprawdź, czy bot został oznaczony (wzmianka @bot) lub wiadomość została napisana na kanale prywatnym DM
    is_mentioned = bot.user in message.mentions
    is_dm = isinstance(message.channel, discord.DMChannel)

    if is_mentioned or is_dm:
        # Usuwamy wzmiankę bota z tekstu, aby nie przekazywać jej do sztucznej inteligencji
        prompt = message.content.replace(f"<@!{bot.user.id}>", "").replace(f"<@{bot.user.id}>", "").trim() if hasattr(message.content, "trim") else message.content.replace(f"<@!{bot.user.id}>", "").replace(f"<@{bot.user.id}>", "").strip()
        
        if not prompt:
            await message.reply("Słucham Cię! O co chciałbyś zapytać?")
            return

        async with message.channel.typing():
            try:
                # Pobierz lub utwórz sesję czatu dla danego kanału (obsługa pamięci kontekstu)
                channel_id = str(message.channel.id)
                if channel_id not in chat_sessions:
                    chat_sessions[channel_id] = model.start_chat(history=[])
                
                chat = chat_sessions[channel_id]
                # Wysłanie pytania do Gemini i odebranie odpowiedzi
                response = chat.send_message(prompt)
                response_text = response.text

                # Discord ma limit 2000 znaków na jedną wiadomość.
                # Jeśli odpowiedź AI jest dłuższa, dzielimy ją na mniejsze części.
                if len(response_text) > 2000:
                    for i in range(0, len(response_text), 2000):
                        await message.channel.send(response_text[i:i+2000])
                else:
                    await message.reply(response_text)

            except Exception as e:
                print(f"Błąd Gemini API: {e}")
                await message.reply("Przepraszam, wystąpił problem podczas przetwarzania zapytania przez AI. Upewnij się, że klucz API Gemini jest poprawny.")

    # Pozwala na poprawne działanie standardowych komend (np. !stworz)
    await bot.process_commands(message)

# Komenda do automatycznego tworzenia kanałów i kategorii
@bot.command(name="stworz")
@commands.has_permissions(manage_channels=True)
async def create_channels(ctx, category_name: str, channel_name: str, max_users: int = 0):
    """
    Tworzy nową kategorię, kanał tekstowy oraz kanał głosowy z limitem osób.
    Użycie: !stworz [NazwaKategorii] [NazwaKanalu] [LimitOsobGlosowego]
    Przykład: !stworz Gry CS-GO 3
    """
    guild = ctx.guild

    try:
        # 1. Tworzenie lub pobranie kategorii
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            category = await guild.create_category(category_name)
            await ctx.send(f"Utworzono nową kategorię: **{category_name}**")

        # 2. Tworzenie kanału tekstowego w tej kategorii
        text_channel = await guild.create_text_channel(name=channel_name.lower(), category=category)
        await ctx.send(f"Utworzono kanał tekstowy: {text_channel.mention} w kategorii **{category_name}**")

        # 3. Tworzenie kanału głosowego w tej kategorii z opcjonalnym limitem osób
        voice_channel_name = f"{channel_name}-voice"
        limit = None if max_users <= 0 else max_users
        
        voice_channel = await guild.create_voice_channel(
            name=voice_channel_name,
            category=category,
            user_limit=limit
        )
        
        limit_text = f"bez limitu miejsc" if max_users <= 0 else f"z limitem {max_users} osób"
        await ctx.send(f"Utworzono kanał głosowy: **{voice_channel_name}** ({limit_text})")

    except Exception as e:
        await ctx.send(f"Wystąpił błąd podczas tworzenia kanałów: {e}")

@create_channels.error
async def create_channels_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Nie masz uprawnień `Zarządzanie kanałami` (Manage Channels) do użycia tej komendy!")
    else:
        await ctx.send(f"Błąd komendy: {error}")

# Komenda do czyszczenia wiadomości na kanale
@bot.command(name="wyczysc")
@commands.has_permissions(manage_messages=True)
async def clear_messages(ctx, amount: int = 100):
    """
    Usuwa określoną liczbę wiadomości z kanału (domyślnie 100).
    Użycie: !wyczysc [LiczbaWiadomosci]
    Przykład: !wyczysc 50
    """
    try:
        # Usuwamy najpierw samą komendę wywołującą, a potem 'amount' wiadomości
        deleted = await ctx.channel.purge(limit=amount + 1)
        # Krótka informacja zwrotna, która usunie się po 3 sekundach
        await ctx.send(f"Pomyślnie usunięto {len(deleted) - 1} wiadomości.", delete_after=3.0)
    except Exception as e:
        await ctx.send(f"Wystąpił błąd podczas usuwania wiadomości: {e}")

@clear_messages.error
async def clear_messages_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Nie masz uprawnień `Zarządzanie wiadomościami` (Manage Messages) do użycia tej komendy!")
    else:
        await ctx.send(f"Błąd komendy: {error}")

# Uruchomienie bota
if __name__ == "__main__":
    if not DISCORD_TOKEN or not GEMINI_API_KEY:
        print("BŁĄD: Brak kluczy w pliku kody.txt! Upewnij się, że utworzyłeś plik kody.txt z parametrami token oraz api.")
    else:
        bot.run(DISCORD_TOKEN)
