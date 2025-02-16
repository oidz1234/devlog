#!/usr/bin/env python3
import re
import requests
from datetime import datetime
from pathlib import Path
import base64
import os

# Configuration
CONFIG = {
    # GitHub repository settings
    'REPO_OWNER': 'oidz1234',     # Your GitHub username
    'REPO_NAME': 'devlog',          # Your repository name
    'FILE_PATH': 'devlog.txt',         # Path to devlog.txt in your repo
    
    # Output settings
    'TEMPLATE_PATH': 'template.html',   # Path to template file
    'OUTPUT_DIR': '/srv/devlog/',            # Directory where the HTML will be generated
    'OUTPUT_FILENAME': 'index.html',    # Name of the generated HTML file
    
    # Optional: Set these via environment variables
    'REPO_OWNER_ENV': 'DEVLOG_REPO_OWNER',
    'REPO_NAME_ENV': 'DEVLOG_REPO_NAME',
    'OUTPUT_DIR_ENV': 'DEVLOG_OUTPUT_DIR',
    'OUTPUT_FILENAME_ENV': 'DEVLOG_OUTPUT_FILENAME'
}

def load_config():
    """Load configuration from environment variables if available."""
    config = CONFIG.copy()

    # Override with environment variables if they exist
    if os.getenv(CONFIG['REPO_OWNER_ENV']):
        config['REPO_OWNER'] = os.getenv(CONFIG['REPO_OWNER_ENV'])
    if os.getenv(CONFIG['REPO_NAME_ENV']):
        config['REPO_NAME'] = os.getenv(CONFIG['REPO_NAME_ENV'])
    if os.getenv(CONFIG['OUTPUT_DIR_ENV']):
        config['OUTPUT_DIR'] = os.getenv(CONFIG['OUTPUT_DIR_ENV'])
    if os.getenv(CONFIG['OUTPUT_FILENAME_ENV']):
        config['OUTPUT_FILENAME'] = os.getenv(CONFIG['OUTPUT_FILENAME_ENV'])

    return config

def fetch_from_github(repo_owner, repo_name, file_path='devlog.txt'):
    """Fetch devlog content from public GitHub repository."""
    # Add timestamp to prevent caching
    timestamp = int(datetime.now().timestamp())
    url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{file_path}'
    response = requests.get(url, params={'timestamp': timestamp},
                          headers={'Cache-Control': 'no-cache'})

    if response.status_code != 200:
        raise Exception(f'Failed to fetch file: {response.status_code}')

    content = response.json()['content']
    return base64.b64decode(content).decode('utf-8')

def parse_devlog_content(content):
    """Parse the devlog content and return structured data."""
    entries = []
    all_tags = set()

    # Split into entries based on date patterns
    raw_entries = []
    current_entry = []

    for line in content.split('\n'):
        # If we find a date pattern, it's a new entry
        if re.match(r'\d{2}-\d{2}-\d{2}\s+\w+', line):
            if current_entry:
                raw_entries.append('\n'.join(current_entry))
            current_entry = [line]
        # If we find tags, complete the current entry
        elif '#' in line and any(word.startswith('#') for word in line.split()):
            current_entry.append(line)
            raw_entries.append('\n'.join(current_entry))
            current_entry = []
        elif current_entry:  # If we have a current entry, add the line to it
            current_entry.append(line)

    # Add the last entry if there is one
    if current_entry:
        raw_entries.append('\n'.join(current_entry))

    for entry in raw_entries:
        if not entry.strip():
            continue

        # Extract date (format: DD-MM-YY Day)
        date_match = re.match(r'(\d{2}-\d{2}-\d{2}\s+\w+)', entry)
        if not date_match:
            continue

        display_date = date_match.group(1)
        # Convert to sortable format internally (YYYY-MM-DD)
        day, month, year = display_date.split()[0].split('-')
        date = f'20{year}-{month}-{day}'  # Assuming 20xx for year

        # Get content after the date line
        content_start = entry.find('\n', entry.find(display_date))
        if content_start == -1:
            continue

        content = entry[content_start:].strip()

        # Process code blocks (```...```)
        content = re.sub(
            r'```(.*?)```',
            lambda m: f'<pre><code>{m.group(1)}</code></pre>',
            content,
            flags=re.DOTALL
        )

        # Process Markdown links [text](url)
        content = re.sub(
            r'\[([^\]]+)\]\(([^)]+)\)',
            lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>',
            content
        )

        # Process bare URLs
        content = re.sub(
            r'<(https?://[^>]+)>',
            lambda m: f'<a href="{m.group(1)}">{m.group(1)}</a>',
            content
        )


        # Extract tags (format: #tag1 #tag2)
        tags = re.findall(r'#(\w+)', content)
        all_tags.update(tags)

        # Remove tags from content
        content = re.sub(r'#\w+', '', content).strip()

        entries.append({
            'date': date,
            'display_date': display_date,
            'content': content,
            'tags': tags
        })

    return entries, list(all_tags)

def generate_html(template_path, entries, tags):
    """Generate the HTML file from the template and entries."""
    with open(template_path, 'r') as f:
        template = f.read()

    # Generate tag buttons
    tag_buttons = '\n'.join([
        f'<button onclick="filterByTag(\'{tag}\')">{tag.upper()}</button>'
        for tag in sorted(tags)
    ])

    # Generate entries HTML
    entries_html = ''
    for entry in sorted(entries, key=lambda x: x['date'], reverse=True):
        tags_html = '\n'.join([
            f'<span class="tag" onclick="filterByTag(\'{tag}\')">{tag}</span>'
            for tag in entry['tags']
        ])

        entries_html += f'''
        <div class="entry" data-tags="{' '.join(entry['tags'])}">
            <div class="date">{entry['display_date']}</div>
            <div class="content">{entry['content']}</div>
            <div class="tags">{tags_html}</div>
        </div>
        '''

    # Insert dynamic content into template
    html = template.replace('<!-- Tags will be dynamically inserted here -->', tag_buttons)
    html = html.replace('<!-- Entries will be dynamically inserted here -->', entries_html)

    return html

def main():
    # Load configuration
    config = load_config()
    base_dir = Path(__file__).parent

    try:
        # Create output directory if it doesn't exist
        output_dir = Path(config['OUTPUT_DIR'])
        output_dir.mkdir(parents=True, exist_ok=True)

        # Fetch and parse the devlog
        content = fetch_from_github(
            config['REPO_OWNER'],
            config['REPO_NAME'],
            config['FILE_PATH']
        )
        entries, tags = parse_devlog_content(content)

        # Generate and save the HTML
        html = generate_html(
            base_dir / config['TEMPLATE_PATH'],
            entries,
            tags
        )

        output_path = output_dir / config['OUTPUT_FILENAME']
        with open(output_path, 'w') as f:
            f.write(html)

        print(f"Successfully generated devlog at {output_path}")
        print(f"Stats: {len(entries)} entries, {len(tags)} tags")

    except Exception as e:
        print(f"Error generating devlog: {str(e)}")

if __name__ == '__main__':
    main()
