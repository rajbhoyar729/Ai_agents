import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import json
import random
import string

# Import the data access layer
from restaurants import RESTAURANT_DATA, Restaurant

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants for better maintainability
PEAK_HOUR_START = 19  # 7 PM in 24-hour format
PEAK_HOUR_END = 21    # 9 PM in 24-hour format
WEEKEND_DAYS = {4, 5} # Friday (4), Saturday (5) in weekday()

def validate_date_time(date: str, time: str) -> tuple[bool, str]:
    """
    Validates date (YYYY-MM-DD) and time (e.g., '7:00 PM') formats.
    Returns: (is_valid, error_message_if_invalid)
    """
    try:
        parsed_date = datetime.strptime(date, "%Y-%m-%d")
        parsed_time = datetime.strptime(time, "%I:%M %p")  # Handles 12-hour AM/PM
        return True, ""
    except ValueError as e:
        logger.warning(f"Invalid date/time format: date={date}, time={time}. Error: {e}")
        return False, f"Please provide date as YYYY-MM-DD and time as 'H:MM AM/PM' (e.g., '7:00 PM'). Error: {e}"

def find_restaurants(
    cuisine: Optional[str] = None,
    location: Optional[str] = None,
    party_size: Optional[int] = None,
    date: Optional[str] = None,
    time: Optional[str] = None
) -> Dict[str, Union[str, List[Dict[str, str]]]]:
    """
    Finds restaurants matching user criteria with ranked results and alternatives.

    Args:
        cuisine: Type of cuisine (e.g., "Italian").
        location: Area in Delhi (e.g., "Connaught Place").
        party_size: Number of people.
        date: Reservation date (YYYY-MM-DD).
        time: Reservation time (e.g., "7:00 PM").

    Returns:
        Dict with 'status' ('success', 'not_found', 'error'), 'results' (list of restaurant info),
        and 'message' (user-friendly feedback).
    """
    logger.info(f"find_restaurants called: cuisine={cuisine}, location={location}, party_size={party_size}, date={date}, time={time}")

    # Validate party size
    if party_size is not None:
        try:
            party_size = int(party_size)
            if party_size <= 0:
                raise ValueError("Party size must be positive")
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid party_size: {party_size}. Error: {e}")
            return {"status": "error", "message": f"Party size must be a positive number. You provided: {party_size}"}

    # Validate date and time if provided
    if date and time:
        is_valid, error_msg = validate_date_time(date, time)
        if not is_valid:
            return {"status": "error", "message": error_msg}

    try:
        # Search with sorting by capacity (largest first) for better recommendations
        results: List[Restaurant] = RESTAURANT_DATA.search(
            cuisine=cuisine,
            location=location,
            min_capacity=party_size,
            sort_by="capacity"
        )

        if results:
            # Format results for user-friendly output
            formatted_results = [
                {"id": r.id, "name": r.name, "cuisine": r.cuisine, "location": r.location}
                for r in results[:5]  # Limit to top 5 for simplicity
            ]
            message = f"Found {len(results)} matching restaurants! Here are some options: {', '.join(r['name'] for r in formatted_results)}."
            logger.info(message)
            return {"status": "success", "results": formatted_results, "message": message}
        else:
            # Suggest alternatives if no exact matches
            alternatives = RESTAURANT_DATA.search(min_capacity=party_size)
            if alternatives:
                alt_names = ", ".join(r.name for r in alternatives[:2])
                message = f"No exact matches for {cuisine or 'any cuisine'} in {location or 'any location'}. Try these: {alt_names}."
                logger.info(message)
                return {"status": "not_found", "results": [], "message": message}
            else:
                message = "Sorry, no restaurants match your criteria right now."
                logger.info(message)
                return {"status": "not_found", "results": [], "message": message}

    except Exception as e:
        logger.exception(f"Error in find_restaurants: {e}")
        return {"status": "error", "message": "An unexpected error occurred while searching. Please try again."}

def check_availability(
    restaurant_id: str,
    party_size: int,
    date: str,
    time: str
) -> Dict[str, str]:
    """
    Checks table availability with realistic simulation and user-friendly feedback.

    Args:
        restaurant_id: Unique restaurant ID.
        party_size: Number of people.
        date: Reservation date (YYYY-MM-DD).
        time: Reservation time (e.g., "7:00 PM").

    Returns:
        Dict with 'status' ('available', 'limited', 'unavailable', 'error') and 'message'.
    """
    logger.info(f"check_availability called: restaurant_id={restaurant_id}, party_size={party_size}, date={date}, time={time}")

    # Input validation
    try:
        party_size = int(party_size)
        if party_size <= 0:
            raise ValueError("Party size must be positive")
    except (ValueError, TypeError) as e:
        return {"status": "error", "message": f"Party size must be a positive number. You provided: {party_size}"}

    is_valid, error_msg = validate_date_time(date, time)
    if not is_valid:
        return {"status": "error", "message": error_msg}

    try:
        restaurant = RESTAURANT_DATA.get_by_id(restaurant_id)
        if not restaurant:
            return {"status": "error", "message": f"No restaurant found with ID '{restaurant_id}'."}

        # Capacity check
        if party_size > restaurant.max_capacity:
            message = f"Sorry, {restaurant.name} can’t accommodate {party_size} people (max capacity: {restaurant.max_capacity})."
            logger.info(message)
            return {"status": "unavailable", "message": message}

        # Peak time simulation
        parsed_date = datetime.strptime(date, "%Y-%m-%d")
        parsed_time = datetime.strptime(time, "%I:%M %p")
        hour = parsed_time.hour

        is_peak = (
            parsed_date.weekday() in WEEKEND_DAYS and
            PEAK_HOUR_START <= hour < PEAK_HOUR_END
        )

        if is_peak and (party_size / restaurant.max_capacity) > 0.7:
            message = f"Limited availability at {restaurant.name} for {party_size} on {date} at {time}. Earlier or later times might work better."
            logger.info(message)
            return {"status": "limited", "message": message}

        message = f"Good news! {restaurant.name} has a table for {party_size} on {date} at {time}."
        logger.info(message)
        return {"status": "available", "message": message}

    except Exception as e:
        logger.exception(f"Error in check_availability: {e}")
        return {"status": "error", "message": "An unexpected error occurred while checking availability."}

