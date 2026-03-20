# Contributing

This is a small project, so there's not much ceremony here.

## Getting started

1. Fork the repo and clone your fork.
2. Set up a virtual environment and install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Windows: .\venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Copy `local_config.example.json` to `local_config.json` and fill in your IGDB credentials.
4. Run `python3 GameInfo.py` (or `python GameInfo.py` on Windows) to make sure everything works.

## Making changes

- Branch off `main`.
- Try to keep pull requests focused on one thing.
- If you're touching platform-specific behavior, check that it works on macOS, Windows, and Linux. See `reveal_in_file_manager()` in `utils.py` for how OS differences are handled.
- Test on at least one platform before submitting. If you only have access to one OS, say so in the PR description so others can help verify.

## Code style

No linter or formatter configured. Match the existing code: readable and simple.

## Reporting bugs

Open an issue with steps to reproduce, your OS, and Python version. Screenshots help if the bug is visual.

## Pull requests

- Describe what changed and why.
- Include a screenshot if the change is visual.
- Link related issues if any exist.
