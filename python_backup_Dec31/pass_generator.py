import bcrypt
import codecs


print("Input password for website")
password = input().encode('utf-8')

hashed = bcrypt.hashpw(password, bcrypt.gensalt())      # Hash a password for the first time, with a randomly-generated salt

file = codecs.open("passw", "wb")
file.write(hashed)
file.close()
print("password saved")

