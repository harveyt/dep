TESTS	= $(filter-out %~, $(wildcard test-*))

test:
	@status=0;				\
	for test in $(TESTS); do		\
		./$$test || status=1;		\
	done;					\
	exit $$status
