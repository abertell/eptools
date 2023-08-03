from PIL import Image, ImageOps

#Tile class from @klementc
class Tile():
    def __init__(self):
        self.Tag = ""
        self.TileID = ""
        self.TileName = ""
        self.Pos = []
        self.Rotation = 0
        self.Width = 0
        self.Height = 0

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

#encodeLevel method from @klementc
def makeLevelFromFrames(frames,dx=0,dy=0,frameLen=1):
    return encodeLevel("Name",makeTilesFromFrames(frames,dx,dy,frameLen),0)
