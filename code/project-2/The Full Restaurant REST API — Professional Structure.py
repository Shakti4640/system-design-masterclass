# ============================================================
# PROJECT 2: COMPLETE REST API — THE RESTAURANT CHAIN
# Builds on Project 1's client-server model
# Adds: REST conventions, proper routing, validation,
#       pagination, filtering, error handling, versioning
# ============================================================

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import re
import datetime
import uuid
import urllib.parse
import threading
import time

# ============================================================
# SECTION 1: IN-MEMORY DATA STORE
# (Project 3 will replace this with a real database)
# ============================================================

class DataStore:
    """Simple in-memory store simulating a database"""
    
    def __init__(self):
        self.menu_items = {}
        self.orders = {}
        self.item_counter = 0
        self.order_counter = 0
        self.lock = threading.Lock()
        self._seed_data()
    
    def _seed_data(self):
        """Pre-populate with sample menu items"""
        seed_items = [
            {"name": "Margherita Pizza", "category": "pizza",
             "price": 12.99, "available": True, "prep_time_mins": 15},
            {"name": "Pepperoni Pizza", "category": "pizza",
             "price": 14.99, "available": True, "prep_time_mins": 18},
            {"name": "Caesar Salad", "category": "salad",
             "price": 8.99, "available": True, "prep_time_mins": 5},
            {"name": "Garlic Bread", "category": "appetizer",
             "price": 5.99, "available": True, "prep_time_mins": 8},
            {"name": "Tiramisu", "category": "dessert",
             "price": 7.99, "available": False, "prep_time_mins": 0},
            {"name": "Veggie Burger", "category": "burger",
             "price": 11.99, "available": True, "prep_time_mins": 12},
            {"name": "Chicken Wings", "category": "appetizer",
             "price": 9.99, "available": True, "prep_time_mins": 20},
            {"name": "Pasta Carbonara", "category": "pasta",
             "price": 13.99, "available": True, "prep_time_mins": 16},
        ]
        for item_data in seed_items:
            self.create_item(item_data)
    
    def next_item_id(self):
        with self.lock:
            self.item_counter += 1
            return self.item_counter
    
    def next_order_id(self):
        with self.lock:
            self.order_counter += 1
            return self.order_counter
    
    def create_item(self, data):
        item_id = self.next_item_id()
        now = datetime.datetime.now().isoformat()
        item = {
            "id": item_id,
            "name": data["name"],
            "category": data.get("category", "uncategorized"),
            "price": data["price"],
            "available": data.get("available", True),
            "prep_time_mins": data.get("prep_time_mins", 10),
            "created_at": now,
            "updated_at": now
        }
        self.menu_items[item_id] = item
        return item
    
    def get_item(self, item_id):
        return self.menu_items.get(item_id)
    
    def list_items(self, filters=None, page=1, limit=10, sort_by="id",
                   sort_order="asc"):
        items = list(self.menu_items.values())
        
        # Apply filters
        if filters:
            if "category" in filters:
                items = [i for i in items
                         if i["category"] == filters["category"]]
            if "available" in filters:
                avail = filters["available"].lower() == "true"
                items = [i for i in items if i["available"] == avail]
            if "min_price" in filters:
                items = [i for i in items
                         if i["price"] >= float(filters["min_price"])]
            if "max_price" in filters:
                items = [i for i in items
                         if i["price"] <= float(filters["max_price"])]
            if "search" in filters:
                term = filters["search"].lower()
                items = [i for i in items
                         if term in i["name"].lower()]
        
        # Sort
        reverse = sort_order.lower() == "desc"
        if sort_by in ("id", "name", "price", "category"):
            items.sort(key=lambda x: x.get(sort_by, ""), reverse=reverse)
        
        # Pagination
        total = len(items)
        start = (page - 1) * limit
        end = start + limit
        paginated = items[start:end]
        
        return {
            "items": paginated,
            "pagination": {
                "total": total,
                "page": page,
                "limit": limit,
                "total_pages": max(1, -(-total // limit)),  # Ceiling div
                "has_next": end < total,
                "has_prev": page > 1
            }
        }
    
    def update_item(self, item_id, data, partial=True):
        item = self.menu_items.get(item_id)
        if not item:
            return None
        
        if partial:
            # PATCH: update only provided fields
            for key, value in data.items():
                if key in ("name", "category", "price", "available",
                           "prep_time_mins"):
                    item[key] = value
        else:
            # PUT: replace entire resource (keep id and timestamps)
            item["name"] = data.get("name", "")
            item["category"] = data.get("category", "uncategorized")
            item["price"] = data.get("price", 0)
            item["available"] = data.get("available", True)
            item["prep_time_mins"] = data.get("prep_time_mins", 10)
        
        item["updated_at"] = datetime.datetime.now().isoformat()
        return item
    
    def delete_item(self, item_id):
        if item_id in self.menu_items:
            del self.menu_items[item_id]
            return True
        return False
    
    def create_order(self, data):
        order_id = self.next_order_id()
        now = datetime.datetime.now().isoformat()
        
        # Calculate total
        total = 0
        order_items = []
        for entry in data.get("items", []):
            item = self.menu_items.get(entry["item_id"])
            if item:
                line_total = item["price"] * entry.get("quantity", 1)
                total += line_total
                order_items.append({
                    "item_id": item["id"],
                    "name": item["name"],
                    "quantity": entry.get("quantity", 1),
                    "unit_price": item["price"],
                    "line_total": round(line_total, 2)
                })
        
        order = {
            "id": order_id,
            "customer_name": data.get("customer_name", "Anonymous"),
            "items": order_items,
            "total_price": round(total, 2),
            "status": "received",
            "notes": data.get("notes", ""),
            "created_at": now,
            "updated_at": now
        }
        self.orders[order_id] = order
        return order
    
    def get_order(self, order_id):
        return self.orders.get(order_id)
    
    def list_orders(self, filters=None, page=1, limit=10):
        orders = list(self.orders.values())
        
        if filters:
            if "status" in filters:
                orders = [o for o in orders
                          if o["status"] == filters["status"]]
        
        total = len(orders)
        start = (page - 1) * limit
        end = start + limit
        
        return {
            "orders": orders[start:end],
            "pagination": {
                "total": total,
                "page": page,
                "limit": limit,
                "total_pages": max(1, -(-total // limit)),
                "has_next": end < total,
                "has_prev": page > 1
            }
        }
    
    def update_order_status(self, order_id, new_status):
        order = self.orders.get(order_id)
        if not order:
            return None
        
        valid_transitions = {
            "received": ["preparing", "cancelled"],
            "preparing": ["ready", "cancelled"],
            "ready": ["delivered"],
            "delivered": [],
            "cancelled": []
        }
        
        current = order["status"]
        if new_status not in valid_transitions.get(current, []):
            return {
                "error": True,
                "message": f"Cannot transition from '{current}' to "
                           f"'{new_status}'",
                "valid_transitions": valid_transitions.get(current, [])
            }
        
        order["status"] = new_status
        order["updated_at"] = datetime.datetime.now().isoformat()
        return order


# Global data store instance
db = DataStore()


# ============================================================
# SECTION 2: VALIDATION ENGINE
# ============================================================

class Validator:
    """Centralized input validation"""
    
    @staticmethod
    def validate_menu_item(data, partial=False):
        errors = []
        
        if not partial or "name" in data:
            name = data.get("name", "")
            if not name or not isinstance(name, str):
                errors.append({
                    "field": "name",
                    "issue": "is required and must be a non-empty string"
                })
            elif len(name) > 100:
                errors.append({
                    "field": "name",
                    "issue": "must be 100 characters or fewer"
                })
        
        if not partial or "price" in data:
            price = data.get("price")
            if price is None:
                if not partial:
                    errors.append({
                        "field": "price",
                        "issue": "is required"
                    })
            elif not isinstance(price, (int, float)) or price < 0:
                errors.append({
                    "field": "price",
                    "issue": "must be a non-negative number"
                })
            elif price > 9999.99:
                errors.append({
                    "field": "price",
                    "issue": "must be less than 10000"
                })
        
        if "category" in data:
            valid_categories = [
                "pizza", "burger", "salad", "appetizer",
                "dessert", "pasta", "beverage", "uncategorized"
            ]
            if data["category"] not in valid_categories:
                errors.append({
                    "field": "category",
                    "issue": f"must be one of: {valid_categories}"
                })
        
        if "available" in data:
            if not isinstance(data["available"], bool):
                errors.append({
                    "field": "available",
                    "issue": "must be true or false"
                })
        
        return errors
    
    @staticmethod
    def validate_order(data):
        errors = []
        
        items = data.get("items")
        if not items or not isinstance(items, list):
            errors.append({
                "field": "items",
                "issue": "is required and must be a non-empty list"
            })
            return errors
        
        if len(items) > 50:
            errors.append({
                "field": "items",
                "issue": "cannot have more than 50 items per order"
            })
            return errors
        
        for idx, entry in enumerate(items):
            item_id = entry.get("item_id")
            if not item_id or not isinstance(item_id, int):
                errors.append({
                    "field": f"items[{idx}].item_id",
                    "issue": "is required and must be an integer"
                })
                continue
            
            menu_item = db.get_item(item_id)
            if not menu_item:
                errors.append({
                    "field": f"items[{idx}].item_id",
                    "issue": f"item {item_id} does not exist"
                })
            elif not menu_item["available"]:
                errors.append({
                    "field": f"items[{idx}].item_id",
                    "issue": f"'{menu_item['name']}' is currently unavailable"
                })
            
            qty = entry.get("quantity", 1)
            if not isinstance(qty, int) or qty < 1 or qty > 100:
                errors.append({
                    "field": f"items[{idx}].quantity",
                    "issue": "must be an integer between 1 and 100"
                })
        
        return errors


# ============================================================
# SECTION 3: REST API ROUTER
# ============================================================

class Router:
    """
    Pattern-based URL router
    Maps METHOD + URL pattern → handler function
    Extracts path parameters like {id}
    """
    
    def __init__(self):
        self.routes = []
    
    def add_route(self, method, pattern, handler):
        # Convert /items/{id} to regex /items/(?P<id>[^/]+)
        regex_pattern = re.sub(
            r'\{(\w+)\}',
            r'(?P<\1>[^/]+)',
            pattern
        )
        regex_pattern = f'^{regex_pattern}$'
        self.routes.append({
            "method": method.upper(),
            "pattern": pattern,
            "regex": re.compile(regex_pattern),
            "handler": handler
        })
    
    def resolve(self, method, path):
        for route in self.routes:
            if route["method"] != method.upper():
                continue
            match = route["regex"].match(path)
            if match:
                params = match.groupdict()
                # Convert numeric params to int
                for key, value in params.items():
                    if value.isdigit():
                        params[key] = int(value)
                return route["handler"], params
        
        return None, {}


# ============================================================
# SECTION 4: API HANDLER (THE BRAIN)
# ============================================================

class RestaurantAPIHandler(BaseHTTPRequestHandler):
    
    # Class-level router (shared across all requests)
    router = Router()
    
    # ---- Response Helpers ----
    
    def send_json(self, status_code, data):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods',
                         'GET, POST, PUT, PATCH, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers',
                         'Content-Type, Authorization, X-Request-ID')
        
        # Echo request ID for tracing
        request_id = self.headers.get('X-Request-ID', str(uuid.uuid4()))
        self.send_header('X-Request-ID', request_id)
        
        body = json.dumps(data, indent=2)
        self.send_header('Content-Length', str(len(body.encode('utf-8'))))
        self.end_headers()
        self.wfile.write(body.encode('utf-8'))
    
    def send_success(self, data, status_code=200, meta=None):
        response = {"success": True, "data": data}
        if meta:
            response["meta"] = meta
        self.send_json(status_code, response)
    
    def send_error(self, status_code, code, message, details=None):
        response = {
            "success": False,
            "error": {
                "code": code,
                "message": message
            }
        }
        if details:
            response["error"]["details"] = details
        self.send_json(status_code, response)
    
    def read_body(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            body = self.rfile.read(content_length)
            try:
                return json.loads(body.decode('utf-8')), None
            except json.JSONDecodeError as e:
                return None, str(e)
        return {}, None
    
    def get_query_params(self):
        parsed = urllib.parse.urlparse(self.path)
        return dict(urllib.parse.parse_qsl(parsed.query))
    
    def get_clean_path(self):
        parsed = urllib.parse.urlparse(self.path)
        return parsed.path.rstrip('/')
    
    # ---- Request Routing ----
    
    def route_request(self, method):
        path = self.get_clean_path()
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        request_id = self.headers.get('X-Request-ID', 'none')
        print(f"[{timestamp}] {method:6s} {self.path} "
              f"[from: {self.client_address[0]}] "
              f"[req-id: {request_id}]")
        
        handler, params = self.router.resolve(method, path)
        
        if handler:
            handler(self, **params)
        else:
            self.send_error(404, "NOT_FOUND",
                            f"Endpoint {method} {path} not found",
                            {
                                "hint": "Check /api/v1 for available endpoints",
                                "docs": "/api/v1"
                            })
    
    def do_GET(self):
        self.route_request("GET")
    
    def do_POST(self):
        self.route_request("POST")
    
    def do_PUT(self):
        self.route_request("PUT")
    
    def do_PATCH(self):
        self.route_request("PATCH")
    
    def do_DELETE(self):
        self.route_request("DELETE")
    
    def do_OPTIONS(self):
        # CORS preflight
        self.send_json(200, {"methods": ["GET","POST","PUT","PATCH","DELETE"]})
    
    def log_message(self, format, *args):
        pass  # Suppress default logging


# ============================================================
# SECTION 5: ROUTE HANDLERS (Business Logic)
# ============================================================

# ---- Root / API Discovery ----

def handle_api_root(handler):
    handler.send_success({
        "service": "Restaurant Chain API",
        "version": "1.0.0",
        "endpoints": {
            "GET /api/v1/health": "Health check",
            "GET /api/v1/menu-items": "List menu items (with filters)",
            "POST /api/v1/menu-items": "Create a menu item",
            "GET /api/v1/menu-items/{id}": "Get specific item",
            "PUT /api/v1/menu-items/{id}": "Replace entire item",
            "PATCH /api/v1/menu-items/{id}": "Partially update item",
            "DELETE /api/v1/menu-items/{id}": "Delete an item",
            "GET /api/v1/orders": "List orders",
            "POST /api/v1/orders": "Place an order",
            "GET /api/v1/orders/{id}": "Get specific order",
            "PATCH /api/v1/orders/{id}": "Update order status"
        },
        "query_params": {
            "menu-items": "?category=pizza&available=true&min_price=5"
                          "&max_price=20&search=marg&sort=price"
                          "&order=asc&page=1&limit=10",
            "orders": "?status=received&page=1&limit=10"
        }
    })


# ---- Health Check ----

def handle_health(handler):
    handler.send_success({
        "status": "healthy",
        "timestamp": datetime.datetime.now().isoformat(),
        "total_menu_items": len(db.menu_items),
        "total_orders": len(db.orders)
    })


# ---- Menu Items: LIST ----

def handle_list_items(handler):
    params = handler.get_query_params()
    
    # Extract pagination params
    try:
        page = max(1, int(params.pop("page", 1)))
        limit = min(100, max(1, int(params.pop("limit", 10))))
    except ValueError:
        handler.send_error(400, "INVALID_PARAM",
                           "page and limit must be integers")
        return
    
    # Extract sort params
    sort_by = params.pop("sort", "id")
    sort_order = params.pop("order", "asc")
    
    if sort_by not in ("id", "name", "price", "category"):
        handler.send_error(400, "INVALID_PARAM",
                           f"Cannot sort by '{sort_by}'",
                           {"valid_sort_fields": [
                               "id", "name", "price", "category"
                           ]})
        return
    
    # Remaining params are filters
    result = db.list_items(
        filters=params, page=page, limit=limit,
        sort_by=sort_by, sort_order=sort_order
    )
    
    handler.send_success(result["items"], meta=result["pagination"])


# ---- Menu Items: GET ONE ----

def handle_get_item(handler, id):
    item = db.get_item(id)
    if not item:
        handler.send_error(404, "NOT_FOUND",
                           f"Menu item with id={id} not found")
        return
    handler.send_success(item)


# ---- Menu Items: CREATE ----

def handle_create_item(handler):
    body, parse_error = handler.read_body()
    if parse_error:
        handler.send_error(400, "INVALID_JSON",
                           f"Could not parse request body: {parse_error}")
        return
    
    # Validate
    errors = Validator.validate_menu_item(body, partial=False)
    if errors:
        handler.send_error(422, "VALIDATION_ERROR",
                           "Request validation failed", errors)
        return
    
    item = db.create_item(body)
    handler.send_success(item, status_code=201)


# ---- Menu Items: REPLACE (PUT) ----

def handle_replace_item(handler, id):
    existing = db.get_item(id)
    if not existing:
        handler.send_error(404, "NOT_FOUND",
                           f"Menu item with id={id} not found")
        return
    
    body, parse_error = handler.read_body()
    if parse_error:
        handler.send_error(400, "INVALID_JSON",
                           f"Could not parse request body: {parse_error}")
        return
    
    # PUT requires ALL fields (full replacement)
    errors = Validator.validate_menu_item(body, partial=False)
    if errors:
        handler.send_error(422, "VALIDATION_ERROR",
                           "PUT requires all fields", errors)
        return
    
    item = db.update_item(id, body, partial=False)
    handler.send_success(item)


# ---- Menu Items: PARTIAL UPDATE (PATCH) ----

def handle_update_item(handler, id):
    existing = db.get_item(id)
    if not existing:
        handler.send_error(404, "NOT_FOUND",
                           f"Menu item with id={id} not found")
        return
    
    body, parse_error = handler.read_body()
    if parse_error:
        handler.send_error(400, "INVALID_JSON",
                           f"Could not parse request body: {parse_error}")
        return
    
    if not body:
        handler.send_error(400, "EMPTY_BODY",
                           "PATCH requires at least one field to update")
        return
    
    # PATCH only validates provided fields
    errors = Validator.validate_menu_item(body, partial=True)
    if errors:
        handler.send_error(422, "VALIDATION_ERROR",
                           "Validation failed for provided fields", errors)
        return
    
    item = db.update_item(id, body, partial=True)
    handler.send_success(item)


# ---- Menu Items: DELETE ----

def handle_delete_item(handler, id):
    existing = db.get_item(id)
    if not existing:
        handler.send_error(404, "NOT_FOUND",
                           f"Menu item with id={id} not found")
        return
    
    # Check if any active order references this item
    for order in db.orders.values():
        if order["status"] in ("received", "preparing"):
            for oi in order["items"]:
                if oi["item_id"] == id:
                    handler.send_error(
                        409, "CONFLICT",
                        f"Cannot delete: item is in active order "
                        f"#{order['id']}",
                        {"active_order_id": order["id"]}
                    )
                    return
    
    db.delete_item(id)
    # 204 No Content — successful delete, nothing to return
    handler.send_response(204)
    handler.send_header('Content-Length', '0')
    handler.end_headers()


# ---- Orders: LIST ----

def handle_list_orders(handler):
    params = handler.get_query_params()
    
    try:
        page = max(1, int(params.pop("page", 1)))
        limit = min(100, max(1, int(params.pop("limit", 10))))
    except ValueError:
        handler.send_error(400, "INVALID_PARAM",
                           "page and limit must be integers")
        return
    
    result = db.list_orders(filters=params, page=page, limit=limit)
    handler.send_success(result["orders"], meta=result["pagination"])


# ---- Orders: CREATE ----

def handle_create_order(handler):
    body, parse_error = handler.read_body()
    if parse_error:
        handler.send_error(400, "INVALID_JSON",
                           f"Could not parse request body: {parse_error}")
        return
    
    errors = Validator.validate_order(body)
    if errors:
        handler.send_error(422, "VALIDATION_ERROR",
                           "Order validation failed", errors)
        return
    
    order = db.create_order(body)
    handler.send_success(order, status_code=201)


# ---- Orders: GET ONE ----

def handle_get_order(handler, id):
    order = db.get_order(id)
    if not order:
        handler.send_error(404, "NOT_FOUND",
                           f"Order with id={id} not found")
        return
    handler.send_success(order)


# ---- Orders: UPDATE STATUS (PATCH) ----

def handle_update_order(handler, id):
    order = db.get_order(id)
    if not order:
        handler.send_error(404, "NOT_FOUND",
                           f"Order with id={id} not found")
        return
    
    body, parse_error = handler.read_body()
    if parse_error:
        handler.send_error(400, "INVALID_JSON",
                           f"Could not parse request body: {parse_error}")
        return
    
    new_status = body.get("status")
    if not new_status:
        handler.send_error(400, "MISSING_FIELD",
                           "Field 'status' is required",
                           {"valid_statuses": [
                               "received", "preparing", "ready",
                               "delivered", "cancelled"
                           ]})
        return
    
    result = db.update_order_status(id, new_status)
    
    if result and result.get("error"):
        handler.send_error(409, "INVALID_TRANSITION",
                           result["message"],
                           {"valid_transitions": 
                            result["valid_transitions"]})
        return
    
    if not result:
        handler.send_error(404, "NOT_FOUND",
                           f"Order with id={id} not found")
        return
    
    handler.send_success(result)


# ============================================================
# SECTION 6: REGISTER ALL ROUTES
# ============================================================

router = RestaurantAPIHandler.router

# API Discovery
router.add_route("GET", "/api/v1", handle_api_root)

# Health
router.add_route("GET", "/api/v1/health", handle_health)

# Menu Items — Full CRUD
router.add_route("GET",    "/api/v1/menu-items",      handle_list_items)
router.add_route("POST",   "/api/v1/menu-items",      handle_create_item)
router.add_route("GET",    "/api/v1/menu-items/{id}",  handle_get_item)
router.add_route("PUT",    "/api/v1/menu-items/{id}",  handle_replace_item)
router.add_route("PATCH",  "/api/v1/menu-items/{id}",  handle_update_item)
router.add_route("DELETE", "/api/v1/menu-items/{id}",  handle_delete_item)

# Orders
router.add_route("GET",   "/api/v1/orders",      handle_list_orders)
router.add_route("POST",  "/api/v1/orders",      handle_create_order)
router.add_route("GET",   "/api/v1/orders/{id}",  handle_get_order)
router.add_route("PATCH", "/api/v1/orders/{id}",  handle_update_order)


# ============================================================
# SECTION 7: SERVER STARTUP
# ============================================================

def run_server(port=8080):
    server = HTTPServer(('127.0.0.1', port), RestaurantAPIHandler)
    
    print(f"\n{'=' * 65}")
    print(f"  🍽️  RESTAURANT CHAIN REST API v1.0")
    print(f"  Running on: http://127.0.0.1:{port}")
    print(f"{'=' * 65}")
    print(f"\n  📍 Endpoints:")
    print(f"  {'─' * 60}")
    print(f"  GET    /api/v1                  → API Discovery")
    print(f"  GET    /api/v1/health           → Health Check")
    print(f"  GET    /api/v1/menu-items       → List Items")
    print(f"  POST   /api/v1/menu-items       → Create Item")
    print(f"  GET    /api/v1/menu-items/{{id}}  → Get Item")
    print(f"  PUT    /api/v1/menu-items/{{id}}  → Replace Item")
    print(f"  PATCH  /api/v1/menu-items/{{id}}  → Update Item")
    print(f"  DELETE /api/v1/menu-items/{{id}}  → Delete Item")
    print(f"  GET    /api/v1/orders           → List Orders")
    print(f"  POST   /api/v1/orders           → Create Order")
    print(f"  GET    /api/v1/orders/{{id}}      → Get Order")
    print(f"  PATCH  /api/v1/orders/{{id}}      → Update Status")
    print(f"  {'─' * 60}")
    print(f"\n  📦 Preloaded: {len(db.menu_items)} menu items")
    print(f"  💡 Try: curl http://127.0.0.1:{port}/api/v1/menu-items")
    print(f"\n{'=' * 65}\n")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Server stopped.")
        server.shutdown()


# ============================================================
# SECTION 8: COMPREHENSIVE CLIENT TEST SUITE
# ============================================================

def run_client_tests():
    """Exercises EVERY endpoint and edge case"""
    import urllib.request
    
    time.sleep(1)
    base = "http://127.0.0.1:8080"
    
    def api_call(method, path, body=None, expect_status=None):
        url = f"{base}{path}"
        data = json.dumps(body).encode('utf-8') if body else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header('Content-Type', 'application/json')
        req.add_header('Accept', 'application/json')
        req.add_header('X-Request-ID', str(uuid.uuid4())[:8])
        
        try:
            with urllib.request.urlopen(req) as resp:
                status = resp.status
                if resp.headers.get('Content-Length', '0') != '0':
                    result = json.loads(resp.read().decode('utf-8'))
                else:
                    result = {"_no_content": True}
        except urllib.error.HTTPError as e:
            status = e.code
            result = json.loads(e.read().decode('utf-8'))
        
        status_icon = "✅" if status < 400 else "⚠️" if status < 500 else "❌"
        print(f"  {status_icon} [{status}] {method:6s} {path}")
        if body:
            print(f"         Body: {json.dumps(body)}")
        
        if result.get("success") is False:
            err = result.get("error", {})
            print(f"         Error: {err.get('code')}: {err.get('message')}")
            if err.get("details"):
                for d in err["details"][:3]:
                    print(f"           → {d['field']}: {d['issue']}")
        elif result.get("_no_content"):
            print(f"         (No Content — Successful Delete)")
        else:
            data_val = result.get("data")
            if isinstance(data_val, list):
                print(f"         Returned: {len(data_val)} items")
                meta = result.get("meta")
                if meta:
                    print(f"         Page {meta['page']}/{meta['total_pages']}"
                          f" (total: {meta['total']})")
            elif isinstance(data_val, dict) and "id" in data_val:
                name_field = data_val.get('name',
                              data_val.get('customer_name', ''))
                print(f"         ID: {data_val['id']} | {name_field}")
                if "status" in data_val:
                    print(f"         Status: {data_val['status']}")
                if "total_price" in data_val:
                    print(f"         Total: ${data_val['total_price']}")
            elif isinstance(data_val, dict):
                for key in list(data_val.keys())[:4]:
                    print(f"         {key}: {data_val[key]}")
        
        print()
        return result
    
    print(f"\n{'=' * 65}")
    print(f"  🧪 COMPREHENSIVE REST API TEST SUITE")
    print(f"{'=' * 65}")
    
    # ================================================================
    # TEST GROUP 1: Discovery & Health
    # ================================================================
    print(f"\n  {'─' * 60}")
    print(f"  📋 TEST GROUP 1: API Discovery & Health Check")
    print(f"  {'─' * 60}\n")
    
    api_call("GET", "/api/v1")
    api_call("GET", "/api/v1/health")
    
    # ================================================================
    # TEST GROUP 2: List Menu Items (with Filters & Pagination)
    # ================================================================
    print(f"\n  {'─' * 60}")
    print(f"  📋 TEST GROUP 2: List & Filter Menu Items")
    print(f"  {'─' * 60}\n")
    
    # List all items (default pagination)
    api_call("GET", "/api/v1/menu-items")
    
    # Filter by category
    api_call("GET", "/api/v1/menu-items?category=pizza")
    
    # Filter by availability
    api_call("GET", "/api/v1/menu-items?available=true")
    
    # Filter by price range
    api_call("GET", "/api/v1/menu-items?min_price=10&max_price=15")
    
    # Search by name
    api_call("GET", "/api/v1/menu-items?search=chicken")
    
    # Sort by price descending
    api_call("GET", "/api/v1/menu-items?sort=price&order=desc")
    
    # Pagination: page 1 with 3 items per page
    api_call("GET", "/api/v1/menu-items?page=1&limit=3")
    
    # Pagination: page 2 with 3 items per page
    api_call("GET", "/api/v1/menu-items?page=2&limit=3")
    
    # Combined: category + sort + pagination
    api_call("GET", "/api/v1/menu-items?category=appetizer"
                    "&sort=price&order=asc&page=1&limit=5")
    
    # Invalid sort field
    api_call("GET", "/api/v1/menu-items?sort=flavor")
    
    # ================================================================
    # TEST GROUP 3: Get Single Menu Item
    # ================================================================
    print(f"\n  {'─' * 60}")
    print(f"  📋 TEST GROUP 3: Get Single Menu Item")
    print(f"  {'─' * 60}\n")
    
    # Existing item
    api_call("GET", "/api/v1/menu-items/1")
    
    # Another existing item
    api_call("GET", "/api/v1/menu-items/3")
    
    # Non-existent item
    api_call("GET", "/api/v1/menu-items/999")
    
    # ================================================================
    # TEST GROUP 4: Create Menu Items (POST)
    # ================================================================
    print(f"\n  {'─' * 60}")
    print(f"  📋 TEST GROUP 4: Create Menu Items")
    print(f"  {'─' * 60}\n")
    
    # Valid creation
    result = api_call("POST", "/api/v1/menu-items", {
        "name": "Hawaiian Pizza",
        "category": "pizza",
        "price": 15.99,
        "available": True,
        "prep_time_mins": 20
    })
    new_item_id = result.get("data", {}).get("id")
    
    # Another valid creation
    api_call("POST", "/api/v1/menu-items", {
        "name": "Chocolate Lava Cake",
        "category": "dessert",
        "price": 8.99,
        "available": True,
        "prep_time_mins": 10
    })
    
    # Missing required field (name)
    api_call("POST", "/api/v1/menu-items", {
        "category": "pizza",
        "price": 12.99
    })
    
    # Invalid price (negative)
    api_call("POST", "/api/v1/menu-items", {
        "name": "Bad Pizza",
        "price": -5.00
    })
    
    # Invalid category
    api_call("POST", "/api/v1/menu-items", {
        "name": "Sushi Roll",
        "category": "japanese",
        "price": 16.99
    })
    
    # Empty body
    api_call("POST", "/api/v1/menu-items", {})
    
    # ================================================================
    # TEST GROUP 5: Update Menu Items (PUT vs PATCH)
    # ================================================================
    print(f"\n  {'─' * 60}")
    print(f"  📋 TEST GROUP 5: PUT (Replace) vs PATCH (Partial Update)")
    print(f"  {'─' * 60}\n")
    
    # PATCH: Update only the price of item 1
    print("  --- PATCH: Partial update (only price) ---")
    api_call("PATCH", "/api/v1/menu-items/1", {
        "price": 13.99
    })
    
    # PATCH: Update availability
    print("  --- PATCH: Toggle availability ---")
    api_call("PATCH", "/api/v1/menu-items/5", {
        "available": True
    })
    
    # PATCH: Invalid field value
    print("  --- PATCH: Invalid value ---")
    api_call("PATCH", "/api/v1/menu-items/1", {
        "price": -10
    })
    
    # PATCH: Empty body
    print("  --- PATCH: Empty body (should fail) ---")
    api_call("PATCH", "/api/v1/menu-items/1", {})
    
    # PATCH: Non-existent item
    print("  --- PATCH: Item doesn't exist ---")
    api_call("PATCH", "/api/v1/menu-items/999", {
        "price": 5.00
    })
    
    # PUT: Full replacement (all fields required)
    print("  --- PUT: Full replacement ---")
    api_call("PUT", "/api/v1/menu-items/2", {
        "name": "Supreme Pepperoni Pizza",
        "category": "pizza",
        "price": 16.99,
        "available": True,
        "prep_time_mins": 22
    })
    
    # PUT: Missing fields (should fail — PUT needs everything)
    print("  --- PUT: Missing fields (should fail) ---")
    api_call("PUT", "/api/v1/menu-items/2", {
        "name": "Incomplete Pizza"
    })
    
    # Verify item 1 was updated (GET after PATCH)
    print("  --- Verify: GET after PATCH ---")
    api_call("GET", "/api/v1/menu-items/1")
    
    # Verify item 2 was replaced (GET after PUT)
    print("  --- Verify: GET after PUT ---")
    api_call("GET", "/api/v1/menu-items/2")
    
    # ================================================================
    # TEST GROUP 6: Create Orders
    # ================================================================
    print(f"\n  {'─' * 60}")
    print(f"  📋 TEST GROUP 6: Create Orders")
    print(f"  {'─' * 60}\n")
    
    # Valid order with multiple items
    result = api_call("POST", "/api/v1/orders", {
        "customer_name": "Alice Johnson",
        "items": [
            {"item_id": 1, "quantity": 2},
            {"item_id": 3, "quantity": 1},
            {"item_id": 4, "quantity": 3}
        ],
        "notes": "Extra cheese on pizza please"
    })
    order_1_id = result.get("data", {}).get("id")
    
    # Another valid order
    result = api_call("POST", "/api/v1/orders", {
        "customer_name": "Bob Smith",
        "items": [
            {"item_id": 2, "quantity": 1},
            {"item_id": 7, "quantity": 2}
        ],
        "notes": ""
    })
    order_2_id = result.get("data", {}).get("id")
    
    # Order with non-existent item
    api_call("POST", "/api/v1/orders", {
        "customer_name": "Charlie",
        "items": [
            {"item_id": 999, "quantity": 1}
        ]
    })
    
    # Order with empty items list
    api_call("POST", "/api/v1/orders", {
        "customer_name": "Diana",
        "items": []
    })
    
    # Order without items field
    api_call("POST", "/api/v1/orders", {
        "customer_name": "Eve"
    })
    
    # Order with invalid quantity
    api_call("POST", "/api/v1/orders", {
        "customer_name": "Frank",
        "items": [
            {"item_id": 1, "quantity": -5}
        ]
    })
    
    # ================================================================
    # TEST GROUP 7: Get & List Orders
    # ================================================================
    print(f"\n  {'─' * 60}")
    print(f"  📋 TEST GROUP 7: Get & List Orders")
    print(f"  {'─' * 60}\n")
    
    # List all orders
    api_call("GET", "/api/v1/orders")
    
    # Get specific order
    if order_1_id:
        api_call("GET", f"/api/v1/orders/{order_1_id}")
    
    # Non-existent order
    api_call("GET", "/api/v1/orders/999")
    
    # Filter by status
    api_call("GET", "/api/v1/orders?status=received")
    
    # ================================================================
    # TEST GROUP 8: Order Status Transitions (State Machine)
    # ================================================================
    print(f"\n  {'─' * 60}")
    print(f"  📋 TEST GROUP 8: Order Status Transitions")
    print(f"  {'─' * 60}\n")
    
    if order_1_id:
        # Valid: received → preparing
        print("  --- Transition: received → preparing ---")
        api_call("PATCH", f"/api/v1/orders/{order_1_id}", {
            "status": "preparing"
        })
        
        # Valid: preparing → ready
        print("  --- Transition: preparing → ready ---")
        api_call("PATCH", f"/api/v1/orders/{order_1_id}", {
            "status": "ready"
        })
        
        # Valid: ready → delivered
        print("  --- Transition: ready → delivered ---")
        api_call("PATCH", f"/api/v1/orders/{order_1_id}", {
            "status": "delivered"
        })
        
        # Invalid: delivered → preparing (can't go backward)
        print("  --- Invalid: delivered → preparing ---")
        api_call("PATCH", f"/api/v1/orders/{order_1_id}", {
            "status": "preparing"
        })
    
    if order_2_id:
        # Valid: received → cancelled
        print("  --- Transition: received → cancelled ---")
        api_call("PATCH", f"/api/v1/orders/{order_2_id}", {
            "status": "cancelled"
        })
        
        # Invalid: cancelled → preparing (can't resurrect)
        print("  --- Invalid: cancelled → preparing ---")
        api_call("PATCH", f"/api/v1/orders/{order_2_id}", {
            "status": "preparing"
        })
    
    # Missing status field
    print("  --- Missing status field ---")
    api_call("PATCH", "/api/v1/orders/1", {})
    
    # ================================================================
    # TEST GROUP 9: Delete Menu Items
    # ================================================================
    print(f"\n  {'─' * 60}")
    print(f"  📋 TEST GROUP 9: Delete Menu Items")
    print(f"  {'─' * 60}\n")
    
    # Delete the Hawaiian Pizza we created (no active orders reference it)
    if new_item_id:
        print("  --- Delete item with no active orders ---")
        api_call("DELETE", f"/api/v1/menu-items/{new_item_id}")
        
        # Verify it's gone
        print("  --- Verify deletion ---")
        api_call("GET", f"/api/v1/menu-items/{new_item_id}")
    
    # Delete non-existent item
    print("  --- Delete non-existent item ---")
    api_call("DELETE", "/api/v1/menu-items/999")
    
    # ================================================================
    # TEST GROUP 10: Edge Cases & Error Handling
    # ================================================================
    print(f"\n  {'─' * 60}")
    print(f"  📋 TEST GROUP 10: Edge Cases & Error Handling")
    print(f"  {'─' * 60}\n")
    
    # Unknown endpoint
    api_call("GET", "/api/v1/unknown-endpoint")
    
    # Wrong method on existing endpoint
    api_call("DELETE", "/api/v1/menu-items")
    
    # POST to endpoint that only accepts GET
    api_call("POST", "/api/v1/health")
    
    # Very large page number (empty result)
    api_call("GET", "/api/v1/menu-items?page=999")
    
    # ================================================================
    # TEST GROUP 11: Final State Verification
    # ================================================================
    print(f"\n  {'─' * 60}")
    print(f"  📋 TEST GROUP 11: Final State — Full Data Check")
    print(f"  {'─' * 60}\n")
    
    # Final menu items count
    result = api_call("GET", "/api/v1/menu-items?limit=100")
    items_data = result.get("data", [])
    print(f"  📊 Total menu items remaining: {len(items_data)}")
    for item in items_data:
        avail = "✅" if item["available"] else "❌"
        print(f"     {avail} [{item['id']:2d}] {item['name']:<25s} "
              f"${item['price']:.2f} ({item['category']})")
    
    # Final orders count
    print()
    result = api_call("GET", "/api/v1/orders?limit=100")
    orders_data = result.get("data", [])
    print(f"  📊 Total orders: {len(orders_data)}")
    status_icons = {
        "received": "📥", "preparing": "🔥",
        "ready": "✅", "delivered": "🚗", "cancelled": "❌"
    }
    for order in orders_data:
        icon = status_icons.get(order["status"], "❓")
        print(f"     {icon} [Order #{order['id']}] "
              f"{order['customer_name']:<15s} "
              f"${order['total_price']:.2f} → {order['status']}")
    
    # ================================================================
    # SUMMARY
    # ================================================================
    print(f"\n{'=' * 65}")
    print(f"  ✅ ALL TESTS COMPLETE")
    print(f"{'=' * 65}")
    print(f"""
  REST Principles Demonstrated:
  ─────────────────────────────
  ✅ Resources as nouns in URLs (/menu-items, /orders)
  ✅ HTTP methods as verbs (GET, POST, PUT, PATCH, DELETE)
  ✅ Proper status codes (200, 201, 204, 400, 404, 409, 422)
  ✅ Consistent JSON response envelope
  ✅ Field-level validation with detailed errors
  ✅ Pagination (page, limit, total, has_next, has_prev)
  ✅ Filtering (category, price range, availability, search)
  ✅ Sorting (sort field + order direction)
  ✅ PUT vs PATCH distinction
  ✅ State machine for order transitions
  ✅ Conflict detection (delete item in active order)
  ✅ API versioning (/api/v1/)
  ✅ Request tracing (X-Request-ID header)
  ✅ Self-documenting root endpoint
    """)


# ============================================================
# SECTION 9: MAIN ENTRY POINT
# ============================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "server":
        run_server()
    elif len(sys.argv) > 1 and sys.argv[1] == "client":
        run_client_tests()
    else:
        # Run both: server in background, client in foreground
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        run_client_tests()