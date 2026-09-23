# Noel AI på en riktig server (så Hugo kommer in dygnet runt)

Appen ligger på en liten Linux-server som alltid är på. Portföljer och noteringar
ligger på serverns disk (försvinner inte), och data uppdateras automatiskt varje
dag **17:00** (kurser, panel, statistik, signaler) — plus en körning **18:00** som
skriver över med de slutliga slutkurserna (Stockholmsbörsen stänger 17:30).

## Det du gör (5 minuter)

1. Skapa ett konto på <https://www.hetzner.com/cloud> och en server:
   - **Image:** Ubuntu 24.04 · **Typ:** CX22 (x86, 4 GB RAM, ~4–5 €/mån) eller större — den dagliga uppdateringen tar ~2 min och högst ~2,2 GB RAM (uppmätt)
   - **SSH-nyckel:** lägg in den publika nyckeln som Claude gav dig (rad som börjar `ssh-ed25519 …`)
2. Skicka serverns **IP-adress** till Claude.

## Det Claude gör sen

```bash
deploy/deploy.sh <ip> --with-data     # första gången: kod + databaser + installation
deploy/deploy.sh <ip>                 # senare uppdateringar av koden (rör aldrig portföljerna)
```

Adressen blir `https://<ip-med-bindestreck>.sslip.io` (automatiskt HTTPS). Vill ni ha
en egen domän: peka en A-post på IP:n och kör `deploy.sh <ip> --domain noel.exempel.se`.

## Regler att hålla i huvudet

- **Servern är sanningen för portföljerna.** Efter go-live: handla på den publika adressen.
  `deploy.sh` skriver aldrig över `paper_trades.duckdb` på servern.
- Lösenorden (`MARC_USER_JONAS_PASSWORD`, `MARC_USER_HUGO_PASSWORD`) hämtas ur din lokala
  `.env` och hamnar bara i `/etc/noel.env` på servern (läsbar endast av root). Byt dem
  till något längre nu när sidan är publik — inloggningen låser efter 5 felförsök, men
  korta lösenord är ändå gissningsbara.
- Riktig Trends/nyheter (attention) hämtas **inte** av den dagliga körningen (Google
  rate-limitar och blockerar serverIP:n). Den delen körs vid behov från din Mac
  (`marc pipeline --source yfinance --attention-source real`) och databasen skickas upp
  med `deploy.sh <ip> --with-data`. Kurser, panel, statistik och signaler är alltid färska.

## Felsökning (på servern)

```bash
ssh -i ~/.ssh/noel_deploy_ed25519 root@<ip>
systemctl status noel-app                 # körs appen?
journalctl -u noel-app -n 50              # appens logg
tail -50 /var/log/noel-refresh.log        # senaste dagliga uppdateringarna
systemctl list-timers noel-refresh.timer  # när nästa körning är
systemctl start noel-refresh.service      # kör uppdateringen nu
```

Misslyckas en daglig körning behålls gårdagens databas (bygget sker på en kopia som
bara byts in när allt gått bra).
