import logging
import random
import string
from typing import List, Dict, Optional, Any, Union

# Import the data access layer and the data model
from restaurants import RESTAURANT_DATA, Restaurant

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Tool Implementation Functions ---

def find_restaurants(cuisine: Optional[str] = None,
                     location: Optional[str] = None,
                     party_size: Optional[int] = None,
                     date: Optional[str] = None, # Included for context, not direct filtering here
                     time: Optional[str] = None  # Included for context, not direct filtering here
                     ) -> Dict[str, Union[str, List[Dict[str, str]]]]:
    """
    Finds restaurants based on cuisine, location, and minimum capacity (derived from party_size).

    Args:
        cuisine: The type of cuisine (e.g., "Italian").
        location: The area/neighborhood (e.g., "Downtown").
        party_size: The number of people needing seating.
        date: The desired date (for context, currently not used in filtering).
        time: The desired time (for context, currently not used in filtering).

    Returns:
        A dictionary containing:
        - 'status': 'success' or 'not_found'.
        - 'results': A list of {'id': str, 'name': str} dictionaries for matching restaurants,
                     or an empty list if none found.
    """
    logger.info(f"Executing find_restaurants: cuisine='{cuisine}', location='{location}', party_size={party_size}, date='{date}', time='{time}'")

    # Basic validation (LLM should provide valid types, but good practice)
    min_capacity = None
    if party_size is not None:
        try:
            min_capacity = int(party_size)
            if min_capacity <= 0:
                 logger.warning("Party size must be positive.")
                 min_capacity = 1 # Default to 1 if invalid non-positive provided
        except (ValueError, TypeError):
            logger.warning(f"Invalid party_size '{party_size}', ignoring capacity filter.")
            min_capacity = None # Ignore capacity filter if type is wrong

    try:
        # Use the search method from the repository
        matching_restaurants: List[Restaurant] = RESTAURANT_DATA.search(
            cuisine=cuisine,
            location=location,
            min_capacity=min_capacity
        )

        # Format the results as required by the system prompt description
        results_list = [{"id": r.id, "name": r.name} for r in matching_restaurants]

        if results_list:
            logger.info(f"Found {len(results_list)} matching restaurants.")
            return {"status": "success", "results": results_list}
        else:
            logger.info("No restaurants found matching the criteria.")
            return {"status": "not_found", "results": []}

    except Exception as e:
        logger.exception("An unexpected error occurred during find_restaurants", exc_info=True)
        return {"status": "error", "message": "An internal error occurred while searching for restaurants."}


