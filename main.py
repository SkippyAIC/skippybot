import discord
from discord.ext import commands
from discord.utils import get
import os
import pageParser

from difflib import get_close_matches
from requests import post
from random import randint, choice as randChoice
from json import loads

##from dotenv import load_dotenv
##from discord_slash import SlashCommand, SlashContext
##from discord_slash.utils.manage_commands import create_option
import time
import re

##load_dotenv()
bot = commands.Bot(command_prefix="./", help_command = None)
cooldown = {}
apikey = os.getenv("apikey")
ExceptionDict = {
    "FormattingException": "{0} returned a formatting exception! This often occurs due to format quirks that require manual embed refinement to fix. The Skippy.aic Developer has been notified, and {0} will be fixed soon.",
    "NotExisting": "{} doesn't exist yet!",
    "SlotGoblinException": "{} returned a Slot Goblin exception. This is usually due to issues on Wikidot's servers, and prevents an SCP from being viewed entirely."
}

usedQuotes = []
quotes = []
termDict = {} 
index = {}

devID = 0
reportChannelID = 0

@bot.event
async def on_ready():
    ## Changes bot activity to "Watching the Foundation's database. ./scphelp"
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="the Foundation's database. ./scphelp"))

def initalizeItems():
    termFile = open("termDict.json", "r")
    quoteFile = open("quotes.txt", "r")
    scp001stuff = open("001index.json", "r")
    
    for i in quoteFile.readlines():
        i = i.rstrip()
        quotes.append(i)
        
    indexRead = loads(scp001stuff.read())
    termRead = loads(termFile.read())
    
    for key, item in termRead.items():
        termDict[key] = item
    for key, item in indexRead.items():
        index[key] = item
        
    termFile.close()
    quoteFile.close()
    scp001stuff.close()
    
    
@commands.cooldown(1, 10, commands.BucketType.user)
@bot.command(pass_context=True)
async def scp(ctx, arg: str, skipBlackMoon = False):

    ## ./scp article pulling command, skipBlackMoon can be invoked by other functions to skip the "Black Moon authorization check". Primarily used by the autoEmbed function to remain unintrusive.
    ## Converts argument to entirely-lowercase to ensure URL compatibility. EX article URLs do not contain capitals, and will not be requested correctly.
    arg = arg.lower()
    if arg == "random":
        arg = str(randint(1, 6999))
    
    if len(arg) == 1:
        arg = "00" + arg
    elif len(arg) == 2:
        arg = "0" + arg
        
    SCPInfo = pageParser.SCP(item=arg)
    
    if arg == "001":
        await Index001(ctx) ##If ./scp 001 is given, the Index001 function is called to send the index to the user.
        return
    elif arg in index:
        if not skipBlackMoon:
            await blackMoon(ctx)
        if SCPInfo.color == 0:
            color = 0xff0000
        else:
            color = SCPInfo.color
    else:
        if SCPInfo.color == 0:
            color = await colorChecker(SCPInfo.obj)
        else:
            color = SCPInfo.color
        
    authors = ", ".join(i for i in SCPInfo.authors)
    
    if SCPInfo.embedName:
        title = SCPInfo.embedName.format(f"\nby {authors}")
    else:
        title = "{} - {}\nby {}"
    
    embed=discord.Embed(title=title.format(SCPInfo.number, SCPInfo.name, authors), url=SCPInfo.url, color=color)
    
    if SCPInfo.pic != "0":
        embed.set_image(url=SCPInfo.pic) ## Sets image if not str "0"
    
    if SCPInfo.adult:
        adultEmbed = discord.Embed(title="Adult Content Warning", description=f"{SCPInfo.number} contains adult content. {ctx.author.mention}, to read the content, please type 'yes'.", color=0xffff00)
        
        adultCheck = await awaitReply(ctx, embed=adultEmbed, adult=True) ## bot.wait_for function with adult bool value
        if not adultCheck:
            adultEmbed = discord.Embed(title="Check failed", description=f"Failed to type 'yes', not sending {SCPInfo.name}", color=0xffff00)
            await universalSend(ctx=ctx, embed=adultEmbed)
            return
    
    if SCPInfo.obj in ExceptionDict and not isinstance(SCPInfo.obj, tuple):
        ## If Object Class is a recognized exception, inform user. If exception is FormattingException,  autoreport to the reports channel.
        await universalSend(ctx, msg=ExceptionDict[SCPInfo.obj].format(SCPInfo.number))
        if SCPInfo.obj == "FormattingException":
            await scpreport(arg, SCPInfo.obj)
        return
    
    if SCPInfo.ACS or SCPInfo.flops:
        ## Both ACS and flops define SCPInfo.obj as a tuple object.
        embed.add_field(name="Object Class:", value=SCPInfo.obj[0], inline=False)
        embed.add_field(name="Disruption Class:", value=SCPInfo.obj[1], inline=False)
        if SCPInfo.ACS:
            ## Only ACS has Risk Class.
            embed.add_field(name="Risk Class:", value=SCPInfo.obj[2], inline=False)
        embed.add_field(name="Description:", value=SCPInfo.desc, inline=False)
    else:
        ## If not ACS or flops, SCPInfo.obj is treated as a normal string.
        embed.add_field(name="Object Class:", value=SCPInfo.obj, inline=False)
        embed.add_field(name="Description:", value=SCPInfo.desc, inline=False)
    
    footerSetup = '{}\n{}{}'
    if SCPInfo.rating == 9999:
        footerRating = ""
    else:
        footerRating = "Rating: {} • ".format(SCPInfo.rating)
    
    if len(quotes) == 0:
        for item in usedQuotes:
            quotes.append(item)
        usedQuotes.clear()
    
    if not SCPInfo.footerOverride:
        changeFooter = True
        randomQuote = randChoice(quotes)
        usedQuotes.append(randomQuote)
        quotes.remove(randomQuote)
        print(quotes, usedQuotes)
    else:
        changeFooter = False
        randomQuote = SCPInfo.footerOverride
    
    if SCPInfo.refined and not SCPInfo.hiderefined:
        footerFinish = "Refined by Skippy.aic Developer"
    elif SCPInfo.hiderefined:
        footerFinish = ""
    else:
        footerFinish = "Is this SCP bugged? Open an issue on Skippy.aic's GitHub".format(arg)
    
    footer = footerSetup.format(randomQuote, footerRating, footerFinish)
    
    embed.set_footer(text=footer)

    await universalSend(ctx=ctx, embed=embed, webhook=SCPInfo.webhook if SCPInfo.webhook else False, changeFooter=changeFooter)

