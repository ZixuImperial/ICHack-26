#!/usr/bin/env python3
"""
Recycling Log Analyzer
Reads recycling_log.csv and analyzes material distribution with intelligent material recognition.
"""

import csv
import re
from collections import defaultdict, Counter
from typing import Dict, List, Tuple


# Material categories and their common variations/keywords
MATERIAL_CATEGORIES = {
    'PET Plastic': ['pet', 'polyethylene terephthalate', 'pete', 'plastic #1'],
    'HDPE Plastic': ['hdpe', 'high-density polyethylene', 'plastic #2'],
    'PVC Plastic': ['pvc', 'polyvinyl chloride', 'vinyl', 'plastic #3'],
    'LDPE Plastic': ['ldpe', 'low-density polyethylene', 'plastic #4'],
    'PP Plastic': ['pp', 'polypropylene', 'plastic #5'],
    'PS Plastic': ['ps', 'polystyrene', 'styrofoam', 'plastic #6'],
    'Other Plastic': ['plastic #7', 'mixed plastic', 'other plastic'],
    'Generic Plastic': ['plastic'],
    'Glass': ['glass', 'bottle glass', 'jar glass'],
    'Paper': ['paper', 'newspaper', 'office paper'],
    'Cardboard': ['cardboard', 'corrugated', 'carton'],
    'Metal - Aluminum': ['aluminum', 'aluminium', 'alu', 'tin can'],
    'Metal - Steel': ['steel', 'tin', 'metal can'],
    'Metal - Other': ['metal', 'copper', 'brass'],
    'Organic': ['food waste', 'organic', 'compost'],
    'Textile': ['fabric', 'textile', 'clothing', 'cloth'],
    'Electronics': ['electronic', 'e-waste', 'battery', 'circuit'],
    'Other': []  # Catch-all for unrecognized materials
}


def normalize_material(material_text: str) -> str:
    """
    Normalize material names by matching against known categories.

    Args:
        material_text: Raw material string from LLM output

    Returns:
        Normalized material category name
    """
    if not material_text:
        return 'Unknown'

    # Convert to lowercase for matching
    material_lower = material_text.lower().strip()

    # Try to match against known categories
    for category, keywords in MATERIAL_CATEGORIES.items():
        for keyword in keywords:
            if keyword in material_lower:
                return category

    # If no match found and it contains "plastic", categorize as Generic Plastic
    if 'plastic' in material_lower or 'polymer' in material_lower:
        return 'Generic Plastic'

    # Return original text if no category matches (will be grouped as 'Other')
    return material_text.title()


def read_recycling_logs(csv_file: str = 'recycling_log.csv') -> List[Dict[str, str]]:
    """
    Read the recycling log CSV file.

    Args:
        csv_file: Path to the CSV file

    Returns:
        List of dictionaries containing log entries
    """
    logs = []
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                logs.append(row)
        print(f"✓ Successfully read {len(logs)} entries from {csv_file}")
        return logs
    except FileNotFoundError:
        print(f"✗ Error: {csv_file} not found. No data to analyze.")
        return []
    except Exception as e:
        print(f"✗ Error reading CSV: {str(e)}")
        return []


