import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime
import pytz
import os
from flask import Flask
from threading import Thread

# --- Render 24/7 Setup ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- Configuration ---
TOKEN = os.getenv("TOKEN")
ANIMATED_GIF_URL = "https://cdn.discordapp.com/attachments/1427316841482551306/1465341734493093911/2544-car.gif" 
INFORMAL_VOICE = "https://discord.com/channels/1416139064947642522/1464906449716121706"
RP_VOICE = "https://discord.com/channels/1416139064947642522/1464906407949238396"
INFORMAL_CHANNEL_ID = 1464906135546101975
RP_FACTORY_CHANNEL_ID = 1464906118437408861
RP_TIMES = ['15:50', '21:50', '03:50']

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- 🎭 LUXURY UI SYSTEM ---
class LuxuryView(discord.ui.View):
    def __init__(self, voice_link, max_slots, is_rp=False, title="Event"):
        super().__init__(timeout=None) 
        self.max_slots = max_slots
        self.is_rp = is_rp
        self.title = title
        self.current_members = []
        self.message = None
        self.add_item(discord.ui.Button(label="🔊 Join Voice", url=voice_link, style=discord.ButtonStyle.link))

    async def auto_disable(self):
        """10 Minute Timer to Lock Buttons"""
        await asyncio.sleep(600) 
        for item in self.children:
            if not hasattr(item, 'url'):
                item.disabled = True
        if self.message:
            try: await self.message.edit(view=self)
            except: pass

    @discord.ui.button(label="✨ Register", style=discord.ButtonStyle.success)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer() # Interaction Failed Fix
        if interaction.user in self.current_members:
            return await interaction.followup.send("❌ Pehle se register ho!", ephemeral=True)
        if len(self.current_members) >= self.max_slots:
            return await interaction.followup.send("🚫 Slots full!", ephemeral=True)
        
        self.current_members.append(interaction.user)
        try: 
            await interaction.user.send(f"✅ Success! Tumne **{self.title}** ke liye register kar liya hai.")
        except: pass
        await self.update_ui(interaction)

    @discord.ui.button(label="❌ Leave", style=discord.ButtonStyle.danger)
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if interaction.user not in self.current_members:
            return await interaction.followup.send("❌ List mein nahi ho!", ephemeral=True)
        
        self.current_members.remove(interaction.user)
        try:
            await interaction.user.send(f"⚠️ Tumne **{self.title}** se apna naam hata liya hai.")
        except: pass
        await self.update_ui(interaction)

    async def update_ui(self, interaction):
        if self.is_rp:
            main = self.current_members[:25]
            subs = self.current_members[25:]
            p_list = "**Main Squad (25):**\n" + ("\n".join([f"• {m.mention}" for m in main]) or "*Waiting...*")
            if subs: p_list += "\n\n**Substitutes (5):**\n" + "\n".join([f"• {m.mention}" for m in subs])
        else:
            p_list = "\n".join([f"• {m.mention}" for m in self.current_members]) or "*Waiting...*"

        embed = interaction.message.embeds[0]
        embed.set_field_at(0, name=f"👥 Participants ({len(self.current_members)}/{self.max_slots})", value=p_list, inline=False)
        await interaction.edit_original_response(embed=embed, view=self)

# --- ⏰ AUTO LOOP ---
@tasks.loop(minutes=1)
async def auto_loop():
    IST = pytz.timezone('Asia/Kolkata')
    now = datetime.now(IST)
    now_hm = now.strftime("%H:%M")

    # Informal (Every hour at :00)
    if now.minute == 0:
        ch = bot.get_channel(INFORMAL_CHANNEL_ID)
        if ch:
            embed = discord.Embed(title="👑 OFFICIAL INFORMAL", description="─── ⋆⋅☆⋅⋆ ───\nRegistration open! Join now.\n─── ⋆⋅☆⋅⋆ ───", color=0x2b2d31)
            embed.add_field(name="👥 Participants (0/10)", value="*Waiting...*", inline=False)
            embed.set_image(url=ANIMATED_GIF_URL)
            view = LuxuryView(INFORMAL_VOICE, 10, title="Informal")
            msg = await ch.send("@everyone", embed=embed, view=view)
            view.message = msg
            asyncio.create_task(view.auto_disable())

    # RP Loop (Fixed Timings)
    if now_hm in RP_TIMES:
        ch = bot.get_channel(RP_FACTORY_CHANNEL_ID)
        if ch:
            embed = discord.Embed(title="🏭 RP FACTORY", description="─── ⋆⋅☆⋅⋆ ───\nStarts in 10 mins! Register fast.\n─── ⋆⋅☆⋅⋆ ───", color=0xffd700)
            embed.add_field(name="👥 Participants (0/30)", value="*Waiting...*", inline=False)
            embed.set_image(url=ANIMATED_GIF_URL)
            view = LuxuryView(RP_VOICE, 30, is_rp=True, title="RP Factory")
            msg = await ch.send("@everyone", embed=embed, view=view)
            view.message = msg
            asyncio.create_task(view.auto_disable())

# --- 🛠️ COMMANDS ---
@bot.command()
@commands.has_permissions(administrator=True)
async def setup_event(ctx):
    def check(m): return m.author == ctx.author and m.channel == ctx.channel
    try:
        await ctx.send("📝 **Event Name?**")
        name = (await bot.wait_for('message', check=check, timeout=60)).content
        await ctx.send("🔢 **Slot Limit?**")
        limit = int((await bot.wait_for('message', check=check, timeout=60)).content)
        await ctx.send("🔊 **Voice Link?**")
        vc = (await bot.wait_for('message', check=check, timeout=60)).content

        embed = discord.Embed(title=f"🌟 {name.upper()}", color=0x00aaff)
        embed.add_field(name=f"👥 Participants (0/{limit})", value="*Waiting...*", inline=False)
        embed.set_image(url=ANIMATED_GIF_URL)
        view = LuxuryView(vc, limit, title=name)
        msg = await ctx.send("@everyone", embed=embed, view=view)
        view.message = msg
        asyncio.create_task(view.auto_disable())
    except:
        await ctx.send("❌ Error in setup.")

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is Online and Ready!")
    if not auto_loop.is_running(): auto_loop.start()

keep_alive()
bot.run(TOKEN)
