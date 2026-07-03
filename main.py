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

        # Analiza intencji za pomocą słów kluczowych w zapytaniu do bota
        prompt_lower = prompt.lower()
        
        # 1. Intencja: CZYSZCZENIE KANAŁU
        if "wyczyść" in prompt_lower or "usun" in prompt_lower or "usuń" in prompt_lower:
            if "wiadomo" in prompt_lower or "kanał" in prompt_lower or "czat" in prompt_lower or "czyszcz" in prompt_lower:
                if message.author.guild_permissions.manage_messages:
                    async with message.channel.typing():
                        try:
                            # Wyciągamy cyfry z tekstu (np. "wyczyść 50" -> 50)
                            import re
                            numbers = re.findall(r'\d+', prompt)
                            limit_amount = int(numbers[0]) if numbers else 100
                            
                            # Czyszczenie wiadomości
                            deleted = await message.channel.purge(limit=limit_amount + 1)
                            await message.channel.send(f"🧹 Pomyślnie wyczyszczono {len(deleted) - 1} wiadomości na żądanie administratora.", delete_after=5.0)
                            return
                        except Exception as e:
                            await message.reply(f"Nie udało się wyczyścić wiadomości: {e}")
                            return
                else:
                    await message.reply("Nie masz uprawnień do zarządzania wiadomościami, aby zlecić czyszczenie kanału.")
                    return

        # 2. Intencja: TWORZENIE KANAŁÓW / ZAKŁADEK
        if "stwórz" in prompt_lower or "stworz" in prompt_lower or "utwórz" in prompt_lower or "utworz" in prompt_lower:
            if "kanał" in prompt_lower or "kategori" in prompt_lower or "zakładk" in prompt_lower or "zakladk" in prompt_lower:
                if message.author.guild_permissions.manage_channels:
                    async with message.channel.typing():
                        try:
                            # Tworzymy systemowy prompt do Gemini, żeby wyciągnął parametry w czystym formacie JSON
                            system_instruction = (
                                "Zanalizuj poniższą prośbę użytkownika o stworzenie kanałów na Discordzie. "
                                "Zwróć odpowiedź WYŁĄCZNIE w formacie JSON bez żadnych dodatkowych opisów, markdownu ani znaków ```. "
                                "Format JSON ma wyglądać dokładnie tak:\n"
                                "{\n"
                                "  \"kategoria\": \"Nazwa Kategorii (lub puste jeśli brak)\",\n"
                                "  \"kanal_tekstowy\": \"nazwa-kanalu-tekstowego (lub puste jeśli brak)\",\n"
                                "  \"kanal_glosowy\": \"nazwa-kanalu-glosowego (lub puste jeśli brak)\",\n"
                                "  \"limit_osob\": 0 (lub cyfra limitu dla głosowego)\n"
                                "}\n\n"
                                f"Prośba: {prompt}"
                            )
                            ai_response = model.generate_content(system_instruction).text.strip()
                            # Usuwamy ewentualne formatowanie markdownowe, jeśli AI je dodało
                            ai_response = ai_response.replace("```json", "").replace("```", "").strip()
                            
                            import json
                            data = json.loads(ai_response)
                            
                            guild = message.guild
                            category_name = data.get("kategoria")
                            text_name = data.get("kanal_tekstowy")
                            voice_name = data.get("kanal_glosowy")
                            user_limit = data.get("limit_osob", 0)
                            
                            created_info = []
                            category = None
                            
                            # Tworzenie kategorii
                            if category_name:
                                category = discord.utils.get(guild.categories, name=category_name)
                                if not category:
                                    category = await guild.create_category(category_name)
                                    created_info.append(f"kategorię **{category_name}**")
                            
                            # Tworzenie kanału tekstowego
                            if text_name:
                                await guild.create_text_channel(name=text_name.lower().replace(" ", "-"), category=category)
                                created_info.append(f"kanał tekstowy **{text_name.lower().replace(' ', '-')}**")
                                
                            # Tworzenie kanału głosowego
                            if voice_name:
                                limit = None if user_limit <= 0 else user_limit
                                await guild.create_voice_channel(name=voice_name.replace(" ", "-"), category=category, user_limit=limit)
                                limit_txt = "bez limitu" if user_limit <= 0 else f"limit {user_limit} osób"
                                created_info.append(f"kanał głosowy **{voice_name}** ({limit_txt})")
                                
                            if created_info:
                                await message.reply(f"🤖 Rozkaz wykonany! Pomyślnie stworzyłem: {', '.join(created_info)}.")
                            else:
                                await message.reply("Nie zrozumiałem dokładnie, jakie kanały mam stworzyć. Spróbuj napisać np.: 'stwórz kategorię Gry a w niej kanał głosowy CS z limitem 3 osób'.")
                            return
                        except Exception as e:
                            await message.reply(f"Błąd podczas automatycznego tworzenia kanałów: {e}")
                            return
                else:
                    await message.reply("Nie masz uprawnień do zarządzania kanałami na tym serwerze.")
                    return

        # Domyślny bieg: Standardowa rozmowa z Gemini
        async with message.channel.typing():
            try:
                channel_id = str(message.channel.id)
                if channel_id not in chat_sessions:
                    chat_sessions[channel_id] = model.start_chat(history=[])
                
                chat = chat_sessions[channel_id]
                response = chat.send_message(prompt)
                response_text = response.text

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
