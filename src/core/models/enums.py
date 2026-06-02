from enum import Enum


class TokenShape(str, Enum):
    CIRCLE = "CIRCLE"
    HEXAGON = "HEXAGON"


class TokenFrontType(str, Enum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"


class TokenState(str, Enum):
    FACE_DOWN = "FACE_DOWN"
    FACE_UP = "FACE_UP"
    EXCLUDED = "EXCLUDED"
    LOCKED = "LOCKED"

'''
FACE_DOWN : token placed in bag but not revealed.
FACE_UP : token drawn/revealed
EXCLUDED : token excluded from session, not inserted into Bag
LOCKED : token temporarily locked (not editable, not drawable from the bag).
'''