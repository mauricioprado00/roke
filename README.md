# roke

A rofi front-end for KeePass databases: pick a database, unlock it, fuzzy-find
an entry, then auto-type or copy its password, or read its notes.
The full behaviour is in [specs.md](specs.md).

## Requirements

- `rofi`, or `fzf` for the terminal version
- `keepassxc-cli`, which decrypts the database into memory
- `python3` with `cryptography` (`apt install python3-cryptography`)
- `dotool` for auto-type; `xdotool` is used when `dotool` is missing
- `xclip` for copying

## Install

```sh
sudo make install                 # /usr/local/bin/roke and fuzke
make install PREFIX=~/.local      # ~/.local/bin/roke and fuzke, no sudo
```

`make uninstall` (with the same `PREFIX`) removes them.

## Usage

Run `roke`, typically from a window-manager key binding. Escape goes back one
menu; at the database list it exits. `roke path/to/file.kdbx` opens that
database straight away and adds it to the recent databases.

`fuzke` (or `roke --cli`) is the terminal version: coloured fzf menus, and
autotype asks how many seconds to wait, with a countdown. `roke --default cli`
makes plain `roke` use it whenever started from a terminal; key bindings keep
using rofi. `roke --default rofi` undoes that.

After unlocking, recently used entries come first, then **Navigate groups**,
which browses the group tree and can exclude a group from the entry list,
then the remaining entries.

State lives in `~/.config/roke/`: settings in `config`, the recent databases and directories in
plain text, excluded groups as salted hashes, and each database's entry
last-use times in `cache/`, encrypted with that database's master password.
See [specs.md](specs.md) §3.2.

## Tests

```sh
make test
```
