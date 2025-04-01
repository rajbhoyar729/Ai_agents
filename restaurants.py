import json
import logging
from typing import List, Optional, Dict, Any, Union # Ensure Union is imported

from pydantic import BaseModel, Field, validator, ValidationError

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Data Model Definition ---

class Restaurant(BaseModel):
    """
    Represents a single restaurant location with its details.
    Uses Pydantic for data validation and clear schema definition.
    """
    id: str = Field(..., description="Unique identifier for the restaurant (e.g., 'del001')")
    name: str = Field(..., description="Name of the restaurant")
    location: str = Field(..., description="Area or neighborhood in Delhi (e.g., 'Connaught Place', 'Khan Market')")
    cuisine: str = Field(..., description="Primary type of cuisine served (e.g., 'North Indian', 'Mughlai', 'Italian')")
    # Using a Dict for opening hours for flexibility
    opening_hours: Dict[str, str] = Field(..., description="Dictionary of day -> hours string (e.g., {'Daily': '12pm-1am'})")
    max_capacity: int = Field(..., gt=0, description="Estimated maximum seating capacity")
    address: str = Field(..., description="General address or landmark")
    phone: Optional[str] = Field(None, description="Contact phone number (may be placeholder)")
    description: Optional[str] = Field(None, description="Brief description of the restaurant's specialty or vibe")

    @validator('id')
    def id_must_be_alphanumeric(cls, v):
        if not v.isalnum():
            raise ValueError('Restaurant ID must be alphanumeric')
        return v.lower() # Ensure consistent casing for IDs

# --- Data Repository ---