async def scpreport(arg, exception):
    ## Takes context object and article number, if autoReport is True, then "Skippy.aic" is supplied in place of the user's ID.

    mentionDev = f"<@{devID}>"

    reportChannel = bot.get_channel(reportChannelID)
    
    if not os.path.exists(f"refined/{arg}.json"):
        await reportChannel.send(f"Reported SCP {mentionDev} \nSCP reported: {arg}\nException: {exception}")
        
@commands.cooldown(1, 10, commands.BucketType.user)
@bot.command(pass_context=True)
async def scpsearch(ctx, *args):
    arg = " ".join(i for i in args)
    url = "https://api.crom.avn.sh/graphql"
    query = '''{
  searchPages(
    query: "searchArg"
    filter: { anyBaseUrl: "http://scp-wiki.wikidot.com/scp-" }
  ) {
    url
    wikidotInfo {
      title
    }
  }
}'''.replace("searchArg", arg)

    json = {"query": query}
    findPage = post(url, json=json).json()
    pageData = findPage["data"]["searchPages"]

    if len(pageData) == 0:
        embed = discord.Embed(title="No articles found for term **'{}'**!".format(arg), description="Try using different search terms.", color=0xff0000)
        await universalSend(ctx=ctx, embed=embed, mention=True)
        return
        
    SCPRetrieved = pageData[0]["wikidotInfo"]["title"].replace("SCP-", "")
    await scp(ctx, arg=SCPRetrieved)
    
