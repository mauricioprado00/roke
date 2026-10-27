PREFIX ?= /usr/local
BINDIR ?= $(PREFIX)/bin

.PHONY: install uninstall test

install:
	install -Dm755 roke $(DESTDIR)$(BINDIR)/roke

uninstall:
	rm -f $(DESTDIR)$(BINDIR)/roke

test:
	python3 -m unittest discover tests
