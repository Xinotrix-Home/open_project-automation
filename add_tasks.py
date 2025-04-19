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

# Sort data to ensure parents are created before children
sorted_data = sorted(all_data, key=lambda x: str(x.get('WBS ID', '')))

# Dictionary to store created work packages by WBS ID
work_packages = {}

# Create all work packages with parent relationships in a single pass
print("Creating work packages with parent relationships...")
for index, row in enumerate(sorted_data):
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
        print(f"Including parent link: {name} -> {parent_wbs_id} (ID: {parent_id})")
    
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
            work_packages[wbs_id] = wp_id
            
            parent_info = f" (child of {parent_wbs_id})" if parent_wbs_id and parent_wbs_id in work_packages else ""
            print(f"Created {item_type}: {name} with ID {wp_id}, WBS: {wbs_id}{parent_info} ({index+1}/{len(sorted_data)})")
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
print(f"Successfully created {len(work_packages)} work packages out of {len(sorted_data)} items.")

# Check for items with failed parent relationships
items_without_parents = []
for row in sorted_data:
    wbs_id = str(row.get('WBS ID', ''))
    parent_wbs_id = str(row.get('Parent WBS ID', ''))
    name = row.get('Name', '')
    
    if wbs_id in work_packages and parent_wbs_id and parent_wbs_id in work_packages:
        # Check if the parent relationship is correctly set
        child_id = work_packages[wbs_id]
        try:
            wp_response = requests.get(
                f"{BASE_URL}/work_packages/{child_id}", 
                headers=headers
            )
            wp_response.raise_for_status()
            wp_data = wp_response.json()
            
            parent_link = wp_data.get('_links', {}).get('parent', {}).get('href', '')
            expected_parent_id = work_packages[parent_wbs_id]
            expected_link = f"/api/v3/work_packages/{expected_parent_id}"
            
            if parent_link != expected_link:
                items_without_parents.append({
                    "wbs_id": wbs_id,
                    "name": name,
                    "parent_wbs_id": parent_wbs_id
                })
        except:
            # If we can't check, assume it might need fixing
            items_without_parents.append({
                "wbs_id": wbs_id,
                "name": name,
                "parent_wbs_id": parent_wbs_id
            })

if items_without_parents:
    print(f"\n{len(items_without_parents)} items may need manual parent relationship adjustment:")
    for item in items_without_parents:
        print(f"  - WBS: {item['wbs_id']}, Name: {item['name']}, Parent WBS: {item['parent_wbs_id']}")

# List all created work packages for reference
print("\nCreated Work Packages:")
for wbs_id, wp_id in sorted(work_packages.items()):
    item = next((r for r in sorted_data if str(r.get('WBS ID', '')) == wbs_id), None)
    if item:
        parent_wbs_id = str(item.get('Parent WBS ID', ''))
        parent_info = f" (parent: {parent_wbs_id})" if parent_wbs_id and parent_wbs_id in work_packages else ""
        print(f"WBS: {wbs_id}, ID: {wp_id}, Name: {item.get('Name', '')}{parent_info}")