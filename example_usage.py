#!/usr/bin/env python3
"""
Example usage of the recycling log analyzer.
Demonstrates how to programmatically access material distribution data.
"""

from analyze_logs import read_recycling_logs, analyze_material_distribution, export_analysis_to_dict
import json


def example_get_top_materials(n=5):
    """Get the top N most common materials."""
    logs = read_recycling_logs()
    if not logs:
        return []

    analysis = analyze_material_distribution(logs)
    materials = analysis['materials']

    # Sort by count and get top N
    top_materials = sorted(materials.items(),
                          key=lambda x: x[1]['count'],
                          reverse=True)[:n]

    return [(material, stats['count'], stats['percentage'])
            for material, stats in top_materials]


def example_get_recyclability_rate():
    """Calculate overall recyclability rate."""
    logs = read_recycling_logs()
    if not logs:
        return 0

    recyclable_count = sum(1 for log in logs
                          if 'yes' in log.get('recyclable', '').lower())
    total = len(logs)

    return (recyclable_count / total * 100) if total > 0 else 0


def example_export_to_json(output_file='analysis_results.json'):
    """Export analysis results to JSON file."""
    logs = read_recycling_logs()
    if not logs:
        return False

    analysis = analyze_material_distribution(logs)
    structured_data = export_analysis_to_dict(analysis)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(structured_data, f, indent=2)

    print(f"✓ Analysis exported to {output_file}")
    return True


if __name__ == '__main__':
    print("\n📊 Example Usage of Recycling Log Analyzer\n")

    # Example 1: Get top materials
    print("Top 5 Materials:")
    top_materials = example_get_top_materials(5)
    for i, (material, count, percentage) in enumerate(top_materials, 1):
        print(f"  {i}. {material}: {count} items ({percentage:.1f}%)")

    # Example 2: Get overall recyclability rate
    print(f"\nOverall Recyclability Rate: {example_get_recyclability_rate():.1f}%")

    # Example 3: Export to JSON
    print()
    example_export_to_json()

    print("\n✓ Examples completed!\n")
