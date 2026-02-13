# v1.2.1

'''
Current features:
- `>ep [Level ID]`: Level info + times
- `>stats [Username]`: Player stats
- `>roll (amount)`:  Roll random levels
- `>new [user] (amount)`: Roll unbeaten levels for user
- `>improve [user] (amount)`: Roll improvable (not WR) levels for user
- `>snipe [user] (amount)`:  Roll snipe-able (WR) levels for user
- New levels/times will also post automatically (checked every 5 minutes)

(all `(amount)` fields are optional and must be between 1 and 10)
'''

import time
import json
import random
import requests
from feedparser import parse
from wand.image import Image
from wand.exceptions import CacheError

import discord
from discord.ext import tasks

TOKEN = '<discord bot token>'
localpath = '<path for saving level previews>'

ALL_LEVELS = [] # pre-compute and paste for faster startup
use_preload_intvs = False
user_data_cache = {}
max_requests = 10

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
    global ALL_LEVELS
    print('starting')
    if ALL_LEVELS:
        if use_preload_intvs:
            gen = zip(ALL_LEVELS[::2],ALL_LEVELS[1::2])
            ALL_LEVELS = sum(([*range(a,b+1)] for a,b in gen),[])
    else: ALL_LEVELS = get_all_levels()
    print('all',len(ALL_LEVELS),'level ids found')
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
    msg = message.channel.send
    if s[:4] == '>ep ': await disp_level(s[4:],msg)
    elif s[:7] == '>stats ': await disp_stats(s[7:],msg)
    elif s[:5] == '>roll':
        if not s[5:]: s += ' 1'
        await wrap_pull(pull_any,s[6:]+s[5:],msg)
    elif s[:5] == '>new ': await wrap_pull(pull_new,s[5:],msg)
    elif s[:9] == '>improve ': await wrap_pull(pull_improve,s[9:],msg)
    elif s[:7] == '>snipe ': await wrap_pull(pull_snipe,s[7:],msg)

async def disp_level(arg,msg):
    try: arg = int(arg)
    except ValueError:
        await msg('Invalid argument (enter a level ID)')
        return
    print('received request for level',arg)
    e = write_level_info(arg)
    if not e:
        await msg(f'Level {arg} not found')
        return
    name = create_image(f'{url}/static/lvls/{arg}.svg')
    kw = {'embed':e}
    if name:
        src = f'attachment://{name}'
        e.set_image(url=src)
        kw['file'] = discord.File(localpath,filename=name)
    await msg(**kw)

async def disp_level_terse(arg,msg):
    try: arg = int(arg)
    except ValueError:
        await msg('Invalid argument (enter a level ID)')
        return
    print('received request for level',arg)
    e = write_level_info_terse(arg)
    if not e:
        await msg(f'Level {arg} not found')
        return
    name = create_image(f'{url}/static/lvls/{arg}.svg')
    kw = {'embed':e}
    if name:
        src = f'attachment://{name}'
        e.set_thumbnail(url=src)
        kw['file'] = discord.File(localpath,filename=name)
    await msg(**kw)

async def disp_stats(arg,msg):
    print('received request for user',arg)
    res = user_stats(arg)
    if not res:
        await msg(f'User {arg} not found')
        return
    await msg(embed=res)

async def wrap_pull(pull,arg,msg):
    args = arg.split(' ')
    if len(args) > 1:
        num = args[-1]
        try: num = int(num)
        except ValueError:
            await msg(f'Invalid amount: {num}')
            return
        if num > max_requests or num < 1:
            await msg(f'Invalid amount (must be between 1 and 10)')
            return
        user = ' '.join(args[:-1])
    else: user,num = arg,1
    print('pull',user,num)
    await pull(user,num,msg)

async def pull_any(user,num,msg):
    if num>1: await msg(f"Rolling {num} random levels...")
    else: await msg(f"Rolling a random level...")
    for i in range(num): await disp_level_terse(random.choice(ALL_LEVELS),msg)

async def pull_new(user,num,msg):
    data = user_data_cache.get(user,[])
    if not data:
        data = get_user(user)
        if not data:
            await msg(f'User {user} not found')
            return
    if num>1: await msg(f"Finding {num} levels {user} hasn't beaten...")
    else: await msg(f"Finding a level {user} hasn't beaten...")
    pool = set(ALL_LEVELS)-set(int(i[0]) for i in data if i[4]!='TAS')
    if not pool:
        await msg(f'User {user} has beaten all levels!')
        return
    for i in range(num): await disp_level_terse(random.choice([*pool]),msg)

async def pull_improve(user,num,msg):
    data = user_data_cache.get(user,[])
    if not data:
        data = get_user(user)
        if not data:
            await msg(f'User {user} not found')
            return
    if num>1: await msg(f"Finding {num} levels {user} can improve...")
    else: await msg(f"Finding a level {user} can improve...")
    d = {}
    for i in data:
        if i[4]=='TAS': continue
        lv = int(i[0])
        r = int(i[4].partition('/')[0])
        d[lv] = min(r,d.get(lv,2))
    pool = [i for i in d if d[i]>1]
    if not pool:
        await msg(f'User {user} has all WRs!')
        return
    for i in range(num): await disp_level_terse(random.choice(pool),msg)

