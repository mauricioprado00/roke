# roke

A rofi front-end for KeePass databases: pick a database, unlock it, fuzzy-find
an entry, then auto-type or copy its password, or read its notes.
The full behaviour is in [specs.md](specs.md).

## Requirements

- `rofi`
- `keepassxc-cli`, which decrypts the database into memory
- `python3` with `cryptography` (`apt install python3-cryptography`)
- `dotool` for auto-type; `xdotool` is used when `dotool` is missing
- `xclip` for copying

## Usage

Run `roke`, typically from a window-manager key binding. Escape goes back one
menu; at the database list it exits.

State lives in `~/.config/roke/`: the recent databases and directories in
plain text, and each database's entry last-use times in `cache/`, encrypted
with that database's master password.

## Tests

```sh
python3 -m unittest discover tests
```
