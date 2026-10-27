# roke — Specification

## 1. Overview

roke is a rofi-based launcher for KeePass databases. It lets the user open a
KeePass database, fuzzy-search or browse its entries, and then either
auto-type a password into the focused window, copy it to the clipboard, or
read the entry's notes.

It is a single Python script, `roke`.

### 1.1 External dependencies

| Purpose          | Tool                                               |
| ---------------- | -------------------------------------------------- |
| Menu / prompt UI | `rofi` (1.7.5 or later)                            |
| Decryption       | `keepassxc-cli`                                    |
| Runtime          | `python3` with `cryptography` (`python3-cryptography`) |
| Auto-type        | `dotool`; `xdotool` is used when `dotool` is missing |
| Clipboard        | `xclip`                                            |

### 1.2 Installation

`make install` copies the script to `$(PREFIX)/bin/roke` (`PREFIX` defaults to
`/usr/local`; `DESTDIR` is honoured). `make uninstall` removes it and
`make test` runs the unit tests.

## 2. User flow

```
Database selection ──► (Browse) ──► Unlock ──► Entry list ──► Entry actions
                                                  │               ▲
                                                  └► Navigate groups
```

General behaviour of every menu:

- **Escape** goes back one menu. At the database list it exits.
- Typing filters the list, case-insensitively, using fuzzy matching.

### 2.1 Database selection

The first menu lists recently opened databases that still exist, most recent
first. The final item is always **Choose…**, which opens the directory
browser (§2.2).

### 2.2 Directory browser

**Choose…** first shows a list of starting places, in this order:

1. the user's home directory;
2. the XDG user directories Desktop, Documents, Downloads, Music, Pictures and
   Videos, as configured in `~/.config/user-dirs.dirs`;
3. `/`;
4. every directory a database was previously chosen from in this browser.

Only directories that exist are listed, and each appears once.

Selecting a directory lists its contents:

1. KeePass database files (`*.kdbx`, any case);
2. `../`, which moves to the parent directory (absent at `/`);
3. its subdirectories, shown with a trailing `/`.

Each group is sorted by name, and hidden files and directories are not shown.
Selecting a subdirectory lists that subdirectory. Escape returns to the
starting places. Selecting a database records its directory (§2.2, item 4)
and proceeds to unlocking (§2.3).

### 2.3 Unlocking

The user is prompted for the database's master password in a masked rofi
prompt. The database is then decrypted into memory with
`keepassxc-cli export` (§3.1). Key files and hardware keys are not supported.

- **On success:** the database is recorded as recently used (§2.1) and the
  entry list is shown (§2.4).
- **On failure:** the error from `keepassxc-cli` is shown with two options:
  **Try again**, which re-prompts for the password, and **Abort**, which
  exits. Escape also exits.
- **Escape at the password prompt:** returns to the database list.

### 2.4 Entry list

The entry list contains every entry in the database except:

- entries in the recycle bin;
- earlier versions of entries (entry history);
- entries in excluded groups and their subgroups (§2.6).

**Order:**

1. entries that have been used, most recently used first;
2. **Navigate groups**, which opens the group navigator (§2.6);
3. entries that have never been used, sorted by name.

An entry counts as used whenever any of its actions (§2.5) is performed.

**Row format:** the title followed by its group path, e.g.
`Title  ·  Group > Subgroup`. The root group is omitted, so entries directly
in the root show only their title.

**Filtering:** typed input fuzzy-matches against the entry's title, group
path, URL and username.

**Ranking while filtering:** entries whose title matches come first. rofi's
fuzzy sort scores only the displayed text and favours matches near its start,
which is why the title leads the row. Matches in the group path rank below
title matches, and matches only in the URL or username rank last. A weak fuzzy
title match can still rank below a strong group match. Entries with the same
score keep the order above, and with nothing typed the order is unchanged.

### 2.5 Entry actions

Selecting an entry opens an action menu headed by the entry's full path
(`Group > Subgroup > Title`). The options, in order:

