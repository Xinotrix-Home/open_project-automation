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

# OpenProject API setup
BASE_URL = "https://pm.xinotrix.com/api/v3"
API_KEY = "49ac665b8a92d98d4d7a30da050794610819cf17705757c43d2ebd3b3db623d3"

# Base64 encode the API key for Basic Auth
encoded_key = base64.b64encode(f"apikey:{API_KEY}".encode()).decode()

headers = {
    "Authorization": f"Basic {encoded_key}",
    "Content-Type": "application/json"
}

# Step 1: List all projects to find the correct project ID
try:
    print("Fetching available projects...")
    projects_response = requests.get(f"{BASE_URL}/projects", headers=headers)
    projects_response.raise_for_status()
    projects_data = projects_response.json()
    
    print("Available projects:")
    for project in projects_data.get('_embedded', {}).get('elements', []):
        print(f"Name: {project.get('name')}, ID: {project.get('id')}, Identifier: {project.get('identifier')}")
    
    # Ask user to confirm project ID
    PROJECT_ID = input("Enter the numeric project ID to use: ")
    
except requests.exceptions.RequestException as e:
    print(f"Error fetching projects: {e}")
    if hasattr(e, 'response') and e.response:
        print(f"Response content: {e.response.text}")
    exit(1)

# Step 2: List all available work package types
try:
    print("\nFetching available work package types...")
    types_response = requests.get(f"{BASE_URL}/types", headers=headers)
    types_response.raise_for_status()
    types_data = types_response.json()
    
    print("Available work package types:")
    for wp_type in types_data.get('_embedded', {}).get('elements', []):
        print(f"Name: {wp_type.get('name')}, ID: {wp_type.get('id')}")
    
    # Ask user to confirm type IDs
    PHASE_TYPE_ID = input("Enter the numeric ID for Phase type: ")
    TASK_TYPE_ID = input("Enter the numeric ID for Task type: ")
    
except requests.exceptions.RequestException as e:
    print(f"Error fetching work package types: {e}")
    if hasattr(e, 'response') and e.response:
        print(f"Response content: {e.response.text}")
    exit(1)

# Create a test work package to verify
try:
    print("\nCreating a test work package...")
    test_payload = {
        "_links": {
            "project": {"href": f"/api/v3/projects/{PROJECT_ID}"},
            "type": {"href": f"/api/v3/types/{TASK_TYPE_ID}"}
        },
        "subject": "Test Work Package",
        "description": {"raw": "This is a test work package to verify API functionality"}
    }
    
    test_response = requests.post(
        f"{BASE_URL}/work_packages",
        headers=headers,
        json=test_payload
    )
    test_response.raise_for_status()
    test_data = test_response.json()
    print(f"Test work package created successfully with ID: {test_data.get('id')}")
    
    # Show the exact payload that succeeded
    print("\nSuccessful payload structure:")
    print(json.dumps(test_payload, indent=2))
    
except requests.exceptions.RequestException as e:
    print(f"Error creating test work package: {e}")
    if hasattr(e, 'response') and e.response:
        print(f"Response content: {e.response.text}")
    exit(1)

print("\nDiagnostic script completed. Use the information above to adjust your main script.")