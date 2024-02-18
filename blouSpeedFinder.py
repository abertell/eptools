#left only works at x = 1025
#right works at x = 0, 425-500, 850-1000, 6575-8175

from math import trunc, floor

playerW = 13.8
tileW = 25
eps = 0.01

def rnd(x):
    return trunc(x*20)/20

def bloublou(x,v,wall,left=False):
    if left: return floor((x+v-playerW/2+1)/tileW)*tileW >= wall and rnd(x+v) < wall+playerW/2-1-eps
    return floor((x+v+playerW/2-1)/tileW)*tileW < wall and rnd(x+v) > wall-playerW/2+1-eps

def testblou(wall):
    speeds = []
    for v in range(-470,471):
        w = wall*20 + (118 if v<0 else -118)
        nx = (w-v)/20
        if bloublou(nx,v/20,wall,v<0): speeds.append(v/20)
    return speeds

def DispBlouSpeeds(wallX):
    print(f'x = {wallX}:')
    speeds = testblou(wallX)
    i = 0
    while i<len(speeds):
        print(*speeds[i:i+8],sep=', ')
        i += 8

DispBlouSpeeds(1000)
DispBlouSpeeds(1025)