1. **Autotype**
2. **Copy password**
3. **View notes**

Each action records the entry's last use (§3.2). After Autotype or Copy
password roke exits; after View notes it returns to the action menu.

#### 2.5.1 Autotype

After a 500 ms start delay, which lets focus return to the target window, the
password is typed with a 25 ms delay between characters. These are KeePassXC's
default Auto-Type delays.

`dotool` is used when installed, otherwise `xdotool`. The typing program is
started before the delay, so that dotool's virtual keyboard is ready, and the
password is sent to it over stdin.

#### 2.5.2 Copy password

The password is copied to the clipboard (the X `CLIPBOARD` selection) with
`xclip`. The clipboard is not cleared afterwards.

#### 2.5.3 View notes

The notes are shown as a rofi list, one row per line, or `(no notes)` when
empty. They are passed to rofi over stdin, so they are never written to disk
(§3.1).

### 2.6 Group navigation and exclusion

**Navigate groups** opens the root group. A group's menu lists, in order:

1. `..`, which goes up one level (from the root, back to the entry list);
2. **Exclude group** or **Include group** (§2.6.1), except at the root;
3. its subgroups, shown as `Name >`;
4. the entries directly in that group, shown by title.

Subgroups and entries appear in database order. The menu's message line shows
the group's path, followed by `(excluded from the entry list)` when the group
or one of its ancestors is excluded. Escape behaves like `..`. Selecting an
entry opens its action menu (§2.5), and Escape there returns to the group.

#### 2.6.1 Excluding groups

**Exclude group** hides the group's entries, and those of all its subgroups,
from the entry list (§2.4). They remain reachable through Navigate groups.
For an excluded group the option reads **Include group**, which removes the
exclusion.

A subgroup of an excluded group is hidden through its parent but is not
itself excluded, so its menu offers **Exclude group**. Exclusions apply per
database and survive master password changes (§3.2).

## 3. Security and persistence

### 3.1 Handling secrets

- The database is decrypted only into memory, by reading the XML that
  `keepassxc-cli export` writes to stdout.
- The master password, entry passwords and notes are passed between programs
  only over stdin and stdout pipes. They never appear on a command line, where
  other processes could read them, and are never written to disk.
- **Notes:** no temporary file is created to display them.
- Every file roke creates is private to the user (umask `077`: files `0600`,
  directories `0700`), and is written atomically.

### 3.2 Persisted state

All state lives in `~/.config/roke/` (`$XDG_CONFIG_HOME/roke/`):

| File                   | Contents                                    | Protection |
| ---------------------- | ------------------------------------------- | ---------- |
| `recent-databases`     | database paths, newest first, at most 30     | plain text |
| `recent-directories`   | directories, newest first, at most 30        | plain text |
| `excluded-groups`      | one hash per excluded group                  | salted hash |
| `salt`                 | 32 random bytes, hex                         | plain text |
| `cache/<id>`           | entry last-use times for one database        | encrypted  |

**Excluded groups:** each line is
`HMAC-SHA256(salt, JSON [absolute database path, group name, …])` in hex. Group
names are never stored, and the file does not depend on the master password,
so it survives password changes. A group is identified by its path, so
renaming or moving the group or the database file drops its exclusion. The
salt is stored next to the hashes, so the hashes defeat precomputed tables
but not someone with access to both files who guesses a group's name.

**Entry last-use times:** `<id>` is the SHA-256 of the database's absolute
path. The file holds a JSON object with a random salt, a nonce and the
ciphertext of a map from entry UUID to Unix time. The key is
`scrypt(master password, salt, N=2^15, r=8, p=1)` and the cipher is
AES-256-GCM. Stored in the clear, this data would reveal which accounts exist
and are in use, and would amount to a usage log.

**Master password change:** if the database unlocks but its last-use file
cannot be decrypted with that password, the master password has changed. The
file is discarded and a new one is started.
