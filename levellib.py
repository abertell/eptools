#from zopfli.zlib import compress
#from zlib import decompress
import zlib
import base64
import io
import struct
import os
import math
import numpy as np

class Tile():
  def __init__(self):
    self.Tag = ""
    self.TileID = ""
    self.TileName = ""
    self.Pos = []
    self.Rotation = 0
    self.Width = 0
    self.Height = 0

class TileDesc:
  def __init__(self, canvasID, xmlID, name, tileid, canResize, canRotate, hasTag, hasName, griding, offsetPoint, size):
    self.Name = name
    self.CanvasID = canvasID
    self.XmlID = xmlID
    self.TileID = tileid
    self.CanResize = canResize
    self.CanRotate = canRotate
    self.HasTag = hasTag
    self.HasName = hasName
    self.Griding = griding
    self.OffsetPoint = offsetPoint
    self.Size = size

Tiles = {
  "end" : TileDesc("End Point","end","Tiles/finish","e",False,False,False,False,25,[0,0],[25,25]),
  "start" : TileDesc("Start Point","start","Tiles/start","s",False,False,False,False,25,[0,0],[25,25]),
  "tile" : TileDesc("Block","tile","Tiles/block","b",False,False,False,False,25,[0,0],[25,25]),
  "trigger" : TileDesc("Trigger","trigger","Tiles/trigger","r",True,False,False,True,25,[0,0],[25,25]),
  "hiddenTile" : TileDesc("Hidden Block","hiddenTile","Tiles/hiddenBlock"," ",False,False,False,False,25,[0,0],[25,25]),
  "popSpike" : TileDesc("Pop Spike","popSpike","Tiles/popSpike","p",True,True,False,True,0,[2,0],[24,54]),
  "spike" : TileDesc("Spike","spike","Tiles/spike","k",False,True,False,False,25,[0,0],[25,25]),
  "halfBlock" : TileDesc("Half Block","halfBlock","Tiles/halfBlock","h",False,False,False,False,12.5,[0,0],[25,12]),
  "grinder" : TileDesc("Grinder","grinder","Tiles/grinder","g",True,False,False,True,0,[78.075, 78.075],[156.15, 156.15]),
  "axe" : TileDesc("Axe","axe","Tiles/axe","a",True,True,False,True,0,[-57.5,0],[115,63.3]),
  "rightTreadmill" : TileDesc("Right Treadmill","rightTreadmill","Tiles/rTrendmill",">",False,False,False,False,25,[0,0],[25,25]),
  "leftTreadmill" : TileDesc("Left Treadmill","leftTreadmill","Tiles/lTrendmill","<",False,False,False,False,25,[0,0],[25,25]),
  "bouncer" : TileDesc("Bouncer","bouncer","Tiles/bouncer","x",False,True,False,True,25,[0,0],[25,25]),
  "fallSpike" : TileDesc("Falling Spike", "fallSpike","Tiles/fallSpike","f",False,True,False,False,25,[2,0],[23.25,25]),
  "laser" : TileDesc("Laser Cannon","laser","Tiles/laser","l",False,True,False,False,0,[10,10],[20,20]),
  "teleport" : TileDesc("Teleporter","teleport","Tiles/teleporter","t",True,False,False,True,0,[12,37.05],[25.05,42.05]),
  "checkPoint" : TileDesc("Checkpoint","checkpoint","Tiles/checkpoint","c",False,False,False,False,0,[1.75,39],[3.5,39]),
  "textBlock" : TileDesc("Text Block","textBlock","Tiles/textBlock","q",True,True,True,False,0,[0,0],[50,50])
}

TileDesc = {
  1 : 'e', #
  2 : 's', #
  3 : 'b', #
  4 : ' ', #
  5 : 'p', #
  6 : 'k', #
  7 : 'h', #
  8 : 'g', #
  9 : 'a', #
  10 : '>',#
  11 : '<',#
  12 : 'x',#
  13 : 'f',#
  14 : 'l',#
  15 : 't',#
  16 : 'c',#
  17 : 'q',#
  18 : 'r'
}

TileDescBin = {
  'e' : 1, #
  's' : 2, #
  'b' : 3, #
  ' ' : 4, #
  'p' : 5, #
  'k' : 6, #
  'h' : 7, #
  'g' : 8, #
  'a' : 9, #
  '>' : 10,#
  '<' : 11,#
  'x' : 12,#
  'f' : 13,#
  'l' : 14,#
  't' : 15,#
  'c' : 16,#
  'q' : 17,#
  'r' : 18
}

BinTiles = {
  Tiles["end"].TileID : Tiles["end"],
  Tiles["start"].TileID: Tiles["start"] ,
  Tiles["tile"].TileID: Tiles["tile"] ,
  Tiles["hiddenTile"].TileID: Tiles["hiddenTile"] ,
  Tiles["popSpike"].TileID: Tiles["popSpike"] ,
  Tiles["spike"].TileID: Tiles["spike"] ,
  Tiles["halfBlock"].TileID: Tiles["halfBlock"] ,
  Tiles["grinder"].TileID: Tiles["grinder"] ,
  Tiles["axe"].TileID: Tiles["axe"] ,
  Tiles["rightTreadmill"].TileID: Tiles["rightTreadmill"] ,
  Tiles["leftTreadmill"].TileID: Tiles["leftTreadmill"] ,
  Tiles["bouncer"].TileID: Tiles["bouncer"] ,
  Tiles["fallSpike"].TileID: Tiles["fallSpike"] ,
  Tiles["laser"].TileID: Tiles["laser"] ,
  Tiles["teleport"].TileID: Tiles["teleport"] ,
  Tiles["checkPoint"].TileID: Tiles["checkPoint"] ,
  Tiles["textBlock"].TileID: Tiles["textBlock"],
  Tiles["trigger"].TileID: Tiles["trigger"]
}

