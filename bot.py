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
LOGS_CHANNEL_ID = 1466330191117815829
RP_TIMES = ['15:50', '21:50', '03:50']

intents = discord.Intents.all() # Full power intents
bot = commands.Bot(command_prefix="!", intents=intents)

async def send_log(title, description, color=0x3498db):
    try:
        log_ch = bot.get_channel(LOGS_CHANNEL_ID)
        if log_ch:
            embed = discord.Embed(title=title, description=description, color=color)
            embed.timestamp = datetime.now(pytz.timezone('Asia/Kolkata'))
            await log_ch.send(embed=embed)
    except: pass

class LuxuryView(discord.ui.View):
    def __init__(self, voice_link, max_slots, title="Event"):
        super().__init__(timeout=None) 
        self.max_slots = max_slots
        self.title = title
        self.current_members = []
        self.is_disabled = False 
        self.add_item(discord.ui.Button(label="🔊 Join Voice", url=voice_link, style=discord.ButtonStyle.link))

    async def auto_disable(self, message):
        await asyncio.sleep(600) 
        if not self.is_disabled:
            self.is_disabled = True
            for item in self.children:
                if not hasattr(item, 'url'): item.disabled = True
            try:
                p_list = "\n".join([f"› {m.mention}" for m in self.current_members]) or "*No one registered*"
                embed = message.embeds[0]
                embed.description = "─── ⋆⋅☆⋅⋆ ───\n🚫 **EVENT IS OVER | REGISTRATION CLOSED**\nTime limit exceeded (10 Mins).\n─── ⋆⋅☆⋅⋆ ───"
                embed.set_field_at(0, name=f"👥 Final Participants ({len(self.current_members)})", value=p_list, inline=False)
                await message.edit(embed=embed, view=self)
                await send_log("⏰ Auto-Closed", f"Event **{self.title}** closed.", color=0xe67e22)
            except: pass

    @discord.ui.button(label="✨ Register", style=discord.ButtonStyle.success)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.is_disabled: return await interaction.response.send_message("❌ Closed!", ephemeral=True)
        await interaction.response.defer()
        if interaction.user in self.current_members: return await interaction.followup.send("❌ Already registered!", ephemeral=True)
        if len(self.current_members) >= self.max_slots: return await interaction.followup.send("🚫 Full!", ephemeral=True)
        self.current_members.append(interaction.user)
        await send_log("✅ Registered", f"**{interaction.user}** -> **{self.title}**")
        try: await interaction.user.send(f"✅ Registered for **{self.title}**!")
        except: pass
        await self.update_ui(interaction)

    @discord.ui.button(label="❌ Leave", style=discord.ButtonStyle.danger)
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.is_disabled: return await interaction.response.send_message("❌ Over!", ephemeral=True)
        await interaction.response.defer()
        if interaction.user not in self.current_members: return await interaction.followup.send("❌ Not in list!", ephemeral=True)
        self.current_members.remove(interaction.user)
        await send_log("⚠️ Left", f"**{interaction.user}** left **{self.title}**")
        try: await interaction.user.send(f"⚠️ Left **{self.title}**.")
        except: pass
        await self.update_ui(interaction)

    @discord.ui.button(label="🛑 End Event", style=discord.ButtonStyle.secondary)
    async def end_event(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Admin Only!", ephemeral=True)
        self.is_disabled = True
        p_list = "\n".join([f"› {m.mention}" for m in self.current_members]) or "*No one registered*"
        self.clear_items()
        for item in self.children:
             if hasattr(item, 'url'): self.add_item(item)
        embed = interaction.message.embeds[0]
        embed.description = "─── ⋆⋅☆⋅⋆ ───\n🏁 **EVENT IS OVER | REGISTRATION CLOSED**\nEnded by Admin.\n─── ⋆⋅☆⋅⋆ ───"
        embed.set_field_at(0, name=f"👥 Final Participants ({len(self.current_members)})", value=p_list, inline=False)
        await interaction.response.edit_message(embed=embed, view=None)
        await send_log("🛑 Ended", f"Admin **{interaction.user}** ended **{self.title}**.")

    async def update_ui(self, interaction):
        p_list = "\n".join([f"› {m.mention}" for m in self.current_members]) or "*Waiting...*"
        embed = interaction.message.embeds[0]
        embed.set_field_at(0, name=f"👥 Participants ({len(self.current_members)}/{self.max_slots})", value=p_list, inline=False)
        await interaction.edit_original_response(embed=embed, view=self)

@bot.command()
async def setup_event(ctx):
    def check(m): return m.author == ctx.author and m.channel == ctx.channel
    try:
        # Step 1: Force ID
        await ctx.send("❓ **Step 1:** Kaunse channel mein bheju? (Us channel ki **ID copy karke paste karein**, mention mat karein)")
        msg = await bot.wait_for('message', check=check, timeout=60.0)
        ch_id = int(msg.content.strip())
        target_channel = bot.get_channel(ch_id)

        # Step 2: Slots
        await ctx.send("❓ **Step 2:** Kitne members?")
        msg = await bot.wait_for('message', check=check, timeout=60.0)
        slots = int(msg.content)

        # Step 3: VC Link
        await ctx.send("❓ **Step 3:** VC Link?")
        msg = await bot.wait_for('message', check=check, timeout=60.0)
        vc_link = msg.content

        # Step 4: Title
        await ctx.send("❓ **Step 4:** Title?")
        msg = await bot.wait_for('message', check=check, timeout=60.0)
        event_title = msg.content

        embed = discord.Embed(title=f"🏆 {event_title.upper()}", color=0x00ff00)
        embed.description = "─── ⋆⋅☆⋅⋆ ───\n✨ **REGISTRATION OPEN (10 MINS)**\n─── ⋆⋅☆⋅⋆ ───"
        embed.add_field(name=f"👥 Participants (0/{slots})", value="*Waiting...*", inline=False)
        embed.set_image(url=ANIMATED_GIF_URL)
        
        view = LuxuryView(vc_link, slots, title=event_title)
        await target_channel.send("@everyone", embed=embed, view=view)
        await ctx.send(f"✅ Posted in {target_channel.mention}!")

    except Exception as e:
        await ctx.send(f"❌ Error: ID sahi se daalo! ({e})")

@tasks.loop(minutes=1)
async def auto_loop():
    IST = pytz.timezone('Asia/Kolkata')
    now = datetime.now(IST)
    if now.minute == 0:
        ch = bot.get_channel(INFORMAL_CHANNEL_ID)
        if ch:
            view = LuxuryView(INFORMAL_VOICE, 10, title="Informal")
            embed = discord.Embed(title="👑 INFORMAL", color=0x5865F2)
            embed.description = "─── ⋆⋅☆⋅⋆ ───\n✨ **REGISTRATION OPEN (10 MINS)**\n─── ⋆⋅☆⋅⋆ ───"
            embed.add_field(name="👥 Participants (0/10)", value="*Waiting...*", inline=False)
            embed.set_image(url=ANIMATED_GIF_URL)
            await ch.send("@everyone", embed=embed, view=view)

    if now.strftime("%H:%M") in RP_TIMES:
        ch = bot.get_channel(RP_FACTORY_CHANNEL_ID)
        if ch:
            view = LuxuryView(RP_VOICE, 30, title="RP Factory")
            embed = discord.Embed(title="🏭 RP FACTORY", color=0xffd700)
            embed.description = "─── ⋆⋅☆⋅⋆ ───\n🔥 **REGISTRATION OPEN (10 MINS)**\n─── ⋆⋅☆⋅⋆ ───"
            embed.add_field(name="👥 Participants (0/30)", value="*Waiting...*", inline=False)
            embed.set_image(url=ANIMATED_GIF_URL)
            await ch.send("@everyone", embed=embed, view=view)

@bot.event
async def on_ready():
    print(f"✅ Bot Live: {bot.user}")
    if not auto_loop.is_running(): auto_loop.start()

keep_alive()
bot.run(TOKEN)
