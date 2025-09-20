#!/usr/bin/env python3
"""
Captain Gang - USTA Team Player Analyzer

This script analyzes USTA player pages to find all teams a player captains
and extracts all players from those teams to show how many times they've
played together.
"""

import argparse
import requests
from bs4 import BeautifulSoup
import re
from collections import defaultdict
import sys
from urllib.parse import urljoin, urlparse
import time


class USTACaptainAnalyzer:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.player_counts = defaultdict(int)
        self.base_url = "https://leagues.ustanorcal.com"
        
    def get_page(self, url):
        """Fetch a web page with error handling and rate limiting"""
        try:
            print(f"Fetching: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            time.sleep(1)  # Rate limiting
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def parse_player_page(self, player_id):
        """Parse the main player page to find captain teams and player name"""
        url = f"{self.base_url}/playermatches.asp?id={player_id}"
        html = self.get_page(url)
        if not html:
            return [], None
        
        soup = BeautifulSoup(html, 'html.parser')
        captain_teams = []
        player_name = None
        
        # Extract player name from the page header
        # Look for the player name in the main heading
        name_elements = soup.find_all(['h1', 'h2', 'h3', 'b'])
        for element in name_elements:
            text = element.get_text(strip=True)
            # Look for patterns that suggest this is the player name
            if text and len(text) > 3 and not any(keyword in text.lower() for keyword in ['usta', 'northern', 'california', 'leagues', 'matches']):
                # Check if it looks like a name (contains letters and possibly commas)
                if re.match(r'^[A-Za-z\s,\.]+$', text) and len(text.split()) >= 2:
                    player_name = text
                    break
        
        # If we didn't find a name in headings, look in the first table or other elements
        if not player_name:
            # Look for the player name in the first table or main content area
            tables = soup.find_all('table')
            if tables:
                first_table = tables[0]
                cells = first_table.find_all(['td', 'th'])
                for cell in cells:
                    text = cell.get_text(strip=True)
                    if text and len(text) > 3 and re.match(r'^[A-Za-z\s,\.]+$', text) and len(text.split()) >= 2:
                        if not any(keyword in text.lower() for keyword in ['usta', 'northern', 'california', 'leagues', 'matches', 'rating', 'expiration']):
                            player_name = text
                            break
        
        # Look for team links where the player is a captain
        # The pattern shows "Captain" or "Co-Captain" in the team name
        team_links = soup.find_all('a', href=re.compile(r'teaminfo\.asp\?id=\d+'))
        
        for link in team_links:
            team_text = link.get_text(strip=True)
            if 'Captain' in team_text:
                # Extract team ID from href
                href = link.get('href')
                team_id_match = re.search(r'id=(\d+)', href)
                if team_id_match:
                    team_id = team_id_match.group(1)
                    captain_teams.append({
                        'id': team_id,
                        'name': team_text,
                        'url': urljoin(self.base_url, href)
                    })
                    print(f"Found captain team: {team_text} (ID: {team_id})")
        
        return captain_teams, player_name
    
    def parse_team_page(self, team_info):
        """Parse a team page to extract all players"""
        html = self.get_page(team_info['url'])
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        players = []
        seen_players = set()  # Track unique players to avoid duplicates
        
        # Look for player links in the team roster
        # Players are typically in a table with links to their profiles
        player_links = soup.find_all('a', href=re.compile(r'playermatches\.asp\?id=\d+'))
        
        for link in player_links:
            player_text = link.get_text(strip=True)
            if player_text and len(player_text) > 2:  # Filter out empty or very short text
                # Extract player ID
                href = link.get('href')
                player_id_match = re.search(r'id=(\d+)', href)
                if player_id_match:
                    player_id = player_id_match.group(1)
                    # Create a unique key for this player in this team
                    player_key = f"{player_id}_{player_text}"
                    if player_key not in seen_players:
                        seen_players.add(player_key)
                        players.append({
                            'id': player_id,
                            'name': player_text,
                            'team': team_info['name']
                        })
        
        # Also look for players in table rows that might not have direct links
        # This handles cases where player names are displayed differently
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                for cell in cells:
                    # Look for text that might be player names
                    text = cell.get_text(strip=True)
                    if text and self.looks_like_player_name(text):
                        # Check if this text is already captured as a link
                        if not any(p['name'] == text for p in players):
                            player_key = f"unknown_{text}"
                            if player_key not in seen_players:
                                seen_players.add(player_key)
                                players.append({
                                    'id': 'unknown',
                                    'name': text,
                                    'team': team_info['name']
                                })
        
        print(f"Found {len(players)} players in team: {team_info['name']}")
        return players
    
    def looks_like_player_name(self, text):
        """Heuristic to determine if text looks like a player name"""
        # Skip if it's too short or contains certain keywords
        if len(text) < 3:
            return False
        
        skip_keywords = [
            'Captain', 'Co-Captain', 'Team', 'League', 'Division', 'Win', 'Loss', 'Rating',
            'City', 'Gender', 'Matches', 'Player', 'Status', 'Outcome', 'Round', 'Home',
            'Away', 'Confirmed', 'Scheduled', 'Defaults', 'Singles', 'Doubles', 'Eligibility',
            'Expiration', 'Local', 'Sectional', 'National', 'PlayOff', 'Registration',
            'Closed', 'Currently', 'playing', 'If', 'a', 'problem', 'exists', 'Red',
            'Rostered', 'Individual', 'Won', 'Scheduled', 'Day', 'Match', 'date', 'time',
            'Standings', 'Rules', 'Newsletters', 'Availability', 'Coordinator', 'Print',
            'Blank', 'Score', 'Card', 'Mountain', 'View', 'San', 'Jose', 'Santa', 'Clara',
            'Sunnyvale', 'Fremont', 'Palo', 'Alto', 'Cupertino', 'San', 'Mateo', 'Antioch',
            'San', 'Francisco', 'Campbell', 'Los', 'Gatos', 'Milpitas', 'Portola', 'Valley',
            'Stanford', 'South', 'San', 'Francisco', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri',
            'Sat', 'Sun'
        ]
        
        # Check if any skip keyword is in the text
        if any(keyword.lower() in text.lower() for keyword in skip_keywords):
            return False
        
        # Skip if it's all uppercase (likely headers or labels)
        if text.isupper() and len(text) > 3:
            return False
        
        # Skip if it contains numbers only or special characters
        if re.match(r'^[\d\s\-_]+$', text):
            return False
        
        # Look for patterns that suggest player names
        # Names typically have letters and might have commas, periods, or spaces
        # Should have at least one letter and look like a name
        if re.match(r'^[A-Za-z\s,\.]+$', text) and len(text.split()) >= 1:
            # Additional check: should not be just common words
            common_words = ['the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by']
            if text.lower() not in common_words:
                return True
        
        return False
    
    def analyze_captain(self, player_id):
        """Main analysis function"""
        print(f"Analyzing captain with ID: {player_id}")
        
        # Get all teams this player captains and the player name
        captain_teams, player_name = self.parse_player_page(player_id)
        
        if not captain_teams:
            print("No captain teams found!")
            return
        
        print(f"Found {len(captain_teams)} captain teams")
        
        # For each team, get all players
        all_players = []
        for team in captain_teams:
            players = self.parse_team_page(team)
            all_players.extend(players)
        
        # Count how many times each player appears
        player_counts = defaultdict(int)
        for player in all_players:
            player_counts[player['name']] += 1
        
        # Display results
        print("\n" + "="*60)
        print("CAPTAIN GANG ANALYSIS RESULTS")
        print("="*60)
        print(f"Captain ID: {player_id}")
        if player_name:
            # Clean up the name by removing extra whitespace
            clean_name = ' '.join(player_name.split())
            print(f"Captain/Co-Captain: {clean_name}")
        print(f"Teams analyzed: {len(captain_teams)}")
        print(f"Total player appearances: {len(all_players)}")
        print(f"Unique players: {len(player_counts)}")
        print("\nPlayer appearances across all captain teams:")
        print("-" * 60)
        
        # Sort by count (descending) then by name
        sorted_players = sorted(player_counts.items(), key=lambda x: (-x[1], x[0]))
        
        for player_name, count in sorted_players:
            print(f"{player_name:<40} {count:>3} times")
        
        print("\n" + "="*60)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze USTA captain teams and player appearances",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 captain_gang.py -c 302463
  python3 captain_gang.py --captain 302463
        """
    )
    
    parser.add_argument(
        '-c', '--captain',
        type=str,
        required=True,
        help='USTA player ID of the captain to analyze'
    )
    
    args = parser.parse_args()
    
    analyzer = USTACaptainAnalyzer()
    analyzer.analyze_captain(args.captain)


if __name__ == "__main__":
    main()
