import gspread
import time
import requests
import json
import base64
from google.oauth2.service_account import Credentials

# Define the scope
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

# Load credentials and connect to Google Sheets
credentials = Credentials.from_service_account_file('credentials.json', scopes=scope)
client = gspread.authorize(credentials)
sheet = client.open("EDU GPT").sheet1

# Get all data from the sheet
all_data = sheet.get_all_records()

# OpenProject API setup
BASE_URL = "https://pm.xinotrix.com/api/v3"
API_KEY = "49ac665b8a92d98d4d7a30da050794610819cf17705757c43d2ebd3b3db623d3"
PROJECT_ID = "3"

# Base64 encode the API key for Basic Auth
encoded_key = base64.b64encode(f"apikey:{API_KEY}".encode()).decode()

headers = {
    "Authorization": f"Basic {encoded_key}",
    "Content-Type": "application/json"
}

# Build a proper parent-child relationship map
def build_hierarchy(data):
    # First, create a map of all items by WBS ID
    items_by_wbs = {}
    for row in data:
        wbs_id = str(row.get('WBS ID', ''))
        if wbs_id:
            items_by_wbs[wbs_id] = row
    
    # Now build the dependency chains
    hierarchy_groups = {}
    processed = set()
    
    # Helper function to get the depth of an item
    def get_depth(wbs_id, visited=None):
        if visited is None:
            visited = set()
        
        # Avoid circular dependencies
        if wbs_id in visited:
            print(f"Warning: Circular dependency detected for {wbs_id}")
            return 0
        
        visited.add(wbs_id)
        
        item = items_by_wbs.get(wbs_id)
        if not item:
            return 0
            
        parent_wbs_id = str(item.get('Parent WBS ID', ''))
        
        # No parent = depth 0
        if not parent_wbs_id or parent_wbs_id not in items_by_wbs:
            return 0
            
        # Depth = parent's depth + 1
        return get_depth(parent_wbs_id, visited) + 1
    
    # Assign each item to its depth group
    for wbs_id, item in items_by_wbs.items():
        if wbs_id in processed:
            continue
            
        depth = get_depth(wbs_id)
        if depth not in hierarchy_groups:
            hierarchy_groups[depth] = []
            
        hierarchy_groups[depth].append(item)
        processed.add(wbs_id)
    
    return hierarchy_groups

# Build the hierarchy based on actual parent-child relationships
hierarchy_levels = build_hierarchy(all_data)

# Dictionary to store created work packages by WBS ID
work_packages = {}
# Keep a record of exactly what was created
created_items = {}

# Process each level in order (level 0 first, then 1, etc.)
max_level = max(hierarchy_levels.keys()) if hierarchy_levels else 0
print(f"Found items with hierarchy levels up to {max_level}")

