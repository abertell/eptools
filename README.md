# eptools
Any (small) miscellaneous tools for exit path I make.

Dependencies:
- levellib: useful tools for encoding/decoding exit path levels, written by @klementc

Current:
- blouSpeedFinder: computes all possible bloublou speeds at a given x coordinate
- counterOverlay: key overlay with hotkeys for incrementing a counter (requires [pynput](https://pypi.org/project/pynput/))
- gifToLevel: GIF to level converter (requires [pillow](https://pypi.org/project/pillow/))
- makeTransient: replaces all blocks in a level with pop triggers that follow a certain timed path
- randomUnplayed: selects a random unplayed level from the database (requires database files in comments)

Future (maybe):
- Double/bloublou finder for TASing (this is already done I just don't want to refactor it)
- AI generated levels
- ???
