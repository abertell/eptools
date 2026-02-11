# v1.1.3

import time
import json
import requests
from wand.image import Image
from feedparser import parse

import discord
from discord.ext import tasks

TOKEN = '<discord bot token>'
localpath = '<path for saving level previews>'

delay = 5 # minutes

url = 'http://exitpath-maker.net'

TEAL = discord.Color.teal()
GOLD = discord.Color.gold()

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

channels = {}
feed = {}

@client.event
async def on_ready():
    print('starting')
    for guild in client.guilds:
        for channel in guild.text_channels:
            if channel.name == 'ep-bot': channels[guild.name] = channel
    print('server list updated:',', '.join(channels))
    check_feed.start()

def check_guild(guild):
    if guild.name in channels: del channels[guild.name]
    for channel in guild.text_channels:
        if channel.name == 'ep-bot': channels[guild.name] = channel

@client.event
async def on_guild_join(guild):
    check_guild(guild)
    print('joined',guild.name)

@client.event
async def on_guild_update(before,after):
    if before.name in channels: del channels[before.name]
    check_guild(after)
    print('updated',before.name)

@client.event
async def on_guild_remove(guild):
    if guild.name in channels: del channels[guild.name]
    print('left',guild.name)

@client.event
async def on_guild_channel_delete(channel):
    check_guild(channel.guild)

@client.event
async def on_guild_channel_create(channel):
    check_guild(channel.guild)

@client.event
async def on_guild_channel_update(before,after):
    check_guild(after.guild)

@client.event
async def on_message(message):
    if message.author == client.user: return
    if channels.get(message.guild.name) != message.channel: return
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
        name = create_image(f'{url}/static/lvls/{arg}.svg')
        kw = {'embed':e}
        if name:
            src = f'attachment://{name}'
            e.set_image(url=src)
            kw['file'] = discord.File(localpath,filename=name)
        await message.channel.send(**kw)
    elif s[:7] == '>stats ':
        arg = s[7:]
        print('received request for user',arg)
        res = user_stats(arg)
        if not res:
            await message.channel.send(f'User {arg} not found')
            return
        await message.channel.send(embed=res)

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
    return name

def link_name(name):
    return f'[{name}]({url}/author/{name})'

def link_vid(time,vid):
    return time if vid in ('','No video') else f'[{time}]({vid})'

def skim(s):
    a = []
    read = True
    for i in s:
        if i=='<': read = False
        if read: a.append(i)
        if i=='>': read = True
    return ''.join(a).strip()

def get_lv(level):
    r = requests.get(f'{url}/{level}')
    if r.status_code!=200:
        print('get_lb',r.status_code)
        return
    name = r.text.partition(' - EPLevels')[0].partition('<title>')[2]
    info = r.text.partition('levelPropsTable')[2].partition('</section>')[0]
    info = info.split('<strong>')[1:]
    info = [[i.strip() for i in skim(i).split(':')] for i in info]
    info = dict(i for i in info if len(i)==2)
    info['Name'] = name.replace('&#39;',"'")
    chunks = r.text.partition('Leaderboard')[2].split('title')[1:-1]
    lb = []
    for i in chunks:
        res = [j.partition('</td>')[0].strip() for j in i.split('<td>')[1:6]]
        res.pop(3)
        res[1],res[3] = skim(res[1]),skim(res[3])
        lb.append(res)
    return info,lb

def time_to_cents(time):
    m,_,t = time.partition(':')
    s,_,f = t.partition('.')
    m,s,f = map(int,(m,s,f))
    return 6000*m+100*s+f

def cents_to_time(n):
    return f'{n//360000}h {n%360000//6000}m {n%6000//100}.{n%100}s'

def get_user(user):
    data = []
    r = requests.get(f'{url}/author/{user}/all')
    if r.status_code!=200:
        print('get_user',r.status_code)
        return
    for i in r.text.partition("timesTable")[2].split('title="')[1:-1]:
        b = [j.partition('</td>')[0] for j in i.split('<td>')[1:]]
        b[0] = b[0].partition('href="/')[2].partition('"')[0]
        for j in range(1,len(b)): b[j] = skim(b[j])
        b[1] = time_to_cents(b[1])
        data.append(b)
    return data