def analyze_material_distribution(logs: List[Dict[str, str]]) -> Dict[str, Dict]:
    """
    Analyze material distribution from recycling logs.

    Args:
        logs: List of log entries

    Returns:
        Dictionary with material distribution statistics
    """
    material_counts = Counter()
    recyclable_by_material = defaultdict(lambda: {'yes': 0, 'no': 0, 'maybe': 0})
    location_material_counts = defaultdict(Counter)

    for entry in logs:
        # Extract and normalize material
        raw_material = entry.get('material', '').strip()
        normalized_material = normalize_material(raw_material)

        # Count materials
        material_counts[normalized_material] += 1

        # Track recyclability
        recyclable = entry.get('recyclable', '').lower().strip()
        if 'yes' in recyclable:
            recyclable_by_material[normalized_material]['yes'] += 1
        elif 'no' in recyclable:
            recyclable_by_material[normalized_material]['no'] += 1
        else:
            recyclable_by_material[normalized_material]['maybe'] += 1

        # Track by location
        location = entry.get('location', 'Unknown')
        location_material_counts[location][normalized_material] += 1

    # Calculate percentages
    total_items = len(logs)
    material_distribution = {}

    for material, count in material_counts.most_common():
        percentage = (count / total_items) * 100 if total_items > 0 else 0

        recyclability = recyclable_by_material[material]
        recyclable_rate = (recyclability['yes'] / count * 100) if count > 0 else 0

        material_distribution[material] = {
            'count': count,
            'percentage': round(percentage, 2),
            'recyclable_yes': recyclability['yes'],
            'recyclable_no': recyclability['no'],
            'recyclable_maybe': recyclability['maybe'],
            'recyclable_rate': round(recyclable_rate, 2)
        }

    return {
        'total_items': total_items,
        'materials': material_distribution,
        'by_location': dict(location_material_counts)
    }


def print_analysis(analysis: Dict):
    """
    Pretty print the analysis results.

    Args:
        analysis: Analysis dictionary from analyze_material_distribution
    """
    print("\n" + "="*70)
    print("RECYCLING LOG ANALYSIS")
    print("="*70)

    total = analysis['total_items']
    print(f"\nTotal Items Analyzed: {total}")

    if total == 0:
        print("\nNo data to analyze.")
        return

    print("\n" + "-"*70)
    print("MATERIAL DISTRIBUTION")
    print("-"*70)
    print(f"{'Material':<30} {'Count':<8} {'%':<8} {'Recyclable':<12}")
    print("-"*70)

    for material, stats in sorted(analysis['materials'].items(),
                                   key=lambda x: x[1]['count'],
                                   reverse=True):
        print(f"{material:<30} {stats['count']:<8} {stats['percentage']:<8.2f} "
              f"{stats['recyclable_rate']:<12.1f}%")

    print("\n" + "-"*70)
    print("DETAILED RECYCLABILITY BY MATERIAL")
    print("-"*70)
    print(f"{'Material':<30} {'Yes':<8} {'No':<8} {'Maybe':<8}")
    print("-"*70)

    for material, stats in sorted(analysis['materials'].items(),
                                   key=lambda x: x[1]['count'],
                                   reverse=True):
        print(f"{material:<30} {stats['recyclable_yes']:<8} "
              f"{stats['recyclable_no']:<8} {stats['recyclable_maybe']:<8}")

    # Location breakdown
    if analysis['by_location']:
        print("\n" + "-"*70)
        print("MATERIAL DISTRIBUTION BY LOCATION")
        print("-"*70)

        for location, materials in sorted(analysis['by_location'].items()):
            print(f"\n{location}:")
            for material, count in materials.most_common(5):  # Top 5 per location
                print(f"  {material:<30} {count} items")


def export_analysis_to_dict(analysis: Dict) -> Dict:
    """
    Export analysis in a structured format suitable for further processing.

    Args:
        analysis: Analysis dictionary

    Returns:
        Structured dictionary for export
    """
    return {
        'summary': {
            'total_items': analysis['total_items'],
            'unique_materials': len(analysis['materials'])
        },
        'material_distribution': [
            {
                'material': material,
                **stats
            }
            for material, stats in sorted(analysis['materials'].items(),
                                          key=lambda x: x[1]['count'],
                                          reverse=True)
        ],
        'locations': analysis['by_location']
    }


def main():
    """Main execution function."""
    print("\n🔍 Recycling Log Analyzer")
    print("="*70)

    # Read logs
    logs = read_recycling_logs()

    if not logs:
        return

    # Analyze distribution
    analysis = analyze_material_distribution(logs)

    # Print results
    print_analysis(analysis)

    # Export structured data
    structured_data = export_analysis_to_dict(analysis)

    print("\n" + "="*70)
    print("✓ Analysis complete!")
    print("="*70 + "\n")

    return structured_data


if __name__ == '__main__':
    main()