async def pull_snipe(user,num,msg):
    data = user_data_cache.get(user,[])
    if not data:
        data = get_user(user)
        if not data:
            await msg(f'User {user} not found')
            return
    if num>1: await msg(f"Finding {num} levels to snipe {user} on...")
    else: await msg(f"Finding a level to snipe {user} on...")
    d = {}
    for i in data:
        if i[4]=='TAS': continue
        lv = int(i[0])
        r = int(i[4].partition('/')[0])
        d[lv] = min(r,d.get(lv,2))
    pool = [i for i in d if d[i]<2]
    if not pool:
        await msg(f'User {user} has no WRs :(')
        return
    for i in range(num): await disp_level_terse(random.choice(pool),msg)

def fix_image(img):
    w,h = img.size
    if w>3*h: img.crop((w-3*h)//2,0,(w+3*h)//2,h)
    if h>3*w: img.crop(0,(h-3*w)//2,w,(h+3*w)//2)
    return img

def create_image(src,fix=True):
    try: 
        r = requests.get(src)
        if r.status_code!=200:
            print('create_image failed',r.status_code)
            return
        img = Image(blob=r.content)
        if fix: img = fix_image(img)
        png = img.make_blob("png")
        with open(localpath,'wb') as f: f.write(png)
        name = src.split('/')[-1].replace('svg','png')
        return name
    except CacheError:
        print('image conversion failed')
        return

def mini_entry(entry):
    keys = ('summary','title','link')
    d = {}
    for i in keys: d[i] = entry[i]
    return d

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
    info = [[i.strip() for i in skim(i).partition(':')[::2]] for i in info]
    info = dict(i for i in info if len(i)==2)
    info['Name'] = name.replace('&#39;',"'")
    chunks = r.text.partition('Leaderboard')[2].split('title')[1:-1]
    lb = []
    for i in chunks:
        res = [j.partition('</td>')[0].strip() for j in i.split('<td>')[1:6]]
        res.pop(3)
        res[1],res[3] = skim(res[1]),skim(res[3])
        lb.append(res)
    tas = sum(i[0]=='TAS' for i in lb)
    for i in range(tas+1,len(lb)):
        if lb[i][2] == lb[i-1][2]: lb[i][0] = lb[i-1][0]
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
    r = requests.get(f"{url}/author/{user.replace(' ','%20')}/all")
    if r.status_code!=200:
        print('get_user',r.status_code)
        return
    for i in r.text.partition("timesTable")[2].split('title="')[1:-1]:
        b = [j.partition('</td>')[0] for j in i.split('<td>')[1:]]
        b[0] = b[0].partition('href="/')[2].partition('"')[0]
        for j in range(1,len(b)): b[j] = skim(b[j])
        b[1] = time_to_cents(b[1])
        data.append(b)
    user_data_cache[user] = data
    return data

def get_all_levels():
    gamers = ('Xakaze','Molgmaran','Nairod','GoblinOfCash')
    s = set()
    for i in gamers:
        for j in get_user(i): s.add(int(j[0]))
    return sorted(s)

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
    e.add_field(name='',value='',inline=False)
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
    data = dict(i.partition(': ')[::2] for i in data)
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
                    e.add_field(name='Rank',value=f'{lb[i][0]}/{n-tas}')
                    break
        if data['Comment'] not in ('','No comment'):
            e.add_field(name='Comment',value=data['Comment'],inline=False)
        else: e.add_field(name='',value='',inline=False)
        e.add_field(name='Users',value='\n'.join(link_name(i[1]) for i in lb[tas:]))
        e.add_field(name='Times',value='\n'.join(link_vid(*i[2:4]) for i in lb[tas:]))
    else:
        if data['Comment'] not in ('','No comment'):
            e.add_field(name='Comment',value=data['Comment'],inline=False)
    return e,create_image(f'{url}/static/lvls/{lv}.svg')

def write_level(entry):
    data = entry['summary']
    link = entry['link']
    data = [i.strip().partition('<br />')[0] for i in data.split('\n')]
    data[-2] += ' ' + data[-1]
    data = dict(i.partition(': ')[::2] for i in data[:-1])
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
    tas = sum(i[0]=='TAS' for i in lb)
    e.add_field(name='Users',value='\n'.join(link_name(i[1]) for i in lb[tas:]))
    e.add_field(name='Times',value='\n'.join(link_vid(*i[2:4]) for i in lb[tas:]))
    return e

def write_level_info_terse(level):
    res = get_lv(level)
    if not res: return
    info,lb = res
    e = discord.Embed(
        title=f"{info['Name']} (by {info['Author']})",
        url=f'{url}/{level}',
        color=TEAL)
    tas = sum(i[0]=='TAS' for i in lb)
    e.add_field(name='Users',value='\n'.join(link_name(i[1]) for i in lb[tas:]))
    e.add_field(name='Times',value='\n'.join(link_vid(*i[2:4]) for i in lb[tas:]))
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
            jmini = json.dumps(mini_entry(entry),sort_keys=True)
            feed[entry['published']] = jmini
    else:
        new = []
        for entry in r:
            jmini = json.dumps(mini_entry(entry),sort_keys=True)
            t = entry['published']
            if t not in feed or feed[t] != jmini:
                print('old:',feed[t])
                print('new:',jmini)
                new.append((time.mktime(entry['published_parsed']),hash(entry),entry))
        for t,_,entry in sorted(new):
            jmini = json.dumps(mini_entry(entry),sort_keys=True)
            print(entry['title'])
            feed[entry['published']] = jmini
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
