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

release:
	@version=$(VERSION);					\
	if [[ "$$(git status --porcelain)" != "" ]]; then	\
		echo "Commit all changes first!" >&2;		\
		exit 1;						\
	fi;							\
	if [[ "$$version" == "" ]]; then			\
		echo "Set VERSION variable!" >&2;		\
		exit 1;						\
	fi;							\
	echo "Releasing version $$version";			\
	git tag $$version;					\
	make install;						\
	git push;						\
	git push --tags




