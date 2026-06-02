# Deck/Card Library Encapsulation Rules

## Purpose

This document defines how an AI coding agent must encapsulate any external Deck/Card library used by the Token application.

The external library may be:

```text
pyCardDeck
or
another equivalent Deck/Card package
```

The library must never become part of the Core Domain API.

The Core Domain must depend only on internal abstractions.

---

# Architectural Rule

The Deck/Card library must be wrapped by a custom adapter.

Required structure:

```text
src/
├── core/
│   ├── engine/
│   ├── models/
│   ├── services/
│   └── repositories/
│
└── infrastructure/
    └── deck_adapter/
        ├── token_deck.py
        └── README.md
```

Allowed dependency direction:

```text
core
    depends on
internal interfaces / protocols

infrastructure.deck_adapter
    depends on
external Deck/Card library
```

Forbidden dependency direction:

```text
core
    imports
pyCardDeck
```

---

# Main Principle

The Core must know only this concept:

```text
TokenDeck
```

The Core must not know:

```text
pyCardDeck
Deck
Card
external library classes
external library exceptions
external library configuration
```

The external library is an implementation detail.

---

# Adapter Responsibility

The adapter must expose a stable internal API.

Example adapter name:

```text
TokenDeck
```

Location:

```text
src/infrastructure/deck_adapter/token_deck.py
```

The adapter may internally use:

```text
pyCardDeck.Deck
```

but must expose only project-specific methods.

---

# Required Adapter Methods

The adapter should support at least:

```python
class TokenDeck:
    def __init__(self, token_ids: list[str], seed: int | None = None) -> None:
        ...

    def shuffle(self) -> None:
        ...

    def draw_one(self) -> str:
        ...

    def draw_many(self, k: int) -> list[str]:
        ...

    def remaining_count(self) -> int:
        ...

    def is_empty(self) -> bool:
        ...
```

Optional methods:

```python
    def reset(self, token_ids: list[str]) -> None:
        ...

    def peek_all(self) -> list[str]:
        ...

    def remove(self, token_id: str) -> None:
        ...

    def contains(self, token_id: str) -> bool:
        ...
```

---

# What the Adapter May Do

The adapter may perform only low-level deck operations:

```text
shuffle
draw one
draw many
check remaining cards
reset internal deck
```

The adapter may normalize external exceptions into internal exceptions.

The adapter may convert external card objects into token ids.

The adapter may enforce deterministic shuffle only if the external library supports it reliably.

If deterministic shuffle is not supported by the library, the adapter must use Python random.Random(seed) internally.

---

# What the Adapter Must Not Do

The adapter must not implement domain rules.

Forbidden inside adapter:

```text
TokenState management
FACE_DOWN / FACE_UP transitions
image validation
text validation
category filtering
tag filtering
rarity rules
weighted draw business logic
domain events
session creation
JSON persistence
PyQt6 rendering
QGraphicsScene operations
```

These belong to:

```text
core.models
core.engine
core.services
core.events
infrastructure.json
gui_pyqt
```

---

# Core Engine Responsibility

The Core Engine owns all domain rules.

The Core Engine must handle:

```text
valid token set creation
duplicate prevention
token state changes
FACE_DOWN / FACE_UP / LOCKED / REMOVED
draw eligibility
category filtering
tag filtering
rarity filtering
weighted draw
draw with replacement
draw without replacement
domain events
session reset
draw history
```

The Core Engine may delegate only raw random deck operations to TokenDeck.

---

# Token Identity Rule

The adapter must work with token ids only.

Correct:

```python
TokenDeck(token_ids=["uuid-1", "uuid-2", "uuid-3"])
```

Wrong:

```python
TokenDeck(tokens=[Token(...), Token(...)])
```

Reason:

```text
The adapter must not know the Token model.
The adapter must not know Token metadata.
The adapter must not know Token state.
```

---

# External Library Import Rule

External Deck/Card imports are allowed only in:

```text
src/infrastructure/deck_adapter/
```

Example allowed:

