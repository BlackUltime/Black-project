from threading import Thread
from flask import Flask

app = Flask("")


@app.route("/")
def home():
  return "Bot OK"


Thread(target=lambda: app.run(host="0.0.0.0", port=10000)).start()
import os
import discord
from discord import app_commands
import cloudscraper

# ==============================================================================
# ⚙️ CONFIGURATION
# ==============================================================================

# ⚠️ TON TOKEN DISCORD
TOKEN = os.environ.get("DISCORD_TOKEN")

# ID du rôle attribué si K/D REDSEC >= 3.0
ROLE_VERIFIE_ID = 1541694736471953449

# Clé API Tracker.gg (sans espaces autour)
TRN_API_KEY = "29148dc4-1db0-4544-ab0c-37f335170198".strip()

# ==============================================================================
# 🚀 INITIALISATION DU BOT
# ==============================================================================

class MonBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        print("✅ Commandes Slash enregistrées.")

bot = MonBot()

@bot.event
async def on_ready():
    print(f"🤖 Bot en ligne : {bot.user.name}")

# ==============================================================================
# 🎮 COMMANDE /VERIFIER (MULTI-PLATEFORME)
# ==============================================================================

@bot.tree.command(name="verifier", description="Vérifie ton K/D 3.0+ sur Battlefield REDSEC")
@app_commands.describe(
    pseudo="Ton pseudo exact (EA, PSN ou Gamertag)",
    plateforme="Sélectionne ta plateforme de jeu"
)
@app_commands.choices(plateforme=[
    app_commands.Choice(name="PC (EA / Origin)", value="origin"),
    app_commands.Choice(name="PlayStation (PSN)", value="psn"),
    app_commands.Choice(name="Xbox (Gamertag)", value="xbl")
])
async def verifier(interaction: discord.Interaction, pseudo: str, plateforme: app_commands.Choice[str]):
    await interaction.response.defer(ephemeral=True)

    url = f"https://public-api.tracker.gg/v2/bf6/standard/profile/{plateforme.value}/{pseudo}"
    headers = {
        "TRN-Api-Key": TRN_API_KEY,
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    try:
        # Utilisation de cloudscraper pour contourner la protection Cloudflare
        scraper = cloudscraper.create_scraper()
        response = scraper.get(url, headers=headers, timeout=10)

        if response.status_code == 401:
            await interaction.followup.send(
                "⚠️ **Erreur 401 :** La clé API est refusée par TrackerGG. Vérifie qu'elle est bien active sur https://tracker.gg/developers"
            )
            return
        elif response.status_code == 404:
            await interaction.followup.send(
                f"❌ Joueur **{pseudo}** introuvable sur **{plateforme.name}**. Vérifie l'orthographe et la confidentialité de tes stats."
            )
            return
        elif response.status_code != 200:
            await interaction.followup.send(
                f"⚠️ Erreur de l'API (Code HTTP {response.status_code})."
            )
            return

        data = response.json()
        segments = data.get("data", {}).get("segments", [])
        
        kd_ratio = 0.0
        found = False

        for segment in segments:
            attributes = segment.get("attributes", {})
            stats = segment.get("stats", {})

            if attributes.get("mode") in ["redsec", "br", "battleroyale"]:
                kd_ratio = stats.get("kdRatio", {}).get("value", 0.0)
                found = True
                break

        if not found and segments:
            kd_ratio = segments[0].get("stats", {}).get("kdRatio", {}).get("value", 0.0)

        if kd_ratio >= 3.0:
            role = interaction.guild.get_role(ROLE_VERIFIE_ID)
            if role:
                await interaction.user.add_roles(role)
                await interaction.followup.send(
                    f"✅ **Vérification réussie !** Ton K/D REDSEC ({plateforme.name}) est de **{kd_ratio:.2f}**.\nLe rôle **{role.name}** t'a été attribué !"
                )
            else:
                await interaction.followup.send("⚠️ Le rôle est introuvable sur le serveur.")
        else:
            await interaction.followup.send(
                f"❌ **Accès refusé.** Ton K/D REDSEC actuel est de **{kd_ratio:.2f}** (minimum requis : **3.0**)."
            )

    except Exception as e:
        await interaction.followup.send(f"⚠️ Erreur lors de la vérification : `{e}`")

if __name__ == "__main__":
    bot.run(TOKEN)