@commands.cooldown(1, 10, commands.BucketType.user)
@bot.command(pass_context=True)
async def term(ctx, *args):
    arg = " ".join(i.lower() for i in args)
    if arg == "random":
        arg = randChoice(list(termDict.keys()))
    termName = get_close_matches(arg, termDict.keys(), n=1, cutoff=.5)[0]
    print(termName)
    
    if len(termName) == 0:
        embed = discord.Embed(title="No definitions found for term **'{}'**!".format(arg), description="Try using different search terms.", color=0xff0000)
        await universalSend(ctx=ctx, embed=embed, mention=True)
        return
    
    termDefinition = dict(termDict)[termName]
    if isinstance(termDefinition, int):
        keys = list(termDict.keys())
        termName = keys[termDefinition]
        print(termName)
        termDefinition = dict(termDict)[termName]
        
    if len(quotes) == 0:
        for item in usedQuotes:
            quotes.append(item)
        usedQuotes.clear()
        
    embed = discord.Embed(title=termName, description=termDefinition[0], color=0x0000ff)
    
    print(quotes, usedQuotes)
    footer = randChoice(quotes)
    embed.set_footer(text=footer)
    quotes.remove(footer)
    usedQuotes.append(footer)
    
    if termDefinition[1] != "0":
        color = int(termDefinition[1], 16)
        embed.color = color
        
    if termDefinition[2] != "0":
        image = termDefinition[2]
        embed.set_image(url=image)
        
    await universalSend(ctx=ctx, embed=embed, mention=False)
    

@commands.cooldown(1, 60, commands.BucketType.user)
@bot.command(pass_context=True)    
async def scphelp(ctx):
    embed=discord.Embed(title="Skippy.aic\nPowered by Skippy.aic pageParser and crom, everyone's favorite ~~Keter-class anomaly~~ internet bird", color=0x0000ff)
    
    fields = {
    "View an Article from the SCP Wiki": "``./scp number``\nExample:\n``./scp 173``",
    "Request article using brackets": "``[SCP-number]``\nExample:\n``You can use ./scp 173 or just type [scp-173] in your message!``",
    "View a random SCP": "``./scp random`` or ``[SCP-random]``",
    "Find the definition of a term from the wiki": "Try:\n``./term {}``\nor: ``./term random``".format(randChoice(list(termDict.keys()))),
    "Search SCP article names (Powered by CROM)": "``./scpsearch query``\nExample: ``./scpsearch shy guy``",
    "Article Refinement": "Article Refinement allows the Skippy.aic developer to reformat articles to work with Discord embeds.",
    "Webhook Enhancement": "With the **Manage Webhooks permission**, Skippy.aic can dynamically change its name and profile picture to match the SCP's content! Try:\n``./scp 001-15``",
    "AutoEmbed": "Skippy.aic can automatically detect SCP Wiki URLs posted and display its respective embed.\n**Note: To disable AutoEmbed, disable the 'Add Reactions' permission for the 'Skippy.aic' role. For more info, visit skippyaic.github.io**"}
    for key, val in fields.items():
        embed.add_field(name=key, value=val, inline=True)
    
    embed.set_footer(text="Articles pulled by Skippy.aic are products of their respective SCP Wiki/SCP Sandbox authors.\nArticles may be slightly modified during article refinement to fit in Discord embeds.\nAll articles and images, except for SCP-173's image, are licensed under approved Creative Commons licenses.\nSkippy.aic is licensed under the MIT License.\nFor more information, visit the SCP Wiki Licensing Guide.\nhttps://scp-wiki.wikidot.com/")
    embed.set_image(url="https://i.imgur.com/azFTpKv.png")
    await ctx.send(embed=embed)

async def blackMoon(ctx):
    author = ctx.author.mention
    
    if ctx.author.id == devID:
        author = "O5-7"
    
    embed=discord.Embed(title="**UNAUTHORIZED ACCESS TO SCP-001 DETECTED.**", color=0xff0000)
    embed.add_field(name=f"**VISUAL MEMETIC AUTHORIZATION CHECK DEPLOYED.**\nTYPE YOUR RESPONSE:", value=f"**{author}**, does the Black Moon howl?")
    
    await awaitReply(ctx=ctx, embed=embed)

async def awaitReply(ctx, embed, adult=False):
    await universalSend(ctx=ctx, embed=embed, mention=True)
    message = await bot.wait_for("message", check=lambda message: message.author == ctx.author, timeout=30)
    if adult and message.content.lower() == "yes":
        return True
    else:
        return False

