from PIL import Image
import imagehash

img_1 = Image.open("images/a.png")
img_2 = Image.open("images/a.png")
hash0 = imagehash.average_hash(img_1)
hash1 = imagehash.average_hash(img_2) 

if hash0 - hash1 < 5:
	print("similar images")
else:
	print("not similar images")
