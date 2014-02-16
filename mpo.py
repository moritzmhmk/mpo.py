import re, struct, argparse

marker_prefix = b"\xff"
SOI = b"\xd8"
APP0 = b"\xe0"
APP1 = b"\xe1"
APP2 = b"\xe2"
SOS = b"\xda"
EOI = b"\xd9"

restart_types = [b"\xD0",b"\xD1",b"\xD2",b"\xD3",b"\xD4",b"\xD5",b"\xD6",b"\xD7"]
types_without_length = restart_types+[b"\x00",b"\x01",SOI,EOI]


def read_compressed_image_data(file):
	start_position = file.tell()
	content = file.read()
	file.seek(start_position)
	
	match = re.search(b"\xff[^"+b"".join(restart_types+[b"\x00"])+b"]", content)
	if not match:
		return content
	length_of_content = match.start()
	return file.read(length_of_content)
	
			

def read_next_segment(file_object):
	while True:
		byte = file_object.read(1)
		if not byte:
			break
		if byte == marker_prefix:
			type = file_object.read(1)
			if type == SOS:
				yield type, -1, read_compressed_image_data(file_object)
			elif not type in types_without_length:
				high = ord(file_object.read(1))
				low = ord(file_object.read(1))
				length = (high<<8) + low
				#print(high,low,length)
				yield type, length, file_object.read(length-2)
			else:
				yield type, -1, b""
		else:
			print("FAIL\t",byte)
		


def getExifAndData(img_file):
	imgData=b""
	imgExif=b""
	for type, length, data in read_next_segment(img_file):
		print("{0}\t{1}".format(type,length))
		print("length of data:",len(data))
		print()
		if not type in [SOI, APP0, APP1, EOI]:
			imgData+=(marker_prefix+type)
			if not length==-1:
				imgData += struct.pack('>H', length)
			imgData+=(data)
		elif type==APP1:
			imgExif+=(marker_prefix+type)
			if not length==-1:
				imgExif += struct.pack('>H', length)
			imgExif+=(data)
	print("data_len", len(imgData))
	print("exif_len", len(imgExif))
	return imgData, imgExif

def mpoFromJPG(imgLfile,imgRfile):
	imgLdata,imgLexif = getExifAndData(imgLfile)
	imgRdata,imgRexif = getExifAndData(imgRfile)

	_imgL_size = len(marker_prefix+SOI)+len(imgLexif)+172+len(imgLdata)+len(marker_prefix+EOI)
	imgL_size = struct.pack('<i', _imgL_size)
	print(_imgL_size,imgL_size)

	_imgL_offset=0
	imgL_offset=struct.pack('<i', _imgL_offset)

	_imgR_size = len(marker_prefix+SOI)+len(imgRexif)+98+len(imgRdata)+len(marker_prefix+EOI)
	imgR_size = struct.pack('<i', _imgR_size)
	print(_imgR_size,imgR_size)

	_imgR_offset = (172-8)+len(imgLdata)+len(marker_prefix+EOI)
	imgR_offset = struct.pack('<i', _imgR_offset)

	imgLmpf =marker_prefix+APP2
	imgLmpf+=b"\x00\xaa"#APP2 field length
	imgLmpf+=b"\x4d\x50\x46\x00"#"MPF"
	imgLmpf+=b"\x49\x49\x2a\x00"#ENDIAN [little]
	imgLmpf+=b"\x08\x00\x00\x00"#OFFSET to first IFD
	imgLmpf+=b"\x03\x00"#COUNT
	imgLmpf+=b"\x00\xB0\x07\x00\x04\x00\x00\x00\x30\x31\x30\x30"#VERSION "0100"
	imgLmpf+=b"\x01\xB0\x04\x00\x01\x00\x00\x00\x02\x00\x00\x00"#NUMBER OF IMAGES
	imgLmpf+=b"\x02\xB0\x07\x00\x20\x00\x00\x00\x32\x00\x00\x00"#MP ENTRY
	imgLmpf+=b"\x52\x00\x00\x00"#OFFSET OF NEXT IFD

	imgLmpf+=b"\x02\x00\x02\x20" + imgL_size + imgL_offset + b"\x00\x00\x00\x00"#IFD
	imgLmpf+=b"\x02\x00\x02\x00" + imgR_size + imgR_offset +  b"\x00\x00\x00\x00"#IFD

	imgLmpf+=b"\x05\x00\x00\xB0\x07\x00\x04\x00\x00\x00\x30\x31\x30\x30\x01\xB1\x04\x00\x01\x00\x00\x00\x01\x00\x00\x00\x04\xB2\x04\x00\x01\x00\x00"
	imgLmpf+=b"\x00\x01\x00\x00\x00\x05\xB2\x0A\x00\x01\x00\x00\x00\x94\x00\x00\x00\x06\xB2\x05\x00\x01\x00\x00\x00\x9C\x00\x00\x00\x52\x00\x00\x00"

	imgLmpf+=b"\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF"#!?

	print("LEFT APP0", len(imgLmpf))

	imgRmpf =marker_prefix+APP2
	imgRmpf+=b"\x00\x60"#APP2 field length (*)
	imgRmpf+=b"\x4d\x50\x46\x00"#"MPF"
	imgRmpf+=b"\x49\x49\x2a\x00"#ENDIAN [little]
	imgRmpf+=b"\x08\x00\x00\x00"#OFFSET to first IFD
	imgRmpf+=b"\x05\x00"#COUNT (*)
	imgRmpf+=b"\x00\xB0\x07\x00\x04\x00\x00\x00\x30\x31\x30\x30"#VERSION "0100"
	imgRmpf+=b"\x01\xB0\x04\x00\x01\x00\x00\x00\x02\x00\x00\x00"#NUMBER OF IMAGES
	imgRmpf+=b"\x04\xB2\x04\x00\x01\x00\x00\x00\x01\x00\x00\x00"#BaseViewpointNum
	imgRmpf+=b"\x05\xB2\x0A\x00\x01\x00\x00\x00\x4A\x00\x00\x00"#ConvergenceAngle
	imgRmpf+=b"\x06\xB2\x05\x00\x01\x00\x00\x00\x52\x00\x00\x00"#BaselineLength


	imgRmpf+=b"\x52\x00\x00\x00"#OFFSET OF NEXT IFD

	imgRmpf+=b"\x1C\x00\x00\x00\xD0\x25\x24\x81\x1C\x00\x00\x00\xD0\x25\x24\x81"#!?

	print("RIGHT APP0", len(imgRmpf))

	mpo =marker_prefix+SOI+imgLexif+imgLmpf+imgLdata+marker_prefix+EOI
	mpo+=marker_prefix+SOI+imgRexif+imgRmpf+imgRdata+marker_prefix+EOI
	return mpo
if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument("left", help="path to left jpg image")
	parser.add_argument("right", help="path to right jpg image")
	parser.add_argument("out", help="path to save mpo image to")
	args = parser.parse_args()

	with open(args.left, "rb") as imgLfile, open(args.right, "rb") as imgRfile, open(args.out, "wb") as mpo_file:
		mpo_file.write(mpoFromJPG(imgLfile, imgRfile))
	