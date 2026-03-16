# 🔥 The Tinder Clone Built in 40 Minutes

> **⚠️ DISCLAIMER:** This project is a demonstration of **MicroCoreOS**'s speed and developer experience.
> It was built **live from scratch in approximately 30-40 minutes**, from initial planning to a fully functional set of REST and WebSocket endpoints.

Red-li is a high-performance, event-driven Tinder clone built using the **MicroCoreOS** micro-kernel architecture. It showcases how "Atomic Microkernel" design allows for rapid iteration without sacrificing maintainability or scalability.

---

## 📽️ Why MicroCoreOS?

The goal of this demo was to prove that with the right architecture, AI coding becomes a superpower rather than a maintenance nightmare.

- **1 File = 1 Feature**: No jumping between controllers, routers, and services.
- **Auto-Discovery**: No manual registration. Drop a file, and it works.
- **Dependency Injection**: Tools like `db`, `http`, and `event_bus` are injected by name.
- **Live Manifest**: `AI_CONTEXT.md` regenerates on every boot, giving your AI exact signatures.

---

## 🛠️ Prerequisites

Before you begin, ensure you have the following installed:
- **Python 3.10+**
- **Git**
- **[uv](https://github.com/astral-sh/uv)** (Fast Python package manager)

---

## 🚀 Quick Start

```bash
git clone https://github.com/theanibalos/tinder-clone-example.git
cd tinder-clone-example
cp .env.example .env
uv run main.py
# Visit http://localhost:5000/docs for the OpenAPI spec
```

---

## 🏗️ Implemented Domains

Despite the 40-minute build time, Red-li includes a comprehensive feature set across modular domains:

| Domain         | Key Features                                                |
| :------------- | :---------------------------------------------------------- |
| **Profiles**   | User profiles, dating preferences, and photo management.    |
| **Swipes**     | Liking, passing, and undoing swipes.                        |
| **Matches**    | Automatic match generation triggered by the Event Bus.      |
| **Messages**   | Real-time chat via WebSockets between matches.              |
| **Discovery**  | Recommendation engine for finding potential partners.       |
| **Moderation** | Blocking and reporting systems.                             |
| **Users**      | Authentication (JWT), registration, and account management. |
| **System**     | Live observability, causal tracing, and health monitoring.  |

---

## 🎨 Architecture: Atomic Microkernel

Every features lives in its own "Atomic" plugin. Here is an example of the Matching logic:

```python
# domains/matches/plugins/check_match_plugin.py
async def execute(self, data: dict, context=None):
    # Triggered by 'swipe.created' event via EventBus
    swipe = data["swipe"]
    if swipe["type"] == "like":
        # Check if the other person also liked back
        reverse_swipe = await self.db.query_one(
            "SELECT * FROM swipe WHERE user_id = $1 AND target_id = $2 AND type = 'like'",
            [swipe["target_id"], swipe["user_id"]]
        )
        if reverse_swipe:
            await self.bus.publish("match.created", {"users": [swipe["user_id"], swipe["target_id"]]})
```

---

## 🛠️ Built-in Tools

Red-li leverages the standard MicroCoreOS toolset:

- **`http`**: FastAPI-powered REST, WebSocket, and SSE gateway.
- **`db`**: Async SQLite (swappable for PostgreSQL) with $1, $2 placeholders.
- **`event_bus`**: Pub/Sub + Causal Tracing (every event knows its parent).
- **`auth`**: JWT lifecycle and secure hashing.
- **`telemetry`**: Zero-config OpenTelemetry integration.

---

## 🔍 Observability

- **Causal Tracing**: View the tree of events that led to a specific match or message.
- **System Metrics**: Real-time performance tracking of every tool call.
- **OpenAPI**: Fully documented endpoints generated automatically.

---

**Developed by Anibal Fernandez** ([@theanibalos](https://github.com/theanibalos)) to demonstrate the future of AI-assisted engineering.