class RestaurantRepository:
    """
    Manages the collection of restaurant data.
    Provides methods to access and search restaurant information.
    Acts as an in-memory database for this application.
    """
    _instance = None # Singleton pattern

    def __new__(cls, data_source: Optional[Union[str, List[Dict[str, Any]]]] = None):
        # Implement Singleton pattern
        if cls._instance is None:
            cls._instance = super(RestaurantRepository, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, data_source: Optional[Union[str, List[Dict[str, Any]]]] = None):
        """
        Initializes the repository, loading data from a source.

        Args:
            data_source (Optional[Union[str, List[Dict[str, Any]]]]):
                - File path to a JSON file.
                - List of restaurant dictionaries.
                - None (uses default hardcoded Delhi data).
        """
        if self._initialized:
            return

        self._restaurants: Dict[str, Restaurant] = {}
        self._load_data(data_source)
        self._initialized = True
        logger.info(f"RestaurantRepository initialized with {len(self._restaurants)} Delhi restaurants.")

    def _load_data(self, data_source: Optional[Union[str, List[Dict[str, Any]]]]):
        """Loads restaurant data from the specified source or uses default data."""
        raw_data = None
        source_type = "default hardcoded" # Default description

        if isinstance(data_source, str):
            source_type = f"file: {data_source}"
            try:
                with open(data_source, 'r', encoding='utf-8') as f: # Added encoding
                    raw_data = json.load(f)
                logger.info(f"Loaded restaurant data from {source_type}")
            except FileNotFoundError:
                logger.error(f"Data source file not found: {data_source}. Using default data.")
                raw_data = self._get_default_data()
            except json.JSONDecodeError:
                logger.error(f"Error decoding JSON from file: {data_source}. Using default data.")
                raw_data = self._get_default_data()
            except Exception as e:
                logger.error(f"Unexpected error loading data from {data_source}: {e}. Using default data.")
                raw_data = self._get_default_data()

        elif isinstance(data_source, list):
            source_type = "provided list"
            raw_data = data_source
            logger.info(f"Loaded restaurant data from {source_type}.")
        else:
            logger.info("No data source provided, using default hardcoded Delhi data.")
            raw_data = self._get_default_data()

        # Validate and store data
        if isinstance(raw_data, list):
            count = 0
            processed_ids = set()
            for i, item in enumerate(raw_data):
                try:
                    # Ensure ID exists before validation
                    item_id = str(item.get('id', f'missing_id_{i}')).lower()
                    if item_id in processed_ids:
                         logger.warning(f"Duplicate restaurant ID '{item_id}' found at index {i}. Skipping.")
                         continue

                    restaurant = Restaurant(**item) # Validate against the Pydantic model
                    self._restaurants[restaurant.id] = restaurant # Use validated ID
                    processed_ids.add(restaurant.id)
                    count += 1
                except ValidationError as e:
                    logger.error(f"Data validation error for item at index {i}: {e}. Skipping item: {item}")
                except Exception as e:
                    logger.error(f"Unexpected error processing item at index {i}: {e}. Item: {item}")
            logger.info(f"Successfully validated and loaded {count} restaurants from {source_type} source.")

        else:
            logger.error(f"Failed to load restaurant data. Raw data from {source_type} was not a list.")


    def get_by_id(self, restaurant_id: str) -> Optional[Restaurant]:
        """Retrieves a single restaurant by its unique ID (case-insensitive)."""
        return self._restaurants.get(restaurant_id.lower())

    def get_all_restaurants(self) -> List[Restaurant]:
        """Returns a list of all loaded restaurant objects."""
        return list(self._restaurants.values())

    def search(self,
               cuisine: Optional[str] = None,
               location: Optional[str] = None,
               min_capacity: Optional[int] = None) -> List[Restaurant]:
        """
        Searches for restaurants based on provided criteria.

        Args:
            cuisine: Filter by cuisine (case-insensitive substring match).
            location: Filter by location (case-insensitive exact match).
            min_capacity: Filter by minimum required seating capacity.

        Returns:
            List[Restaurant]: Matching restaurants.
        """
        results = list(self._restaurants.values())

        try:
            if cuisine:
                results = [r for r in results if cuisine.lower() in r.cuisine.lower()]
            if location:
                 # Allow partial match for location as well for flexibility? Or stick to exact? Let's try partial.
                 # results = [r for r in results if location.lower() == r.location.lower()] # Exact match
                 results = [r for r in results if location.lower() in r.location.lower()] # Partial match
            if min_capacity is not None and min_capacity > 0:
                 results = [r for r in results if r.max_capacity >= min_capacity]
        except Exception as e:
            logger.error(f"Error during search: {e}. Criteria: cuisine='{cuisine}', location='{location}', min_cap={min_capacity}", exc_info=True)
            return [] # Return empty list on error

        logger.info(f"Search found {len(results)} restaurants matching: cuisine='{cuisine}', location='{location}', min_cap={min_capacity}")
        return results

    def get_distinct_cuisines(self) -> List[str]:
        """Returns a sorted list of unique cuisine types available."""
        cuisines = {r.cuisine for r in self._restaurants.values()}
        return sorted(list(cuisines))

    def get_distinct_locations(self) -> List[str]:
        """Returns a sorted list of unique locations available."""
        locations = {r.location for r in self._restaurants.values()}
        return sorted(list(locations))

    def _get_default_data(self) -> List[Dict[str, Any]]:
        """Provides hardcoded sample restaurant data for famous/representative Delhi places."""
        # --- Famous/Representative Delhi Restaurants ---
        return [
            {"id": "del001", "name": "Bukhara", "location": "Chanakyapuri", "cuisine": "North Indian", "opening_hours": {"Daily": "12:30pm-2:45pm, 7pm-11:45pm"}, "max_capacity": 120, "address": "ITC Maurya, Diplomatic Enclave", "phone": "011-26112233", "description": "Legendary for its Dal Bukhara and Tandoori dishes. Rustic ambiance."},
            {"id": "del002", "name": "Indian Accent", "location": "Lodhi Road", "cuisine": "Modern Indian", "opening_hours": {"Daily": "12pm-2:30pm, 7pm-10:30pm"}, "max_capacity": 80, "address": "The Lodhi Hotel", "phone": "011-66175151", "description": "Globally acclaimed inventive Indian cuisine with stunning presentation."},
            {"id": "del003", "name": "Karim's", "location": "Old Delhi", "cuisine": "Mughlai", "opening_hours": {"Daily": "11am-1am"}, "max_capacity": 100, "address": "Near Jama Masjid, Gali Kababian", "phone": "011-23264981", "description": "Historic institution famous for kebabs, biryani, and mutton korma."},
            {"id": "del004", "name": "Varq", "location": "Connaught Place", "cuisine": "Modern Indian", "opening_hours": {"Daily": "12:30pm-2:45pm, 7:30pm-11:30pm"}, "max_capacity": 70, "address": "The Taj Mahal Hotel, Mansingh Road", "phone": "011-66566162", "description": "Fine dining with artistic presentation and unique Indian flavors."},
            {"id": "del005", "name": "Saravana Bhavan", "location": "Connaught Place", "cuisine": "South Indian", "opening_hours": {"Daily": "8am-10:45pm"}, "max_capacity": 150, "address": "P-13, Connaught Circus", "phone": "011-23347755", "description": "Extremely popular chain for authentic South Indian vegetarian food."},
            {"id": "del006", "name": "SodaBottleOpenerWala", "location": "Khan Market", "cuisine": "Parsi", "opening_hours": {"Daily": "12pm-11:30pm"}, "max_capacity": 60, "address": "73, Khan Market", "phone": "011-43504778", "description": "Quirky Bombay-Irani cafe style with delicious Parsi dishes."},
            {"id": "del007", "name": "Olive Bar & Kitchen", "location": "Mehrauli", "cuisine": "Mediterranean", "opening_hours": {"Daily": "12:30pm-12:30am"}, "max_capacity": 100, "address": "Near Qutub Minar, One Style Mile", "phone": "011-29574444", "description": "Beautiful ambiance, known for its Sunday brunch and European food."},
            {"id": "del008", "name": "Dum Pukht", "location": "Chanakyapuri", "cuisine": "Awadhi", "opening_hours": {"Daily": "7pm-11:45pm"}, "max_capacity": 80, "address": "ITC Maurya, Diplomatic Enclave", "phone": "011-26112233", "description": "Refined slow-cooked Awadhi cuisine in a regal setting."},
            {"id": "del009", "name": "Big Chill Cafe", "location": "Khan Market", "cuisine": "Italian", "opening_hours": {"Daily": "12pm-11:30pm"}, "max_capacity": 70, "address": "Multiple locations, 68A Khan Market", "phone": "011-41757533", "description": "Hugely popular cafe known for pasta, pizzas, and decadent desserts."},
            {"id": "del010", "name": "Yeti - The Himalayan Kitchen", "location": "Hauz Khas Village", "cuisine": "Tibetan", "opening_hours": {"Daily": "12pm-11pm"}, "max_capacity": 50, "address": "30, Hauz Khas Village", "phone": "+91-9810986399", "description": "Authentic Tibetan and Himalayan cuisine, known for momos and thukpa."},
            {"id": "del011", "name": "Moti Mahal Delux", "location": "Greater Kailash (GK) 1", "cuisine": "North Indian", "opening_hours": {"Daily": "12pm-12am"}, "max_capacity": 90, "address": "M Block Market, GK 1", "phone": "011-29230111", "description": "Claimed inventors of Butter Chicken, classic North Indian fare."},
            {"id": "del012", "name": "Parikrama - The Revolving Restaurant", "location": "Connaught Place", "cuisine": "Multi-cuisine", "opening_hours": {"Daily": "12:30pm-11:30pm"}, "max_capacity": 100, "address": "Antriksh Bhavan, KG Marg", "phone": "011-23721616", "description": "Offers panoramic views of the city while serving Indian and Chinese food."},
            {"id": "del013", "name": "Gulati Restaurant", "location": "Pandara Road Market", "cuisine": "North Indian", "opening_hours": {"Daily": "12pm-12am"}, "max_capacity": 120, "address": "Pandara Road Market", "phone": "011-23388836", "description": "Famous for its buffet and butter chicken on Pandara Road."},
            {"id": "del014", "name": "Social", "location": "Hauz Khas Village", "cuisine": "Cafe", "opening_hours": {"Daily": "11am-1am"}, "max_capacity": 150, "address": "9A & 12, Hauz Khas Village", "phone": "+91-7838652814", "description": "Popular co-working space and cafe/bar with quirky food and drinks."},
            {"id": "del015", "name": "The Grammar Room", "location": "Mehrauli", "cuisine": "Cafe", "opening_hours": {"Daily": "10am-12am"}, "max_capacity": 60, "address": "One Style Mile, Kalka Das Marg", "phone": "+91-8130688884", "description": "Chic cafe with great coffee, brunch options, and cocktails."},
            {"id": "del016", "name": "Naivedyam", "location": "Hauz Khas Village", "cuisine": "South Indian", "opening_hours": {"Daily": "11am-11pm"}, "max_capacity": 70, "address": "Shop 1, Hauz Khas Village", "phone": "011-26960426", "description": "Authentic South Indian vegetarian thalis and dosas."},
            {"id": "del017", "name": "Artusi Ristorante", "location": "Greater Kailash (GK) 2", "cuisine": "Italian", "opening_hours": {"Daily": "1pm-11:30pm"}, "max_capacity": 50, "address": "M Block Market, GK 2", "phone": "011-49066666", "description": "Authentic Emilia-Romagna cuisine, known for handmade pasta."},
            {"id": "del018", "name": "Punjabi By Nature", "location": "Connaught Place", "cuisine": "North Indian", "opening_hours": {"Daily": "12pm-11:30pm"}, "max_capacity": 100, "address": "Amba Deep Building, KG Marg", "phone": "011-41516666", "description": "Known for large portions, vodka golgappas, and Punjabi classics."},
            {"id": "del019", "name": "Farzi Cafe", "location": "Connaught Place", "cuisine": "Modern Indian", "opening_hours": {"Daily": "12pm-1am"}, "max_capacity": 90, "address": "E Block, Inner Circle", "phone": "+91-9599889700", "description": "Molecular gastronomy and playful twists on Indian street food."},
            {"id": "del020", "name": "Khan Chacha", "location": "Khan Market", "cuisine": "Mughlai", "opening_hours": {"Daily": "12pm-11pm"}, "max_capacity": 40, "address": "Flat 50, Middle Lane, Khan Market", "phone": "011-24633242", "description": "Iconic spot famous for its delicious Kathi Rolls."},
            {"id": "del021", "name": "Jamun", "location": "Lodhi Colony Market", "cuisine": "North Indian", "opening_hours": {"Daily": "12pm-3:30pm, 7pm-12:30am"}, "max_capacity": 70, "address": "17, Main Market, Lodhi Colony", "phone": "+91-9999891002", "description": "Regional Indian dishes in a vibrant, purple-themed setting."},
            {"id": "del022", "name": "Leo's Pizzeria", "location": "Vasant Vihar", "cuisine": "Italian", "opening_hours": {"Tue-Sun": "12:30pm-11pm"}, "max_capacity": 40, "address": "Priya Complex, Vasant Vihar", "phone": "+91-9821277236", "description": "Excellent Neapolitan-style pizzas in a casual setting."},
            {"id": "del023", "name": "Coast Cafe", "location": "Hauz Khas Village", "cuisine": "Coastal Indian", "opening_hours": {"Daily": "12pm-11pm"}, "max_capacity": 60, "address": "H-2, Second Floor, Hauz Khas Village", "phone": "+91-41651850", "description": "Kerala-inspired cuisine with cocktails in a bright, airy space."},
        ]

