# ============================================================
# MANUAL TESTING WITH CURL
# Start the server first: python project2.py server
# Then run these in another terminal
# ============================================================

# --- Discovery ---
curl -s http://127.0.0.1:8080/api/v1 | python -m json.tool

# --- Health ---
curl -s http://127.0.0.1:8080/api/v1/health | python -m json.tool

# --- List all menu items ---
curl -s http://127.0.0.1:8080/api/v1/menu-items | python -m json.tool

# --- Filter: only pizzas ---
curl -s "http://127.0.0.1:8080/api/v1/menu-items?category=pizza" | python -m json.tool

# --- Filter: price range + sort ---
curl -s "http://127.0.0.1:8080/api/v1/menu-items?min_price=10&max_price=15&sort=price&order=desc" | python -m json.tool

# --- Pagination ---
curl -s "http://127.0.0.1:8080/api/v1/menu-items?page=1&limit=3" | python -m json.tool

# --- Get single item ---
curl -s http://127.0.0.1:8080/api/v1/menu-items/1 | python -m json.tool

# --- Create new item (POST) ---
curl -s -X POST http://127.0.0.1:8080/api/v1/menu-items \
  -H "Content-Type: application/json" \
  -d '{"name":"Fish Tacos","category":"appetizer","price":10.99,"available":true}' \
  | python -m json.tool

# --- Partial update (PATCH) ---
curl -s -X PATCH http://127.0.0.1:8080/api/v1/menu-items/1 \
  -H "Content-Type: application/json" \
  -d '{"price":14.99}' \
  | python -m json.tool

# --- Full replace (PUT) ---
curl -s -X PUT http://127.0.0.1:8080/api/v1/menu-items/1 \
  -H "Content-Type: application/json" \
  -d '{"name":"Classic Margherita","category":"pizza","price":13.99,"available":true,"prep_time_mins":14}' \
  | python -m json.tool

# --- Delete item ---
curl -s -X DELETE http://127.0.0.1:8080/api/v1/menu-items/8 -w "\nHTTP Status: %{http_code}\n"

# --- Place order (POST) ---
curl -s -X POST http://127.0.0.1:8080/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{"customer_name":"Test User","items":[{"item_id":1,"quantity":2},{"item_id":3,"quantity":1}]}' \
  | python -m json.tool

# --- Update order status (PATCH) ---
curl -s -X PATCH http://127.0.0.1:8080/api/v1/orders/1 \
  -H "Content-Type: application/json" \
  -d '{"status":"preparing"}' \
  | python -m json.tool

# --- Test error: invalid pizza ---
curl -s -X POST http://127.0.0.1:8080/api/v1/menu-items \
  -H "Content-Type: application/json" \
  -d '{"name":"","price":-5,"category":"alien_food"}' \
  | python -m json.tool

# --- Test error: bad order transition ---
curl -s -X PATCH http://127.0.0.1:8080/api/v1/orders/1 \
  -H "Content-Type: application/json" \
  -d '{"status":"delivered"}' \
  | python -m json.tool