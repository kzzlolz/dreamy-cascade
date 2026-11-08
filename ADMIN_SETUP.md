# Dreamy Cascade admin panel setup

The private owner dashboard is served by the existing Flask service, so the public GitHub Pages site never receives Discord OAuth secrets.

## 1. Create a Discord OAuth application

1. Open the Discord Developer Portal and create an application for Dreamy Cascade.
2. Open **OAuth2** and copy the **Client ID** and **Client Secret**.
3. Add this exact Redirect URL:

   `https://serverwidget.onrender.com/auth/discord/callback`

4. The dashboard only requests the `identify` scope. Do not add a bot token here.

## 2. Configure the existing Render web service

Add these environment variables to the existing `serverwidget` service:

| Variable | Value |
|---|---|
| `DISCORD_CLIENT_ID` | OAuth application Client ID |
| `DISCORD_CLIENT_SECRET` | OAuth application Client Secret |
| `FLASK_SESSION_SECRET` | A long random secret (at least 32 random bytes) |
| `DISCORD_REDIRECT_URI` | `https://serverwidget.onrender.com/auth/discord/callback` |
| `PROFILE_DB_PATH` | `/var/data/dreamy-cascade-profiles.sqlite3` |

Keep the Client Secret and Flask session secret in Render environment variables only. Never put them in GitHub, the webpage, or Discord messages.

## 3. Enable persistent profile storage

The profile database is SQLite at `/var/data/dreamy-cascade-profiles.sqlite3`. Attach a persistent disk to the Render service with mount path:

`/var/data`

Without a persistent disk, the service's local filesystem may be cleared during a restart or redeploy, and saved profiles could be lost.

## 4. Deploy and sign in

Deploy the `admin-profile-system` branch (or merge its pull request into `main` and let Render deploy the updated backend).

Open:

`https://serverwidget.onrender.com/admin`

Sign in with one of the two owner Discord accounts allowlisted in `admin_panel.py`. Other Discord accounts are denied.

## What this first version does

- Lets an authorised owner select a current human member from the live Discord member API.
- Creates, edits, previews, and deletes profile records.
- Stores a display-name override, short introduction, biography, interests, optional avatar URL, and up to eight social links.
- Protects write actions with the owner session and a CSRF token.

This first milestone is the private editor and storage API. The public member-profile popup and member self-editing Discord commands are separate follow-up stages.
