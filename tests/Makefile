TESTS	= test-init \
	  test-init-with-git \
	  test-add \
	  test-add-fails-without-vcs \
	  test-add-non-root \
	  test-config-work-dir \
	  test-refresh-simple \
	  test-refresh-older \
	  test-record-simple \
	  test-build-two-level \
	  test-build-two-level-shared \
	  test-branch \
	  test-merge \
	  test-list

test:
	@status=0;				\
	for test in $(TESTS); do		\
		./$$test || status=1;		\
	done;					\
	exit $$status
