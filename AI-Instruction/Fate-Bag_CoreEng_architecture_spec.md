# Token Application Architecture Specification

## Objective

Define a technology-independent domain architecture for a Token/Card application implemented initially with:

- Python
- PyQt6
- Pydantic
- QGraphicsScene
- JSON persistence
- Deck/Card library (adapter layer)
- No SQL persistence

Architecture model:

```text
Domain Model
    |
Game Engine
    |
Application Services
    |
Adapters
    |
GUI (PyQt6)
```

The architecture must allow future migration to:

```text
Core Domain
    |
FastAPI
    |
React Frontend
```

---

# Technology Decisions

## Approved Technologies

```text
Python
PyQt6
Pydantic
QGraphicsScene
JSON
pyCardDeck (or equivalent Deck/Card library)
```

## Forbidden Dependencies Inside Core

The following must never be imported inside:

```text
core/models
core/engine
core/services
core/events
```

Forbidden:

```text
PyQt6
QWidget
QPixmap
QGraphicsScene
React
HTML
CSS
FastAPI
```

The core must remain UI-agnostic.

---

# Deck/Card Library Evaluation

## Usage Strategy

Deck/Card libraries are suitable for:

```text
shuffle
draw
draw_many
discard
deck management
random extraction
```

## Required Extension Layer

A custom adapter must wrap the library.

Example:

```text
TokenDeck
    wraps
Deck/Card Library
```

The library alone does not provide:

```text
token metadata
token states
categories
weights
rarity
positioning
domain events
serialization rules
```

These features must be implemented in the Core Domain.

## Suitability Assessment

| Feature | Native Deck Library | Adapter Required |
|----------|----------|----------|
| Shuffle | Yes | No |
| Draw | Yes | No |
| Draw N | Yes | No |
| Unique Cards | Usually | No |
| Token Metadata | No | Yes |
| Categories | No | Yes |
| Tags | No | Yes |
| State Management | No | Yes |
| Positioning | No | Yes |
| Events | No | Yes |
| Serialization | Partial | Yes |
| Weighted Draw | Rarely | Yes |
| Rarity Rules | No | Yes |

Conclusion:

Deck/Card libraries are acceptable as low-level randomization engines but not as the domain model.

---

# Domain Model

## TokenShape

Allowed values:

```text
CIRCLE
HEXAGON
```

## TokenFrontType

Allowed values:

```text
TEXT
IMAGE
```

## TokenState

Allowed values:

```text
FACE_DOWN
FACE_UP
EXCLUDED
SELECTED
LOCKED
REMOVED
```

## Token

Required fields:

```text
id
name
shape
front_type
front_value
back_value
categories
tags
metadata
weight
rarity
```

Field definitions:

### id

```text
UUID
Auto-generated
Immutable
```

### name

```text
Non-empty string
```

### shape

```text
TokenShape
```

### front_type

```text
TEXT
IMAGE
```

### front_value

If TEXT:

```text
Non-empty text
```

If IMAGE:

```text
Existing image file path
```

### back_value

```text
Common image path
or
Custom image path
```

### categories

```text
List[str]
```

### tags

```text
List[str]
```

### metadata

```text
Dict[str, Any]
```

### weight

```text
float
default = 1.0
```

### rarity

```text
Optional string
```

---

# TableToken

Represents a Token instance inside a session.

Fields:

```text
token_id
state
x
y
z
rotation
```

Constraints:

```text
x: 0.0 - 100.0
y: 0.0 - 100.0
z: 0.0 - 100.0
rotation: 0 - 180
```

---

# Session Model

Fields:

```text
session_id
seed
table_tokens
created_at
```

Properties:

```text
unique tokens
deterministic recreation
draw history
```

---

# Engine Requirements

## Session Creation

Supported:

```text
use_all_tokens()
use_token_ids()
exclude_token_ids()
use_category()
use_random_subset()
```

Guarantees:

```text
no duplicates
valid token references only
all tokens initially FACE_DOWN
```

---

# Shuffle

Supported:

```text
shuffle()
shuffle(seed)
```

Guarantees:

```text
deterministic seed support
random order
no duplication
```

---

# Position Generation

Supported:

```text
random positions
grid positions
custom positions
```

Output:

```text
x
y
z
rotation
```

The GUI converts these values to pixels.

---

# Draw Operations

Supported:

```text
draw(k)
draw_one()
draw_specific(token_id)
draw_category(category)
draw_weighted()
draw_without_replacement()
draw_with_replacement()
draw_excluding(ids)
draw_by_rarity()
```

---

# Reveal Operations

Supported:

```text
reveal(token_id)
reveal_many(ids)
reveal_all()
```

State transition:

```text
FACE_DOWN -> FACE_UP
```

---

# Hide Operations

Supported:

```text
hide(token_id)
hide_many(ids)
hide_all()
```

State transition:

```text
FACE_UP -> FACE_DOWN
```

---

# Reset Operations

Supported:

```text
reset_session()
reset_draw_history()
reset_positions()
```

Guarantees:

```text
all tokens FACE_DOWN
history cleared
```

---

# Validation Rules

## Token Validation

Invalid:

```text
missing name
empty text front
missing image
invalid image path
invalid shape
invalid front type
negative weight
```

---

## Session Validation

Invalid:

```text
empty token set
duplicate token ids
invalid references
```

---

## Draw Validation

Invalid:

```text
k < 0
session not initialized
token does not exist
```

Behavior:

```text
strict mode -> exception
safe mode -> clamp result
```

---

# Domain Events

The Core emits events.

The GUI listens.

The Core never references GUI classes.

## Events

```text
TokenCreated
TokenUpdated
TokenDeleted

SessionStarted
SessionLoaded
SessionClosed

TokensDrawn
TokenRevealed
TokenHidden

SessionReset
SessionShuffled
```

---

# Event Contract

Each event contains:

```text
event_id
event_type
timestamp
payload
```

---

# Application Services

Services orchestrate the engine.

Examples:

```text
TokenService
SessionService
DrawService
PersistenceService
```

Services may:

```text
load repositories
validate requests
emit events
invoke engine methods
```

---

# Repository Layer

## TokenRepository

Responsibilities:

```text
save_token
load_token
delete_token
list_tokens
```

## SessionRepository

Responsibilities:

```text
save_session
load_session
delete_session
```

---

# JSON Persistence

Required:

```text
Token -> dict
dict -> Token

Session -> dict
dict -> Session
```

Implementation:

```text
Pydantic model_dump()
Pydantic model_validate()
```

JSON is the single persistence mechanism for version 1.

---

# GUI Contract

The GUI must never contain business rules.

Allowed:

```text
render token
flip animation
drag interaction
selection interaction
display dialogs
```

Forbidden:

```text
draw logic
shuffle logic
validation logic
session rules
```

These responsibilities belong exclusively to the Core.

---

# Future Migration Path

Current:

```text
Core
    |
PyQt6
```

Future:

```text
Core
    |
FastAPI
    |
React
```

Migration goal:

```text
Reuse:
- models
- engine
- services
- events
- repositories

Replace:
- PyQt6 GUI
```

Expected Core Reuse:

```text
>= 80%
```
