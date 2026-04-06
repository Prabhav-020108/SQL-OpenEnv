# SQL-OpenEnv
Baseline Results
[START] task=select_basics env=sql_env model=Qwen/Qwen2.5-72B-Instruct
[STEP] step=1 action=SELECT name, email FROM customers WHERE city = 'New York' ORDER BY name ASC reward=1.00 done=true error=null
[END] success=true steps=1 score=1.000 rewards=1.00
[START] task=aggregate_filter env=sql_env model=Qwen/Qwen2.5-72B-Instruct
[STEP] step=1 action=SELECT c.name, SUM(o.amount) AS total_spent FROM customers c JOIN orders o ON c.id = o.customer_id G reward=1.00 done=true error=null
[END] success=true steps=1 score=1.000 rewards=1.00
[START] task=multi_join env=sql_env model=Qwen/Qwen2.5-72B-Instruct
[STEP] step=1 action=SELECT      strftime('%Y-%m', orders.order_date) AS month,     categories.name AS category_name,     reward=1.00 done=true error=null
[END] success=true steps=1 score=1.000 rewards=1.00