for level in range(max_level + 1):
    print(f"\nProcessing hierarchy level {level}...")
    
    if level not in hierarchy_levels:
        continue
    
    # Sort items at each level by WBS ID to maintain order
    level_items = sorted(hierarchy_levels[level], key=lambda x: str(x.get('WBS ID', '')))
    
    for row in level_items:
        wbs_id = str(row.get('WBS ID', ''))
        item_type = row.get('Type', '')
        name = row.get('Name', '')
        description = row.get('Description', '')
        estimated_hours = row.get('Estimated Hours', 0) 
        parent_wbs_id = str(row.get('Parent WBS ID', ''))
        
        # Skip rows with missing essential data
        if not wbs_id or not item_type or not name:
            print(f"Skipping row with incomplete data: {row}")
            continue
        
        # Skip if we've already created this item (avoid duplicates)
        if wbs_id in work_packages:
            print(f"Skipping already created item: {name} (WBS: {wbs_id})")
            continue
        
        # Determine OpenProject type ID
        type_id = "3" if item_type.lower() == "phase" else "1"
        
        # Create work package with parent link if available
        wp_payload = {
            "_links": {
                "project": {"href": f"/api/v3/projects/{PROJECT_ID}"},
                "type": {"href": f"/api/v3/types/{type_id}"}
            },
            "subject": name,
            "description": {"raw": description if description else f"Work package for {name}"}
        }
        
        # Add parent link if parent exists and was created successfully
        if parent_wbs_id and parent_wbs_id in work_packages:
            parent_id = work_packages[parent_wbs_id]
            wp_payload["_links"]["parent"] = {"href": f"/api/v3/work_packages/{parent_id}"}
            print(f"Setting parent for {name} (WBS: {wbs_id}) to {parent_wbs_id} (ID: {parent_id})")
        elif parent_wbs_id:
            print(f"Warning: Parent {parent_wbs_id} not found for {name} (WBS: {wbs_id})")
        
        # Add estimated time if provided
        if estimated_hours:
            try:
                hours = int(float(estimated_hours))
                wp_payload["estimatedTime"] = f"PT{hours}H"
            except (ValueError, TypeError):
                print(f"Warning: Invalid estimated hours for {name}: {estimated_hours}")
        
        # Create the work package
        max_retries = 3
        for attempt in range(max_retries):
            try:
                wp_response = requests.post(
                    f"{BASE_URL}/work_packages", 
                    headers=headers, 
                    json=wp_payload
                )
                wp_response.raise_for_status()
                wp_data = wp_response.json()
                wp_id = wp_data.get('id')
                
                # Store both the ID and the full data for reference
                work_packages[wbs_id] = wp_id
                created_items[wbs_id] = {
                    "id": wp_id,
                    "name": name,
                    "type": item_type,
                    "parent_wbs": parent_wbs_id,
                    "parent_id": work_packages.get(parent_wbs_id) if parent_wbs_id in work_packages else None
                }
                
                parent_info = f" (child of {parent_wbs_id})" if parent_wbs_id and parent_wbs_id in work_packages else ""
                print(f"Created {item_type}: {name} with ID {wp_id}, WBS: {wbs_id}{parent_info}")
                break
            except requests.exceptions.RequestException as e:
                print(f"Error creating {item_type} {name} (attempt {attempt+1}/{max_retries}): {e}")
                
                if hasattr(e, 'response') and e.response:
                    error_text = e.response.text
                    try:
                        error_json = json.loads(error_text)
                        print(f"Error details: {json.dumps(error_json, indent=2)}")
                    except:
                        print(f"Error response: {error_text}")
                
                # If this was our last attempt, continue to the next item
                if attempt == max_retries - 1:
                    print(f"Failed to create {item_type} {name} after {max_retries} attempts")
                    continue
                
                # If we get a 409 Conflict when trying to set parent, try without parent
                if hasattr(e, 'response') and e.response and e.response.status_code == 409 and "parent" in wp_payload.get("_links", {}):
                    print(f"Conflict when setting parent. Trying without parent relationship...")
                    # Remove the parent link and try again
                    del wp_payload["_links"]["parent"]
                
                # Wait a bit longer between retries
                time.sleep(2)
        
        # Add a small delay between creations
        time.sleep(1)

print("\nProcess completed.")
print(f"Successfully created {len(work_packages)} work packages out of {len(all_data)} items.")

# Check for missing items
missing_items = [row for row in all_data if str(row.get('WBS ID', '')) not in work_packages]
if missing_items:
    print(f"Warning: {len(missing_items)} items were not created:")
    for item in missing_items:
        print(f"  - WBS: {item.get('WBS ID', '')}, Name: {item.get('Name', '')}")

# Check for items without proper parent relationships
orphaned_items = []
for wbs_id, item_data in created_items.items():
    parent_wbs = item_data.get('parent_wbs')
    parent_id = item_data.get('parent_id')
    
    if parent_wbs and not parent_id:
        orphaned_items.append({
            "wbs_id": wbs_id,
            "name": item_data.get('name'),
            "parent_wbs": parent_wbs
        })

if orphaned_items:
    print(f"\n{len(orphaned_items)} items were created without proper parent relationships:")
    for item in orphaned_items:
        print(f"  - WBS: {item['wbs_id']}, Name: {item['name']}, Missing Parent: {item['parent_wbs']}")
    print("These items may need manual parent-child relationship adjustments in OpenProject.")

