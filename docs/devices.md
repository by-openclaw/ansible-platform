# Devices and apps

How to use the platform from your phone, tablet and computer. One sign-in (Authentik, with MFA) opens every service; a few native apps need an *app password*, explained below. `<domain>` is the company domain you were given.

## 1. First step, once: sign in to Nextcloud

Open `https://nextcloud.<domain>` and sign in with the company login. This first sign-in also connects **Mail**: the platform stores your mailbox for you, so Mail, Calendar, Contacts, Talk and Files are ready without any further password. If Mail shows an empty account or refuses actions, sign out and sign in again once.

Where things live:

| Need | Where |
|---|---|
| Company files | Nextcloud → Files → **Company** |
| Chat, calls, screen sharing | Nextcloud → Talk → **General** (and any room you are invited to) |
| Shared calendar | Nextcloud → Calendar → **Company** |
| Company contacts | Nextcloud → Contacts → **Company** (colleagues appear automatically) |
| Meetings with people outside the company | `https://meet.<domain>` |
| Passwords | Bitwarden app pointed at `https://vaultwarden.<domain>` |

## 2. iPhone and iPad

**Mail (push)**: Settings → Mail → Accounts → Add account → **Microsoft Exchange**. Email: your address; server: `mail.<domain>`; user: your address; password: a **mail app password** (section 5). In the account, keep **Mail** on and switch Contacts, Calendars and Reminders **off** for this account (those come from Nextcloud below).

**Calendar, Contacts, Reminders**: in Nextcloud on the phone's browser, open Settings → *Mobile & desktop* and install the **iOS profile**; it adds the CalDAV and CardDAV accounts in one tap (you approve it in Settings → Profile Downloaded). It asks for a Nextcloud app password (section 5).

**Apps**: *Nextcloud Talk*, *Nextcloud* (files), *Nextcloud Notes* from the App Store. Sign in with the server `https://nextcloud.<domain>`; the app opens the browser for the company login, no password to copy. *Jitsi Meet* for external meetings, *Bitwarden* for passwords.

## 3. Samsung and other Android phones

**Mail (push)**: Samsung Email → Add account → **Exchange** (server `mail.<domain>`, user = your address, a mail app password). Keep only Mail synced in that account. Any IMAP client also works (`mail.<domain>`, IMAP 993 SSL, SMTP 587 STARTTLS, same app password).

**Calendar, Contacts, Tasks**: install **DAVx⁵** (Play Store or F-Droid) → Login with URL and user name → `https://nextcloud.<domain>` → it opens the browser for the company login and creates the sync account. Then Samsung Calendar and Contacts show the Nextcloud data; *Tasks.org* shows your tasks.

**Apps**: *Nextcloud Talk*, *Nextcloud*, *Nextcloud Notes*, *Jitsi Meet*, *Bitwarden*, all signed in through the browser login.

## 4. Computer

Everything works in the browser at `https://nextcloud.<domain>` and `https://meet.<domain>`. Optional: the **Nextcloud Desktop** client to sync the Company drive, and the **Nextcloud Talk** desktop app. A classic mail program (Thunderbird, Outlook) uses IMAP 993 SSL and SMTP 587 STARTTLS on `mail.<domain>` with a mail app password.

## 5. App passwords

Your company password stays in Authentik and is never typed into a mail or sync app. Native apps use per-device app passwords that you can revoke one by one:

- **Mail app password** (phones, mail programs): sign in to `https://mail.<domain>` with the company login → *App passwords* → *Add*. Name it after the device.
- **Nextcloud app password** (iOS profile, DAVx⁵ when asked, desktop client): Nextcloud → Settings → *Security* → *Devices & sessions* → *Create new app password*. Apps that open the browser login create theirs automatically.

Lost or replaced a device: revoke its app passwords in the same two places and tell the platform admins by replying to your welcome mail.

## 6. What is not on your phone

Talk calls beyond a handful of people, call recording and whiteboards arrive with the next platform phase. Meetings with external guests are on `https://meet.<domain>`.
