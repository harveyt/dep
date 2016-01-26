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
	$(MAKE) release-create
	$(MAKE) release-publish

release-create:
	@version=$(VERSION);					\
	if [[ "$$(git status --porcelain)" != "" ]]; then	\
		git status;					\
		echo "\nerror: Commit all changes first!" >&2;	\
		exit 1;						\
	fi;							\
	if [[ "$$version" == "" ]]; then			\
		git tag --column;				\
		echo "\nerror: Set VERSION variable!" >&2;	\
		exit 1;						\
	fi;							\
	echo "Releasing version $$version"
	git tag $$version
	make install

release-publish:
	git push
	git push --tags




