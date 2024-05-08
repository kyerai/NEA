def hash_password(password):
    # Define a list of characters to use for hashing
    characters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+-=[]{}|;:,.<>/?"
    
    # Initialize the hash value
    hash_value = 0
    
    # Iterate over each character in the password
    for char in password:
        # Add the ASCII value of the character to the hash value
        hash_value += ord(char)
        
        # Perform some bitwise operations on the hash value
        hash_value = (hash_value << 5) - hash_value + ord(char)
    
    # Return the hashed password
    return hash_value

def unhash_password(hashed_password, hash_value):
    # Define a list of characters to use for hashing
    characters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+-=[]{}|;:,.<>/?"
    
    # Initialize the password
    password = ""
    
    # Iterate over each character in the hashed password
    for char in hashed_password:
        # Perform some bitwise operations to reverse the hashing
        char_value = (char + hash_value) // ord(char)
        
        # Find the corresponding character in the list of characters
        password += characters[char_value % len(characters)]
    
    # Return the unhashed password
    return password

# Get the password from the user
password = input("Enter your password: ")

# Hash the password
hashed_password = hash_password(password)

# Print the hashed password
print("Hashed password:", hashed_password)

# Unhash the password
unhashed_password = unhash_password(hashed_password)

# Print the unhashed password
print("Unhashed password:", unhashed_password)