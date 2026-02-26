# v1.0.0

'''
Commands only work in the ⁠bingo-bot channel, and can start with > or !.

Before/after the game:

    >new N: Launch a new N x N game (N between 2 and 9, large boards are SLOW)
    >join (R/G/B/Y): Join one of the 4 available teams (must be before game starts)
    >start: Start the game


During the game:

    The bot will send messages containing a grid of level links, and an image with some summary info
        If the image is too small, click on it to zoom in
    Runs can all be done in practice mode, regardless of usual obstacle cycles
    Runs should be submitted immediately after completion (no hoarding runs)
    >A3 1:05.13 with the corresponding values to submit a time
    >undo if you accidentally mis-enter a time (try to avoid this)
    >end: End the game early
    First team to secure a row/column/diagonal of all one color wins
        Tied times count for neither team
'''

import time
import random
import requests
from wand.image import Image as WImage
from wand.exceptions import CacheError,ImageError,ResourceLimitError
from PIL import Image,ImageDraw,ImageFont,ImageChops

import discord

TOKEN = '<discord bot token>'
localpath = '<path for saving level previews>'
fontpath = '<path to a font file>'

url = 'http://exitpath-maker.net'

ALL_LEVELS = [] # pre-compute and paste, can find script in epDiscordBot.py

font = ImageFont.truetype(fontpath,25)
bigfont = ImageFont.truetype(fontpath,36)
biggerfont = ImageFont.truetype(fontpath,50)
biggestfont = ImageFont.truetype(fontpath,100)

red = '#ff8080'
green = '#80ff80'
blue = '#8080ff'
yellow = '#ffff80'
gray = '#808080'
colors = [red,blue,green,yellow]
colornames = ['red','blue','green','yellow']

def time_to_cents(time):
    m,_,t = time.partition(':')
    if not t: t,m = m,0
    s,_,f = t.partition('.')
    if not f: f = '0'
    while len(f)<2: f+='0'
    m,s,f = map(int,(m,s,f))
    return 6000*m+100*s+f

def cents_to_time(n):
    if n<6000: return f'{n//100}.{n%100:02d}'
    return f'{n//6000}:{n%6000//100:02d}.{n%100:02d}'

def reparse(time):
    return cents_to_time(time_to_cents(time))

def skim(s):
    a = []
    read = True
    for i in s:
        if i=='<': read = False
        if read: a.append(i)
        if i=='>': read = True
    return ''.join(a).strip()

def get_lv(lvl):
    r = requests.get(f'{url}/{lvl}')
    if r.status_code!=200:
        print('get_lv',r.status_code)
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

def get_image(lvl):
    r = requests.get(f'{url}/static/lvls/{lvl}.svg')
    if r.status_code!=200:
        print('get image failed',r.status_code)
        return
    try:
        get = WImage(blob=r.content).make_blob("png")
        path = f'{localpath}/temp.png'
        with open(path,'wb') as f: f.write(get)
    except (CacheError,ImageError,ResourceLimitError):
        print('image conversion failed')
        return
    return Image.open(path)

