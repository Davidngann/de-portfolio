# SQL Performance Analysis — NYC Trips Dataset
**Dataset:** 500,000 synthetic NYC taxi trips  
**Database:** PostgreSQL 17 ([neon.tech](https://neon.com/))  
**Date:** March 2026

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

## Query 1 — Function on Indexed Column (EXTRACT vs Range Filter)

### Problem
Let say we want to get all the rows from our db with `pickup_datetime` in 2023.
`pickup_datetime` also has been indexed since it got queried frequently.
It might looks fancy and cleaner if we use certain function like `EXTRACT (YEAR FROM pickup_datetime) = 2023`.
Sadly, using extra function might actually hurt the query performance.

### Query (before)
```sql
EXPLAIN ANALYZE
SELECT * FROM trips
WHERE EXTRACT(YEAR FROM pickup_datetime) = 2023;
```

### EXPLAIN ANALYZE Output (before)
```
Gather  (cost=1000.00..11638.00 rows=2500 width=74) (actual time=0.239..208.804 rows=500000 loops=1)
  Workers Planned: 2
  Workers Launched: 2
  ->  Parallel Seq Scan on trips  (cost=0.00..10388.00 rows=1042 width=74) (actual time=0.011..38.887 rows=166667 loops=3)
        Filter: (EXTRACT(year FROM pickup_datetime) = '2023'::numeric)
Planning Time: 0.083 ms
Execution Time: 229.175 ms
```

### Interpretation
- Scan type: Parallel Seq Scan
- Cost: (cost=1000.00..11638.00 rows=2500 width=74) (actual time=0.239..208.804 rows=500000 loops=1)
- Planning Time: 0.083 ms
- Execution Time: 229.175 ms

Pay attention to this part: `Gather  (cost=1000.00..11638.00 rows=2500 width=74) (actual time=0.239..208.804 rows=500000 loops=1)`  
`(cost=1000.00..11638.00 rows=2500 width=74)` is the result of PSQL estimation of the output.  
- The cost of 1000.00 is the start-up cost to do the query before first row can be returned. The number 1000 is typically appeared when we run the query with multiple workers.
- The cost of 11638.00 is the total cost needed to complete the query.  
- Now, the interesting part: `rows=2500`. Despite of the clean look of using EXTRACT(),  
By applying a function to the column in our case, it will disable the ability of PSQL to know beforehand how many data it should expect. To handle that, PSQL estimates by using a default `selectivity` which set to 0.5%.  
So, `500,000 * 0.5% = 2500`.
- Furthermore, PSQL might think this operation are going to cost a lot.  
So, it spins up more worker to perform the query.

### Fix Applied
```sql
EXPLAIN ANALYZE
SELECT * FROM trips
WHERE pickup_datetime >= '2023-01-01' AND pickup_datetime < '2024-01-01';
```

### EXPLAIN ANALYZE Output (after)
```
QUERY PLAN
Seq Scan on trips  (cost=0.00..14763.00 rows=499900 width=74) (actual time=0.013..48.158 rows=500000 loops=1)
  Filter: ((pickup_datetime >= '2023-01-01 00:00:00'::timestamp without time zone) AND (pickup_datetime < '2024-01-01 00:00:00'::timestamp without time zone))
Planning Time: 0.061 ms
Execution Time: 65.144 ms
```

### What changed and why
- Scan type changed from Parallel Seq Scan to Seq Scan because it can estimate, with higher confidence, how many rows it's going to visit and decided it doesn't require multiple workers.
- Estimate accuracy improved because by using the raw range, it can use the data collected in `pg_stats` to estimate with high confidence.
- Execution time: 
    - BEFORE:   - Planning Time: 0.083 ms - Execution Time: 229.175 ms
    - AFTER:    - Planning Time: 0.064 ms - Execution Time: 63.463 ms

```
Although, both queries benefit from page caching, the specific range filter is faster because accurate row estimates allowed the planner to use a single-worker sequential scan, avoiding the overhead of launching and coordinating parallel workers.

In summary, Imagine you are in the physical warehouse.  
The (before) query is like you know you need to traverse around the warehouse and check some locations. But you don't really know how many locations. So, you call multiple workers, split them and tell them to go around to check the locations given to them, the workers check and take something, go to the next location, and repeat.
The (after) query is like because you know roughly (with high confidence by checking `pg_stats`), you call up a single worker to go to all of the locations and check whether the item is within specification. If yes, take it.
```
---

## Query 2 — Missing Index on Filtered Column
### Problem
#### What actually happens under the hood when we filter and sort our data with unindexed columns?  
If we have a certain queries that is running frequently, we might see better performance (cheaper \$\$) by adding index to the frequently queried columns.  
Note that, even though index might help in many cases, it should be used strategically as PSQL might decide to not even use the index if it's not worth it.  
So, how do we know that PSQL uses index to perform our specific query?

### Query
```SQL
EXPLAIN ANALYZE
SELECT * FROM trips
WHERE pickup_zone = 'JFK'
ORDER BY fare_amount DESC;

-- To add index
CREATE INDEX IF NOT EXISTS idx_trips_zone_fare ON trips(pickup_zone, fare_amount DESC);

-- To drop index
DROP INDEX IF EXISTS idx_trips_zone_fare;
```

### EXPLAIN ANALYZE (before)
```SQL
QUERY PLAN
Gather Merge  (cost=12843.82..19113.45 rows=53736 width=74) (actual time=65.751..99.792 rows=62448 loops=1)
  Workers Planned: 2
  Workers Launched: 2
  ->  Sort  (cost=11843.79..11910.96 rows=26868 width=74) (actual time=57.505..60.335 rows=20816 loops=3)
        Sort Key: fare_amount DESC
        Sort Method: quicksort  Memory: 2996kB
        Worker 0:  Sort Method: quicksort  Memory: 2645kB
        Worker 1:  Sort Method: quicksort  Memory: 2803kB
        ->  Parallel Seq Scan on trips  (cost=0.00..9867.17 rows=26868 width=74) (actual time=0.008..40.414 rows=20816 loops=3)
              Filter: (pickup_zone = 'JFK'::text)
              Rows Removed by Filter: 145851
Planning Time: 0.085 ms
Execution Time: 102.218 ms
```
Let's stroll around:
From the execution perspective (Bottom-Up), what happened is:
1. `Parallel Seq Scan` -> We run a parallel seq scan which divided into three chunks (`loops=3`) -> We have three workers walkthrough the database and check on each row that they visit if `pickup_zone = 'JFK'`   
*HOLD ON! why three workers? I can only see two workers launched! -> I will explain later.  
2. `Sort` -> Now, each workers carry their own records/rows. Since we have `ORDER BY fare_amount DESC` clause, 
each worker is going to sort the records that they owned with `quicksort` method. Meaning, each worker use in-memory sorting method.
3. `Gather Merge` -> After each worker has their own sorted records, those records will be merged together with `K-way merge` with time complexity of _`O(n log K)`_ where n is total records and K is number of workers (lists). 


#### Why Three workers?   

It's stated that  
```
    Workers Planned: 2  
    Workers Launched: 2
```  
Then why I said three?
There is one more worker that doesn't explisitly named, which is the leader. The leader is the one who responsible for merging all of the records that each worker has sorted. But, rather than just waiting for data to come in for sorting, the leader is also come down to help other required processes such as seq scan.
We can also observe:
        Sort Method: quicksort  Memory: 2996kB
        Worker 0:  Sort Method: quicksort  Memory: 2645kB
        Worker 1:  Sort Method: quicksort  Memory: 2803kB
The first line is actually the leader doing the quicksort, utilizing 2996kB.


### EXPLAIN ANALYZE (after)
```SQL
QUERY PLAN
Sort  (cost=17654.81..17816.02 rows=64483 width=74) (actual time=60.225..69.603 rows=62448 loops=1)
  Sort Key: fare_amount DESC
  Sort Method: external merge  Disk: 5544kB
  ->  Bitmap Heap Scan on trips  (cost=1568.17..9637.20 rows=64483 width=74) (actual time=8.337..27.899 rows=62448 loops=1)
        Recheck Cond: (pickup_zone = 'JFK'::text)
        Heap Blocks: exact=7263
        ->  Bitmap Index Scan on idx_trips_zone_fare  (cost=0.00..1552.04 rows=64483 width=0) (actual time=7.532..7.532 rows=62448 loops=1)
              Index Cond: (pickup_zone = 'JFK'::text)
Planning Time: 10.936 ms
Execution Time: 72.796 ms
```
Let's stroll around:
From the execution perspective (Bottom-Up), what happened is:
1. `Bitmap Index Scan on idx_trips_zone_fare` -> After we add index `ON trips(pickup_zone, fare_amount DESC)`, and PSQL deems index scan is worth it, it starts by running bitmap index scan to get the actual location of each rows with index condition of `pickup_zone = 'JFK'` from our `WHERE` clause. 
2. `Bitmap Heap Scan` -> The collected pages and slots from step 1 will be visited and rechecked to get the actual data that we need.
3. `Sort` -> Finally, all the retrieved data is sorted based on `fare_amount DESC`, using external merge sorting method.

### Interpretation
- What is Bitmap Index Scan doing?  
    - To understand this, we need to understand how indexing works.  
    During the creation of index, PSQL generates new database objects that contains few things like the indexed key values, and the pointer/actual location of the data (`page, slot`).
    Example: If indexed key value = 42, and the pointer is (page 2, slot 5) -> (42 -> page 2, slot 5)
    So, during Bitmap Index Scan, the goal is to create the list of all location of the records with specific indexed key value. In the query which `WHERE pickup_zone = 'JFK'`. It will collect something like ('JFK', page 11, slot 14).

- What is Bitmap Heap Scan doing?
    - PSQL will retrieve all of the records from the list created by Bitmap Index Scan. The goal of this scan is to actually retrieve the data.
    - We can also observe `Heap Blocks: exact=7263`. It means that PSQL have the list of all of the precise record locations.
    - There is another type of heap block called `Lossy Heap Blocks`. It means that rather than storing the exact location of each records, PSQL will store the "lossy" information instead.
    Example: if exact heap block store something like ('JFK', page 11, slot 14), the information we have is `in page 11, we have one or more slots with the data we are looking for`. This is typically happen when the data we are looking for is too big to fit the allocated `work_mem`.

- Why did parallel workers disappear after indexing?
    - Because PSQL can estimate more accurately about the task at hand. In our case, PSQL deems that it only need one worker to do all the work.

- What was the external merge warning and what caused it?
    - External merge is what people called `spilled into disk` where rather than perform the task solely in-memory, it uses the disk to store the temporary data for the task. It happens when `work_mem` can't be used to contain all of the data required during the task.

- Lovely lesson from this analysis is that `running in parallel` or `more workers` don't necessarily mean better.
- Indexes help with filtering. But, they rarely help with full aggregations across an entire table.

---

## Query 3 — GROUP BY + ORDER BY Aggregation

### Problem
Is aggregation costly?
Will indexing help to reduce the cost of aggregation?

### Query
```SQL
EXPLAIN ANALYZE
SELECT pickup_zone, SUM(total_amount) as revenue
FROM trips
GROUP BY pickup_zone
ORDER BY revenue DESC;
```

### EXPLAIN ANALYZE Output
```QUERY PLAN
Sort  (cost=11390.45..11390.47 rows=8 width=40) (actual time=165.519..167.989 rows=8 loops=1)
  Sort Key: (sum(total_amount)) DESC
  Sort Method: quicksort  Memory: 25kB
  ->  Finalize GroupAggregate  (cost=11388.24..11390.33 rows=8 width=40) (actual time=165.502..167.982 rows=8 loops=1)
        Group Key: pickup_zone
        ->  Gather Merge  (cost=11388.24..11390.11 rows=16 width=40) (actual time=165.493..167.967 rows=24 loops=1)
              Workers Planned: 2
              Workers Launched: 2
              ->  Sort  (cost=10388.22..10388.24 rows=8 width=40) (actual time=158.453..158.454 rows=8 loops=3)
                    Sort Key: pickup_zone
                    Sort Method: quicksort  Memory: 25kB
                    Worker 0:  Sort Method: quicksort  Memory: 25kB
                    Worker 1:  Sort Method: quicksort  Memory: 25kB
                    ->  Partial HashAggregate  (cost=10388.00..10388.10 rows=8 width=40) (actual time=158.434..158.437 rows=8 loops=3)
                          Group Key: pickup_zone
                          Batches: 1  Memory Usage: 24kB
                          Worker 0:  Batches: 1  Memory Usage: 24kB
                          Worker 1:  Batches: 1  Memory Usage: 24kB
                          ->  Parallel Seq Scan on trips  (cost=0.00..9346.33 rows=208333 width=14) (actual time=0.005..20.603 rows=166667 loops=3)
Planning Time: 0.095 ms
Execution Time: 168.027 ms
```
### Interpretation
Let's stroll around:
From the execution perspective (Bottom-Up), what happened is:
1. `Parallel Seq Scan` -> We have three workers running paralle seq scan.
2. `Partial HashAggregate` -> rather than doing the aggregation after all of the records gathered, each worker performs aggregation only on the records they have.
3. `Sort` -> Each worker will sort the records in their allocated memory.
4. `Gather Merge` -> All of the records sorted and merged into one big table with partial aggregate information.
5. `Finalize GroupAggregate` -> The partial aggregate information from previous steps finally get merged.
6. `Sort` -> Final sort after we get the end result of group aggregation.

- Why does Sort by pickup_zone happen before the merge?
    - The sort by `pickup_zone` happens before `Gather Merge` for two reasons. First, `Gather Merge` requires pre-sorted input streams to perform its ordered merge efficiently.
    - Second, it allows `Finalize GroupAggregate` to process one zone at a time. All Brooklyn partial sums arrive consecutively, get combined, then move to the next zone. Without pre-sorting, Finalize would need to hold all zones in memory simultaneously.
    - Imagine we have three conveyor belts of various fruits merging into one single belt.  
    We are responsible to put each fruit into their respective buckets.
    It will be easier for us to process one type of fruit at a time, rather than multiple different fruits coming at us.
    [A, B, C, C, B, A, A, E, F, B, C] -> harder, requiring more buckets allocated to anticipate all of the fruits.
    [A, A, A, B, B, B, C, C, C, D, D] -> easier, we know we only need one bucket at a time. When new fruit comes, we just change to the new bucket.

- Why does Postgres use two-phase aggregation (Partial → Finalize)?
    - To prevent bottleneck by scanning all of the data all at once. This is when parallel work shines.

- What does `Batches: 1` tell you?
    - If we see batches > 1, it spilled to the disk. If it's happened, it doesn't always mean "BAD" if we run a rarely used query. But, it should generally be avoided for high frequency queries.  

- Will index help?
    - We can experiment and try to add sum_total as the index `CREATE INDEX IF NOT EXISTS idx_trips_total_amount ON trips(total_amount);`. But, the index will not be used because of aggregation function requires all records to be visited in our case.
    - If we put WHERE clause on our query, it will help by reducing number of rows PSQL needs to visit.
    - Since aggregation typically is important for business operations, it's impossible to avoid aggregation. There are many other ways to optimize for this type of problems, but it's beyond the scope of my current analysis.

---

## Key Takeaways
* Indexing is useful to pull records with the query that doesn't need to visit all of the records.
* Always check how the query perform, not how the query looks.
* Narrow down what we are looking for. It can be by selecting only specific columns or put WHERE clause.
* Spinning up multiple workers for parallel works is not always resulting in better performance.
* We can tune our PSQL engine to perfom better by setting `work_mem` appropriately. If it's too low, sorts and hash operations may spill to temporary disk files. If it's too high, total memory usage can grow very quickly across concurrent queries and operations, which can create memory pressure or even out-of-memory(OOM) errors.



## What I Got Wrong
- I assumed ANALYZE would fix the EXTRACT row estimate. It doesn't.  
  ANALYZE collects statistics on raw column values, not function outputs.  
  The 2,500 estimate is a hardcoded default selectivity, not a statistics problem.

- I assumed the range filter query would use the datetime index. It didn't.  
  with 100% of rows matching, a Seq Scan is cheaper than 500,000 random index jumps.  

- I assumed higher work_mem would significantly improve performance.  
  The sort time improved but total execution stayed similar because disk spills at small scale are cheap.  
  `work_mem` wins at large scale on slower storage.