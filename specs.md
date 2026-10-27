# roke — Specification

## 1. Overview

roke is a rofi-based launcher for KeePass databases. It lets the user open a
KeePass database, fuzzy-search its entries, and then either auto-type a
password into the focused window or copy it to the clipboard.

### 1.1 External dependencies

| Purpose          | Tool     |
| ---------------- | -------- |
| Menu / prompt UI | `rofi`   |
| Auto-type        | `dotool` |
| Clipboard        | `xclip`  |

## 2. User flow

```
Database selection ──► (Browse) ──► Unlock ──► Entry list ──► Entry actions
```

### 2.1 Database selection

The first menu lists recently opened databases.

- Items are sorted by last use, most recent first.
- The final item is always **Choose…**, which opens the directory browser
  (§2.2).

### 2.2 Directory browser

Selecting **Choose…** shows a list of starting locations:

- the common places a file manager such as Dolphin offers: the user's home
  directory, `~/Documents`, `~/Downloads` and similar standard user
  directories (only those that exist);
- every directory the user has previously chosen in this browser.

When a directory is selected, its contents are listed as follows:

1. KeePass database files in that directory, if any, at the top.
2. Its subdirectories, below them.

Selecting a subdirectory repeats this listing for that subdirectory. Selecting
a database file proceeds to unlocking (§2.3).

### 2.3 Unlocking

After a database is selected, the user is prompted for its master password.

- **On success:** the database is recorded as recently used (§2.1) and the
  entry list is shown (§2.4).
- **On failure:** the user is asked whether to **Try again** (re-prompt for
  the password) or **Abort**.

### 2.4 Entry list

Once the database is open, all entries are listed.

- **Ordering:** by last use, most recent first. An entry counts as used
  whenever any of its actions (§2.5) is performed.
- **Display format:** the full group path followed by the title, e.g.
  `Group > Subgroup > Subgroup > Title`.
- **Filtering:** typed input fuzzy-matches against the entry's **title**,
  **URL** and **username**.

### 2.5 Entry actions

Selecting an entry opens an action menu with the following options, in this
order:

1. **Autotype**
2. **Copy password**
3. **View notes**

Performing any of these actions updates the entry's last-use time (§2.4, §3.2).

#### 2.5.1 Autotype

After a short delay (to let focus return to the target window), the password
is typed with `dotool`.

- **Timing:** the start delay and inter-character delay match KeePass's
  defaults.
- **Fallback:** where KeePass has no equivalent setting, use the timing of the
  user's existing `timestamp-type` script: a 50 ms inter-character delay.

#### 2.5.2 Copy password

The entry's password is copied to the clipboard with `xclip`. The clipboard is
not cleared afterwards.

#### 2.5.3 View notes

The entry's notes are displayed to the user, subject to the security
requirements in §3.1.

## 3. Security and persistence

### 3.1 Displaying notes

- **Preferred:** notes are displayed without ever being written to disk, not
  even to a temporary file.
- **Fallback:** if a temporary file is unavoidable, it must:
  - have permissions `0700`;
  - be short-lived, deleted as soon as it is no longer needed.
- **Disclosure:** if the implementation cannot avoid creating a temporary
  file, this must be raised with the project owner before it is adopted.

### 3.2 Persisted state

| Data                          | Storage                                         |
| ----------------------------- | ----------------------------------------------- |
| Recently opened databases     | Plain text                                      |
| Previously chosen directories | Plain text                                      |
| Entry last-use times          | Encrypted, per database (see below)             |

Entry last-use data must be encrypted with the master password used to unlock
the corresponding database. Stored in the clear, it would reveal which
accounts exist and are in use, and would amount to a usage log.

- **Location:** one file per database under `~/.config/roke/cache/`, separate
  from the database itself. roke never writes to the `.kdbx` file.
- **Master password change:** if the database unlocks but its last-use file
  cannot be decrypted with that password, the master password has changed.
  The file is discarded and a new one is started.
