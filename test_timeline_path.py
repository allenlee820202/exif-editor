#!/usr/bin/env python3
"""
Test script for timelinePath functionality in location_history.py
"""

import datetime
from location_history import find_closest_location

def test_timeline_path():
    """Test the timelinePath entry type handling"""
    
    # Sample timelinePath entry similar to the one you provided
    timeline_entry = {
        'endTime': '2025-09-16T20:00:00.000Z',
        'startTime': '2025-09-16T18:00:00.000Z',
        'timelinePath': [
            {'point': 'geo:64.142619,-21.913976', 'durationMinutesOffsetFromStartTime': '5'},
            {'point': 'geo:64.142500,-21.916587', 'durationMinutesOffsetFromStartTime': '97'},
            {'point': 'geo:64.142052,-21.917882', 'durationMinutesOffsetFromStartTime': '101'},
            {'point': 'geo:64.141756,-21.918009', 'durationMinutesOffsetFromStartTime': '102'},
            {'point': 'geo:64.141757,-21.919281', 'durationMinutesOffsetFromStartTime': '103'},
            {'point': 'geo:64.142201,-21.921271', 'durationMinutesOffsetFromStartTime': '105'},
            {'point': 'geo:64.142437,-21.922411', 'durationMinutesOffsetFromStartTime': '106'},
            {'point': 'geo:64.142419,-21.922387', 'durationMinutesOffsetFromStartTime': '109'},
            {'point': 'geo:64.143217,-21.926352', 'durationMinutesOffsetFromStartTime': '110'},
            {'point': 'geo:64.145039,-21.924839', 'durationMinutesOffsetFromStartTime': '111'},
            {'point': 'geo:64.146472,-21.923519', 'durationMinutesOffsetFromStartTime': '112'},
            {'point': 'geo:64.146092,-21.919495', 'durationMinutesOffsetFromStartTime': '113'},
            {'point': 'geo:64.146624,-21.909030', 'durationMinutesOffsetFromStartTime': '114'},
            {'point': 'geo:64.147268,-21.895967', 'durationMinutesOffsetFromStartTime': '115'},
            {'point': 'geo:64.151076,-21.877133', 'durationMinutesOffsetFromStartTime': '116'},
            {'point': 'geo:64.148453,-21.864792', 'durationMinutesOffsetFromStartTime': '117'},
            {'point': 'geo:64.143706,-21.853396', 'durationMinutesOffsetFromStartTime': '118'},
            {'point': 'geo:64.133688,-21.849905', 'durationMinutesOffsetFromStartTime': '120'}
        ]
    }
    
    # Test cases with different photo times
    test_cases = [
        {
            'name': 'Photo at start time + 5 minutes (should match first point)',
            'photo_time': datetime.datetime.fromisoformat('2025-09-16T18:05:00.000+00:00'),
            'expected_lat': 64.142619,
            'expected_lon': -21.913976
        },
        {
            'name': 'Photo at start time + 110 minutes (should match middle point)', 
            'photo_time': datetime.datetime.fromisoformat('2025-09-16T19:50:00.000+00:00'),
            'expected_lat': 64.143217,
            'expected_lon': -21.926352
        },
        {
            'name': 'Photo at start time + 120 minutes (should match last point)',
            'photo_time': datetime.datetime.fromisoformat('2025-09-16T20:00:00.000+00:00'),
            'expected_lat': 64.133688,
            'expected_lon': -21.849905
        },
        {
            'name': 'Photo at start time + 104 minutes (should match closest point at 103)',
            'photo_time': datetime.datetime.fromisoformat('2025-09-16T19:44:00.000+00:00'),
            'expected_lat': 64.141757,  # Point at 103 minutes (closest to 104)
            'expected_lon': -21.919281
        }
    ]
    
    for test_case in test_cases:
        print(f"\nTesting: {test_case['name']}")
        
        result = find_closest_location(test_case['photo_time'], [timeline_entry])
        
        if result:
            print(f"  Found location: {result['lat']:.6f}, {result['lon']:.6f}")
            print(f"  Expected: {test_case['expected_lat']:.6f}, {test_case['expected_lon']:.6f}")
            print(f"  Semantic type: {result['semantic_type']}")
            print(f"  Time diff: {result['time_diff_minutes']} minutes")
            
            # Check if coordinates match (within small tolerance for floating point)
            lat_match = abs(result['lat'] - test_case['expected_lat']) < 0.000001
            lon_match = abs(result['lon'] - test_case['expected_lon']) < 0.000001
            
            if lat_match and lon_match:
                print("  ✅ PASS - Coordinates match expected values")
            else:
                print("  ❌ FAIL - Coordinates don't match expected values")
        else:
            print("  ❌ FAIL - No location found")


if __name__ == '__main__':
    test_timeline_path()