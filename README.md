# HitaKort Bot

HitaKort is a Telegram bot that generates heatmaps based on user inputs. The
name "HitaKort" comes from Old Norse, where "Hita" means "heat" and "Kort" means
"map".

## Features

- Create customizable grid-based heatmaps
- Set custom grid sizes
- Add hits to the grid
- Generate visual heatmap images
- Reset heatmaps

## Installation

```sh
git clone https://github.com/Nachtalb/hitakort.git
cd hitakort
poetry install
```

## Usage

To start the bot, use the following command:

```sh
hitakort --token YOUR_BOT_TOKEN [options]
```

### Command-line Options

- `--token`: Your Telegram Bot API token (required)
- `--base-url`: Base URL for the bot API (default: Telegram's official API URL)
- `--local-mode`: Run the bot in local mode
- `--admins`: List of admin IDs, separated by commas
- `--lock`: Lock the bot to the configured admins

#### Webhook Mode

To run the bot in webhook mode, add the `webhook` subcommand and the following
options:

```sh
hitakort --token YOUR_BOT_TOKEN webhook --webhook-url YOUR_WEBHOOK_URL [options]
```

- `--webhook-url`: URL for the webhook (required in webhook mode)
- `--webhook-path`: Custom webhook path
- `--listen`: IP address to listen on (default: 0.0.0.0)
- `--port`: Port to listen on (default: 8433)

## Bot Commands

- `/start`: Start the bot and receive a welcome message
- `/size <num>`: Set the grid size (e.g., `/size 6` for a 6x6 grid)
- `/image`: Generate and receive the current heatmap image
- `/reset`: Reset the heatmap and grid size

## Adding Hits

To add a hit to the grid, simply send a message in the format `ROW COLUMN`,
where `ROW` is a letter and `COLUMN` is a number (e.g., A1, B2, C3).

## License

This project is licensed under the LGPL-3.0 License. See the LICENSE file for
details.
