import logging
import sys
import httpx
from mcp.server.fastmcp import FastMCP

# STDIO servers must NEVER print to stdout, so all logs go to stderr
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
log = logging.getLogger("meals")

mcp = FastMCP("meals")
BASE = "https://www.themealdb.com/api/json/v1/1"


def _get(path: str, params: dict) -> dict:
    """Call TheMealDB. Network or JSON problems raise a clean error."""
    try:
        r = httpx.get(f"{BASE}/{path}", params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPError as e:
        log.error("network error: %s", e)
        raise RuntimeError(f"TheMealDB request failed: {e}")
    except ValueError as e:
        raise RuntimeError(f"TheMealDB returned invalid JSON: {e}")


def _full(m: dict) -> dict:
    """Turn raw TheMealDB meal into the meal_details shape."""
    ingredients = []
    for i in range(1, 21):
        name = (m.get(f"strIngredient{i}") or "").strip()
        if name:
            ingredients.append({"name": name, "measure": (m.get(f"strMeasure{i}") or "").strip()})
    return {
        "id": m["idMeal"], "name": m["strMeal"], "category": m["strCategory"],
        "area": m["strArea"], "instructions": m["strInstructions"],
        "image": m["strMealThumb"], "source": m.get("strSource"),
        "youtube": m.get("strYoutube"), "ingredients": ingredients,
    }


@mcp.tool()
def search_meals_by_name(query: str, limit: int = 5) -> dict:
    """Search meals by name. limit is 1-25."""
    limit = max(1, min(25, limit))
    meals = _get("search.php", {"s": query}).get("meals")
    if not meals:
        return {"results": [], "message": "no matches"}
    return {"results": [
        {"id": m["idMeal"], "name": m["strMeal"], "area": m["strArea"],
         "category": m["strCategory"], "thumb": m["strMealThumb"]}
        for m in meals[:limit]]}


@mcp.tool()
def meals_by_ingredient(ingredient: str, limit: int = 12) -> dict:
    """List meals that use a main ingredient."""
    limit = max(1, min(50, limit))
    meals = _get("filter.php", {"i": ingredient}).get("meals")
    if not meals:
        return {"results": [], "message": "no matches"}
    return {"results": [
        {"id": m["idMeal"], "name": m["strMeal"], "thumb": m["strMealThumb"]}
        for m in meals[:limit]]}


@mcp.tool()
def random_meal() -> dict:
    """Return one random meal with full details."""
    meals = _get("random.php", {}).get("meals")
    if not meals:
        return {"message": "no matches"}
    return _full(meals[0])


@mcp.tool()
def meal_details(id: str) -> dict:
    """Return full recipe details for a meal id."""
    meals = _get("lookup.php", {"i": str(id)}).get("meals")
    if not meals:
        return {"message": "no matches"}
    return _full(meals[0])


if __name__ == "__main__":
    mcp.run()  # STDIO transport