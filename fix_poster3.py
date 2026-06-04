import re

with open("plugins/thumbnail_maker.py", "r") as f:
    data = f.read()

# Replace font sizes to make them look better and adjust coords for Poster 3
# Let's adjust title position to perfectly match the preview.
# Title should be smaller, say size 60, white color
# Title coordinates from (1115, 170) -> x=1115, y=170 is fine but wait, title is 65 in Roboto-Black.

# I will write a sed script to adjust some coordinates.
