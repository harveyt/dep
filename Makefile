# -*- Makefile -*-
BINDIR	= /usr/local/bin
LIBDIR	= /usr/local/lib
MODS	= $(wildcard dep/*.py dep/cmd/*.py)
FILES	= dep.py $(MODS)

install:
	rm -f $(BINDIR)/dep
	rm -rf $(LIBDIR)/dep
	./install_files $(BINDIR) $(LIBDIR) $(FILES)
	chmod a+rx $(BINDIR)/dep
	python -m compileall $(patsubst %,$(LIBDIR)/%,$(MODS))

test:
	$(MAKE) -C tests -w test
