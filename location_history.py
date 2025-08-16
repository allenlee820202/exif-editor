"""
Google Location History processing module.

This module provides functionality to process Google Location History JSON files
and match location data with photo timestamps for EXIF GPS tagging.
"""

import os
import json
import datetime
from typing import List, Dict, Optional, Tuple, Any
import exif


def parse_time(time_str: str) -> Optional[datetime.datetime]:
    """Parse ISO time string to datetime object.
    
    Args:
        time_str: ISO formatted time string like "2013-07-21T18:20:06.088+08:00"
        
    Returns:
        Parsed datetime object or None if parsing fails
    """
    try:
        if time_str:
            # Remove microseconds and parse
            time_str = time_str.split('.')[0] + time_str[-6:]
            return datetime.datetime.fromisoformat(time_str.replace('Z', '+00:00'))
    except Exception:
        pass
    return None


def get_photo_timestamp(file_path: str) -> Optional[datetime.datetime]:
    """Extract timestamp from photo EXIF data.
    
    Args:
        file_path: Path to the photo file
        
    Returns:
        Photo timestamp with timezone info, or None if extraction fails
    """
    try:
        datetime_str = exif.get_exif_date_time_original(file_path)
        timezone_offset = exif.get_offset_time_data(file_path)
        timestamp = None
        
        if datetime_str:
            timestamp = datetime.datetime.strptime(datetime_str, '%Y:%m:%d %H:%M:%S')
            
        if timezone_offset:
            # timezone_offset looks like "+08:00" or "-05:00"
            # Parse sign, hours, and minutes from the offset string
            sign = 1 if timezone_offset[0] == '+' else -1
            hours = int(timezone_offset[1:3])
            minutes = int(timezone_offset[4:6])
            offset = datetime.timedelta(hours=sign * hours, minutes=sign * minutes)
            timestamp = timestamp.replace(tzinfo=datetime.timezone(offset))
        elif timestamp:
            # Default to UTC if no timezone offset available
            timestamp = timestamp.replace(tzinfo=datetime.timezone.utc)
            
        return timestamp
    except Exception:
        # Fallback to file modification time
        try:
            return datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
        except Exception:
            pass
    return None


