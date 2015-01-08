# -*- Makefile -*-
NAME	= dep
BINDIR	= /usr/local/bin
VERSION	= $(shell git describe --tags 2>/dev/null || echo unknown)

install:
	rm -f $(BINDIR)/$(NAME)
	awk '/%%README%%/ {								\
		while ((getline line < "README.md") > 0 && line !~ /^Copyright/)	\
			printf("# %s\n", line);						\
		next;									\
	}										\
	/%%LICENSE%%/ {									\
		while ((getline line < "LICENSE") > 0)					\
			 printf("# %s\n", line);					\
		next;									\
	}										\
	{ sub(/%%VERSION%%/, "$(VERSION)", $$0); print $$0; }' \
		$(NAME).py > $(BINDIR)/$(NAME)
	chmod a+rx $(BINDIR)/$(NAME)

test:
	$(MAKE) -C tests -w test
