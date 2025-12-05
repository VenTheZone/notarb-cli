# NotArb CLI Monitor

[![PyPI version](https://badge.fury.io/py/notarb-cli.svg)](https://pypi.org/project/notarb-cli/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

A terminal-based monitoring dashboard for NotArb MEV bots. Displays real-time profit tracking, fees analysis, and log monitoring.

![Screenshot](screenshot.png)

## Features

- Real-time profit/loss tracking with detailed statistics
- Fee breakdown analysis (Jito tips, transaction fees)
- Live log monitoring (bot and Jupiter server logs)
- Interactive terminal dashboard with keyboard navigation
- Process monitoring and system status

## Requirements

- Python 3.8 or higher
- Running NotArb bot with log files in `logs/` directory
- `logs/notarb.log` and `logs/jupiter.log` files present

## Installation

### Option 1: Install from source (recommended)

```bash
# Clone or download the package
cd notarb-cli

# Install dependencies
pip install rich psutil

# Install the package in development mode
pip install -e .
```

### Option 2: Using conda (on Arch Linux)

```bash
# Create and activate conda environment
conda create -n notarb-cli python=3.10
conda activate notarb-cli

# Install dependencies
conda install rich psutil

# Install the package
pip install -e .
```

## Usage

1. Ensure your NotArb bot is running and generating logs in the `logs/` directory
2. Run the CLI monitor:
   ```bash
   notarb-cli
   ```
3. Use keyboard shortcuts to navigate:
   - `L` - View logs
   - `P` - Profit report
   - `F` - Fees report
   - `B` - Toggle bot (if applicable)
   - `Q` - Quit

## Configuration

The CLI expects the following directory structure:
```
your-bot-directory/
├── logs/
│   ├── notarb.log      # Bot log file
│   ├── jupiter.log     # Jupiter server log file
│   └── profits.json    # Profit tracking data (auto-generated)
└── [run notarb-cli from here]
```

## Example Configurations

Example configuration files are provided in the `examples/` directory:
- `examples/bot-config.toml` - Sample bot configuration
- `examples/jupiter-config.toml` - Sample Jupiter server configuration
- `examples/example_config.txt` - Additional configuration examples

Copy and modify these files according to your setup.

## Log Format Requirements

The CLI parses profit information from log lines. For accurate tracking, ensure your bot logs profit information in formats like:

```
Profit: 0.001 SOL
Arbitrage executed. Net: 0.005 SOL
```

## Dependencies

- `rich` - Terminal UI library
- `psutil` - System and process monitoring

## License

MIT License

## Troubleshooting

### No logs displayed
- Ensure `logs/notarb.log` and `logs/jupiter.log` exist
- Check file permissions
- Verify bot is running and writing to log files

### Profit parsing not working
- Check log format matches expected patterns
- Verify profit amounts are logged as "Profit: X.XXX SOL"

### Permission errors
- Run with appropriate user permissions
- Ensure log files are readable

## Development

To contribute or modify:
```bash
# Install in development mode
pip install -e .

# Run tests (if available)
python -m pytest

# Run the CLI
notarb-cli