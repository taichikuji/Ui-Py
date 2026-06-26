# Sakamoto Context

Sakamoto is a voice-first Discord community bot for small-to-medium servers. This glossary defines the canonical language for voice sessions, moderation actions, and optional integrations.

## Language

### Voice Experience

**Generator Channel**:
A designated voice channel that triggers creation of a member-owned **Temporary Lobby** when joined.
_Avoid_: Lobby creator, spawn channel, auto-room

**Temporary Lobby**:
A short-lived voice channel created for one member and deleted automatically when empty.
_Avoid_: Private room, permanent room, session room

**Lobby Owner**:
The member who triggered a **Temporary Lobby** and receives management controls for that lobby.
_Avoid_: Host, admin, operator

**Playback Session**:
The active music state for one guild, including connection, current track, and pending **Queue Entries**.
_Avoid_: Player instance, stream job

**Queue Entry**:
A single requested track waiting in a guild's **Playback Session**.
_Avoid_: Playlist item, ticket

### Moderation and Safety

**Voice Votekick**:
A time-bounded vote by voice-channel participants to remove one member from the current voice channel.
_Avoid_: Ban vote, timeout vote

**Temporary Rejoin Ban**:
A short-lived channel permission block applied after a successful **Voice Votekick**.
_Avoid_: Permanent ban, mute

**Server Moderator**:
A server member with elevated Discord permissions used to configure and safeguard bot behavior.
_Avoid_: Owner (unless literally the server owner), staff (too broad)

### Integrations and Operations

**Steam Link**:
The persisted mapping between a Discord user and their SteamID64.
_Avoid_: Steam account cache, Steam token

**Pipenv Environment**:
The canonical Python dependency and execution environment for this repository.
_Avoid_: Global pip installs, ad-hoc virtualenv workflows

**Optional Integration**:
A feature module that may be unavailable without making the bot's core voice experience unhealthy.
_Avoid_: Required module, core dependency

**Degraded Capability**:
A non-core feature that is unavailable while core slash-command and voice workflows remain operational.
_Avoid_: Outage, crash

## Relationships

- One **Generator Channel** in a guild can create many **Temporary Lobbies** over time.
- One **Temporary Lobby** has exactly one initial **Lobby Owner**.
- One guild has zero or one active **Playback Session** at any moment.
- One **Playback Session** contains zero or more **Queue Entries**.
- One user has zero or one **Steam Link**.
- Python dependency installation and command execution run through the **Pipenv Environment** (`pipenv sync`, `pipenv run ...`).
- A successful **Voice Votekick** creates one **Temporary Rejoin Ban** for one target member in one channel.
- An **Optional Integration** can be unavailable while the core bot remains in **Degraded Capability** rather than outage.

## Example Dialogue

> **Dev:** "If a member joins the Generator Channel, do we move everyone into the same lobby?"
> **Domain expert:** "No, each join event creates a separate Temporary Lobby with its own Lobby Owner."
>
> **Dev:** "If Steam is not configured, is that a service outage?"
> **Domain expert:** "No, Steam is an Optional Integration, so core voice features stay healthy and only that capability is degraded."

## Flagged Ambiguities

- "Lobby" was used for both the trigger channel and the generated channel; resolved as **Generator Channel** vs **Temporary Lobby**.
- "Kick" was used to mean either Discord server kick or voice-only removal; resolved as **Voice Votekick** for the voice-only action.
- "Broken bot" was used when optional features failed; resolved as **Degraded Capability** unless core voice flows are affected.
