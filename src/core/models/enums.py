from enum import Enum


class TokenShape(str, Enum):
    CIRCLE = "CIRCLE"
    SQUARE = "SQUARE"
    PENTAGON = "PENTAGON"
    EPTAGON = "EPTAGON"
    HEXAGON = "HEXAGON"
    OCTAGON = "OCTAGON"
    STAR = "STAR"
    RECTANGLE_3_4 = "RECTANGLE_3:4"
    RECTANGLE_4_3 = "RECTANGLE_4:3"
    RECTANGLE_3_5 = "RECTANGLE_3:5"
    RECTANGLE_5_3 = "RECTANGLE_5:3"


class TokenFrontType(str, Enum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    TEXT_IMAGE = "TEXT_IMAGE"


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