```python
# src/infrastructure/deck_adapter/token_deck.py

import pyCardDeck
```

Example forbidden:

```python
# src/core/engine/session_engine.py

import pyCardDeck
```

---

# Exception Handling Rule

External exceptions must not leak outside the adapter.

Correct:

```python
try:
    card = self._deck.draw()
except ExternalDeckEmptyError as exc:
    raise DeckEmptyError() from exc
```

Wrong:

```python
raise pyCardDeck.SomeException()
```

Internal exceptions should be defined in the project, for example:

```text
DeckEmptyError
InvalidDeckOperationError
DeckAdapterError
```

Recommended location:

```text
src/infrastructure/deck_adapter/exceptions.py
```

or, if the Core must catch them:

```text
src/core/engine/exceptions.py
```

---

# Deterministic Seed Rule

The application requires repeatable shuffle behavior.

The adapter must support:

```python
TokenDeck(token_ids, seed=1234)
```

Expected behavior:

```text
same token ids + same seed = same draw order
```

If the external library does not guarantee seeded shuffle:

```text
do not rely on the external library shuffle
use random.Random(seed) on a local list of token ids
```

Preferred implementation for deterministic behavior:

```python
import random

class TokenDeck:
    def __init__(self, token_ids: list[str], seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self._cards = list(token_ids)

    def shuffle(self) -> None:
        self._rng.shuffle(self._cards)

    def draw_one(self) -> str:
        if not self._cards:
            raise DeckEmptyError()
        return self._cards.pop()
```

Using the external library is optional if it weakens determinism.

---

# Draw Many Rule

The method:

```python
draw_many(k)
```

must validate:

```text
k >= 0
k <= remaining_count in strict mode
```

If strict mode is not implemented in the adapter, the Core Engine must decide behavior.

Preferred adapter behavior:

```text
raise internal exception when k is invalid
```

The Core Engine may catch and transform this into safe behavior.

---

# Replacement Rule

The adapter should primarily support draw without replacement.

The Core Engine must decide whether a draw is:

```text
with replacement
without replacement
```

If draw with replacement is needed, the Core Engine may either:

```text
not remove the token from eligible candidates
or
reinsert the drawn token after draw
```

The adapter must not decide this business rule.

---

# Weighted Draw Rule

Weighted draw must not be delegated to a generic Deck/Card library unless the adapter can guarantee exact behavior.

Preferred responsibility:

```text
core.engine handles weighted candidate selection
```

The adapter may still be used after the weighted candidate list has been prepared.

---

# Category and Tag Rule

The adapter must not filter by category or tag.

Correct flow:

```text
Core Engine filters token ids by category/tag
Core Engine passes eligible ids to TokenDeck
TokenDeck shuffles/draws ids
Core Engine updates session state
```

Wrong flow:

```text
TokenDeck receives Token objects and filters category/tag internally
```

---

# State Rule

The adapter must not know table state.

Forbidden in adapter:

```text
FACE_DOWN
FACE_UP
SELECTED
LOCKED
REMOVED
EXCLUDED
```

Correct flow:

```text
Core Engine determines eligible FACE_DOWN token ids
TokenDeck draws from those ids
Core Engine updates selected tokens to FACE_UP
Core Engine emits TokensDrawn event
```

---

# Event Rule

The adapter must not emit domain events.

Forbidden:

```python
self.event_bus.emit(TokensDrawn(...))
```

Events are emitted by:

```text
core.services
or
core.engine
```

---

# Serialization Rule

The adapter must not serialize sessions or tokens.

Forbidden:

```text
TokenDeck -> JSON
JSON -> TokenDeck
```

Serialization belongs to:

```text
infrastructure.json
```

The adapter may be reconstructed from serialized session state by receiving token ids.

---

# GUI Rule

The adapter must not import or reference:

```text
PyQt6
QGraphicsScene
QGraphicsItem
QWidget
QPixmap
QPainter
```

The adapter must not know:

```text
pixel size
screen position
animation
flip rendering
mouse selection
```

---

# Recommended Minimal Implementation