def check_availability(restaurant_id: str,
                       party_size: int,
                       date: str,
                       time: str) -> Dict[str, str]:
    """
    Checks simulated availability for a given restaurant, party size, date, and time.

    Args:
        restaurant_id: The unique ID of the restaurant.
        party_size: The number of people.
        date: The desired date (YYYY-MM-DD).
        time: The desired time (e.g., "7:00 PM").

    Returns:
        A dictionary containing:
        - 'status': 'available', 'unavailable', 'limited', or 'error'.
        - 'message': A descriptive note about the availability or error.
    """
    logger.info(f"Executing check_availability: restaurant_id='{restaurant_id}', party_size={party_size}, date='{date}', time='{time}'")

    try:
        restaurant = RESTAURANT_DATA.get_by_id(restaurant_id)
        if not restaurant:
            logger.warning(f"Restaurant ID '{restaurant_id}' not found.")
            return {"status": "error", "message": f"Restaurant with ID '{restaurant_id}' could not be found."}

        party_size_int = int(party_size) # Ensure integer
        if party_size_int <= 0:
             return {"status": "error", "message": "Party size must be greater than zero."}

        # --- Simulation Logic ---
        # 1. Capacity Check
        if party_size_int > restaurant.max_capacity:
            logger.info(f"Availability check failed: party size {party_size_int} exceeds max capacity {restaurant.max_capacity} for {restaurant_id}.")
            return {"status": "unavailable", "message": f"Sorry, the requested party size ({party_size_int}) exceeds the maximum capacity ({restaurant.max_capacity}) for {restaurant.name}."}

        # 2. Simple "Busy Times" Simulation (Example)
        #    Let's make Friday/Saturday 7 PM - 9 PM "limited" if close to capacity
        #    This is highly simplified!
        is_peak_time = False
        try:
            # Basic check - needs more robust date/time parsing in a real app
            from datetime import datetime
            parsed_date = datetime.strptime(date, "%Y-%m-%d")
            # Simple time check (assumes HH:MM AM/PM or HH:MM format)
            hour = -1
            time_lower = time.lower()
            if "pm" in time_lower and ":" in time_lower:
                 hour_str = time_lower.split(":")[0]
                 hour = int(hour_str) + 12 if hour_str != "12" else 12 # Basic PM conversion
            elif "am" in time_lower and ":" in time_lower:
                 hour_str = time_lower.split(":")[0]
                 hour = int(hour_str) if hour_str != "12" else 0 # Basic AM conversion
            elif ":" in time_lower: # Assume 24hr if no AM/PM
                hour = int(time_lower.split(":")[0])


            # Friday is 4, Saturday is 5 in weekday() (Monday is 0)
            if parsed_date.weekday() in [4, 5] and 19 <= hour < 21: # 7 PM to 8:59 PM
                 is_peak_time = True
        except ValueError:
            logger.warning(f"Could not parse date '{date}' or time '{time}' for peak time check. Assuming not peak.")
        except Exception:
             logger.warning(f"Error during peak time check logic for date '{date}', time '{time}'. Assuming not peak.")


        if is_peak_time and (party_size_int / restaurant.max_capacity) > 0.7: # If >70% capacity during peak
            logger.info(f"Limited availability for {restaurant_id} at peak time {date} {time} due to capacity usage.")
            return {"status": "limited", "message": f"There is limited availability for {party_size_int} guests at {restaurant.name} around {time} on {date}. We might have slightly earlier or later slots."}

        # 3. Default: Available
        logger.info(f"Availability check successful for {restaurant_id} at {date} {time}.")
        return {"status": "available", "message": f"Table for {party_size_int} at {restaurant.name} on {date} at {time} appears to be available."}

    except (ValueError, TypeError) as e:
        logger.error(f"Invalid input type for check_availability: {e}")
        return {"status": "error", "message": "Invalid input provided for checking availability (e.g., party size should be a number)."}
    except Exception as e:
        logger.exception("An unexpected error occurred during check_availability", exc_info=True)
        return {"status": "error", "message": "An internal error occurred while checking availability."}


def make_reservation(restaurant_id: str,
                     party_size: int,
                     date: str,
                     time: str,
                     user_name: str,
                     user_contact: str) -> Dict[str, str]:
    """
    Simulates making a reservation after checking availability.

    Args:
        restaurant_id: The unique ID of the restaurant.
        party_size: The number of people.
        date: The reservation date (YYYY-MM-DD).
        time: The reservation time.
        user_name: Name for the reservation.
        user_contact: Contact info (phone/email).

    Returns:
        A dictionary containing:
        - 'status': 'success' or 'failed'.
        - 'message': Confirmation details or failure reason.
        - 'confirmation_id' (optional): A unique ID if successful.
    """
    logger.info(f"Executing make_reservation: restaurant_id='{restaurant_id}', party_size={party_size}, date='{date}', time='{time}', name='{user_name}'")

    # 1. Re-check availability using the same logic
    availability_result = check_availability(restaurant_id, party_size, date, time)

    if availability_result["status"] not in ["available", "limited"]: # Treat 'limited' as bookable for simulation
        logger.warning(f"Reservation failed for {restaurant_id}: Availability status was {availability_result['status']}.")
        return {"status": "failed", "message": f"Reservation failed. Reason: {availability_result['message']}"}

    # 2. Simulate booking success (we are not storing it persistently)
    try:
        restaurant = RESTAURANT_DATA.get_by_id(restaurant_id) # Assumed to exist from check
        confirmation_id = "FS" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
        success_message = (
            f"Reservation confirmed for {user_name}! Details:\n"
            f"- Restaurant: {restaurant.name} ({restaurant_id})\n"
            f"- Party Size: {party_size}\n"
            f"- Date: {date}\n"
            f"- Time: {time}\n"
            f"- Confirmation ID: {confirmation_id}\n"
            f"We look forward to seeing you!"
        )
        logger.info(f"Reservation simulation successful for {restaurant_id}. Confirmation: {confirmation_id}")
        return {"status": "success", "message": success_message, "confirmation_id": confirmation_id}

    except Exception as e:
        logger.exception("An unexpected error occurred during make_reservation simulation", exc_info=True)
        return {"status": "failed", "message": "An internal error occurred while trying to make the reservation."}


