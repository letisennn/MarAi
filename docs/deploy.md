# Ge Hugo (eller vem som helst) en länk till appen

> **Vald väg (2026-09-24, Jonas): egen liten server.** Se [`deploy/README.md`](../deploy/README.md) —
> alltid på, portföljer/noteringar på serverns disk och daglig uppdatering 17:00. Alternativen
> nedan är kvar som bakgrund; Alternativ A (Streamlit Cloud) valdes bort eftersom disken där
> töms vid omstart och portföljerna då skulle försvinna.

Appen är en lokal Streamlit-server på din Mac (`localhost:8501`) — den syns bara
på din egen dator. För att någon annan ska komma åt den behövs ett av följande.
Datan är syntetisk, så inget känsligt läcker, men lås ändå med ett lösenord om
länken lämnar er två.

## Alternativ A — Streamlit Community Cloud (stabil länk, rekommenderas)

Gratis. Ger en fast `https://<namn>.streamlit.app`-adress som funkar även när din
dator är avstängd. Appen bygger sin egen databas vid första besöket
(`MARC_AUTOBUILD`).

1. Skapa ett **privat** GitHub-repo (t.ex. `marc-ai`). Ingen data följer med —
   `data/marc.duckdb` är gitignorerad, seed-datan i `data/seed/` är med.
2. Peka repot hit och pusha:
   ```
   cd "~/Marc AI"
   git remote add origin git@github.com:<du>/marc-ai.git
   git push -u origin main
   ```
3. Gå till <https://share.streamlit.io> → **New app** → välj repot, branch `main`,
   main file `app/Home.py`.
4. **Advanced settings → Secrets**, klistra in:
   ```
   MARC_AUTOBUILD = "1"
   MARC_USER_JONAS_PASSWORD = "..."
   MARC_USER_HUGO_PASSWORD = "..."
   ```
5. Deploy. Första laddningen tar ~1–2 min (bygger databasen), sedan är den snabb.
6. **Settings → Sharing:** sätt appen till privat och lägg till Hugos
   Google-mail. (Då behövs inte ens lösenordet, men ha kvar det.)

Skicka Hugo: länken + hans lösenord.

## Alternativ B — snabb tunnel (tillfällig länk, din dator måste vara på)

Ger en länk nu, men den byts vid varje omstart och din Mac + servern måste vara
igång. Kräver att du installerar ett verktyg (nekades åt mig automatiskt).

```
brew install cloudflared           # engångs
# kör appen (lösenorden läses från .env, se .env.example):
uv run streamlit run app/Home.py --server.port 8501
# i ett annat terminalfönster:
cloudflared tunnel --url http://localhost:8501
```

`cloudflared` skriver ut en `https://….trycloudflare.com`-adress — skicka den
till Hugo, han loggar in med sitt eget lösenord. (`npx localtunnel --port 8501`
eller `ngrok http 8501` fungerar likadant.)

## Alternativ C — samma nätverk

Om Hugo sitter på samma wifi:

```
uv run streamlit run app/Home.py --server.address 0.0.0.0 --server.port 8501
```

Ge honom `http://<din-lokala-IP>:8501` (syns i Streamlits startutskrift som
"Network URL").

## Inloggningen

Sätt `MARC_USER_JONAS_PASSWORD` och `MARC_USER_HUGO_PASSWORD` (i `.env`
lokalt, eller Streamlit Secrets hostat) så kräver appen inloggning som
antingen Jonas eller Hugo innan något visas — och vem som loggat in styr
vems separata pappersportfölj man handlar i (`marc.paper`). Är ingen av dem
satt (som lokalt utan `.env`) släpps Jonas igenom automatiskt. Inte riktig
säkerhet i djupare mening — bara så att en delad länk inte ligger helt öppen
och att man inte handlar på fel persons konto av misstag.
