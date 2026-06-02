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
    SELECTED = "SELECTED"
    LOCKED = "LOCKED"
    REMOVED = "REMOVED"
