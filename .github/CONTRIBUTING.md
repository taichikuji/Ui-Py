# Contributing to Ui-Py

Thank you for your interest in contributing to Ui-Py! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

Please be respectful and considerate of others when contributing to this project. We aim to foster an inclusive and welcoming community.

## How to Contribute

### Reporting Bugs

If you've found a bug in Ui-Py, please create an issue using the bug report template. To ensure we can address your bug quickly, please:

1. Check if the bug has already been reported
2. Use the Bug Report template when creating a new issue on GitHub
3. Include as much detail as possible, including steps to reproduce, expected behavior, and your environment

### Suggesting Features

Have an idea for a new feature or improvement? We'd love to hear it! Please:

1. Check if the feature has already been suggested
2. Use the Feature Request template when creating a new issue on GitHub
3. Clearly describe the problem your feature would solve and how it should work

### Pull Requests

We welcome pull requests! Here's how to submit one:

1. Fork the repository
2. Create a new branch from `main`
3. Make your changes
4. Test your changes thoroughly
5. Submit a pull request (the PR template will load automatically)

## Development Setup

To set up the project for local development:

1. Clone your fork of the repository
2. Install dependencies with pipenv:
   ```bash
   pipenv install --dev
   ```
3. Create a Discord bot through the [Discord Developer Portal](https://discord.com/developers/applications)
4. Set your bot token as an environment variable:
   ```bash
   export TOKEN='YOUR_DISCORD_BOT_TOKEN'
   ```
5. Run the bot in development mode:
   ```bash
   pipenv run python main.py
   ```

## Project Structure

Ui-Py follows a modular architecture:

- `main.py`: Core bot initialization and setup
- `functions/`: Contains all bot extensions
  - `system/`: System and administrative commands
  - `tool/`: User-oriented features and utilities
- `.github/`: GitHub templates and configuration
- `media/`: Assets and resources

## Adding New Features

To add a new feature:

1. Decide if it's a system feature or a tool
2. Create a new Python file in the appropriate directory:
   - System commands go in `functions/system/`
   - User tools go in `functions/tool/`
3. Follow the existing module pattern with a main cog class and a setup function
4. Use Discord.py's command and event decorators for functionality
5. Test your feature thoroughly before submitting a PR

## Code Style Guidelines

Please follow these guidelines for your code contributions:

- Follow PEP 8 standards
- Use meaningful variable and function names
- Add appropriate docstrings and comments
- Maintain consistent naming conventions with the existing codebase
- Use type hints where appropriate

## Testing

Before submitting your changes, please test them thoroughly. Ensure:

1. Your feature works as expected
2. Your change doesn't break existing functionality
3. Your code doesn't generate new warnings or errors

## Documentation

If you're adding new features or changing existing ones, please update the documentation accordingly. This includes:

- Docstrings in the code
- Comments explaining complex logic
- Updating the PROJECT_GUIDE.md if necessary

## Questions?

If you have any questions about contributing, please open an issue with your question or reach out to the project maintainers.

Thank you for contributing to Ui-Py!