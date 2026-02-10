import json
import requests
from wand.image import Image
from feedparser import parse

import discord
from discord.ext import tasks

TOKEN = '<discord bot token>'
localpath = '<path for saving level previews>'

url = 'http://exitpath-maker.net'

TEAL = discord.Color.teal()
GOLD = discord.Color.gold()

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

channels = []

@client.event
async def on_ready():
    for guild in client.guilds:
        for channel in guild.text_channels:
            if channel.name == 'ep-bot':
                channels.append(channel)
    print('servers:',[i.guild.name for i in channels])
    check_feed.start()

@client.event
async def on_message(message):
    if message.author == client.user: return
    if message.channel not in channels: return
    s = message.content
    if s[:4] == '>ep ':
        arg = s[4:]
        try: arg = int(arg)
        except ValueError:
            await message.channel.send('Invalid argument (enter a level ID)')
            return
        print('received request for level',arg)
        e = write_level_info(arg)
        if not e:
            await message.channel.send(f'Level {arg} not found')
            return
        res = create_image(f'{url}/static/lvls/{arg}.svg')
        kw = {'embed':e}
        if res:
            name,file = res
            src = f'attachment://{name}'
            e.set_image(url=src)
            kw['file'] = file
        await message.channel.send(**kw)

def fix_image(img):
    w,h = img.size
    if w>3*h: img.crop((w-3*h)//2,0,(w+3*h)//2,h)
    if h>3*w: img.crop(0,(h-3*w)//2,w,(h+3*w)//2)
    return img

def create_image(src,fix=True):
    r = requests.get(src)
    if r.status_code!=200:
        print('create_thumbnail failed',r.status_code)
        return
    img = Image(blob=r.content)
    if fix: img = fix_image(img)
    png = img.make_blob("png")
    with open(localpath,'wb') as f: f.write(png)
    name = src.split('/')[-1].replace('svg','png')
    file = discord.File(localpath,filename=name)
    return name,file

def link_name(name):
    return f'[{name}]({url}/author/{name})'

def skim(s):
    a = []
    read = True
    for i in s:
        if i=='<': read = False
        if read: a.append(i)
        if i=='>': read = True
    b = ''.join(a).strip().split(':')
    return [i.strip() for i in b]

def get_lv(level):
    r = requests.get(f'{url}/{level}')
    if r.status_code!=200:
        print('get_lb',r.status_code)
        return
    name = r.text.partition(' - EPLevels')[0].partition('<title>')[2]
    info = r.text.partition('levelPropsTable')[2].partition('</section>')[0].split('<strong>')[1:]
    info = [skim(i) for i in info]
    info = dict(i for i in info if len(i)==2)
    info['Name'] = name
    chunks = r.text.partition('Leaderboard')[2].split('title')[1:-1]
    lb = []
    for i in chunks:
        res = [j.partition('</td>')[0].strip() for j in i.split('<td>')[1:4]]
        res[1] = res[1].partition('">')[2].partition('</a>')[0]
        lb.append(res)
    return info,lb

def write_time(entry):
    data = entry['summary']
    link = entry['link']
    lv = link.split('/')[-1]
    res,got_lv = get_lv(lv),False
    if not res is None:
        info,lb = res
        author = info['Author']
        got_lv = True
    data = [i.strip().partition('<br />')[0] for i in data.split('\n')]
    data = [i for i in data if i]
    data = dict(i.split(': ') for i in data)
    istas = data['Is tas'] == '1'
    kw = {'title':entry['title'],'url':link}
    if got_lv:
        if author == 'Archive':
            kind,_,name = kw['title'].partition(': ')
            a,_,b = name.partition('] ')
            kw['title'] = f'{kind}: {b} (by {a[1:]}) [Archived]'
        else: kw['title'] += f' (by {author})'
    if istas:
        kw['color'] = GOLD
        kw['title'] = 'New TAS'+kw['title'][3:]
    e = discord.Embed(**kw)
    user,runtime = data['By'],data['Chrono']
    e.add_field(name='Player',value=link_name(user))
    e.add_field(name='Time',value=runtime)
    if got_lv:
        n = len(lb)
        tas = sum(i[0]=='TAS' for i in lb)
        if istas: e.add_field(name='Rank',value=f'-/{n-tas}')
        else:
            for i in range(tas,n):
                if lb[i] == [str(i-tas+1),user,runtime]:
                    e.add_field(name='Rank',value=f'{i-tas+1}/{n-tas}')
                    break
        e.add_field(name='WR',value=f'{lb[0][2]} by {link_name(lb[0][1])}',inline=False)
    if 'Video' in data:
        e.add_field(name='Video',value=f'[link]({data["Video"]})',inline=False)
    if data['Comment'] != 'No comment':
        e.add_field(name='Comment',value=data['Comment'],inline=False)
    return e,create_image(f'{url}/static/lvls/{lv}.svg')

def write_level(entry):
    data = entry['summary']
    link = entry['link']
    data = [i.strip().partition('<br />')[0] for i in data.split('\n')]
    data[-2] += ' ' + data[-1]
    data = dict(i.split(': ') for i in data[:-1])
    e = discord.Embed(title=entry['title'],url=link,color=TEAL)
    user = data['By']
    e.add_field(name='Author',value=link_name(user))
    e.add_field(name='Description',value=data['Description'],inline=False)
    return e,create_image(data['Preview'].split('"')[-2])

def write_level_info(level):
    res = get_lv(level)
    if not res: return
    info,lb = res
    e = discord.Embed(title=info['Name'],url=f'{url}/{level}',color=TEAL)
    for field in info:
        if field == 'Name': continue
        if field == 'Description' and info[field] == 'No description': continue
        e.add_field(name=field,value=info[field],inline=False)
    e.add_field(name='Users',value='\n'.join(i[1] for i in lb))
    e.add_field(name='Times',value='\n'.join(i[2] for i in lb))
    return e

last_request = None

@tasks.loop(minutes=5)
async def check_feed():
    global last_request
    print('running loop')
    r = parse(f'{url}/rss.xml')
    if 'entries' not in r:
        print('rss request failed')
        return
    r = r['entries']
    if not last_request is None:
        new = []
        i = 0
        while json.dumps(r[i],sort_keys=True) != last_request:
            new.append(r[i])
            i += 1
        for entry in new[::-1]:
            kind = entry['title'].partition(':')[0]
            islvl = kind == 'New level'
            if islvl: e,res = write_level(entry)
            else: e,res = write_time(entry)
            kw = {'embed':e}
            if res:
                name,file = res
                src = f'attachment://{name}'
                if islvl: e.set_image(url=src)
                else: e.set_thumbnail(url=src)
                kw['file'] = file
            for channel in channels:
                await channel.send(**kw)
    last_request = json.dumps(r[0],sort_keys=True)
    print('up to date')

client.run(TOKEN)
