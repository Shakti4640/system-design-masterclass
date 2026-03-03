# ============================================================
# PROJECT 1A: RAW TCP SERVER — THE ABSOLUTE FOUNDATION
# This is what happens UNDERNEATH HTTP
# Understanding this = understanding everything above it
# ============================================================

import socket
import threading
import json
import datetime

# ============================================================
# THE PIZZA SHOP SERVER (TCP Level)
# ============================================================

class PizzaShopServer:
    
    def __init__(self, host='127.0.0.1', port=9999):
        # The shop's address and counter number
        self.host = host
        self.port = port
        # Create the socket (the communication endpoint)
        # AF_INET = IPv4 addressing
        # SOCK_STREAM = TCP (reliable, ordered delivery)
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Allow reuse of address (prevents "Address already in use" error)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Our pizza menu (this is our "data")
        self.menu = {
            "margherita": {"price": 10, "time_mins": 12},
            "pepperoni": {"price": 13, "time_mins": 15},
            "veggie": {"price": 11, "time_mins": 14},
            "bbq_chicken": {"price": 14, "time_mins": 18}
        }
        # Track orders (simple in-memory storage)
        self.orders = {}
        self.order_counter = 0
        # Thread lock for order_counter (safe concurrent access)
        self.lock = threading.Lock()
    
    def start(self):
        # BIND: Attach socket to specific address + port
        self.server_socket.bind((self.host, self.port))
        # LISTEN: Start accepting connections (backlog=5)
        # Backlog = how many pending connections can wait in queue
        self.server_socket.listen(5)
        print(f"[PIZZA SHOP OPEN] Listening on {self.host}:{self.port}")
        print(f"[INFO] Waiting for customers...\n")
        
        while True:
            # ACCEPT: Block until a client connects
            # Returns: new socket for THIS specific client + their address
            client_socket, client_address = self.server_socket.accept()
            print(f"[NEW CUSTOMER] Connected from {client_address}")
            # Handle each customer in a separate thread
            # So one slow order doesn't block everyone
            thread = threading.Thread(
                target=self.handle_customer,
                args=(client_socket, client_address)
            )
            thread.daemon = True  # Thread dies when main program exits
            thread.start()
    
    def handle_customer(self, client_socket, client_address):
        try:
            while True:
                # RECEIVE data from client (max 4096 bytes at a time)
                raw_data = client_socket.recv(4096)
                
                # If empty data → client disconnected
                if not raw_data:
                    print(f"[CUSTOMER LEFT] {client_address}")
                    break
                
                # Decode bytes to string, then parse JSON
                request_str = raw_data.decode('utf-8').strip()
                print(f"[REQUEST from {client_address}] {request_str}")
                
                try:
                    request = json.loads(request_str)
                except json.JSONDecodeError:
                    response = {
                        "status": 400,
                        "error": "Invalid request format. Send JSON."
                    }
                    client_socket.send(json.dumps(response).encode('utf-8'))
                    continue
                
                # PROCESS the request based on "action"
                response = self.process_request(request, client_address)
                
                # SEND response back
                response_str = json.dumps(response)
                client_socket.send(response_str.encode('utf-8'))
                print(f"[RESPONSE to {client_address}] {response_str}\n")
                
        except ConnectionResetError:
            print(f"[CONNECTION LOST] {client_address} disconnected abruptly")
        except Exception as e:
            print(f"[ERROR] Handling {client_address}: {e}")
        finally:
            # ALWAYS clean up the connection
            client_socket.close()
    
    def process_request(self, request, client_address):
        action = request.get("action", "").lower()
        timestamp = datetime.datetime.now().isoformat()
        
        # ACTION: Get the menu
        if action == "get_menu":
            return {
                "status": 200,
                "message": "Here is our menu",
                "data": self.menu,
                "timestamp": timestamp
            }
        
        # ACTION: Place an order
        elif action == "place_order":
            pizza_name = request.get("pizza", "").lower()
            
            if pizza_name not in self.menu:
                return {
                    "status": 404,
                    "error": f"Pizza '{pizza_name}' not found on menu",
                    "available": list(self.menu.keys()),
                    "timestamp": timestamp
                }
            
            # Thread-safe order ID generation
            with self.lock:
                self.order_counter += 1
                order_id = f"ORD-{self.order_counter:04d}"
            
            pizza_info = self.menu[pizza_name]
            self.orders[order_id] = {
                "pizza": pizza_name,
                "price": pizza_info["price"],
                "status": "preparing",
                "customer": str(client_address),
                "ordered_at": timestamp
            }
            
            return {
                "status": 201,
                "message": f"Order placed successfully!",
                "order_id": order_id,
                "pizza": pizza_name,
                "price": pizza_info["price"],
                "estimated_time_mins": pizza_info["time_mins"],
                "timestamp": timestamp
            }
        
        # ACTION: Check order status
        elif action == "check_order":
            order_id = request.get("order_id", "")
            
            if order_id not in self.orders:
                return {
                    "status": 404,
                    "error": f"Order '{order_id}' not found",
                    "timestamp": timestamp
                }
            
            return {
                "status": 200,
                "order": self.orders[order_id],
                "timestamp": timestamp
            }
        
        # ACTION: Cancel an order
        elif action == "cancel_order":
            order_id = request.get("order_id", "")
            
            if order_id not in self.orders:
                return {
                    "status": 404,
                    "error": f"Order '{order_id}' not found",
                    "timestamp": timestamp
                }
            
            self.orders[order_id]["status"] = "cancelled"
            return {
                "status": 200,
                "message": f"Order {order_id} cancelled",
                "timestamp": timestamp
            }
        
        # UNKNOWN action
        else:
            return {
                "status": 400,
                "error": f"Unknown action: '{action}'",
                "available_actions": [
                    "get_menu",
                    "place_order",
                    "check_order",
                    "cancel_order"
                ],
                "timestamp": timestamp
            }


