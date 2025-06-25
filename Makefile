.PHONY: all
all:

.PHONY: tidy
tidy:
	black ./

.PHONY: checkstyle
checkstyle:
	ruff check

.PHONY: test
test: checkstyle
