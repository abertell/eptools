#SETUP

from tkinter import *
from tkinter import font
from pynput import keyboard as kb
root = Tk()
root.title("Random stuff")
root.configure(bg='black')
DEFAULT_FONT = font.nametofont("TkDefaultFont")


#CUSTOM PARAMETERS

COUNT_KEY = 'c'
RESET_KEY = 'esc'
HEADER_TEXT = ''
COUNTER_LABEL = 'Deaths:'

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
    if len(key)>1: keylist.append(eval(f"kb.Key.{key}"))
    else:
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

def count():
    global counter
    counter += 1
    label2.configure(text=f"{counter}")

def reset():
    global counter
    counter = 0
    label2.configure(text="0")

def show(target,disp):
    target.configure(text=disp)

def hide(target):
    target.configure(text='')

counter = 0
label1 = Label(root, text=COUNTER_LABEL, bg='black', fg='white')
label1.grid(column=0, row=2)
label2 = Label(root, text="0", bg='black', fg='white')
label2.grid(column=1, row=2)

spacing = [1,6,10,4,4,4]
space = []
for i in range(6):
    space.append(Label(root, text=" "*spacing[i], bg='black', fg='white'))
    space[i].grid(column=i, row=0)
space[0].configure(text=HEADER_TEXT)

keyup = Label(root, bg='black', fg='white', font=ARROW_FONT)
keyup.grid(column=4, row=1)
upkeys = interpret_key('w')+[kb.Key.up]

keyleft = Label(root, bg='black', fg='white', font=ARROW_FONT)
keyleft.grid(column=3, row=2)
leftkeys = interpret_key('a')+[kb.Key.left]

keydown = Label(root, bg='black', fg='white', font=ARROW_FONT)
keydown.grid(column=4, row=2)
downkeys = interpret_key('s')+[kb.Key.down]

keyright = Label(root, bg='black', fg='white', font=ARROW_FONT)
keyright.grid(column=5, row=2)
rightkeys = interpret_key('d')+[kb.Key.right]

keyflow = Label(root, bg='black', fg='white', font=FLOW_FONT)
keyflow.grid(column=2, row=2)
flowkeys = [kb.Key.space, kb.Key.shift, kb.Key.shift_r]

countkeys = interpret_key(COUNT_KEY)
resetkeys = interpret_key(RESET_KEY)

def on_press(key):
    if key in countkeys: count()
    if key in resetkeys: reset()
    if key in upkeys: show(keyup, UP_SYMBOL)
    if key in leftkeys: show(keyleft, LEFT_SYMBOL)
    if key in downkeys: show(keydown, DOWN_SYMBOL)
    if key in rightkeys: show(keyright, RIGHT_SYMBOL)
    if key in flowkeys: show(keyflow, FLOW_SYMBOL)

def on_release(key):
    if key in upkeys: hide(keyup)
    if key in leftkeys: hide(keyleft)
    if key in downkeys: hide(keydown)
    if key in rightkeys: hide(keyright)
    if key in flowkeys: hide(keyflow)

listener = kb.Listener(on_press=on_press, on_release=on_release)
listener.start()
root.mainloop()
