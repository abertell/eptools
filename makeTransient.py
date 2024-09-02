import levellib as lvl
from math import sqrt
euclidean = lambda a,b: sqrt((a[0]-b[0])**2+(a[1]-b[1])**2)
maximum = lambda a,b: max(abs(a[0]-b[0]),abs(a[1]-b[1]))
manhattan = lambda a,b: abs(a[0]-b[0])+abs(a[1]-b[1])

# code: level code

# waypoints: markers (from some reference run) that determine how fast the
#   level should move - movement is interpolated linearly between waypoints.
#   Currently these have to be added manually.

# finTime: finish time of reference run

# headstart: how early the blocks spawn before the reference run reaches them

# despawnTime: how long the blocks last before disappearing

# cycleTime: how long until the level can be retried from the start

# blockRadius: blocks will spawn in when they are within this radius of the
#   waypoint path

# dist: distance metric for blockRadius (euclidean, manhattan, or maximum)

# pace: a global modifier to all waypoint splits - 0.95 means 95% speed.


## CONFIG ##

code = ""
waypoints = [
    #(x,y,time),
    
]
finTime = 60.00
headstart = 2.00
despawnTime = 7.00
cycleTime = 30.00
blockRadius = 10
dist = euclidean
pace = 1.0


## CODE ##

name = code[:code.index('~')]+' (Transient)'
tiles = lvl.decodeLevel(code)
for i in range(len(waypoints)):
    waypoints[i] = (*waypoints[i][:2],round((waypoints[i][2])*30/pace))
finTime = round(finTime*30/pace)
headstart = round(headstart*30)
despawnTime = round(despawnTime*30)
cycleTime = round(cycleTime*30)
blocks = []
other = []
maxX = maxY = 0
for tile in tiles:
    t = tile.TileID
    if t=='b': blocks.append(tile)
    else: other.append(tile)
    if t=='s': start = tile
    elif t=='e': fin = tile
    maxX = max(maxX,tile.Pos[0])
    maxY = max(maxY,tile.Pos[1])
hid = lvl.Tile()
hid.Pos = [maxX,maxY]
hid.Width = 25
hid.Height = 25
hid.TileID = ' '
other.append(hid)
waypoints = [
    (*start.Pos,0),
    *waypoints,
    (*fin.Pos,finTime)
]
first = {}
last = {}
for i in range(len(waypoints)-1):
    px,py,pt = waypoints[i]
    nx,ny,nt = waypoints[i+1]
    dt = nt-pt
    for t in range(pt,nt):
        x = px*(nt-t)/dt+nx*(t-pt)/dt
        y = py*(nt-t)/dt+ny*(t-pt)/dt
        for block in blocks:
            pos = tuple(block.Pos)
            if dist(pos,(x-12.5,y-12.5))<blockRadius*25:
                last[pos] = t
                if pos not in first: first[pos] = t
for pos in first:
    pop = lvl.Tile()
    pop.Pos = [*pos]
    pop.Width = 25
    pop.Height = 25
    pop.TileID = 'r'
    diff = last[pos]-first[pos]+despawnTime+1
    wait = max(first[pos]-headstart,0)
    pop.TileName = f'POP{wait},{diff},{max(cycleTime-diff,1)}'
    other.append(pop)

print(lvl.encodeLevel(name,other,2))
