# pipeidea — System Flow

```
                                    USER INPUT
                                        |
                            +-----------+-----------+
                            |           |           |
                         [seed]    [seed+seed]   [topic]
                            |           |           |
                          BLOOM     COLLISION     FORAGE
                            |           |           |
                            +-----+-----+
                                  |
                                  v
                    +=============================+
                    |      PROFILE LOADER         |
                    |  ~/.pipeidea/profiles/       |
                    |                             |
                    |  Active: steve-jobs/         |
                    |  +-----------------------+  |
                    |  | identity.md           |  |
                    |  | taste.md     *        |  |  * most important file
                    |  | ambition.md           |  |
                    |  | knowledge.md          |  |
                    |  | randomness.md         |  |
                    |  | techniques.md         |  |
                    |  | protocol.md           |  |
                    |  | dialogue.md           |  |
                    |  | output.md             |  |
                    |  | modes/{mode}.md       |  |
                    |  +-----------------------+  |
                    |    missing? --> default/     |
                    +=============================+
                                  |
                                  v
                    +=============================+
                    |        COMPOSER             |
                    |     (soul/composer.py)       |
                    |                             |
                    |  Reads profile MDs          |
                    |  Resolves inheritance        |
                    |  Injects runtime context:    |
                    |    - seed content            |
                    |    - garden echoes *         |
                    |    - web stimuli *           |
                    |    - random stimulus *       |
                    |                             |
                    |  Outputs: system prompt      |
                    +=============================+
                          |               |
             * = taste    |               |
               gate       v               v
             applied  +--------+    +-----------+
                      | GARDEN |    |   FORAGE  |
                      | ECHOES |    |  (web)    |
                      +--------+    +-----------+
                      | Search |    | Tavily /  |
                      | past   |    | DDG       |
                      | ideas  |    | search    |
                      |        |    |           |
                      | TASTE  |    | TASTE     |
                      | GATE:  |    | GATE:     |
                      | Still  |    | Surprising|
                      | alive? |    | or noise? |
                      | Kill   |    | Kill      |
                      | stale  |    | generic   |
                      +--------+    +-----------+
                          |               |
                          +-------+-------+
                                  |
                                  v
                    +=============================+
                    |    THE CREATIVE MIND         |
                    |    (single AI call)          |
                    |                             |
                    |    Four Pillars Active:      |
                    |                             |
                    |    KNOWLEDGE                |
                    |    Cast out to 5+ distant    |
                    |    domains simultaneously    |
                    |            |                 |
                    |            v                 |
                    |    TASTE                     |
                    |    Deep structural bridges,  |
                    |    not surface analogies.     |
                    |    Kill anything dead.        |
                    |            |                 |
                    |            v                 |
                    |    RANDOMNESS                |
                    |    ~10-15% wild intrusion.   |
                    |    Chase tangents.            |
                    |            |                 |
                    |            v                 |
                    |    AMBITION                  |
                    |    Refuse smallness.          |
                    |    World-changing or nothing. |
                    |                             |
                    |    Thinking Protocol:        |
                    |    RADIATE --> CONNECT -->   |
                    |    DISRUPT --> TRANSFORM --> |
                    |    CRYSTALLIZE               |
                    |    (free to reorder/loop)    |
                    |                             |
                    |    SELF-EDIT:                |
                    |    Kill mediocre output.     |
                    |    Show 2 alive > 8 filler.  |
                    +=============================+
                                  |
                                  v
                    +=============================+
                    |         OUTPUT               |
                    |                             |
                    |  Surviving ideas only:       |
                    |  - Punchy title              |
                    |  - Vivid description          |
                    |  - Tags / domains             |
                    |  - Favorite marked            |
                    |  - Thread left hanging        |
                    |    (invites next turn)        |
                    +=============================+
                            |           |
                    +-------+           +--------+
                    |                            |
                    v                            v
            +--------------+          +------------------+
            |    GARDEN    |          |   MULTI-TURN     |
            |   (SQLite)   |          |   DIALOGUE       |
            |              |          |                  |
            | Auto-save    |          | "go wilder"      |
            | session +    |          | "that third one" |
            | ideas for    |          | "connect to X"   |
            | future       |          | "I hate these"   |
            | cross-       |          | drop a URL       |
            | pollination  |          |                  |
            +--------------+          +------ + ---------+
                                             |
                                             | loops back to
                                             v
                                        COMPOSER
                                    (with dialogue.md
                                     guiding response)


========================================================
                    PROVIDER LAYER
========================================================

    composer.py --> provider abstraction --> AI API
                    |         |         |
                 Claude    OpenAI    Gemini
                    |         |         |
              (provider-agnostic, swappable via --provider flag)


========================================================
                    INTERFACES
========================================================

    CLI (typer)                    Web UI (FastAPI + htmx)
    |                              |
    pipeidea bloom "X"             Browser at localhost
    pipeidea collide "X" "Y"       SSE streaming
    pipeidea garden                Idea cards
    pipeidea --profile jobs        Dark theme
    |                              |
    +--- both use the same soul, composer, and provider layer ---+


========================================================
    WHAT LIVES WHERE
========================================================

    ~/.pipeidea/
        profiles/                  <-- THE PRODUCT (editable MD)
            default/               <-- unnamed creative force
                identity.md
                taste.md           <-- most important file
                ambition.md
                knowledge.md
                randomness.md
                techniques.md
                protocol.md
                dialogue.md
                output.md
                modes/
                    bloom.md
                    collision.md
                    forage.md
                    revisit.md
            steve-jobs/            <-- overrides only what's different
            da-vinci/
            my-custom/
        garden.db                  <-- SQLite idea storage
        config.toml                <-- API keys, default provider, default profile

    src/pipeidea/                   <-- PLUMBING (Python)
        cli.py
        server.py
        config.py
        soul/
            composer.py
            random_stimulus.py
            profiles.py
        providers/
            base.py, claude.py, openai.py, gemini.py
        forage/
            search.py, scrape.py, stimulus.py
        garden/
            db.py, models.py
```

## The Core Insight

```
Imagination = (Knowledge x Taste + Randomness) ^ Ambition
```

The product IS the markdown files. The Python is plumbing.
The most important file is taste.md.
The most important moment is the self-edit: kill mediocre output before the user sees it.
