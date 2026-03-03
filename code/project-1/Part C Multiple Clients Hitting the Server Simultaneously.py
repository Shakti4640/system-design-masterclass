# ============================================================
# PROJECT 1C: CONCURRENT CLIENTS — WHY THREADING MATTERS
# Shows what happens when MANY customers arrive at once
# This directly sets up WHY we need Project 4 (Scaling)
# and Project 6 (Load Balancing)
# ============================================================

import socket
import json
import threading
import time
import random

def simulate_customer(customer_id, host='127.0.0.1', port=9999):
    """Each customer is an independent client thread"""
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((host, port))
        
        # Random delay to simulate real-world timing
        time.sleep(random.uniform(0.1, 0.5))
        
        # Each customer orders a random pizza
        pizzas = ["margherita", "pepperoni", "veggie", "bbq_chicken"]
        chosen_pizza = random.choice(pizzas)
        
        # Step 1: Get menu
        request = json.dumps({"action": "get_menu"})
        client.send(request.encode('utf-8'))
        response = json.loads(client.recv(4096).decode('utf-8'))
        
        time.sleep(random.uniform(0.1, 0.3))
        
        # Step 2: Place order
        request = json.dumps({
            "action": "place_order",
            "pizza": chosen_pizza
        })
        client.send(request.encode('utf-8'))
        response = json.loads(client.recv(4096).decode('utf-8'))
        
        order_id = response.get('order_id', 'NONE')
        price = response.get('price', 0)
        
        print(f"  Customer #{customer_id:02d} | "
              f"Ordered: {chosen_pizza:<12} | "
              f"Order: {order_id} | "
              f"Price: ${price}")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"  Customer #{customer_id:02d} | ERROR: {e}")
        return False


def run_concurrent_simulation(num_customers=20):
    """Launch many customers simultaneously"""
    print(f"\n{'=' * 60}")
    print(f"  SIMULATING {num_customers} CONCURRENT CUSTOMERS")
    print(f"  (Make sure Part A server is running on port 9999)")
    print(f"{'=' * 60}\n")
    
    start_time = time.time()
    threads = []
    
    # Launch all customers at roughly the same time
    for i in range(1, num_customers + 1):
        t = threading.Thread(target=simulate_customer, args=(i,))
        threads.append(t)
        t.start()
    
    # Wait for all customers to finish
    for t in threads:
        t.join()
    
    elapsed = time.time() - start_time
    
    print(f"\n{'=' * 60}")
    print(f"  ALL {num_customers} CUSTOMERS SERVED")
    print(f"  Total time: {elapsed:.2f} seconds")
    print(f"  Avg per customer: {elapsed/num_customers:.3f} seconds")
    print(f"{'=' * 60}")
    print(f"\n  💡 INSIGHT: With threading, the server handled")
    print(f"     {num_customers} customers concurrently.")
    print(f"     Without threading, they'd wait in line = {elapsed * num_customers:.1f}s total")
    print(f"\n  🔗 This is WHY we need:")
    print(f"     → Project 4: Scaling (what if 10,000 customers?)")
    print(f"     → Project 6: Load Balancer (split across servers)")


if __name__ == "__main__":
    run_concurrent_simulation(20)