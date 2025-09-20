# Captain Gang - USTA Team Player Analyzer

This Python script analyzes USTA player pages to find all teams a player captains and extracts all players from those teams to show how many times they've played together.

## Installation

1. Install the required dependencies:
```bash
pip3 install -r requirements.txt
```

## Usage

```bash
python3 captain_gang.py -c <USTA_PLAYER_ID>
```

### Example

To analyze Yufeng Jiang's teams (USTA ID: 297164):
```bash
python3 captain_gang.py -c 297164
```

## What it does

1. **Fetches the player page**: Goes to `https://leagues.ustanorcal.com/playermatches.asp?id=<PLAYER_ID>`
2. **Finds captain teams**: Identifies all teams where the player is listed as "Captain" or "Co-Captain"
3. **Crawls team pages**: For each captain team, visits the team page to get the roster
4. **Extracts players**: Collects all player names from each team roster
5. **Counts appearances**: Shows how many times each player has appeared across all captain teams

## Output

The script outputs:
- Number of captain teams found
- Total player appearances across all teams
- Number of unique players
- A sorted list of players and how many times they've appeared

## Features

- **Rate limiting**: Includes delays between requests to be respectful to the server
- **Error handling**: Gracefully handles network errors and missing pages
- **Flexible parsing**: Uses multiple strategies to find player names in different page formats
- **Clean output**: Provides readable, formatted results

## Requirements

- Python 3.6+
- Internet connection
- Valid USTA Northern California player ID
