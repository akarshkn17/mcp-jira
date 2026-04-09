import csv
import logging
from typing import List, Dict, Any

def export_to_csv(issues: List[Dict[str, Any]], output_path: str = "export.csv") -> bool:
    """
    Exports a list of flattened Jira issue dictionaries to a CSV file.
    
    Args:
        issues: List of dictionary containing issue data
        output_path: The file path to save the CSV to.
        
    Returns:
        bool: True if successful, False otherwise.
    """
    if not issues:
        logging.warning("No issues to export.")
        return False
        
    # Extract keys from the first issue to use as headers
    fieldnames = list(issues[0].keys())
    
    try:
        with open(output_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            for issue in issues:
                writer.writerow(issue)
        logging.info(f"Successfully exported {len(issues)} issues to {output_path}")
        return True
    except Exception as e:
        logging.error(f"Failed to export to CSV: {e}")
        return False
