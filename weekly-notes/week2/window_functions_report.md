# Window Functions & Recursive CTEs — NYC Trips Dataset
**Dataset:** 500,000 synthetic NYC taxi trips  
**Database:** PostgreSQL 17 ([neon.tech](https://neon.com/))  
**Date:** March 2026

** A little note: the word record, data, and rows in this analysis might be used interchangeably.

## Setup
The Dataset is created synthetically with 500,000 rows for NYC Taxi Trips simple simulation  
The dataset sample can be seen in: [sample](../week2/dataset_top10_sample.csv).  
Here's the query:
```SQL
-- Create the table
CREATE TABLE trips (
    trip_id         SERIAL PRIMARY KEY,
    pickup_datetime TIMESTAMP,
    dropoff_datetime TIMESTAMP,
    pickup_zone     TEXT,
    dropoff_zone    TEXT,
    passenger_count INT,
    trip_distance   FLOAT,
    fare_amount     NUMERIC(10,2),
    tip_amount      NUMERIC(10,2),
    total_amount    NUMERIC(10,2),
    payment_type    TEXT
);
```

```SQL
-- Fill the table
INSERT INTO trips (
    pickup_datetime,
    dropoff_datetime,
    pickup_zone,
    dropoff_zone,
    passenger_count,
    trip_distance,
    fare_amount,
    tip_amount,
    total_amount,
    payment_type
)
SELECT
    -- random datetime in 2023
    timestamp '2023-01-01' + (random() * interval '364 days'),
    timestamp '2023-01-01' + (random() * interval '364 days') + interval '15 minutes',
    (ARRAY['JFK','LaGuardia','Midtown','Brooklyn','Bronx','Queens','Harlem','Staten Island'])[floor(random()*8+1)],
    (ARRAY['JFK','LaGuardia','Midtown','Brooklyn','Bronx','Queens','Harlem','Staten Island'])[floor(random()*8+1)],
    floor(random()*4+1)::int,
    round((random()*30)::numeric, 2),
    round((random()*80+5)::numeric, 2),
    round((random()*20)::numeric, 2),
    round((random()*100+5)::numeric, 2),
    (ARRAY['credit_card','cash','no_charge','dispute'])[floor(random()*4+1)]
FROM generate_series(1, 500000);
```

---

## Query 1 — Running Total of Revenue by Day

### Problem
What is the cumulative revenue over time across all trips in 2023?

### Query
```SQL
EXPLAIN ANALYZE
SELECT
    DATE(pickup_datetime) AS trip_date,
    SUM(total_amount) AS daily_revenue,
    SUM(SUM(total_amount)) OVER (
        ORDER BY DATE(pickup_datetime)
    ) AS running_total
FROM trips
GROUP BY DATE(pickup_datetime)
ORDER BY trip_date;
```

### EXPLAIN ANALYZE Output
```
QUERY PLAN
WindowAgg  (cost=69388.96..89388.92 rows=500000 width=68) (actual time=173.143..282.290 rows=364 loops=1)
  ->  GroupAggregate  (cost=69388.92..80638.92 rows=500000 width=36) (actual time=172.852..282.023 rows=364 loops=1)
        Group Key: (date(pickup_datetime))
        ->  Sort  (cost=69388.92..70638.92 rows=500000 width=10) (actual time=172.533..222.037 rows=500000 loops=1)
              Sort Key: (date(pickup_datetime))
              Sort Method: external merge  Disk: 10304kB
              ->  Seq Scan on trips  (cost=0.00..13513.00 rows=500000 width=10) (actual time=0.013..79.950 rows=500000 loops=1)
Planning Time: 0.106 ms
Execution Time: 284.223 ms
```

### Interpretation
Let's stroll around:  
From the execution perspective (Bottom-Up), what happened is:  
1. `Seq Scan` -> Scan the trips table sequentially. There is no any filter applied. So, `Seq Scan` is relatively cheap.
2. `Sort` -> Sort the records with (date(pickup_time)). So `GroupAggregate` can be processed efficiently. Notice that this operation `Sort Method: external merge  Disk: 10304kB`.
3. `GroupAggregate` -> Aggregating records per group for clause `SUM(total_amount)` based on `(date(pickup_datetime))`. We got `rows=364` since our data only contain records within 2023.
4. `WindowAgg` -> Performing the window function to get running total. 

- Why did the sort spill to disk?
    - The sort spilled to disk because sorting 500,000 rows by `DATE(pickup_datetime)` where it produces ~10MB of intermediate data, exceeding the default `work_mem` allocation. When `work_mem` is insufficient, PSQL writes sorted chunks to disk and merges them in passes with the external merge method.

- Why is WindowAgg cheap despite coming last?
    - It's relatively cheap operation since it only requires to calculate the total by summing previous total + current total.  
Illustration:
```
Row 1: running_total = 142,350.00  → store this value
Row 2: running_total = 142,350.00 + 138,920.00 = 281,270.00  → replace stored value
Row 3: running_total = 281,270.00 + 141,100.00 = 422,370.00  → replace stored value
```

- What does SUM(SUM(total_amount)) mean and why is it written that way?
    - The nested SUM operations is a consequence of the non-existent value of `daily_revenue` to begin with. So the inner `SUM(total_amount)` is to calculate daily_revenue.  
    - The outer SUM is the window function `SUM(SUM(total_amount)) OVER (ORDER BY DATE(pickup_datetime)) AS running_total`.
    - Importantly, `SUM(total_amount)` is computed only once during `GroupAggregate`. The result feeds both the `daily_revenue` output column and the WindowAgg input simultaneously. That's one calculation, two destinations.

---

## Query 2 — Rank Trips Within Each Zone by Fare

### Problem
Which trips were the most expensive within each pickup zone?

### Query
```sql
EXPLAIN ANALYZE
SELECT
    trip_id,
    pickup_zone,
    fare_amount,
    RANK() OVER (
        PARTITION BY pickup_zone
        ORDER BY fare_amount DESC
    ) AS rank_in_zone
FROM trips
ORDER BY pickup_zone, rank_in_zone
LIMIT 20;
```

### EXPLAIN ANALYZE Output
```
QUERY PLAN
Limit  (cost=43060.67..43063.73 rows=20 width=26) (actual time=821.436..828.176 rows=20 loops=1)
  ->  Incremental Sort  (cost=43060.67..119562.77 rows=500000 width=26) (actual time=821.435..828.172 rows=20 loops=1)
        Sort Key: pickup_zone, (rank() OVER (?))
        Presorted Key: pickup_zone
        Full-sort Groups: 1  Sort Method: top-N heapsort  Average Memory: 26kB  Peak Memory: 26kB
        Pre-sorted Groups: 1  Sort Method: top-N heapsort  Average Memory: 26kB  Peak Memory: 26kB
        ->  WindowAgg  (cost=33024.68..100007.79 rows=500000 width=26) (actual time=745.366..817.131 rows=62565 loops=1)
              ->  Gather Merge  (cost=33024.55..91257.79 rows=500000 width=18) (actual time=745.358..790.574 rows=62565 loops=1)
                    Workers Planned: 2
                    Workers Launched: 2
                    ->  Sort  (cost=32024.52..32545.36 rows=208333 width=18) (actual time=713.920..720.401 rows=21662 loops=3)
                          Sort Key: pickup_zone, fare_amount DESC
                          Sort Method: external merge  Disk: 5552kB
                          Worker 0:  Sort Method: external merge  Disk: 4664kB
                          Worker 1:  Sort Method: external merge  Disk: 4968kB
                          ->  Parallel Seq Scan on trips  (cost=0.00..9346.33 rows=208333 width=18) (actual time=0.006..70.846 rows=166667 loops=3)
Planning Time: 0.078 ms
Execution Time: 829.062 ms
```

### Interpretation
Let's stroll around:  
From the execution perspective (Bottom-Up), what happened is:
1. `Parallel Seq Scan` -> We have 3 workers running Parallel Seq Scan. Each worker scans its share of the full table (~166,667 rows each). The total across 3 loops equals the full 500,000 rows. PSQL estimates row counts before knowing the exact data distribution, which is why estimated rows differ slightly from actual.
2. `Sort` -> Sorting the records by pickup_zone and fare_amount DESC. This is our most costly operation. It uses three workers to sort with `external merge` and takes the longest to run. All three workers spilled to disk simultaneously (~5.5MB each, ~15MB total), competing for the same I/O bandwidth. This is why this step dominates the total execution time.
3. `Gather Merge` -> All sorted data is merged together to form a single table.
4. `WindowAgg` -> This is where the window function being processed. But, since the window function used is `RANK() OVER (...)`, it's not aggregation in traditional sense. It just takes each record, compare it with the previous record, and slap a rank into the record.
5. `Incremental Sort` -> This is a method that PSQL used to sort small chunk of records at a time, avoiding costly sorting operation by sorting the entire dataset. It's beneficial especially for `ORDER BY` and `LIMIT` queries.  
Since `pickup_zone` is already sorted from previous steps, Incremental Sort only needs to sort by the newly computed `rank_in_zone` value within each zone group  with `top-N heapsort` method, avoiding a full re-sort of the entire dataset.
This is why we see that `Parallel Seq Scan` scan the entire dataset (500k records), but in step `Sort`, only 64986 `(rows=21662 loops=3)` records returned to the process above it. In some cases, processes in PSQL doesn't wait for the process below it to send the complete result to run the their own task. Since we have `LIMIT 20` clause, it makes more sense to process the records just enough to get the 20 rows that we needed.

- What is `PARTITION BY` doing differently from `GROUP BY`?
    - `GROUP BY` groups rows and collapses each group into one result row, usually for aggregate function like `SUM()`, `AVG()`, or `COUNT()`. On the other hand, `PARTITION BY` used with window function, divides rows into partition for calculation but keep every original row in the output.

- How does `RANK()` behave with ties vs `ROW_NUMBER()` vs `DENSE_RANK()`?
    - In `QUERY PLAN` perspective, the plans are the same. The difference is:  
        - `RANK()` will give the same rank number to tied rows, with gaps. We might see the rank colum to be like [1,1,3,3,5,5,5,8].
        - `DENSE_RANK()` will give the same rank number to tied rows, with NO gaps. We might see the rank colum to be like [1,1,2,2,3,3,3,4].
        - `ROW_NUMBER()` will give an unique sequential number to each row. So, there will be no repeated number within the same partition.
    The trickier part is:
    ```SQL
    RANK() OVER (
        PARTITION BY pickup_zone
        ORDER BY fare_amount DESC
    ) AS rank_in_zone
    ```
    If we have have tied `fare_amount` within the same partition, both `RANK()` and `ROW_NUMBER()` might give undeterministic result. Let say we have a simple table and we use `RANK()`, observe the `trip_id`:
    | trip_id | fare_amount | rank |
    |---|---|---|
    | 101 | 90 | 2 |
    | 102 | 90 | 2 |

    On the next query, it might become:

    | trip_id | fare_amount | rank |
    |---|---|---|
    | 102 | 90 | 2 |
    | 101 | 90 | 2 |
    
    So, if we want to get the stable output, we should add another column in `ORDER BY`, like `trip_id` in our case. 
    ```SQL
    RANK() OVER (
    PARTITION BY pickup_zone
    ORDER BY fare_amount DESC, trip_id ASC
    ) AS rank_in_zone
    ```

    The non-determinism problem is silent. PSQL won't warn us. The query succeeds, returns results, and looks correct. You only discover the issue when downstream reports show different numbers on different days. This makes it one of the more dangerous gotchas in production pipelines.  
    The rule: any window function or `ORDER BY` clause should have a tiebreaker column that guarantees uniqueness. It's usually a primary key.
---

## Query 3 — 7-Day Moving Average of Daily Trip Count

### Problem
How does daily trip volume trend over time, smoothed over a 7-day window?

### Query
```sql
EXPLAIN ANALYZE
SELECT
    DATE(pickup_datetime) AS trip_date,
    COUNT(*) AS daily_trips,
    ROUND(AVG(COUNT(*)) OVER (
        ORDER BY DATE(pickup_datetime)
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 2) AS moving_avg_7day
FROM trips
GROUP BY DATE(pickup_datetime)
ORDER BY trip_date;
```

### EXPLAIN ANALYZE Output
```
QUERY PLAN
WindowAgg  (cost=67680.96..87680.92 rows=500000 width=44) (actual time=115.934..185.862 rows=364 loops=1)
  ->  GroupAggregate  (cost=67680.92..77680.92 rows=500000 width=12) (actual time=115.725..185.584 rows=364 loops=1)
        Group Key: (date(pickup_datetime))
        ->  Sort  (cost=67680.92..68930.92 rows=500000 width=4) (actual time=115.510..154.812 rows=500000 loops=1)
              Sort Key: (date(pickup_datetime))
              Sort Method: external merge  Disk: 5880kB
              ->  Seq Scan on trips  (cost=0.00..13513.00 rows=500000 width=4) (actual time=0.011..62.650 rows=500000 loops=1)
Planning Time: 0.099 ms
Execution Time: 186.780 ms
```

### Interpretation
Let's stroll around:  
From the execution perspective (Bottom-Up), what happened is:  
*This query plan is essentially the same as query 1 with one slightly different take.
1. `Seq Scan` -> Scan the trips table sequentially. There is no any filter applied. So, `Seq Scan` is relatively cheap.
2. `Sort` -> Sort the records with (date(pickup_time)). So `GroupAggregate` can be processed efficiently. Notice that this operation `Sort Method: external merge  Disk: 5880kB`.
3. `GroupAggregate` -> Aggregating records per group for clause `(COUNT(*)` based on `(date(pickup_datetime))`. producing one row per date. We get 364 rows since our data spans 2023 only.
4. `WindowAgg` -> Performing the window function to get `moving_avg_7day`. 

- What does ROWS BETWEEN 6 PRECEDING AND CURRENT ROW mean precisely?
    - It means take 6 prior rows and current row, then perform a calculation. In this case, on each row, calculate the average within the last 7 days, hence `moving_avg_7day`.

- How does the sliding window frame differ from Query 1's running total?
    - We don't really see it in QUERY PLAN. But essentially Running total (Query 1): The buffer only store 1 value at a time, holding one running sum. Memory stays constant. Meanwhile, moving average (Query 3): The buffer holds exactly 7 values maximum, regardless of how many rows the table has. Memory stays constant after the first 7 rows.
- What happens to the moving average in the first 6 rows?
    - PSQL will use partial window where PSQL just simply check whether it has enough values stored. If not, it will sums all the values in the current buffer and divides it by total number of values in the buffer.
    ```
        Day 1: AVG of 1 day   = COUNT(day1) / 1
        Day 2: AVG of 2 days  = (COUNT(day1) + COUNT(day2)) / 2
        ...
        Day 7: AVG of 7 days  = full window, all subsequent rows use full window.
    ```
---

## Query 4 — Recursive CTE (Zone Hierarchy)

### Problem
Given a parent-child zone hierarchy, retrieve all zones under a given borough at any depth.
We are going to find the hierarchy of Manhattan borough.

### Setup — create the hierarchy table
```SQL
CREATE TABLE zones (
    zone_id   INT PRIMARY KEY,
    zone_name TEXT,
    parent_id INT REFERENCES zones(zone_id)
);

INSERT INTO zones VALUES
-- Boroughs (top level, no parent)
(1, 'Manhattan',     NULL),
(2, 'Brooklyn',      NULL),
(3, 'Queens',        NULL),

-- Districts (children of boroughs)
(4, 'Midtown',       1),
(5, 'Harlem',        1),
(6, 'Downtown BK',   2),
(7, 'Flatbush',      2),
(8, 'JFK Area',      3),
(9, 'Flushing',      3),

-- Sub-zones (children of districts)
(10, 'Times Square', 4),
(11, 'Hell Kitchen', 4),
(12, 'East Harlem',  5),
(13, 'Red Hook',     6),
(14, 'Park Slope',   7),
(15, 'JFK Terminal', 8),
(16, 'Jamaica',      8);
```

### Query
```sql
EXPLAIN ANALYZE
WITH RECURSIVE zone_hierarchy AS (
    -- Part 1: anchor — the starting point
    SELECT zone_id, zone_name, 0 AS level
    FROM zones
    WHERE zone_id = 1

    UNION ALL

    -- Part 2: recursive member — join back to itself
    SELECT z.zone_id, z.zone_name, zh.level+1
    FROM zones z
    JOIN zone_hierarchy zh ON zh.zone_id = z.parent_id
)
SELECT * FROM zone_hierarchy;
```

### Output
```
QUERY PLAN
CTE Scan on zone_hierarchy  (cost=289.93..301.95 rows=601 width=40) (actual time=0.021..0.092 rows=6 loops=1)
  CTE zone_hierarchy
    ->  Recursive Union  (cost=0.15..289.93 rows=601 width=40) (actual time=0.019..0.089 rows=6 loops=1)
          ->  Index Scan using zones_pkey on zones  (cost=0.15..8.17 rows=1 width=40) (actual time=0.018..0.019 rows=1 loops=1)
                Index Cond: (zone_id = 1)
          ->  Hash Join  (cost=0.33..27.57 rows=60 width=40) (actual time=0.013..0.014 rows=2 loops=3)
                Hash Cond: (z.parent_id = zh.zone_id)
                ->  Seq Scan on zones z  (cost=0.00..22.00 rows=1200 width=40) (actual time=0.002..0.003 rows=16 loops=3)
                ->  Hash  (cost=0.20..0.20 rows=10 width=8) (actual time=0.006..0.006 rows=2 loops=3)
                      Buckets: 1024  Batches: 1  Memory Usage: 9kB
                      ->  WorkTable Scan on zone_hierarchy zh  (cost=0.00..0.20 rows=10 width=8) (actual time=0.001..0.001 rows=2 loops=3)
Planning Time: 0.142 ms
Execution Time: 0.126 ms
```

### Interpretation 
Let's stroll around:  
1. To get the recursion running, we need the base case that is going to kick-start/anchor our next iteration in recursive CTE.
2. Take a lot from `Recursive Union`. It has two processes. The first one is `Index Scan using zones_pkey on zones` which is our anchor with the query
```SQL
SELECT zone_id, zone_name, 0 AS level
    FROM zones
    WHERE zone_id = 1
```
3. The recursion occurs in the `Hash Join`.   
    `WorkTable` -> Temporary table for storing records from one level per iteration  
    `Hash`      -> Hash map of the current level parent.  
    `Seq Scan`  -> reads every row from the zones table and delivers them to `Hash Join`.
    `Hash Join` -> Match Seq Scan results against the Hash Map

    ```
    Iteration 1:
        WorkTable   = [1: Manhattan]
        Hash        = {1: Manhattan}
        Seq Scan    = reads every row from zones
        Hash Join   = Check if any records in the zones table matched parent_id = 1 | Found [Midtown, Harlem]. The output get sent to Recursive Union
        Recursive Union accumulates [Manhattan] into the final result and replaces WorkTable with [Midtown, Harlem] for the next iteration
    
        Iteration 2:
        WorkTable   = [4: Midtown, 5:Harlem]
        Hash        = {4: Midtown, 5:Harlem}
        Seq Scan    = reads every row from zones
        Hash Join   = Check if any records in the zones table's parent_id is in the Hash Map | Found [Times Square, Hell Kitchen, East Harlem]
        Recursive Union accumulates [Midtown, Harlem] into the final result and replaces WorkTable with [Times Square, Hell Kitchen, East Harlem] for the next iteration


        Iteration 3:
        WorkTable   = [Times Square, Hell Kitchen, East Harlem]
        Hash        = {10: Times Square, 11: Hell Kitchen, 12: East Harlem}
        Seq Scan    = reads every row from zones
        Hash Join   = Check if any records in the zones table's parent_id is in the Hash Map | Found [] -> Nothing.
        Recursive Union accumulates [Times Square, Hell Kitchen, East Harlem] into the final result and stopped.
    ```

4. `CTE Scan` -> Reads the final materialized result from `Recursive Union` and returns it as the query output.

- What are the two parts of a recursive CTE (anchor + recursive member)?
    - `Anchor` -> Our base case on what to look for to kick-start the iteration.
    - `Recursive member` -> Part of the query that repeatedly references the CTE itself to build the final result iteratively until the termination condition is met.

- How does Postgres know when to stop recursing?
    - When it finds nothing on the current iteration. Note that Recursive CTE can trigger infinite loops if written wrongly.

- Where would you use this pattern in a real logistics pipeline?
    - To find data with hierarchical nature like product hierarchies, logistics route planning, supply chain networks analysis, and many more.

---

## Key Takeaways
- Always add a tiebreaker column to window function `ORDER BY` to avoid silent non-deterministism in production.
- Recursive CTEs always materialize their result.
- Disk spills hurt more under concurrent load such as three workers spilling simultaneously share the same I/O bandwidth.
- Partial windows in the first N-1 rows of a moving average produce incomplete results. So, beware of it for analysis.
---

## What I Got Wrong
- I assumed that in first query, when we have two `SUM()` operations for daily revenue and running_total, it might be calculated twice.  
It actually is only calculated once.
```
Date: 2023-01-01, SUM(total_amount) = 142,350.00
                         ↙                ↘
          daily_revenue column      input to WindowAgg
               142,350.00            → running_total
```

- I assumed that UNION will solve a cycle in data problem like `zone A is parent of zone B, zone B is parent of zone A`.  
But it will be better if we track visited IDs explicitly.
```SQL
WITH RECURSIVE zone_hierarchy AS (
    SELECT zone_id, zone_name, 0 AS level,
           ARRAY[zone_id] AS visited_ids    -- track path
    FROM zones WHERE zone_id = 1

    UNION ALL

    SELECT z.zone_id, z.zone_name, zh.level + 1,
           zh.visited_ids || z.zone_id      -- append current id
    FROM zones z
    JOIN zone_hierarchy zh ON zh.zone_id = z.parent_id
    WHERE NOT z.zone_id = ANY(zh.visited_ids)  -- stop if already visited
)
SELECT zone_id, zone_name, level FROM zone_hierarchy;
```