def find_closest_location(photo_time: datetime.datetime, locations: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Find the closest location entry to photo timestamp.
    
    Args:
        photo_time: Timestamp of the photo
        locations: List of location entries from Google Location History
        
    Returns:
        Dictionary with location data or None if no match found
    """
    closest_location = None
    min_time_diff = float('inf')
    
    for entry in locations:
        entry_time = parse_time(entry.get('startTime', ''))
        if not entry_time:
            continue
            
        time_diff = abs((photo_time - entry_time).total_seconds())
        if time_diff >= min_time_diff:
            continue
        
        # Handle 'visit' entries
        if 'visit' in entry and 'topCandidate' in entry['visit']:
            candidate = entry['visit']['topCandidate']
            if 'placeLocation' in candidate:
                geo_str = candidate['placeLocation']
                if geo_str.startswith('geo:'):
                    coords = geo_str[4:].split(',')
                    if len(coords) == 2:
                        try:
                            lat, lon = float(coords[0]), float(coords[1])
                            min_time_diff = time_diff
                            closest_location = {
                                'lat': lat,
                                'lon': lon,
                                'semantic_type': f"Visit: {candidate.get('semanticType', 'Unknown')}",
                                'probability': candidate.get('probability', '0'),
                                'time_diff_minutes': int(time_diff / 60)
                            }
                        except ValueError:
                            continue
        
        # Handle 'activity' entries
        elif 'activity' in entry:
            activity = entry['activity']
            geo_str = None
            activity_type = 'Unknown'
            
            # Get activity type from topCandidate
            if 'topCandidate' in activity and 'type' in activity['topCandidate']:
                activity_type = activity['topCandidate']['type']
            
            # Try to get location from start first, then end
            if 'start' in activity:
                geo_str = activity['start']
            elif 'end' in activity:
                geo_str = activity['end']
            
            if geo_str and geo_str.startswith('geo:'):
                coords = geo_str[4:].split(',')
                if len(coords) == 2:
                    try:
                        lat, lon = float(coords[0]), float(coords[1])
                        min_time_diff = time_diff
                        closest_location = {
                            'lat': lat,
                            'lon': lon,
                            'semantic_type': f"Activity: {activity_type}",
                            'probability': '1.0',  # Activities are definitive locations
                            'time_diff_minutes': int(time_diff / 60)
                        }
                    except ValueError:
                        continue
    
    return closest_location


def load_location_history(location_file: str) -> List[Dict[str, Any]]:
    """Load Google Location History JSON file.
    
    Args:
        location_file: Path to the location history JSON file
        
    Returns:
        List of location entries
        
    Raises:
        FileNotFoundError: If location file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
    with open(location_file, 'r') as f:
        return json.load(f)


def filter_locations_by_time_range(locations: List[Dict[str, Any]], 
                                 time_range: Tuple[datetime.datetime, datetime.datetime]) -> List[Dict[str, Any]]:
    """Filter location entries within the specified time range.
    
    Args:
        locations: List of location entries
        time_range: Tuple of (start_time, end_time)
        
    Returns:
        Filtered list of location entries
    """
    filtered_locations = []
    start_time, end_time = time_range
    
    for entry in locations:
        entry_time = parse_time(entry.get('startTime', ''))
        if entry_time and start_time <= entry_time <= end_time:
            filtered_locations.append(entry)
    
    return filtered_locations


def extract_photo_time_range(photo_files: List[str]) -> Optional[Tuple[datetime.datetime, datetime.datetime]]:
    """Extract earliest and latest timestamps from photos.
    
    Args:
        photo_files: List of paths to photo files
        
    Returns:
        Tuple of (earliest_time, latest_time) or None if no timestamps found
    """
    timestamps = []
    
    for file_path in photo_files:
        try:
            timestamp = get_photo_timestamp(file_path)  
            if timestamp:
                timestamps.append(timestamp)
        except Exception as e:
            print(f"Could not extract timestamp from {file_path}: {e}")
            continue
    
    if not timestamps:
        return None
    
    return (min(timestamps), max(timestamps))


def process_photos_with_location_history(location_file: str, 
                                       photo_files: List[str],
                                       progress_callback: Optional[callable] = None) -> List[Dict[str, Any]]:
    """Process photos and match them with location history data.
    
    Args:
        location_file: Path to Google Location History JSON file
        photo_files: List of paths to photo files
        progress_callback: Optional callback function called with (current, total) progress
        
    Returns:
        List of dictionaries containing matched photo and GPS data
    """
    try:
        # Load location history
        location_data = load_location_history(location_file)
        
        # Extract time range from photos
        time_range = extract_photo_time_range(photo_files)
        if not time_range:
            return []
        
        # Expand time range by 24 hours on each side for timezone handling
        start_time, end_time = time_range
        expanded_start = start_time - datetime.timedelta(hours=24)
        expanded_end = end_time + datetime.timedelta(hours=24)
        expanded_range = (expanded_start, expanded_end)
        
        # Filter locations within time range
        filtered_locations = filter_locations_by_time_range(location_data, expanded_range)
        
        # Process each photo
        photo_gps_data = []
        total_photos = len(photo_files)
        
        for i, file_path in enumerate(photo_files):
            try:
                # Get photo timestamp
                photo_time = get_photo_timestamp(file_path)
                if photo_time:
                    # Find closest location
                    gps_coords = find_closest_location(photo_time, filtered_locations)
                    if gps_coords:
                        photo_gps_data.append({
                            'file_path': file_path,
                            'timestamp': photo_time,
                            'gps': gps_coords,
                            'filename': os.path.basename(file_path)
                        })
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
            
            # Call progress callback if provided
            if progress_callback:
                progress_callback(i + 1, total_photos)
        
        return photo_gps_data
        
    except Exception as e:
        print(f"Error processing location history: {e}")
        return []
