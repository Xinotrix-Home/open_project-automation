def delete_all_work_packages(base_url, api_key, project_id):
    """
    Delete all work packages (phases and tasks) for a specific project in OpenProject.
    Handles pagination and refreshes work package list between attempts.
    
    Args:
        base_url (str): The base URL of your OpenProject API
        api_key (str): Your OpenProject API key
        project_id (str): The ID of the project to clean up
    
    Returns:
        int: The number of work packages deleted
    """
    import requests
    import base64
    import time
    import json
    
    # Base64 encode the API key for Basic Auth
    encoded_key = base64.b64encode(f"apikey:{api_key}".encode()).decode()
    
    headers = {
        "Authorization": f"Basic {encoded_key}",
        "Content-Type": "application/json"
    }
    
    # Function to get current work packages
    def get_current_work_packages():
        current_work_packages = []
        current_page = 1
        page_size = 100
        
        print(f"Refreshing work package list for project {project_id}...")
        
        while True:
            # Add a cache-busting parameter to avoid stale data
            params = {
                "pageSize": page_size, 
                "offset": (current_page - 1) * page_size,
                "timestamp": int(time.time())  # Cache-busting
            }
            
            try:
                wp_response = requests.get(
                    f"{base_url}/projects/{project_id}/work_packages",
                    headers=headers,
                    params=params
                )
                wp_response.raise_for_status()
                wp_data = wp_response.json()
                
                work_packages = wp_data.get('_embedded', {}).get('elements', [])
                if not work_packages:
                    break
                    
                current_work_packages.extend(work_packages)
                print(f"Fetched page {current_page} with {len(work_packages)} work packages")
                
                # Check if there are more pages
                total = wp_data.get('total', 0)
                if len(current_work_packages) >= total or len(work_packages) < page_size:
                    break
                    
                current_page += 1
            except Exception as e:
                print(f"Error fetching work packages page {current_page}: {e}")
                break
        
        return current_work_packages
    
    # Get initial work package list
    all_work_packages = get_current_work_packages()
    total_count = len(all_work_packages)
    
    print(f"Found a total of {total_count} work packages to delete")
    
    # If no work packages found, return early
    if total_count == 0:
        print("No work packages found to delete.")
        return 0
    
    # Map work packages by ID
    wp_map = {wp.get('id'): wp for wp in all_work_packages}
    
    # Process in batches to handle potential data consistency issues
    deleted_count = 0
    max_attempts = 3
    
    for attempt in range(max_attempts):
        print(f"\nDeletion attempt {attempt + 1}/{max_attempts}")
        
        # Refresh the work package list for each attempt
        if attempt > 0:
            all_work_packages = get_current_work_packages()
            if not all_work_packages:
                print("No more work packages found. Deletion complete.")
                break
                
            # Update the mapping
            wp_map = {wp.get('id'): wp for wp in all_work_packages}
            print(f"Found {len(all_work_packages)} remaining work packages")
        
        # Build parent-child relationships
        child_map = {}
        for wp in all_work_packages:
            wp_id = wp.get('id')
            parent_link = wp.get('_links', {}).get('parent', {}).get('href', '')
            
            if parent_link:
                parent_id = parent_link.split('/')[-1]
                if parent_id not in child_map:
                    child_map[parent_id] = []
                child_map[parent_id].append(wp_id)
        
        # Identify leaf nodes (work packages with no children)
        leaf_nodes = [wp.get('id') for wp in all_work_packages if wp.get('id') not in child_map]
        print(f"Found {len(leaf_nodes)} leaf nodes to delete first")
        
        # Delete leaf nodes first
        for wp_id in leaf_nodes:
            if wp_id not in wp_map:
                continue
                
            try:
                print(f"Deleting work package {wp_id}...")
                delete_response = requests.delete(
                    f"{base_url}/work_packages/{wp_id}",
                    headers=headers
                )
                
                if delete_response.status_code == 404:
                    # Already deleted, count as success
                    print(f"Work package {wp_id} already deleted or not found")
                    deleted_count += 1
                else:
                    delete_response.raise_for_status()
                    print(f"Successfully deleted work package {wp_id}")
                    deleted_count += 1
                
                # Remove from maps
                if wp_id in wp_map:
                    del wp_map[wp_id]
                
                time.sleep(0.5)  # Small delay to avoid API rate limits
            except Exception as e:
                print(f"Error deleting work package {wp_id}: {e}")
        
        # If we've deleted all work packages, we're done
        if not wp_map:
            print("All work packages deleted. Operation complete.")
            break
    
    # Final check to see what's left
    remaining_packages = get_current_work_packages()
    
    print(f"\nDeletion complete. Deleted {deleted_count} work packages.")
    
    if remaining_packages:
        print(f"There are still {len(remaining_packages)} work packages remaining:")
        for wp in remaining_packages:
            print(f"  ID: {wp.get('id')}, Subject: {wp.get('subject')}")
        print("You may need to delete these manually or change the deletion order.")
    
    return deleted_count

delete_all_work_packages("https://pm.xinotrix.com/api/v3", "49ac665b8a92d98d4d7a30da050794610819cf17705757c43d2ebd3b3db623d3", "3")

