.PHONY: install run demo loop register

install:
	pip install -e .

run:
	uvicorn api.server:app --port 8000 --reload

demo:
	python main.py demo https://stripe.com --task "Write a launch tweet"

loop:
	python -m agenthansa.loop

register:
	python -m agenthansa.register
