# Learning artifact: demonstrating generator vs list memory behaviour
# -------------------------------------------------------------------#

# # List approach
# def read_as_list(n):
#     result = []
#     for i in range(n):
#         result.append(i*2)
#     return result


# # Generator approach
# def read_as_generator(n):
#     for i in range(n):
#         yield i*2


# # --- Compare the difference ---
# # Using list
# numbers_list = read_as_list(10)
# print(type(numbers_list))
# print(numbers_list)

# # Using generator
# number_gen = read_as_generator(10)
# print(type(number_gen))
# print(number_gen)

# # Test generator
# print(number_gen)
# print(next(number_gen))
# print(next(number_gen))
# print(next(number_gen))


# for num in read_as_generator(5):
#     print(num)

# -------------------------------------------- #
# -------- Prove the memory difference --------#
import sys
numbers_list = list(range(1000000))
print(f"List size: {sys.getsizeof(numbers_list):,} bytes")

numbers_gen = (i for i in range(1000000))
print(f"Generator size: {sys.getsizeof(numbers_gen):,} bytes")