# https://stackoverflow.com/questions/23530449/rotate-scale-and-translate-2d-coordinates
def mult(matrix1,matrix2):
    # Multiply if correct dimensions
    new_matrix = np.zeros(len(matrix1),len(matrix2[0]))
    for i in range(len(matrix1)):
            for j in range(len(matrix2[0])):
                    for k in range(len(matrix2)):
                            new_matrix[i][j] += matrix1[i][k]*matrix2[k][j]
    return new_matrix

def createTileList(levelStream):
    tileList = []
    ms = [[[1,0],[0,1]]]
    count = int.from_bytes(levelStream.read(4), 'little')
    for i in range(count):
        ms.append([[struct.unpack("f",levelStream.read(4))[0],struct.unpack("f",levelStream.read(4))[0]],
                            [struct.unpack("f",levelStream.read(4))[0],struct.unpack("f",levelStream.read(4))[0]]])
    count = int.from_bytes(levelStream.read(4), 'little')
    for i in range(count):
        id = int.from_bytes(levelStream.read(1), 'little')
        t = id & 0x7F
        descriptor = BinTiles[TileDesc[t]]

        newTile = Tile()
        newTile.TileID = TileDesc[t]

        if(descriptor.HasTag):
            l = int.from_bytes(levelStream.read(1), 'little')
            if(l):
                newTile.Tag = levelStream.read(l).decode("UTF-8")
        if(descriptor.HasName):
            l = int.from_bytes(levelStream.read(1), 'little')
            if(l):
                newTile.TileName = levelStream.read(l).decode("UTF-8")
            else:
                newTile.TileName = " "
        coords = []
        matrix = ms[0]
        if ((id & 0x80) != 0):
            ind = int.from_bytes(levelStream.read(4), byteorder='little')
            matrix = ms[ind]
        offsetX = struct.unpack("f",levelStream.read(4))[0]
        offsetY = struct.unpack("f",levelStream.read(4))[0]
        tX = offsetX
        tY = offsetY
        sX = math.sqrt(matrix[0][0] * matrix[0][0] + matrix[0][1] * matrix[0][1]);
        sY = math.sqrt(matrix[1][0] * matrix[1][0] + matrix[1][1] * matrix[1][1]);
        theta = math.atan2(matrix[0][1], matrix[0][0])
        w = round(sX * descriptor.Size[0])
        h = round(sY * descriptor.Size[1])
        x = round(tX - ((w * sX / 2 * (1.0 - math.cos(theta))) + (h * sY / 2 * math.sin(theta))) - descriptor.OffsetPoint[0] * sX)
        y = round(tY - ((h * sY / 2 * (1.0 - math.cos(theta))) - (w * sX / 2 * math.sin(theta))) - descriptor.OffsetPoint[1] * sY);
        r = round(theta*180/math.pi)
        if(descriptor.TileID=="k"):
            print("({},{})->({},{})".format(offsetX, offsetY,x,y))
        newTile.Width = w
        newTile.Height = h
        newTile.Pos = [x, y]
        newTile.Rotation = r
        tileList.append(newTile)
    return tileList

def decodeLevel(levelCode):
    i = levelCode.find("~#-")
    levelData = levelCode[i+3:-1]
    unbased = base64.b64decode(levelData)
    uncompressed = zlib.decompress(unbased,-15)
    lvlStream = io.BytesIO(uncompressed)
    verif = lvlStream.read(4)
    if(int.from_bytes(verif, byteorder='little') != 0x564C5045):
        print("Error")
        return -1
    lvlStream.read(1)
    lvlStream.read(2)
    lvlStream.read(1)
    return createTileList(lvlStream)


def encodeLevel(name, tileList, cfg):
    lvlCode = io.BytesIO()
    code = "{}~#-".format(name)
    ms = [[[1,0],[0,1]]]
    mis = []
    mxs = []
    for t in tileList:
        m = ms[0]
        rot = -(t.Rotation*math.pi)/180
        sX = float(t.Width)/float((BinTiles[t.TileID].Size[0]))
        sY = float(t.Height)/float((BinTiles[t.TileID].Size[1]))
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
        id = TileDescBin[tile.TileID]
        name = tile.TileName
        trX =(tile.Pos[0])
        trY =(tile.Pos[1])
        td = int.to_bytes(TileDescBin[tile.TileID], 1, byteorder='little')
        tmod = int.to_bytes((0x80 if mis[x] != 0 else 0), 1, byteorder='little')
        lvlCode.write(int.to_bytes((td[0] | tmod[0]), 1, byteorder="little"))
        if (BinTiles[tile.TileID].HasTag):
            tag = tile.Tag if tile.Tag else ""
            lvlCode.write(int.to_bytes(len(tag), 1, byteorder='little'))
            lvlCode.write(bytes(tag, 'utf-8'))
        elif (BinTiles[tile.TileID].HasName):
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