async def Index001(ctx):
    embed1=discord.Embed(title="SCP-001 Index, 1-25", description="We die in the dark so you can live in the light.\n**Secure. Contain. Protect.**\nExample:\n./scp 001-15", color=0xff0000)
    embed2=discord.Embed(title="SCP-001 Index, 26-37", color=0xff0000)
    index1 = dict(list(index.items())[:26])
    index2 = dict(list(index.items())[25:])
    for val in index1:
        embed1.add_field(name=index[val][0], value=val, inline=True)
    for val in index2:
        embed2.add_field(name=index[val][0], value=val, inline=True)
    
    random001 = randChoice(list(index.keys()))
    title001 = index[random001][0]
    embedReply = discord.Embed(title="Check your DMs", description="The SCP-001 index was sent to your DMs.\n\nExample: For '**{0}**', type:\n```./scp {1}``` or ```[scp-{1}]```".format(title001, random001), color=0xff0000)

    try:
        for i in (embed1, embed2):
            await ctx.author.send(embed=i)
        await ctx.reply(embed=embedReply)
    except Exception:
        await ctx.channel.reply(embed=embedReply)

@bot.event
async def on_message(message):
    ##assert message.reference is None and not message.is_system
    try:
        botMember = message.guild.me
    except AttributeError:
        return
        
    for role in botMember.roles:
        if role.is_bot_managed():
            if not role.permissions.add_reactions:
                await bot.process_commands(message)
                return
    
    assert message.author.id != bot.user.id
    
    arg = await autoEmbed(message.content)
    if "[scp" in message.content.lower() or arg != 0:
        if message.author.id in cooldown:
            if int(time.time()) - cooldown[message.author.id] < 10:
                embed=discord.Embed(title="You are on cooldown!", description=f"Try typing your command again in **{int(time.time()) - cooldown[message.author.id]}s**", color=0xff0000)
                await message.channel.send(embed=embed)
                return
            else:
                cooldown.pop(message.author.id)
        else:
            cooldown[message.author.id] = int(time.time())
        
        if arg == 0:
            bracket = re.findall(r"\[(.*?)\]", message.content)[0]
            arg = bracket.lower().replace("scp-", "")
        
        await scp(message, arg, skipBlackMoon = True)
    
    else:
        await bot.process_commands(message)

async def autoEmbed(message):
    regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))" ## FUCK
    
    try:
        extract = re.findall(regex, message)[0][0]
    except IndexError:
        return 0
    
    i = extract.replace("/taboo", "/scp-4000").replace("scp-wiki.wikidot.com", "scpwiki.com") ## this code sucks donkey dick lmao
    
    if "scpwiki.com/" in i:
        if "scp-" in i:
            return i.split(".com/scp-")[1]
        elif "proposal" in i or "keter-duty" in i:
            slug = i.split(".com/")[1]
            ## If SCP-001 article, find 001 article in index
            for key, val in index.items():
                if slug in list(val)[1]:
                    return key
        else:
            return 0
    else:
        return 0

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        embed2=discord.Embed(title="You are on cooldown!", description=f"Try typing your command again in **{int(error.retry_after)}s**", color=0xff0000)
        await ctx.send(embed=embed2)
        ##await ctx.send(f"You are on cooldown. Try typing your command again in **{int(error.retry_after)}s**")
    else:
        raise error

async def universalSend(ctx, msg = None, webhook = False, embed=None, mention=False, changeFooter=True):
    if not webhook:
        try:
            await ctx.reply(content=msg, embed=embed, mention_author=mention)
        except AttributeError:
            await ctx.channel.reply(content=msg, embed=embed, mention_author=mention)
        return

    try:
        hook = await ctx.channel.create_webhook(name=webhook[0].format(ctx.author.name))
        await hook.send(embed=embed, avatar_url=webhook[1])
        await hook.delete()
    except discord.Forbidden:
        if changeFooter:
            embed.set_footer(text="This embed can be enhanced with manage webhooks permissions!")
        await universalSend(ctx, webhook=False, embed=embed)
            

async def colorChecker(classes):
    
    if isinstance(classes, str):
        classes = classes.split()
    
    ClassInfo = {
        0xff0000: ("Keter", "Apollyon", "Amida", "Critical", "[DATA", "Malchut"),
        0xffa500: ("Danger", "Ekhi"),
        0xffff00: ("Euclid", "Keneq", "Warning"),
        0x0000ff: ("Caution", "Vlam", "Thaumiel"),
        0x00ff00: ("Dark", "Safe", "Notice")
    }

    if "Thaumiel" in classes:
        return 0x0000ff

    for key, val in ClassInfo.items():
        for tupleVal in val:
            if tupleVal in classes:
                return key
            else:
                continue
                
    return 0

initalizeItems() ## Initalizes the term dictionary and quotes
bot.run(apikey)