```python
from __future__ import annotations

import random


class DeckEmptyError(Exception):
    pass


class InvalidDeckOperationError(Exception):
    pass


class TokenDeck:
    def __init__(self, token_ids: list[str], seed: int | None = None) -> None:
        if len(token_ids) != len(set(token_ids)):
            raise InvalidDeckOperationError("Duplicate token ids are not allowed")

        self._rng = random.Random(seed)
        self._cards = list(token_ids)

    def shuffle(self) -> None:
        self._rng.shuffle(self._cards)

    def draw_one(self) -> str:
        if not self._cards:
            raise DeckEmptyError("Cannot draw from empty deck")
        return self._cards.pop()

    def draw_many(self, k: int) -> list[str]:
        if k < 0:
            raise InvalidDeckOperationError("k must be >= 0")

        if k > len(self._cards):
            raise DeckEmptyError("Not enough cards in deck")

        return [self.draw_one() for _ in range(k)]

    def remaining_count(self) -> int:
        return len(self._cards)

    def is_empty(self) -> bool:
        return len(self._cards) == 0

    def peek_all(self) -> list[str]:
        return list(self._cards)
```

This implementation may replace an external Deck/Card library if the external library does not provide deterministic behavior.

---

# Recommended pyCardDeck Wrapper

Use this only if pyCardDeck is confirmed compatible with required behavior.

```python
from __future__ import annotations

import pyCardDeck


class TokenDeck:
    def __init__(self, token_ids: list[str], seed: int | None = None) -> None:
        if seed is not None:
            raise NotImplementedError(
                "Seeded deterministic shuffle must be verified before using pyCardDeck here"
            )

        if len(token_ids) != len(set(token_ids)):
            raise InvalidDeckOperationError("Duplicate token ids are not allowed")

        self._deck = pyCardDeck.Deck(cards=list(token_ids), name="Token Deck")

    def shuffle(self) -> None:
        self._deck.shuffle()

    def draw_one(self) -> str:
        try:
            return self._deck.draw()
        except Exception as exc:
            raise DeckEmptyError("Cannot draw from empty deck") from exc

    def draw_many(self, k: int) -> list[str]:
        if k < 0:
            raise InvalidDeckOperationError("k must be >= 0")
        return [self.draw_one() for _ in range(k)]

    def remaining_count(self) -> int:
        return len(self._deck.cards)

    def is_empty(self) -> bool:
        return self.remaining_count() == 0
```

Before using this implementation, the AI agent must verify the real pyCardDeck API.

---

# Testing Requirements

Create tests for:

```text
adapter initialization
duplicate ids rejected
shuffle changes order
same seed gives same order
draw_one removes one id
draw_many removes k ids
draw_many with k < 0 fails
draw_many over available count fails
empty deck draw fails
external exceptions do not leak
```

Recommended location:

```text
src/tests/infrastructure/test_token_deck.py
```

---

# Copilot Agent Instructions

When implementing this layer:

1. Create or update:

```text
src/infrastructure/deck_adapter/token_deck.py
src/infrastructure/deck_adapter/exceptions.py
src/tests/infrastructure/test_token_deck.py
```

2. Do not import external Deck/Card libraries outside:

```text
src/infrastructure/deck_adapter/
```

3. Do not pass Token objects into TokenDeck.

4. Pass only token ids.

5. Keep all state transitions in the Core Engine.

6. Keep all GUI rendering in gui_pyqt.

7. Keep all JSON persistence in infrastructure/json.

8. Prefer deterministic internal implementation if external library behavior is uncertain.

9. Keep adapter API stable even if the external library changes.

10. Add tests proving the Core does not depend directly on pyCardDeck.

---

# Acceptance Criteria

The implementation is valid only if:

```text
core contains no import of pyCardDeck
gui_pyqt contains no import of pyCardDeck
TokenDeck accepts only list[str]
TokenDeck exposes stable project-specific methods
external exceptions are wrapped
deterministic seed behavior is tested
domain state is not managed by adapter
events are not emitted by adapter
JSON persistence is not handled by adapter
```
