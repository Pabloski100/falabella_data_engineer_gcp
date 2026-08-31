import csv
import random
from datetime import timedelta
from faker import Faker

# Inicializar Faker y fijar semilla para reproducibilidad
fake = Faker()
Faker.seed(42)
random.seed(42)

# Configuración de volumen de datos
NUM_CUSTOMERS = 100
NUM_ORDERS = 500

# Archivos de salida
SQL_FILE = 'init.sql'
CSV_FILE = 'shipments.csv'

# Lista de países limitados para que la consulta de Window Functions (Top 3 por país) tenga sentido
COUNTRIES = ['Mexico', 'Colombia', 'Chile', 'Argentina', 'Peru', 'Spain']

def generate_data():
    customers = []
    orders = []
    shipments = []

    print("Generando datos de Clientes...")
    for cust_id in range(1, NUM_CUSTOMERS + 1):
        # Escapar comillas simples en los nombres (ej. O'Connor -> O''Connor) para el SQL
        name = fake.name().replace("'", "''")
        country = random.choice(COUNTRIES)
        email = fake.email()
        customers.append((cust_id, name, country, email))

    print("Generando datos de Órdenes y Envíos...")
    for order_id in range(1, NUM_ORDERS + 1):
        cust_id = random.randint(1, NUM_CUSTOMERS)
        # Fechas de órdenes repartidas en el último año (para la consulta de crecimiento mensual)
        order_date = fake.date_time_between(start_date='-1y', end_date='now')
        # Montos entre $10 y $1000
        total_amount = round(random.uniform(10.0, 1000.0), 2)
        
        orders.append((order_id, cust_id, order_date.strftime('%Y-%m-%d %H:%M:%S'), total_amount))

        # --- Lógica de Envíos (CSV) ---
        shipment_id = f"SHIP-{order_id:05d}"
        
        # Fecha de envío: 1 a 2 días después de la orden
        shipped_date = order_date + timedelta(days=random.randint(1, 2))
        
        # Estado del envío y fecha de entrega
        status_choices = ['Delivered', 'Delivered', 'Delivered', 'In Transit', 'Cancelled']
        status = random.choice(status_choices)
        
        if status == 'Delivered':
            # Tiempo de entrega: 2 a 8 días después del envío (Para probar el SLA de 5 días)
            delivery_date = shipped_date + timedelta(days=random.randint(2, 8))
            delivery_date_str = delivery_date.strftime('%Y-%m-%d %H:%M:%S')
        else:
            delivery_date_str = '' # No entregado aún o cancelado

        shipments.append({
            'shipment_id': shipment_id,
            'order_id': order_id,
            'status': status,
            'shipped_date': shipped_date.strftime('%Y-%m-%d %H:%M:%S'),
            'delivery_date': delivery_date_str
        })

    return customers, orders, shipments

def write_sql(customers, orders):
    print(f"Escribiendo {SQL_FILE}...")
    with open(SQL_FILE, 'w', encoding='utf-8') as f:
        # 1. Crear e insertar Customers
        f.write("-- Creacion de tabla Customers\n")
        f.write("CREATE TABLE IF NOT EXISTS customers (\n")
        f.write("    customer_id INT PRIMARY KEY,\n")
        f.write("    name VARCHAR(255),\n")
        f.write("    country VARCHAR(100),\n")
        f.write("    email VARCHAR(255)\n")
        f.write(");\n\n")

        f.write("INSERT INTO customers (customer_id, name, country, email) VALUES\n")
        customer_values = [f"({c[0]}, '{c[1]}', '{c[2]}', '{c[3]}')" for c in customers]
        f.write(",\n".join(customer_values) + ";\n\n")

        # 2. Crear e insertar Orders
        f.write("-- Creacion de tabla Orders\n")
        f.write("CREATE TABLE IF NOT EXISTS orders (\n")
        f.write("    order_id INT PRIMARY KEY,\n")
        f.write("    customer_id INT,\n")
        f.write("    order_date TIMESTAMP,\n")
        f.write("    total_amount DECIMAL(10,2),\n")
        f.write("    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)\n")
        f.write(");\n\n")

        f.write("INSERT INTO orders (order_id, customer_id, order_date, total_amount) VALUES\n")
        order_values = [f"({o[0]}, {o[1]}, '{o[2]}', {o[3]})" for o in orders]
        f.write(",\n".join(order_values) + ";\n")

def write_csv(shipments):
    print(f"Escribiendo {CSV_FILE}...")
    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['shipment_id', 'order_id', 'status', 'shipped_date', 'delivery_date'])
        writer.writeheader()
        writer.writerows(shipments)

if __name__ == "__main__":
    customers_data, orders_data, shipments_data = generate_data()
    write_sql(customers_data, orders_data)
    write_csv(shipments_data)
    print("¡Archivos generados con éxito!")