def fix_image(img,size):
    r = size[0]/size[1]
    w,h = img.size
    if w>r*h: img = img.crop(((w-r*h)//2,0,(w+r*h)//2,h))
    if h>w/r: img = img.crop((0,(h-w/r)//2,w,(h+w/r)//2))
    img = img.resize(size)
    return img

class Tile:
    def __init__(self,lvl,label,info,wr):
        self.lvl = lvl
        self.label = label
        self.name = info['Name']
        self.author = 'by '+info['Author']
        self.tags = info['Tags'].replace('  ',' ')
        self.wr = wr
        self.code = ''#info['Code']
        img = get_image(lvl)
        if not img: img = Image.new('RGB',(500,300))
        else: img = fix_image(img,(500,300))
        self.preview = img
        self.tint = None
        self.pbq = []

    def get_cur(self):
        if not self.pbq:
            self.tint = None
            return self.wr
        pb = cents_to_time(self.pbq[-1][0])
        if len(self.pbq)<2 or self.pbq[-1][0]<self.pbq[-2][0]:
            return f'{pb} {self.pbq[-1][1]}'
        self.tint = gray
        return f'{pb} [TIE]'
    
    def gen_tile(self):
        base = Image.new('RGB',(500,500))
        base.paste(self.preview,(0,120))
        draw = ImageDraw.Draw(base)
        draw.polygon(((0,0),(0,500),(500,500),(500,0)),outline='white',width=5)
        draw.text((10,0),self.label,fill='white',font=biggestfont)
        draw.text((130,10),self.name,fill='white',font=bigfont)
        draw.text((130,55),self.author,fill='white',font=bigfont)
        draw.text((10,95),self.tags,fill='white',font=font)
        draw.text((10,430),self.get_cur(),fill='white',font=biggerfont)
        if self.tint:
            tint = Image.new('RGB',(500,500),color=self.tint)
            base = ImageChops.multiply(base,tint)
        return base

def spawn_tile(lvl,label):
    res = get_lv(lvl)
    if not res: return
    info,lb = res
    tas = sum(i[0]=='TAS' for i in lb)
    if len(lb)==tas: return
    top = lb[tas]
    wr = f'WR: {reparse(top[2])}'
    return Tile(lvl,label,info,wr)

class Board:
    def __init__(self,n):
        print('new board created')
        self.n = n
        self.grid = []
        self.claims = [0]*(n*n)
        self.win = 0
        ids = ALL_LEVELS[:]
        for i in range(n*n):
            res = None
            while not res:
                lvl = random.choice(ids)
                ids.remove(lvl)
                res = spawn_tile(lvl,f'{chr(65+i//n)}{i%n+1}')
            self.grid.append(res)
            print(f'map {i+1}/{n*n} chosen')
            
    def disp_board(self):
        n = self.n
        base = Image.new('RGB',(500*n,500*n))
        for i in range(n*n):
            y,x = i//n,i%n
            base.paste(self.grid[i].gen_tile(),(x*500,y*500))
        return base

    def upd_tile(self,idx,player,team,time):
        tile = self.grid[idx]
        if tile.pbq and time>tile.pbq[-1][0]: return False
        tile.pbq.append((time,player))
        res = tile.get_cur().partition(' ')[2]
        if res == '[TIE]': self.claims[idx] = -1
        else:
            self.claims[idx] = team
            tile.tint = colors[team-1]
        return True

    def undo(self,idx,player,team,time):
        tile = self.grid[idx]
        if tile.pbq and tile.pbq[-1]==(time,player): tile.pbq.pop()
        else: return False
        if not tile.pbq:
            self.claims[idx] = 0
            return True
        res = tile.get_cur().partition(' ')[2]
        if res == '[TIE]': self.claims[idx] = -1
        else:
            self.claims[idx] = team
            tile.tint = colors[team-1]
        return True

    def check_win(self):
        n = self.n
        G = self.claims
        for t in range(1,5):
            for i in range(n):
                if all(G[i*n+j]==t for j in range(n)): return t
                if all(G[j*n+i]==t for j in range(n)): return t
            if all(G[i*n+i]==t for i in range(n)): return t
            if all(G[i*n+n-1-i]==t for i in range(n)): return t
        return 0

    def dump_codes(self):
        n = self.n
        out = []
        for i in range(n):
            out.append('\t'.join(self.grid[i*n+j].code for j in range(n)))
        print('\n'.join(out))

squares = [
    ':white_square_button:',
    ':red_square:',
    ':blue_square:',
    ':green_square:',
    ':yellow_square:',
    ':white_large_square:',
]

class Manager:
    def __init__(self,n,teams,msg):
        print('new manager created')
        self.n = n
        self.teams = teams
        self.msg = msg
        self.last_action = {}
        self.board = Board(n)
        self.board.dump_codes()
        self.status = 'Game running...'

    async def disp_board(self):
        n = self.n
        path = f'{localpath}/tempboard.png'
        name = 'board.png'
        self.board.disp_board().save(path)
        e = discord.Embed(title=self.status)
        for i in range(n):
            B = self.board
            row = [f'[{squares[B.claims[i*n+j]]}]({url}/{B.grid[i*n+j].lvl})' for j in range(n)]
            row = ' | '.join(row)
            e.add_field(name='',value=row,inline=False)
        e.set_image(url=f'attachment://{name}')
        file = discord.File(path,filename=name)
        await self.msg(file=file,embed=e)

    def check_win(self):
        res = self.board.check_win()
        if res:
            self.board.win = res
            self.status = f'Game over, {colornames[res-1]} team wins!'
        else: self.board.win = 0

    async def submit_time(self,player,idx,time):
        args = (idx,player,self.teams[player],time)
        res = self.board.upd_tile(*args)
        if not res: return res
        self.last_action[player] = args
        self.status = f'New time: {cents_to_time(time)} by {player}'
        self.check_win()
        await self.disp_board()
        return res

    async def undo(self,player):
        args = self.last_action.get(player)
        if args:
            res = self.board.undo(*args)
            if not res: return res
            del self.last_action[player]
            self.status = f'Undoing last time by {player}'
            self.check_win()
            await self.disp_board()
            return res
        return False

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

game = None
ready = False
size = 0
teams = {}
teamlist = ('R','B','G','Y')

@client.event
async def on_message(message):
    global game,ready,size,teams
    if message.author == client.user: return
    if message.channel.name != 'bingo-bot': return
    s = message.content
    user = message.author.nick
    if not user: user = message.author.name
    msg = message.channel.send
    if s and s[0] in '>!':
        if s[1:5] == 'new ':
            if game and not game.board.win:
                await msg('Warning: there is currently an ongoing game. Type `>end` to force reset the game.')
                return
            n = s[5:]
            try: n = int(n)
            except ValueError:
                await msg(f'Invalid board size: {n}')
                return
            if n<2 or n>9:
                await msg('Invalid board size (must be between 2 and 9)')
                return
            size = n
            game = None
            teams = {}
            ready = True
            await msg(f'New {n}x{n} game launched, join teams using `>join (R/G/B/Y)`, start with `>start`')
        elif s[1:4] == 'end':
            game = None
            teams = {}
            ready = False
            await msg('Current game ended')
        elif s[1:6] == 'join ':
            if game:
                await msg('Can only join teams before a game starts')
                return
            team = s[6:].upper()
            if team not in teamlist:
                await msg(f'Invalid team: {team}')
                return
            teams[user] = teamlist.index(team)+1
            print(teams)
            await msg(f'{user} joined the {colornames[teams[user]-1]} team')
        elif s[1:6] == 'start':
            if not ready:
                await msg('New game not yet launched, use `>new N` to launch')
                return
            if not teams:
                await msg('At least one player must join a team')
                return
            await msg(f'Starting game (may take a while)...\nUse `>A3 1:05.13`, etc. to submit times during the game, use `>undo` to undo an incorrect time')
            game = Manager(size,teams,msg)
            await game.disp_board()
        elif s[1:5] == 'undo':
            if not game:
                await msg('Can only undo during games')
                return
            res = await game.undo(user)
            if not res: await msg("Failed to undo {user}'s last time")
        elif s[3:4] == ' ':
            if not game or game.board.win or user not in teams: return
            y,x = ord(s[1].upper())-65,ord(s[2])-49
            if min(x,y)<0 or max(x,y)>=size:
                await msg(f'Invalid coords: {s[1:3]}')
                return
            time = s[4:]
            try: time = time_to_cents(time)
            except ValueError:
                await msg(f'Invalid time: {time}')
                return
            i = y*size+x
            res = await game.submit_time(user,i,time)
            if not res: await msg(f'There is a faster time on {s[1:3]} already')

if __name__ == '__main__': client.run(TOKEN)
