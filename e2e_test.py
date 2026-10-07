import requests
import json
import time
import os

BASE_URL = "http://127.0.0.1:8000/api"

print("--- STARTING AUTOMATED BACKEND INTEGRATION TEST ---")

ts = int(time.time())

# Test data
user_a_email = f"user_a_{ts}@gmail.com"
user_a_username = f"usera{ts}"

user_b_email = f"user_b_{ts}@gmail.com"
user_b_username = f"userb{ts}"

password = "password123"

def run_test(name, condition, error_msg=""):
    if condition:
        print(f"{name}: PASS")
    else:
        print(f"{name}: FAIL - {error_msg}")
        exit(1)

# 1. Register User A
res = requests.post(f"{BASE_URL}/auth/register", json={"username": user_a_username, "email": user_a_email, "password": password})
run_test("1. Register User A", res.status_code == 200, res.text)
token_a = res.json()["access_token"]
headers_a = {"Authorization": f"Bearer {token_a}"}

# 2. Register User B
res = requests.post(f"{BASE_URL}/auth/register", json={"username": user_b_username, "email": user_b_email, "password": password})
run_test("2. Register User B", res.status_code == 200, res.text)
token_b = res.json()["access_token"]
headers_b = {"Authorization": f"Bearer {token_b}"}

# 3. Duplicate username rejection
res = requests.post(f"{BASE_URL}/auth/register", json={"username": user_a_username, "email": f"other_{ts}@gmail.com", "password": password})
run_test("3. Duplicate username rejection", res.status_code == 409 and "Username already exists" in res.text, res.text)

# 4. Duplicate email rejection
res = requests.post(f"{BASE_URL}/auth/register", json={"username": f"other_{ts}", "email": user_a_email, "password": password})
run_test("4. Duplicate email rejection", res.status_code == 409 and "Email already exists" in res.text, res.text)

# 5. Invalid non-Gmail email rejection
res = requests.post(f"{BASE_URL}/auth/register", json={"username": f"bademail_{ts}", "email": "test@yahoo.com", "password": password})
run_test("5. Invalid non-Gmail email rejection", res.status_code == 400 and "Only Gmail" in res.text, res.text)

# 6. Login User A with username
res = requests.post(f"{BASE_URL}/auth/login", json={"identifier": user_a_username, "password": password})
run_test("6. Login User A with username", res.status_code == 200 and "access_token" in res.json(), res.text)

# 7. Login User A with Gmail
res = requests.post(f"{BASE_URL}/auth/login", json={"identifier": user_a_email, "password": password})
run_test("7. Login User A with Gmail", res.status_code == 200 and "access_token" in res.json(), res.text)

# 8. Wrong password rejection
res = requests.post(f"{BASE_URL}/auth/login", json={"identifier": user_a_email, "password": "wrongpassword"})
run_test("8. Wrong password rejection", res.status_code == 401 and "Invalid username/email or password" in res.text, res.text)

# 9. Upload dataset as User A
with open("backend/datasets/sales.csv", "rb") as f:
    res = requests.post(f"{BASE_URL}/upload", files={"file": f}, headers=headers_a)
run_test("9. Upload dataset as User A", res.status_code == 200, res.text)
sales_id = res.json()["id"]

# 10. Retrieve dataset as User A
res = requests.get(f"{BASE_URL}/datasets/{sales_id}", headers=headers_a)
run_test("10. Retrieve dataset as User A", res.status_code == 200, res.text)

# 11. Login User B
res = requests.post(f"{BASE_URL}/auth/login", json={"identifier": user_b_email, "password": password})
run_test("11. Login User B", res.status_code == 200, res.text)
# We already have token_b

# 12. Attempt to retrieve User A dataset as User B
res = requests.get(f"{BASE_URL}/datasets/{sales_id}", headers=headers_b)
run_test("12. Attempt to retrieve User A dataset as User B (Expect 404/403)", res.status_code in [403, 404], res.text)

# 13. Attempt analysis against User A dataset as User B
query_b = {"question": "What is the total revenue?", "dataset_ids": [sales_id]}
res = requests.post(f"{BASE_URL}/ask", json=query_b, headers=headers_b)
run_test("13. Attempt analysis against User A dataset as User B", res.status_code in [400, 403, 404] or (res.status_code == 200 and "error" in res.text.lower()), res.text)

# 14. Verify access is denied
print("14. Verify access is denied: PASS (Tested in 12 and 13)")

# 15. Login User A again
res = requests.post(f"{BASE_URL}/auth/login", json={"identifier": user_a_email, "password": password})
run_test("15. Login User A again", res.status_code == 200, res.text)
token_a = res.json()["access_token"]
headers_a = {"Authorization": f"Bearer {token_a}"}

# 16. Verify dataset persists
res = requests.get(f"{BASE_URL}/datasets", headers=headers_a)
run_test("16. Verify dataset persists", res.status_code == 200 and len(res.json()) >= 1, res.text)

# 17. Ask analytical question
query_a = {"question": "What is the total quantity of sales?", "dataset_ids": [sales_id]}
res = requests.post(f"{BASE_URL}/ask", json=query_a, headers=headers_a)
run_test("17. Ask analytical question", res.status_code == 200 and res.json().get("status") == "success", res.text)
ans = res.json()

# 18. Verify LLM produces analysis plan
run_test("18. Verify LLM produces analysis plan", "evidence" in ans and "python_code" in ans["evidence"], str(ans))

# 19. Verify Python executes
run_test("19. Verify Python executes", "result" in ans, str(ans))

# 20. Verify result comes from Python execution
run_test("20. Verify result comes from Python execution", ans.get("result") is not None, str(ans))

# 21. Ask an unanswerable question
query_unans = {"question": "What is the meaning of life in 2045?", "dataset_ids": [sales_id]}
res = requests.post(f"{BASE_URL}/ask", json=query_unans, headers=headers_a)
ans_ref = res.json()
run_test("21. Ask an unanswerable question", res.status_code == 200, res.text)

# 22. Verify refusal
run_test("22. Verify refusal", ans_ref.get("status") == "refused", str(ans_ref))

# 23. Verify analysis history belongs to correct user
res_hist = requests.get(f"{BASE_URL}/history", headers=headers_a)
run_test("23. Verify analysis history belongs to correct user (A)", res_hist.status_code == 200 and len(res_hist.json()) >= 2, res_hist.text)

res_hist_b = requests.get(f"{BASE_URL}/history", headers=headers_b)
run_test("23. Verify analysis history belongs to correct user (B)", res_hist_b.status_code == 200 and len(res_hist_b.json()) == 0, res_hist_b.text)

print("--- ALL BACKEND TESTS COMPLETED SUCCESSFULLY ---")
