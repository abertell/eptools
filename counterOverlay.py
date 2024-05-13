#SETUP

from tkinter import *
from tkinter import font
from pynput import keyboard as kb
root = Tk()
root.title("Random stuff")
root.configure(bg='black')
DEFAULT_FONT = font.nametofont("TkDefaultFont")


#CUSTOM PARAMETERS

COUNTERS = 2
COUNTER_LABELS = ['Jumps:', 'Resets:']
COUNT_KEYS = ['up', 'esc']
RESET_KEYS = ['backspace', 'backspace']

HEADER_TEXT = ''
UP_SYMBOL = '\u2b9d'
LEFT_SYMBOL = '\u2b9c'
DOWN_SYMBOL = '\u2b9f'
RIGHT_SYMBOL = '\u2b9e'
FLOW_SYMBOL = 'flow'
ARROW_FONT = DEFAULT_FONT
FLOW_FONT = ("Arial", 11, "bold italic")


#CODE

num_map = [41,33,64,35,36,37,94,38,42,40]

def interpret_key(key):
    keylist = []
    if len(key)>1:
        if key in ['up','left','down','right','flow']:
            keylist = gamekeys[key]
        else: keylist.append(eval(f"kb.Key.{key}"))
    elif len(key)==1:
        ind = ord(key)
        alt = 0
        if 65<=ind<=90: alt=ind+32
        elif 97<=ind<=122: alt=ind-32
        elif 48<=ind<=57: alt=num_map[ind]
        elif ind in num_map: alt=num_map.index(ind)+48
        if alt:
            keylist.append(kb.KeyCode.from_char(chr(ind)))
            keylist.append(kb.KeyCode.from_char(chr(alt)))
    return keylist

gamekeys = {
    'up': interpret_key('w')+[kb.Key.up],
    'left': interpret_key('a')+[kb.Key.left],
    'down': interpret_key('s')+[kb.Key.down],
    'right': interpret_key('d')+[kb.Key.right],
    'flow': [kb.Key.space, kb.Key.shift, kb.Key.shift_r]
}

def count(i):
    global counters
    counters[i] += 1
    labels2[i].configure(text=f"{counters[i]}")

def reset(i):
    global counters
    counters[i] = 0
    labels2[i].configure(text="0")

def show(target,disp):
    target.configure(text=disp)

def hide(target):
    target.configure(text='')

counters = [0]*COUNTERS
labels1, labels2, countkeys, resetkeys = [],[],[],[]

for i in range(COUNTERS):
    labels1.append(Label(root, text=COUNTER_LABELS[i], bg='black', fg='white'))
    labels1[-1].grid(column=0, row=i+1)
    labels2.append(Label(root, text="0", bg='black', fg='white'))
    labels2[-1].grid(column=1, row=i+1)
    countkeys.append(interpret_key(COUNT_KEYS[i]))
    resetkeys.append(interpret_key(RESET_KEYS[i]))

spacing = [1,6,10,4,4,4]
space = []
for i in range(6):
    space.append(Label(root, text=" "*spacing[i], bg='black', fg='white'))
    space[i].grid(column=i, row=0)
space[0].configure(text=HEADER_TEXT)

keyup = Label(root, bg='black', fg='white', font=ARROW_FONT)
keyup.grid(column=4, row=1)
keyleft = Label(root, bg='black', fg='white', font=ARROW_FONT)
keyleft.grid(column=3, row=2)
keydown = Label(root, bg='black', fg='white', font=ARROW_FONT)
keydown.grid(column=4, row=2)
keyright = Label(root, bg='black', fg='white', font=ARROW_FONT)
keyright.grid(column=5, row=2)
keyflow = Label(root, bg='black', fg='white', font=FLOW_FONT)
keyflow.grid(column=2, row=2)

def on_press(key):
    if key in gamekeys['up']: show(keyup, UP_SYMBOL)
    if key in gamekeys['left']: show(keyleft, LEFT_SYMBOL)
    if key in gamekeys['down']: show(keydown, DOWN_SYMBOL)
    if key in gamekeys['right']: show(keyright, RIGHT_SYMBOL)
    if key in gamekeys['flow']: show(keyflow, FLOW_SYMBOL)

def on_release(key):
    for i in range(COUNTERS):
        if key in countkeys[i]: count(i)
        if key in resetkeys[i]: reset(i)
    if key in gamekeys['up']: hide(keyup)
    if key in gamekeys['left']: hide(keyleft)
    if key in gamekeys['down']: hide(keydown)
    if key in gamekeys['right']: hide(keyright)
    if key in gamekeys['flow']: hide(keyflow)

listener = kb.Listener(on_press=on_press, on_release=on_release)
listener.start()
root.mainloop()
