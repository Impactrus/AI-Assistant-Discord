# AI-Assistant-Discord

Inteligentny bot na Discorda zintegrowany z modelem językowym **Google Gemini (gemini-pro)**, posiadający zaawansowane możliwości asystenta konwersacyjnego oraz funkcje automatycznego zarządzania i moderacji serwerem (tworzenie kategorii, kanałów tekstowych oraz dedykowanych kanałów głosowych z limitami użytkowników).

---

## 🚀 Główne Funkcjonalności

### 1. Asystent Gemini AI (Chat z kontekstem)
* Bot reaguje na oznaczenie go na kanale (np. `@Bot napisz wiersz o programowaniu`) lub na prywatnych wiadomościach DM.
* **Obsługa pamięci kontekstu (Conversational Memory)**: Bot pamięta przebieg rozmowy na danym kanale, co pozwala na prowadzenie naturalnego dialogu (np. dopytywanie o szczegóły wcześniejszej odpowiedzi).
* Automatyczne dzielenie odpowiedzi przekraczających limit 2000 znaków na Discordzie.

### 2. Automatyzacja tworzenia kanałów (`!stworz`)
* Bot pozwala moderatorom (z uprawnieniem `Zarządzanie kanałami`) na szybkie tworzenie struktur serwera.
* **Komenda**: `!stworz [NazwaKategorii] [NazwaKanalu] [LimitOsobGlosowego]`
* **Działanie**: Bot automatycznie tworzy nową kategorię, w niej kanał tekstowy oraz powiązany kanał głosowy z ustawionym limitem miejsc (np. maks. 3 osoby).

---

## 🛠️ Architektura i Instalacja

Bot został napisany w języku **Python 3** z wykorzystaniem oficjalnych bibliotek Discord API oraz Google Generative AI.

### 1. Wymagania wstępne
* Zainstalowany Python 3.8 lub nowszy.
* Założone konto deweloperskie na Discordzie i utworzona aplikacja bota.
* Klucz API Gemini wygenerowany w Google AI Studio.

### 2. Pobranie i konfiguracja
1. Sklonuj to repozytorium na swój komputer.
2. Zmień nazwę pliku `.env.template` na `.env` i uzupełnij swoje tajne klucze:
   ```env
   DISCORD_TOKEN=twoj_token_bota_discord
   GEMINI_API_KEY=twoj_klucz_api_gemini
   ```
3. Zainstaluj wymagane zależności:
   ```bash
   pip install -r requirements.txt
   ```
4. Uruchom bota:
   ```bash
   python main.py
   ```

---

## 🔌 Jak dodać bota na swój serwer?

1. Wejdź na [Discord Developer Portal](https://discord.com/developers/applications).
2. Wybierz swoją aplikację i przejdź do zakładki **OAuth2** -> **URL Generator**.
3. W sekcji **Scopes** zaznacz: `bot`.
4. W sekcji **Bot Permissions** zaznacz:
   * `Send Messages`
   * `Read Message History`
   * `Manage Channels` (wymagane do komendy `!stworz`)
5. Skopiuj wygenerowany link na dole strony, wklej go do przeglądarki i dodaj bota na wybrany serwer!