def make_reservation(
    restaurant_id: str,
    party_size: int,
    date: str,
    time: str,
    user_name: str,
    user_contact: str
) -> Dict[str, str]:
    """
    Makes a reservation with upselling and detailed confirmation.

    Args:
        restaurant_id: Unique restaurant ID.
        party_size: Number of people.
        date: Reservation date (YYYY-MM-DD).
        time: Reservation time (e.g., "7:00 PM").
        user_name: Customer’s name.
        user_contact: Contact info (e.g., phone/email).

    Returns:
        Dict with 'status' ('success', 'failed'), 'message', and 'confirmation_id' (if success).
    """
    logger.info(f"make_reservation called: restaurant_id={restaurant_id}, party_size={party_size}, date={date}, time={time}, user_name={user_name}")

    # Input validation
    try:
        party_size = int(party_size)
        if party_size <= 0:
            raise ValueError("Party size must be positive")
    except (ValueError, TypeError) as e:
        return {"status": "failed", "message": f"Party size must be a positive number. You provided: {party_size}"}

    if not user_name or not user_contact:
        return {"status": "failed", "message": "Please provide both your name and contact details."}

    is_valid, error_msg = validate_date_time(date, time)
    if not is_valid:
        return {"status": "failed", "message": error_msg}

    # Check availability first
    avail_result = check_availability(restaurant_id, party_size, date, time)
    if avail_result["status"] not in ["available", "limited"]:
        return {"status": "failed", "message": f"Cannot book: {avail_result['message']}"}

    try:
        restaurant = RESTAURANT_DATA.get_by_id(restaurant_id)
        confirmation_id = f"FS-{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}"
        
        # Upselling opportunity
        premium_msg = " Want a premium table with a view for an extra fee? Reply 'yes' to upgrade!"
        message = (
            f"Reservation confirmed for {user_name} at {restaurant.name}!\n"
            f"- Party Size: {party_size}\n"
            f"- Date: {date}\n"
            f"- Time: {time}\n"
            f"- Confirmation ID: {confirmation_id}\n"
            f"We’ll see you soon!{premium_msg if avail_result['status'] == 'available' else ''}"
        )
        logger.info(f"Reservation successful: {confirmation_id}")
        return {"status": "success", "message": message, "confirmation_id": confirmation_id}

    except Exception as e:
        logger.exception(f"Error in make_reservation: {e}")
        return {"status": "failed", "message": "An unexpected error occurred while booking."}

def get_restaurant_details(restaurant_id: str) -> Dict[str, Union[str, Dict[str, Any]]]:
    """
    Retrieves detailed restaurant info for users.

    Args:
        restaurant_id: Unique restaurant ID.

    Returns:
        Dict with 'status' ('success', 'not_found', 'error'), 'details', and 'message'.
    """
    logger.info(f"get_restaurant_details called: restaurant_id={restaurant_id}")

    try:
        restaurant = RESTAURANT_DATA.get_by_id(restaurant_id)
        if restaurant:
            details = {
                "id": restaurant.id,
                "name": restaurant.name,
                "location": restaurant.location,
                "cuisine": restaurant.cuisine,
                "opening_hours": restaurant.opening_hours,
                "capacity": restaurant.max_capacity,
                "address": restaurant.address,
                "phone": restaurant.phone or "Not available",
                "description": restaurant.description or "No description available"
            }
            message = f"Here’s what I found about {restaurant.name} in {restaurant.location}."
            logger.info(message)
            return {"status": "success", "details": details, "message": message}
        else:
            message = f"Sorry, I couldn’t find details for restaurant ID '{restaurant_id}'."
            logger.warning(message)
            return {"status": "not_found", "details": {}, "message": message}

    except Exception as e:
        logger.exception(f"Error in get_restaurant_details: {e}")
        return {"status": "error", "details": {}, "message": "An unexpected error occurred while fetching details."}

# Tool Registry for main.py Access
AVAILABLE_TOOLS = {
    "find_restaurants": find_restaurants,
    "check_availability": check_availability,
    "make_reservation": make_reservation,
    "get_restaurant_details": get_restaurant_details
}