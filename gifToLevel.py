from PIL import Image, ImageOps
import zlib, io, os, struct

#encodeLevel method and Tile class from @klementc
class Tile():
    def __init__(self):
        self.Tag = ""
        self.TileID = ""
        self.TileName = ""
        self.Pos = []
        self.Rotation = 0
        self.Width = 0
        self.Height = 0

def encodeLevel(name, tileList, cfg):
    lvlCode = io.BytesIO()
    code = "{}~#-".format(name)
    ms = [[[1,0],[0,1]]]
    mis = []
    mxs = []
    for t in tileList:
        m = ms[0]
        xScale = 1
        yScale = 1
        rot = -(t.Rotation*math.pi)/180
        sX = float(t.Width)/float((tileDesc.BinTiles[t.TileID].Size[0]))
        sY = float(t.Height)/float((tileDesc.BinTiles[t.TileID].Size[1]))
        m = [[1,0],[0,1]]
        m[0][0]=((math.cos(rot))*sX)
        m[0][1]=((-1*math.sin(rot)))
        m[1][0]=(math.sin(rot))
        m[1][1]=((math.cos(rot))*sY)
        try:
            idx = ms.index(m)
            mis.append(idx)
        except ValueError:
            idx = len(ms)
            ms.append(m)
            mis.append(idx)
    lvlCode.write(int.to_bytes(0x564C5045, 4, byteorder='little'))
    lvlCode.write(int.to_bytes(1, 1, byteorder='little'))
    rd = os.urandom(2)
    lvlCode.write(rd)
    lvlCode.write(int.to_bytes(cfg, 1, byteorder="little"))
    lvlCode.write(int.to_bytes(len(ms)-1, 4, byteorder='little'))
    for lm in ms[1:]:
        lvlCode.write(struct.pack('f', lm[0][0]))
        lvlCode.write(struct.pack('f', lm[0][1]))
        lvlCode.write(struct.pack('f', lm[1][0]))
        lvlCode.write(struct.pack('f', lm[1][1]))
    lvlCode.write(int.to_bytes(len(tileList), 4, byteorder="little"))
    x = 0
    for tile in tileList:
        id = tileDesc.TileDescBin[tile.TileID]
        name = tile.TileName
        xScale = 1
        yScale = 1
        trX =(tile.Pos[0])
        trY =(tile.Pos[1])
        td = int.to_bytes(tileDesc.TileDescBin[tile.TileID], 1, byteorder='little')
        tmod = int.to_bytes((0x80 if mis[x] != 0 else 0), 1, byteorder='little')
        lvlCode.write(int.to_bytes((td[0] | tmod[0]), 1, byteorder="little"))
        if (tileDesc.BinTiles[tile.TileID].HasTag):
            tag = tile.Tag if tile.Tag else ""
            lvlCode.write(int.to_bytes(len(tag), 1, byteorder='little'))
            lvlCode.write(bytes(tag, 'utf-8'))
        elif (tileDesc.BinTiles[tile.TileID].HasName):
            lvlCode.write(int.to_bytes(len(tile.TileName), 1, byteorder='little'))
            lvlCode.write(bytes(tile.TileName, 'utf-8'))
        if (mis[x] != 0):
            lvlCode.write(int.to_bytes(mis[x], 4, byteorder='little'))
        lvlCode.write(struct.pack('f', trX))
        lvlCode.write(struct.pack('f', trY))
        x+=1
    lvlCode.seek(0)
    buffer = lvlCode.read()
    compressed = zlib.compress(buffer)[2:]
    based = base64.b64encode(compressed)
    code += based.decode('utf-8') + "~"
    return code


#load gif with
#gif = Image.open("name.gif")

#resizes gif to scaleX,scaleY
#pixels with grayscale value at least cutoff (0-255) will be drawn
def gifToFrames(gif,scaleX,scaleY,cutoff):
    frames = []
    t = 0
    while True:
        try: gif.seek(t)
        except: break
        altgif = ImageOps.grayscale(gif.resize((scaleX,scaleY)))
        gray = [*altgif.getdata()]
        frames.append([[0]*scaleX for i in range(scaleY)])
        for y in range(scaleY):
            for x in range(scaleX):
                if gray[y*X+x]>=cutoff: frames[t][y][x] = 1
        t+=1
    return frames

def getIntervals(onlist):
    l = len(onlist)
    intervals = []
    on = False
    for i in range(l):
        if onlist[i]:
            if not on:
                intervals.append([i,1])
                on = True
            else:
                intervals[-1][1]+=1
        else:
            if on:
                on = False
                intervals[-1].append(l-intervals[-1][1])
    if on: intervals[-1].append(l-intervals[-1][1])
    return intervals

#translate tiles by dx,dy ingame
#frameLen is number of ingame frames each "frame" lasts
def makeTilesFromFrames(frames,dx=0,dy=0,frameLen=1):
    w = len(frames[0][0])
    h = len(frames[0])
    l = len(frames)
    tileList = []
    for x in range(w):
        for y in range(h):
            onlist = [0]*l
            for t in range(l):
                if frames[t][y][x]: onlist[t] = 1
            for block in getIntervals(onlist):
                new = tile.Tile()
                new.Pos = [x*25+dx,y*25+dy]
                new.Width = 25
                new.Height = 25
                if block[2]:
                    new.TileID = "r"
                    new.TileName = f"POP{block[0]*frameLen},{block[1]*frameLen},{block[2]*frameLen}"
                else:
                    new.TileID = "b"
                tileList.append(new)
    return tileList

def makeLevelFromFrames(frames,dx=0,dy=0,frameLen=1):
    return encodeLevel("Name",makeTilesFromFrames(frames,dx,dy,frameLen),0)
