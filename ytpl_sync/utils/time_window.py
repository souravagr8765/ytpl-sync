from typing import Optional
import datetime

class TimeWindowError(Exception):
    pass

def is_within_time_window(window: Optional[str]) -> bool:
    if window is None:
        return True
        
    try:
        start_str, end_str = window.split('-')
        start_time = datetime.datetime.strptime(start_str.strip(), "%H:%M").time()
        end_time = datetime.datetime.strptime(end_str.strip(), "%H:%M").time()
    except ValueError:
        raise ValueError(f"Invalid time window format: '{window}'. Expected 'HH:MM-HH:MM'.")
        
    now = datetime.datetime.now().time()
    
    if end_time < start_time:
        return now >= start_time or now <= end_time
    else:
        return start_time <= now <= end_time

def assert_time_window(window: Optional[str]) -> None:
    if not is_within_time_window(window):
        raise TimeWindowError(f"Outside configured run window {window}, exiting.")
