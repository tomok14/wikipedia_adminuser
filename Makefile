lint:
	pylint admin.py | tee lintlog
	ruff check admin.py | tee rufflog

honban:
	python admin.py

test:
	python admin.py -t

