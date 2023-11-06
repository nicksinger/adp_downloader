.PHONY: all
all:

.PHONY: tidy
tidy:
	black ./

.PHONY: flake8
flake8:
	flake8 $$(git ls-files "*.py" 2>/dev/null ||find . -maxdepth 1 -name "*.py")

.PHONY: checkstyle
checkstyle: flake8

.PHONY: test
test: checkstyle
