# Pianificazione_Attivita

## Obiettivo

Realizzare una applicazione Token/Card basata su:

```text
Python
PyQt6
Pydantic
JSON
QGraphicsScene
Deck/Card Adapter Layer
```

seguendo rigorosamente le specifiche contenute nei documenti:

```text
Fate-Bag_CoreEng_architecture_spec.md
deck_card_library_encapsulation_rules.md
```

Tutte le attività devono essere completate in ordine.

Non saltare fasi.

Non implementare funzionalità appartenenti a fasi successive.

Ogni fase deve terminare con:

```text
codice funzionante
test automatici
commit Git
```

---

# Fase 0 - Analisi iniziale

## Obiettivi

Leggere e comprendere:

```text
Fate-Bag_CoreEng_architecture_spec.md
deck_card_library_encapsulation_rules.md
```

Verificare che la struttura delle cartelle esista.

Verificare che ogni cartella contenga il proprio README.md.

## Deliverable

Nessun codice.

Solo verifica struttura.

---

# Fase 1 - Environment Setup

## Obiettivi

Preparare ambiente di sviluppo.

## Attività

Creare:

```text
requirements.txt
requirements-dev.txt
```

Installare:

```text
pydantic
PyQt6
pytest
pytest-cov
```

Non installare database.

Non installare ORM.

Non installare FastAPI.

## Configurazione

Creare:

```text
.gitignore
```

con esclusione di:

```text
.venv
__pycache__
.pytest_cache
.idea
.vscode
dist
build
```

Creare:

```text
config/
```

con file placeholder.

## Deliverable

Ambiente Python funzionante.

Comando:

```bash
pytest
```

deve eseguire correttamente.

---

# Fase 2 - Fondazioni del Core

## Obiettivi

Creare tutti i modelli dominio.

## Attività

Implementare:

```text
src/core/models/
```

Creare:

```text
token.py
table_token.py
session.py
enums.py
```

Utilizzare Pydantic.

Implementare:

```text
TokenShape
TokenFrontType
TokenState
```

Implementare:

```text
Token
TableToken
Session
```

Implementare tutte le validazioni previste.

## Test

Creare:

```text
src/tests/core/
```

Verificare:

```text
id automatico
campi obbligatori
path immagini
vincoli coordinate
stati validi
```

## Deliverable

Modelli completi e testati.

---

# Fase 3 - Eventi di Dominio

## Obiettivi

Creare sistema eventi interno.

## Attività

Implementare:

```text
src/core/events/
```

Creare:

```text
base_event.py
event_types.py
event_bus.py
```

Implementare:

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

## Test

Verificare:

```text
registrazione handler
pubblicazione eventi
payload corretto
```

## Deliverable

Sistema eventi indipendente dalla GUI.

---

# Fase 4 - Deck Adapter Layer

## Obiettivi

Implementare l'incapsulamento della libreria Deck/Card.

## Riferimento

Usare esclusivamente:

```text
deck_card_library_encapsulation_rules.md
```

## Attività

Implementare:

```text
src/infrastructure/deck_adapter/
```

Creare:

```text
token_deck.py
exceptions.py
```

Implementare:

```text
shuffle
draw_one
draw_many
remaining_count
is_empty
```

Utilizzare inizialmente implementazione interna deterministica.

L'integrazione con pyCardDeck deve essere opzionale.

## Test

Verificare:

```text
shuffle
seed deterministico
draw
draw_many
empty deck
duplicati
```

## Deliverable

TokenDeck completamente isolato.

---

# Fase 5 - Core Engine

## Obiettivi

Implementare il motore principale.

## Attività

Implementare:

```text
src/core/engine/
```

Creare:

```text
session_engine.py
draw_engine.py
shuffle_engine.py
```

Implementare:

```text
creazione sessione
selezione token
esclusione token
categorie
tag
pesca
reveal
hide
reset
```

Implementare:

```text
draw uniforme
draw con peso
draw con rarità
draw con reinserimento
draw senza reinserimento
```

## Test

Copertura completa delle regole.

## Deliverable

Core Engine completamente indipendente dalla GUI.

---

# Fase 6 - Application Services

## Obiettivi

Creare orchestrazione applicativa.

## Attività

Implementare:

```text
TokenService
SessionService
DrawService
```

I servizi devono:

```text
usare engine
usare repository
emettere eventi
```

I servizi non devono contenere logica GUI.

## Deliverable

API applicativa stabile.

---

# Fase 7 - Persistenza JSON

## Obiettivi

Implementare salvataggio e caricamento.

## Attività

Implementare:

```text
src/infrastructure/json/
```

Creare:

```text
json_token_repository.py
json_session_repository.py
```

Utilizzare:

```text
model_dump()
model_validate()
```

## Supportare

```text
Token -> JSON
JSON -> Token

Session -> JSON
JSON -> Session
```

## Test

Verificare:

```text
save/load token
save/load session
integrità dati
```

## Deliverable

Persistenza completa.

---

# Fase 8 - Test Console Application

## Obiettivi

Verificare il Core senza GUI.

## Attività

Creare:

```text
src/tools/
```

Creare:

```text
test_console_app.py
```

Funzioni:

```text
crea token
crea sessione
shuffle
draw
reveal
save
load
```

Output testuale.

## Deliverable

Verifica completa del Core.

---

# Fase 9 - GUI Tecnica Minima

## Obiettivi

Creare una GUI PyQt minima per test funzionali.

## Attività

Implementare:

```text
MainWindow
```

Componenti:

```text
carica token
crea sessione
draw 1
draw N
reveal all
hide all
reset
```

Visualizzazione:

```text
lista semplice
nessuna grafica avanzata
```

## Deliverable

Test manuale del Core tramite GUI.

---

# Fase 10 - GUI Release 1

## Obiettivi

Realizzare prima versione utilizzabile.

## Attività

Implementare:

```text
QGraphicsScene
QGraphicsView
```

Creare:

```text
TokenGraphicsItem
TokenTableScene
```

Supportare:

```text
token circolari
token esagonali
front image
front text
back image
```

Supportare:

```text
flip
selezione
layout tavolo
```

Le coordinate devono provenire dal Core.

La GUI non deve generare regole di dominio.

## Deliverable

Release 1 funzionante.

---

# Fase 11 - Hardening

## Obiettivi

Migliorare robustezza.

## Attività

Aumentare copertura test.

Verificare:

```text
error handling
file mancanti
sessioni corrotte
json invalidi
draw invalidi
```

## Deliverable

Sistema stabile.

---

# Regole Globali

## Regola 1

Mai importare:

```text
PyQt6
```

dentro:

```text
src/core/
```

## Regola 2

Mai importare:

```text
pyCardDeck
```

fuori da:

```text
src/infrastructure/deck_adapter/
```

## Regola 3

La GUI non contiene business logic.

## Regola 4

Le regole di pesca appartengono al Core Engine.

## Regola 5

La serializzazione appartiene ai repository JSON.

## Regola 6

Ogni fase deve essere completata e testata prima della successiva.

## Regola 7

Ogni nuova classe deve avere test automatici.

## Regola 8

Preferire implementazioni semplici, deterministiche e testabili.