def user_stats(user):
    data = get_user(user)
    if not data: return
    r = requests.get(url)
    if r.status_code!=200:
        print('main page',r.status_code)
        return
    lvls = int(skim(r.text.partition(')')[0]).partition(': ')[2])
    uniq = {}
    tas = dup = 0
    for a in data:
        if a[-1] == 'TAS':
            tas += 1
            continue
        if a[0] in uniq:
            dup += 1
            if a[1] > uniq[a[0]][0]: continue
        uniq[a[0]] = a[1:]
    runs = len(uniq)
    tot = long = only = tr = comments = vids = 0
    rank = [0]*3
    for i in uniq:
        t,c,v,r = uniq[i]
        if c not in ('','No comment'): comments += 1
        if v not in ('','No video'): vids += 1
        tot += t
        if t>360000: long += 1
        r,n = map(int,r.split('/'))
        if r<4: rank[r-1] += 1
        tr += r
        if n<2: only += 1
    e = discord.Embed(
        title=f'Player stats for {user}',
        description=f'Levels beaten: {runs}/{lvls} ({runs/lvls*100:.2f}%)')
    ranks = [
        ':trophy: (only fin)',
        ':first_place_medal:',
        ':second_place_medal:',
        ':third_place_medal:']
    e.add_field(name='Rank',value='\n'.join(ranks))
    e.add_field(name='#',value='\n'.join(map(str,[only]+rank)))
    e.add_field(
        name='Total playtime (only submitted runs)',
        value=cents_to_time(tot),inline=False)
    e.add_field(name='Average rank',value=f'{tr/runs:.2f}')
    e.add_field(name='1hr+ runs',value=str(long))
    e.add_field(name='Comments',value=str(comments))
    e.add_field(name='Videos',value=str(vids))
    e.add_field(name='TAS runs',value=str(tas))
    e.add_field(name='Duplicate runs',value=str(dup))
    return e

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
    writetime = runtime
    if 'Video' in data: writetime = link_vid(runtime,data['Video'])
    e.add_field(name='Time',value=writetime)
    if got_lv:
        n = len(lb)
        tas = sum(i[0]=='TAS' for i in lb)
        if istas: e.add_field(name='Rank',value=f'-/{n-tas}')
        else:
            for i in range(tas,n):
                if lb[i][1:3] == [user,runtime]:
                    e.add_field(name='Rank',value=f'{i-tas+1}/{n-tas}')
                    break
        e.add_field(
            name='WR',
            value=f'{link_vid(*lb[tas][2:4])} by {link_name(lb[tas][1])}',
            inline=False)
    if data['Comment'] not in ('','No comment'):
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
        if field == 'Description' and info[field] == 'No description':
            continue
        e.add_field(name=field,value=info[field],inline=False)
    e.add_field(name='Users',value='\n'.join(link_name(i[1]) for i in lb))
    e.add_field(name='Times',value='\n'.join(link_vid(*i[2:4]) for i in lb))
    return e

@tasks.loop(minutes=delay)
async def check_feed():
    print('running loop at',time.ctime())
    r = parse(f'{url}/rss.xml')
    if 'entries' not in r:
        print('rss request failed')
        return
    r = r['entries']
    # extremely inefficient but the data format is so bad idk another way
    if not feed:
        for entry in r:
            feed[entry['published']] = json.dumps(entry,sort_keys=True)
    else:
        new = []
        for entry in r:
            t = entry['published']
            if t not in feed or feed[t]!=json.dumps(entry,sort_keys=True):
                new.append((time.mktime(entry['published_parsed']),hash(entry),entry))
        for t,_,entry in sorted(new):
            print(entry['title'])
            feed[entry['published']] = json.dumps(entry,sort_keys=True)
            kind = entry['title'].partition(':')[0]
            islvl = kind == 'New level'
            if islvl: e,name = write_level(entry)
            else: e,name = write_time(entry)
            if not name:
                for i in channels: await channels[i].send(embed=e)
                continue
            src = f'attachment://{name}'
            if islvl: e.set_image(url=src)
            else: e.set_thumbnail(url=src)
            for i in channels:
                file = discord.File(localpath,filename=name)
                await channels[i].send(file=file,embed=e)
                
    last_request = json.dumps(r[0],sort_keys=True)
    print('up to date')

client.run(TOKEN)
