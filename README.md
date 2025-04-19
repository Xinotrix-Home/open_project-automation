# OpenProject Automation

A Python-based automation tool for managing tasks in OpenProject using Google Sheets integration.

## Overview

This project provides automation scripts for managing OpenProject tasks through Google Sheets. It includes functionality for adding, deleting, and managing tasks, with a diagnostic tool for troubleshooting.

## Features

- Task management automation
- Google Sheets integration
- Task addition and deletion capabilities
- Diagnostic tools for system verification

## Prerequisites

- Python 3.x
- Google Sheets API access 
- OpenProject credentials

## Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1. download `credentials.json` from here: https://drive.google.com/file/d/1BOn-SIDp5Yqu109zxgMfyvt0ojfv7q8V/view?usp=sharing
2. Place your `credentials.json` file in the project root directory
3. Ensure you have the necessary Google Sheets API access configured (share the google sheets with this service account - google-sheets-api@lunar-arc-444115-v9.iam.gserviceaccount.com)
4. Maintain this sheet structure (https://docs.google.com/spreadsheets/d/19Z_z3Om8QoYF-g_9vee7wLfwQjJSJPahWYyc_fWitkA/edit?usp=sharing)

## Usage

The project includes several Python scripts:

- `diagnostic_script.py`: Run system diagnostics and verification. here you can see the available projects and their corresponding project ID. 
- `add_tasks.py`: Add new tasks to OpenProject (configure the sheet name and project ID)
- `delete_tasks.py`: Remove tasks from OpenProject

Tada!!! Your life becomes EASIER :) 


