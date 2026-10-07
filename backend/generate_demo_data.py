import pandas as pd
import numpy as np
import os

os.makedirs('datasets', exist_ok=True)

# 1. Customers
np.random.seed(42)
customer_ids = range(1, 101)
customers = pd.DataFrame({
    'customer_id': customer_ids,
    'name': [f'Customer_{i}' for i in customer_ids],
    'age': np.random.randint(18, 70, size=100),
    'region': np.random.choice(['Tamil Nadu', 'Maharashtra', 'Karnataka', 'Delhi', 'Kerala'], size=100)
})

# Add a duplicate row for messy data
customers = pd.concat([customers, customers.iloc[[-1]]], ignore_index=True)
customers.to_csv('datasets/customers.csv', index=False)

# 2. Products
products = pd.DataFrame({
    'product_id': ['P1', 'P2', 'P3', 'P4'],
    'product_name': ['Laptop', 'Smartphone', 'Tablet', 'Monitor'],
    'category': ['Electronics', 'Electronics', 'Electronics', 'Peripherals'],
    'price': [1200, 800, 400, 300]
})
products.to_excel('datasets/products.xlsx', index=False)

# 3. Sales
dates = pd.date_range(start='2023-01-01', end='2023-12-31', periods=1000)
sales = pd.DataFrame({
    'sale_id': range(1, 1001),
    'customer_id': np.random.choice(customer_ids, size=1000),
    'product_id': np.random.choice(['P1', 'P2', 'P3', 'P4'], size=1000),
    'date': dates,
    'quantity': np.random.randint(1, 5, size=1000),
    'discount': np.random.uniform(0, 0.2, size=1000)
})

# Add missing values for messy data
sales.loc[np.random.choice(sales.index, size=30, replace=False), 'discount'] = np.nan
# Add inconsistent dates
sales.loc[0, 'date'] = '12-31-2023' # MM-DD-YYYY

sales.to_csv('datasets/sales.csv', index=False)
print("Demo datasets generated.")
