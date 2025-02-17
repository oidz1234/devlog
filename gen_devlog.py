#!/usr/bin/env python3
import re
import requests
from datetime import datetime
from pathlib import Path
import base64
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Configuration
CONFIG = {
    # GitHub repository settings
    'REPO_OWNER': 'oidz1234',
    'REPO_NAME': 'devlog',
    'FILE_PATH': 'devlog.txt',
    
    # Output settings
    'TEMPLATE_PATH': 'template.html',
    'OUTPUT_DIR': '/srv/devlog/',
    'OUTPUT_FILENAME': 'index.html',
    
    # Site settings
    'SITE_URL': 'https://mark.mcnally.je/devlog/',
    'SITE_TITLE': 'Marks Devlog',
    'SITE_AUTHOR': 'Mark McNally',
    'SITE_DESCRIPTION': 'Development Log',
    
    # Environment variable names
    'REPO_OWNER_ENV': 'DEVLOG_REPO_OWNER',
    'REPO_NAME_ENV': 'DEVLOG_REPO_NAME',
    'OUTPUT_DIR_ENV': 'DEVLOG_OUTPUT_DIR',
    'OUTPUT_FILENAME_ENV': 'DEVLOG_OUTPUT_FILENAME',
    'SITE_URL_ENV': 'DEVLOG_SITE_URL',
    'SITE_TITLE_ENV': 'DEVLOG_SITE_TITLE',
    'SITE_AUTHOR_ENV': 'DEVLOG_SITE_AUTHOR',
    'SITE_DESCRIPTION_ENV': 'DEVLOG_SITE_DESCRIPTION'
}

def load_config():
    """Load configuration from environment variables if available."""
    config = CONFIG.copy()
    
    env_mappings = {
        'REPO_OWNER_ENV': 'REPO_OWNER',
        'REPO_NAME_ENV': 'REPO_NAME',
        'OUTPUT_DIR_ENV': 'OUTPUT_DIR',
        'OUTPUT_FILENAME_ENV': 'OUTPUT_FILENAME',
        'SITE_URL_ENV': 'SITE_URL',
        'SITE_TITLE_ENV': 'SITE_TITLE',
        'SITE_AUTHOR_ENV': 'SITE_AUTHOR',
        'SITE_DESCRIPTION_ENV': 'SITE_DESCRIPTION'
    }
    
    for env_key, config_key in env_mappings.items():
        if os.getenv(config[env_key]):
            config[config_key] = os.getenv(config[env_key])
    
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

def generate_rss_feed(entries, config):
    """Generate RSS feed without external dependencies."""
    rss = ET.Element('rss', version='2.0')
    channel = ET.SubElement(rss, 'channel')
    
    # Add required channel elements
    title = ET.SubElement(channel, 'title')
    title.text = config['SITE_TITLE']
    
    link = ET.SubElement(channel, 'link')
    link.text = config['SITE_URL']
    
    description = ET.SubElement(channel, 'description')
    description.text = config['SITE_DESCRIPTION']
    
    # Add optional channel elements
    language = ET.SubElement(channel, 'language')
    language.text = 'en-us'
    
    generator = ET.SubElement(channel, 'generator')
    generator.text = 'Python RSS Generator'
    
    # Add items
    for entry in sorted(entries, key=lambda x: x['date'], reverse=True):
        item = ET.SubElement(channel, 'item')
        
        item_title = ET.SubElement(item, 'title')
        item_title.text = entry['display_date']
        
        item_link = ET.SubElement(item, 'link')
        item_link.text = f"{config['SITE_URL']}#{entry['date']}"
        
        item_guid = ET.SubElement(item, 'guid')
        item_guid.text = f"{config['SITE_URL']}#{entry['date']}"
        
        # Process content: preserve newlines and code blocks
        content = entry['content']
        
        # Convert pre/code blocks to preserve formatting
        content = re.sub(
            r'<pre><code>(.*?)</code></pre>',
            lambda m: '\n\n' + m.group(1) + '\n\n',
            content,
            flags=re.DOTALL
        )
        
        # Remove other HTML tags but preserve their newlines
        content = re.sub(r'<[^>]+>', '', content)
        
        # Ensure proper spacing around code blocks
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # Create description with CDATA
        item_description = ET.SubElement(item, 'description')
        item_description.text = f'<![CDATA[{content}]]>'
        
        # Add publication date
        pub_date = ET.SubElement(item, 'pubDate')
        date_obj = datetime.strptime(entry['date'], '%Y-%m-%d')
        pub_date.text = date_obj.strftime('%a, %d %b %Y 00:00:00 GMT')
        
        # Add author
        author = ET.SubElement(item, 'author')
        author.text = config['SITE_AUTHOR']
        
        # Add categories (tags)
        for tag in entry['tags']:
            category = ET.SubElement(item, 'category')
            category.text = tag
    
    # Convert to string with pretty printing
    xml_str = minidom.parseString(ET.tostring(rss)).toprettyxml(indent="  ")
    
    # Save the feed
    output_dir = Path(config['OUTPUT_DIR'])
    with open(output_dir / 'feed.xml', 'w', encoding='utf-8') as f:
        f.write(xml_str)

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

        # Generate RSS feed
        generate_rss_feed(entries, config)

        print(f"Successfully generated devlog at {output_path}")
        print(f"Stats: {len(entries)} entries, {len(tags)} tags")
        print(f"RSS feed generated at {output_dir}/feed.xml")

    except Exception as e:
        print(f"Error generating devlog: {str(e)}")

if __name__ == '__main__':
    main()
