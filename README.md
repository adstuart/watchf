# watchf — Send a message to Adam

A simple static webpage that lets anyone send a push notification to Adam's phone via [ntfy.sh](https://ntfy.sh). It provides a clean form where you can type a message and click **"Send to Adam"** — the message is delivered as an instant push notification.

Notifications are powered by [ntfy.sh](https://ntfy.sh), a free and open-source pub/sub push notification service. No accounts or API keys are required for public topics.

## How to use it

1. Open the page (see **Hosting on GitHub Pages** below if you need to set it up).
2. Type your message in the text box.
3. Click **Send to Adam**.

The message will appear as a push notification on Adam's phone within seconds.

> **Tip:** You can also press **Ctrl+Enter** (or **⌘+Enter** on macOS) to send.

## How ntfy.sh works

- The page sends a plain-text HTTP `POST` request to `https://ntfy.sh/<topic>`.
- To receive notifications, install the **ntfy** app on your phone:
  - [Android (Google Play)](https://play.google.com/store/apps/details?id=io.heckel.ntfy)
  - [Android (F-Droid)](https://f-droid.org/en/packages/io.heckel.ntfy/)
  - [iOS (App Store)](https://apps.apple.com/us/app/ntfy/id1625396347)
- In the app, subscribe to the topic used on this page (default: `adam-notify`).

## Hosting on GitHub Pages

1. Push this repository to GitHub.
2. Go to **Settings → Pages** and set the source to the root of your default branch.
3. GitHub Pages will serve `index.html` at `https://<username>.github.io/<repo>/`.

## File structure

```
/
├── index.html   # The webpage
└── README.md    # This file
```