def get_restaurant_details(restaurant_id: str) -> Dict[str, Union[str, Dict[str, Any]]]:
    """
    Retrieves detailed information for a specific restaurant.

    Args:
        restaurant_id: The unique ID of the restaurant.

    Returns:
        A dictionary containing:
        - 'status': 'success' or 'not_found' or 'error'.
        - 'details': A dictionary of restaurant details if found, else None.
        - 'message': An error message if status is 'error' or 'not_found'.
    """
    logger.info(f"Executing get_restaurant_details: restaurant_id='{restaurant_id}'")
    try:
        restaurant = RESTAURANT_DATA.get_by_id(restaurant_id)

        if restaurant:
            logger.info(f"Details found for restaurant ID '{restaurant_id}'.")
            # Use .model_dump() for Pydantic v2 or .dict() for Pydantic v1
            details_dict = restaurant.model_dump() if hasattr(restaurant, 'model_dump') else restaurant.dict()
            return {"status": "success", "details": details_dict}
        else:
            logger.warning(f"Restaurant ID '{restaurant_id}' not found.")
            return {"status": "not_found", "details": None, "message": f"Sorry, I couldn't find any details for a restaurant with ID '{restaurant_id}'."}
    except Exception as e:
        logger.exception("An unexpected error occurred during get_restaurant_details", exc_info=True)
        return {"status": "error", "details": None, "message": "An internal error occurred while retrieving restaurant details."}


# --- Tool Dispatcher ---
# Maps tool names (as expected by the LLM) to the actual functions
AVAILABLE_TOOLS = {
    "find_restaurants": find_restaurants,
    "check_availability": check_availability,
    "make_reservation": make_reservation,
    "get_restaurant_details": get_restaurant_details,
}

# --- Example Usage (for testing this module directly) ---
if __name__ == "__main__":
    print("--- Testing Tools ---")

    # Test find_restaurants
    print("\n[Test] Finding Italian restaurants for 2 people...")
    results = find_restaurants(cuisine="Italian", party_size=2, date="2025-04-10", time="6:00 PM")
    print(json.dumps(results, indent=2))

    print("\n[Test] Finding non-existent cuisine...")
    results = find_restaurants(cuisine="Martian", party_size=4, date="2025-04-10", time="7:00 PM")
    print(json.dumps(results, indent=2))

    # Test get_restaurant_details
    print("\n[Test] Getting details for fs001...")
    details = get_restaurant_details(restaurant_id="fs001")
    print(json.dumps(details, indent=2))

    print("\n[Test] Getting details for non-existent fs999...")
    details = get_restaurant_details(restaurant_id="fs999")
    print(json.dumps(details, indent=2))

    # Test check_availability
    print("\n[Test] Checking availability for fs001 (Pasta Palace, cap 60) for 4 people...")
    avail = check_availability(restaurant_id="fs001", party_size=4, date="2025-04-12", time="7:30 PM") # Assume Sat 7:30 PM is peak
    print(json.dumps(avail, indent=2))

    print("\n[Test] Checking availability for fs001 for 70 people...")
    avail = check_availability(restaurant_id="fs001", party_size=70, date="2025-04-10", time="6:00 PM")
    print(json.dumps(avail, indent=2))

    print("\n[Test] Checking availability for fs001 non-peak...")
    avail = check_availability(restaurant_id="fs001", party_size=50, date="2025-04-10", time="5:00 PM") # Thurs 5pm
    print(json.dumps(avail, indent=2))

    # Test make_reservation
    print("\n[Test] Making reservation for fs005 (Bella Napoli, cap 50) for 2...")
    booking = make_reservation(restaurant_id="fs005", party_size=2, date="2025-04-11", time="8:00 PM", user_name="Test User", user_contact="test@example.com")
    print(json.dumps(booking, indent=2))

    print("\n[Test] Making reservation for fs005 for 60 (should fail)...")
    booking = make_reservation(restaurant_id="fs005", party_size=60, date="2025-04-11", time="8:00 PM", user_name="Test User Large", user_contact="test@example.com")
    print(json.dumps(booking, indent=2))

    # Test tool dispatcher
    print("\n[Test] Accessing tool via dispatcher...")
    tool_name = "find_restaurants"
    if tool_name in AVAILABLE_TOOLS:
        func = AVAILABLE_TOOLS[tool_name]
        print(f"Dispatcher found function: {func.__name__}")
        # Example call through dispatcher (using previous results variable for simplicity)
        # Note: Arguments need to be passed correctly in a real scenario
        # results = func(cuisine="Italian", party_size=2, date="2025-04-10", time="6:00 PM")
        # print(json.dumps(results, indent=2))
    else:
        print(f"Tool '{tool_name}' not found in dispatcher.")