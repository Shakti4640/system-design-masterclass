# ============================================================
# PROJECT 1B: HTTP SERVER — BUILDING ON TOP OF TCP
# Now we move from raw TCP to the HTTP protocol
# HTTP is just a STRUCTURED FORMAT on top of TCP
# ============================================================

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import datetime
import urllib.parse

# ============================================================
# IN-MEMORY DATA STORE (our simple "kitchen")
# ============================================================

MENU = {
    "margherita": {"price": 10, "time_mins": 12},
    "pepperoni": {"price": 13, "time_mins": 15},
    "veggie": {"price": 11, "time_mins": 14},
    "bbq_chicken": {"price": 14, "time_mins": 18}
}

ORDERS = {}
ORDER_COUNTER = [0]  # Mutable container for closure access


# ============================================================
# HTTP REQUEST HANDLER
# Every HTTP request maps to a method here
# ============================================================

class PizzaShopHTTPHandler(BaseHTTPRequestHandler):
    
    # ---- UTILITY: Send JSON Response ----
    def send_json_response(self, status_code, data):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        response_body = json.dumps(data, indent=2)
        self.send_header('Content-Length', str(len(response_body)))
        self.end_headers()
        self.wfile.write(response_body.encode('utf-8'))
    
    # ---- UTILITY: Read Request Body ----
    def read_body(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            body = self.rfile.read(content_length)
            return json.loads(body.decode('utf-8'))
        return {}
    
    # ---- UTILITY: Structured Logging ----
    def log_request_info(self, method):
        timestamp = datetime.datetime.now().isoformat()
        print(f"[{timestamp}] {method} {self.path} from {self.client_address[0]}")
    
    # ============================================================
    # GET REQUESTS — Reading Data (like asking questions)
    # ============================================================
    def do_GET(self):
        self.log_request_info("GET")
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        
        # GET /health — Is the server alive?
        if path == '/health':
            self.send_json_response(200, {
                "status": "healthy",
                "uptime": "running",
                "timestamp": datetime.datetime.now().isoformat()
            })
        
        # GET /menu — What pizzas are available?
        elif path == '/menu':
            self.send_json_response(200, {
                "status": 200,
                "message": "Pizza menu",
                "data": MENU,
                "total_items": len(MENU)
            })
        
        # GET /orders — List all orders
        elif path == '/orders':
            self.send_json_response(200, {
                "status": 200,
                "total_orders": len(ORDERS),
                "orders": ORDERS
            })
        
        # GET /orders/ORD-0001 — Get specific order
        elif path.startswith('/orders/'):
            order_id = path.split('/orders/')[1]
            if order_id in ORDERS:
                self.send_json_response(200, {
                    "status": 200,
                    "order": ORDERS[order_id]
                })
            else:
                self.send_json_response(404, {
                    "status": 404,
                    "error": f"Order '{order_id}' not found"
                })
        
        # Unknown path
        else:
            self.send_json_response(404, {
                "status": 404,
                "error": f"Endpoint '{path}' not found",
                "available_endpoints": {
                    "GET": ["/health", "/menu", "/orders", "/orders/{id}"],
                    "POST": ["/orders"],
                    "DELETE": ["/orders/{id}"]
                }
            })
    
    # ============================================================
    # POST REQUESTS — Creating Data (like placing an order)
    # ============================================================
    def do_POST(self):
        self.log_request_info("POST")
        
        if self.path == '/orders':
            body = self.read_body()
            pizza_name = body.get("pizza", "").lower()
            quantity = body.get("quantity", 1)
            
            # Validation
            if not pizza_name:
                self.send_json_response(400, {
                    "status": 400,
                    "error": "Missing 'pizza' field in request body"
                })
                return
            
            if pizza_name not in MENU:
                self.send_json_response(404, {
                    "status": 404,
                    "error": f"Pizza '{pizza_name}' not on menu",
                    "available": list(MENU.keys())
                })
                return
            
            if not isinstance(quantity, int) or quantity < 1:
                self.send_json_response(400, {
                    "status": 400,
                    "error": "Quantity must be a positive integer"
                })
                return
            
            # Create order
            ORDER_COUNTER[0] += 1
            order_id = f"ORD-{ORDER_COUNTER[0]:04d}"
            pizza_info = MENU[pizza_name]
            
            ORDERS[order_id] = {
                "order_id": order_id,
                "pizza": pizza_name,
                "quantity": quantity,
                "unit_price": pizza_info["price"],
                "total_price": pizza_info["price"] * quantity,
                "status": "preparing",
                "estimated_time_mins": pizza_info["time_mins"],
                "ordered_at": datetime.datetime.now().isoformat()
            }
            
            # 201 Created — the correct status for resource creation
            self.send_json_response(201, {
                "status": 201,
                "message": "Order placed successfully",
                "order": ORDERS[order_id]
            })
        
        else:
            self.send_json_response(404, {
                "status": 404,
                "error": f"Cannot POST to '{self.path}'"
            })
    
    # ============================================================
    # DELETE REQUESTS — Removing Data (like cancelling)
    # ============================================================
    def do_DELETE(self):
        self.log_request_info("DELETE")
        
        if self.path.startswith('/orders/'):
            order_id = self.path.split('/orders/')[1]
            
            if order_id not in ORDERS:
                self.send_json_response(404, {
                    "status": 404,
                    "error": f"Order '{order_id}' not found"
                })
                return
            
            if ORDERS[order_id]["status"] == "cancelled":
                self.send_json_response(400, {
                    "status": 400,
                    "error": "Order already cancelled"
                })
                return
            
            ORDERS[order_id]["status"] = "cancelled"
            ORDERS[order_id]["cancelled_at"] = datetime.datetime.now().isoformat()
            
            self.send_json_response(200, {
                "status": 200,
                "message": f"Order {order_id} cancelled",
                "order": ORDERS[order_id]
            })
        
        else:
            self.send_json_response(404, {
                "status": 404,
                "error": f"Cannot DELETE '{self.path}'"
            })
    
    # Suppress default logging (we have our own)
    def log_message(self, format, *args):
        pass


# ============================================================
# START THE HTTP SERVER
# ============================================================

def run_http_server(port=8080):
    server = HTTPServer(('127.0.0.1', port), PizzaShopHTTPHandler)
    print(f"{'=' * 55}")
    print(f"  🍕 PIZZA SHOP HTTP SERVER")
    print(f"  Running on: http://127.0.0.1:{port}")
    print(f"{'=' * 55}")
    print(f"\nAvailable Endpoints:")
    print(f"  GET    /health          → Health check")
    print(f"  GET    /menu            → View menu")
    print(f"  POST   /orders          → Place an order")
    print(f"  GET    /orders          → List all orders")
    print(f"  GET    /orders/{{id}}     → Check specific order")
    print(f"  DELETE /orders/{{id}}     → Cancel an order")
    print(f"\nTest with curl:")
    print(f'  curl http://127.0.0.1:{port}/menu')
    print(f'  curl -X POST http://127.0.0.1:{port}/orders '
          f'-H "Content-Type: application/json" '
          f'-d \'{{"pizza":"margherita","quantity":2}}\'')
    print(f"\n{'=' * 55}\n")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[SHUTTING DOWN] Pizza shop is closing...")
        server.shutdown()


# ============================================================
# HTTP CLIENT — Simulating Customer Requests
# ============================================================

def run_http_client_demo():
    import urllib.request
    import time
    
    time.sleep(1)  # Wait for server to start
    base_url = "http://127.0.0.1:8080"
    
    print("\n" + "=" * 55)
    print("  🧑 CUSTOMER SIMULATION STARTING")
    print("=" * 55)
    
    # Helper to make requests
    def make_request(method, path, body=None):
        url = f"{base_url}{path}"
        data = json.dumps(body).encode('utf-8') if body else None
        req = urllib.request.Request(url, data=data, method=method)
        if body:
            req.add_header('Content-Type', 'application/json')
        
        try:
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                print(f"\n  [{method} {path}] → Status: {result['status']}")
                print(f"  Response: {json.dumps(result, indent=4)}")
                return result
        except urllib.error.HTTPError as e:
            result = json.loads(e.read().decode('utf-8'))
            print(f"\n  [{method} {path}] → Status: {result['status']}")
            print(f"  Error: {json.dumps(result, indent=4)}")
            return result
    
    # Demo sequence
    print("\n--- Step 1: Health Check ---")
    make_request("GET", "/health")
    
    print("\n--- Step 2: View Menu ---")
    make_request("GET", "/menu")
    
    print("\n--- Step 3: Place Order (Margherita x2) ---")
    result = make_request("POST", "/orders", {
        "pizza": "margherita",
        "quantity": 2
    })
    order_id = result["order"]["order_id"]
    
    print("\n--- Step 4: Place Another Order (Pepperoni) ---")
    make_request("POST", "/orders", {
        "pizza": "pepperoni",
        "quantity": 1
    })
    
    print("\n--- Step 5: Try Invalid Pizza ---")
    make_request("POST", "/orders", {
        "pizza": "sushi",
        "quantity": 1
    })
    
    print("\n--- Step 6: Check Specific Order ---")
    make_request("GET", f"/orders/{order_id}")
    
    print("\n--- Step 7: List All Orders ---")
    make_request("GET", "/orders")
    
    print("\n--- Step 8: Cancel First Order ---")
    make_request("DELETE", f"/orders/{order_id}")
    
    print("\n--- Step 9: Verify Cancellation ---")
    make_request("GET", f"/orders/{order_id}")
    
    print("\n--- Step 10: Try Unknown Endpoint ---")
    make_request("GET", "/fly_to_moon")
    
    print("\n" + "=" * 55)
    print("  ✅ CUSTOMER SIMULATION COMPLETE")
    print("=" * 55)


# ============================================================
# MAIN ENTRY POINT
# ============================================================

if __name__ == "__main__":
    import sys
    import threading
    
    if len(sys.argv) > 1 and sys.argv[1] == "server":
        run_http_server()
    elif len(sys.argv) > 1 and sys.argv[1] == "client":
        run_http_client_demo()
    else:
        # Run both: server in background, client in foreground
        server_thread = threading.Thread(target=run_http_server, daemon=True)
        server_thread.start()
        run_http_client_demo()