# ============================================================
# THE CUSTOMER CLIENT (TCP Level)
# ============================================================

class PizzaCustomerClient:
    
    def __init__(self, host='127.0.0.1', port=9999):
        self.host = host
        self.port = port
        self.socket = None
    
    def connect(self):
        # Create socket and connect to server
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))
        print(f"[CONNECTED] to pizza shop at {self.host}:{self.port}\n")
    
    def send_request(self, request_dict):
        if not self.socket:
            print("[ERROR] Not connected. Call connect() first.")
            return None
        
        # Convert dict to JSON string, then to bytes
        request_str = json.dumps(request_dict)
        self.socket.send(request_str.encode('utf-8'))
        
        # Wait for response
        raw_response = self.socket.recv(4096)
        response = json.loads(raw_response.decode('utf-8'))
        return response
    
    def disconnect(self):
        if self.socket:
            self.socket.close()
            print("[DISCONNECTED] from pizza shop")


# ============================================================
# RUN THE DEMO
# ============================================================

def run_server():
    server = PizzaShopServer(host='127.0.0.1', port=9999)
    server.start()

def run_client_demo():
    import time
    # Give server a moment to start
    time.sleep(1)
    
    customer = PizzaCustomerClient(host='127.0.0.1', port=9999)
    customer.connect()
    
    # Step 1: Get the menu
    print("=" * 50)
    print("STEP 1: Asking for the menu")
    print("=" * 50)
    response = customer.send_request({"action": "get_menu"})
    print(f"Status: {response['status']}")
    print(f"Menu: {json.dumps(response['data'], indent=2)}\n")
    
    # Step 2: Order a pizza
    print("=" * 50)
    print("STEP 2: Ordering a Margherita")
    print("=" * 50)
    response = customer.send_request({
        "action": "place_order",
        "pizza": "margherita"
    })
    print(f"Status: {response['status']}")
    print(f"Order ID: {response['order_id']}")
    print(f"Price: ${response['price']}")
    print(f"ETA: {response['estimated_time_mins']} mins\n")
    order_id = response['order_id']
    
    # Step 3: Check order status
    print("=" * 50)
    print("STEP 3: Checking order status")
    print("=" * 50)
    response = customer.send_request({
        "action": "check_order",
        "order_id": order_id
    })
    print(f"Status: {response['status']}")
    print(f"Order: {json.dumps(response['order'], indent=2)}\n")
    
    # Step 4: Try ordering something not on menu
    print("=" * 50)
    print("STEP 4: Ordering something invalid")
    print("=" * 50)
    response = customer.send_request({
        "action": "place_order",
        "pizza": "sushi"
    })
    print(f"Status: {response['status']}")
    print(f"Error: {response['error']}")
    print(f"Available: {response['available']}\n")
    
    # Step 5: Send garbage request
    print("=" * 50)
    print("STEP 5: Unknown action")
    print("=" * 50)
    response = customer.send_request({
        "action": "fly_to_moon"
    })
    print(f"Status: {response['status']}")
    print(f"Error: {response['error']}\n")
    
    # Step 6: Cancel the order
    print("=" * 50)
    print("STEP 6: Cancelling the order")
    print("=" * 50)
    response = customer.send_request({
        "action": "cancel_order",
        "order_id": order_id
    })
    print(f"Status: {response['status']}")
    print(f"Message: {response['message']}\n")
    
    customer.disconnect()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "server":
        run_server()
    elif len(sys.argv) > 1 and sys.argv[1] == "client":
        run_client_demo()
    else:
        # Run both in threads for demo
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        run_client_demo()