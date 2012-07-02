prefix=/usr/local
LIBEXECDIR=$(prefix)/libexec
DESTDIR=

INSTALL=/usr/bin/install -c
LN=/bin/ln
RM=/bin/rm

FAST_EXPORT=fast-export/hg-fast-export.sh fast-export/hg-fast-export.py fast-export/hg2git.py

all: $(FAST_EXPORT)

$(FAST_EXPORT):
	git submodule update --init

install: $(FAST_EXPORT)
	$(INSTALL) -d $(DESTDIR)$(LIBEXECDIR)/yagh
	$(INSTALL) -m 755 src/again.py $(DESTDIR)$(LIBEXECDIR)/yagh/
	$(INSTALL) -m 755 src/fast-export.sh $(DESTDIR)$(LIBEXECDIR)/yagh/
	$(INSTALL) -m 755 src/remote-hg.py $(DESTDIR)$(LIBEXECDIR)/yagh/
	$(INSTALL) -m 755 fast-export/hg-fast-export.sh $(DESTDIR)$(LIBEXECDIR)/yagh/
	$(INSTALL) -m 755 fast-export/hg-fast-export.py $(DESTDIR)$(LIBEXECDIR)/yagh/
	$(INSTALL) -m 755 fast-export/hg2git.py $(DESTDIR)$(LIBEXECDIR)/yagh/

install-git-hg: install
	$(INSTALL) -d $(DESTDIR)$(LIBEXECDIR)/git-core
	$(RM) -f $(DESTDIR)$(LIBEXECDIR)/git-core/git-hg
	$(RM) -f $(DESTDIR)$(LIBEXECDIR)/git-core/git-remote-hg
	$(LN) -s $(LIBEXECDIR)/yagh/fast-export.sh $(DESTDIR)$(LIBEXECDIR)/git-core/git-hg

install-git-hg-again: install
	$(INSTALL) -d $(DESTDIR)$(LIBEXECDIR)/git-core
	$(RM) -f $(DESTDIR)$(LIBEXECDIR)/git-core/git-hg
	$(RM) -f $(DESTDIR)$(LIBEXECDIR)/git-core/git-remote-hg
	$(LN) -s $(LIBEXECDIR)/yagh/again.py $(DESTDIR)$(LIBEXECDIR)/git-core/git-hg

install-git-remote-hg: install
	$(INSTALL) -d $(DESTDIR)$(LIBEXECDIR)/git-core
	$(RM) -f $(DESTDIR)$(LIBEXECDIR)/git-core/git-hg
	$(RM) -f $(DESTDIR)$(LIBEXECDIR)/git-core/git-remote-hg
	$(LN) -s $(LIBEXECDIR)/yagh/remote-hg.py $(DESTDIR)$(LIBEXECDIR)/git-core/git-remote-hg

uninstall:
	$(RM) -f $(DESTDIR)$(LIBEXECDIR)/git-core/git-hg
	$(RM) -f $(DESTDIR)$(LIBEXECDIR)/git-core/git-remote-hg
	$(RM) -rf $(DESTDIR)$(LIBEXECDIR)/yagh