# --- Singleton Instance ---
# Instantiate the repository using the default Delhi data
RESTAURANT_DATA = RestaurantRepository()

# --- Example Usage (for testing this module directly) ---
if __name__ == "__main__":
    logger.info("--- Testing Restaurant Repository with Delhi Data ---")

    # Test getting by ID
    bukhara = RESTAURANT_DATA.get_by_id("del001")
    if bukhara:
        logger.info(f"Found by ID del001: {bukhara.name} ({bukhara.cuisine} in {bukhara.location})")
    else:
        logger.warning("Did not find del001")

    # Test searching
    logger.info("\n--- Searching for Mughlai restaurants ---")
    mughlai_restaurants = RESTAURANT_DATA.search(cuisine="Mughlai")
    for r in mughlai_restaurants:
        logger.info(f"- {r.name} ({r.location}) - ID: {r.id}")

    logger.info("\n--- Searching for cafes in Khan Market ---")
    khan_market_cafes = RESTAURANT_DATA.search(location="Khan Market", cuisine="Cafe")
    for r in khan_market_cafes:
        logger.info(f"- {r.name} - ID: {r.id}") # Should find Social

    logger.info("\n--- Searching for restaurants in Chanakyapuri for at least 75 people ---")
    chanakya_large = RESTAURANT_DATA.search(location="Chanakyapuri", min_capacity=75)
    for r in chanakya_large:
        logger.info(f"- {r.name} (Capacity: {r.max_capacity}) - ID: {r.id}")

    logger.info("\n--- Getting distinct cuisines ---")
    cuisines = RESTAURANT_DATA.get_distinct_cuisines()
    logger.info(cuisines)

    logger.info("\n--- Getting distinct locations ---")
    locations = RESTAURANT_DATA.get_distinct_locations()
    logger.info(locations)