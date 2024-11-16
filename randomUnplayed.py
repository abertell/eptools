# download these and save in the same directory as this file
# https://github.com/klementc/exitpath-maker-archive/blob/master/pbsArchive.csv
# https://github.com/klementc/exitpath-maker-archive/blob/master/levelsArchive.csv

users = ["Nairod"]

from random import choice
from collections import defaultdict

file_path = "pbsArchive.csv"
data_path = "levelsArchive.csv"

levels = defaultdict(list)
has_user = set()
level_data = {}

dat = str(open(data_path,'rb').read()).replace('\\r\\n','').split('\\n')
for s in dat[1:]:
    line = [i for i in s.split(',') if '~#' not in i]
    if len(line)<2:
        continue
    num = line[0]
    author = line[-2]
    newline = line[1:-2]
    if len(newline)>2:
        name = ','.join(newline[:len(newline)//2+1])
    else:
        name = newline[0]
    level_data[num] = (name,author)
    
L = open(file_path).readlines()
for s in L[1:]:
    line = s.strip().split(',')
    lvl,usr,t1,t2,t3,vid = line[:6]
    date,tas = line[-2:]
    comment = ','.join(line[6:-2])
    levels[lvl].append(([*map(int,(t1,t2,t3))],usr,comment,int(tas),bool(vid)))
    if usr in users:
        has_user.add(lvl)

levels = [(i,levels[i]) for i in levels if i not in has_user]
print("enter to roll level")
while True:
    input()
    lvl,info = choice(levels)
    name,author = level_data[lvl]
    name = name.replace('\\','')
    print(f'https://exitpath-maker.net/{lvl}')
    print(f'{name} by {author}')
    print('-'*30)
    for time,usr,comment,tas,vid in sorted(info):
        ustr = '[TAS]'*tas + f'{usr}'
        comment = f'"{comment}"'
        if comment in ['""', '"None"', '"No comment"']:
            comment = ''
        t1,t2,t3 = map(str,time)
        t3 = t3.zfill(2)
        if t1 == '0':
            tstr = f'{t2}.{t3}'
        else:
            tstr = f'{t1}:{t2.zfill(2)}.{t3}'
        print(f'{ustr}: {tstr} {comment}')
    print('-'*30)
    print()
