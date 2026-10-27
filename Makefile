PREFIX ?= /usr/local
BINDIR ?= $(PREFIX)/bin

.PHONY: install uninstall test

install:
	install -Dm755 roke $(DESTDIR)$(BINDIR)/roke
	ln -sf roke $(DESTDIR)$(BINDIR)/fuzke

uninstall:
	rm -f $(DESTDIR)$(BINDIR)/roke $(DESTDIR)$(BINDIR)/fuzke

test:
	python3 -m unittest discover tests
