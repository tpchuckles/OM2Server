import os,glob,subprocess,shlex,time,sys
from tqdm import tqdm
os.makedirs("DCIM",exist_ok=True)

ssid_camera = "E-M5MKIII-P-BJ9A19575"
ssid_home = "whats-in-the-bagginses?"
remote_path = "/media/T7/All Stuff/Pictures/Camera/"
sshpass = "sshpass -p doggo!"
user_ip = "artemis@192.168.0.23"
rsync = "rsync -rvHP DCIM/* "+user_ip+":'"+remote_path+"'"
batch_size = 1000

def main():
	global existing,images
	existing = ls_remote()							# connect to home network, run ls for files on server
	purge_local()
	images = connect_camera()						# connect to camera network, create camera object, list camera images
	local = [ f.split("/")[-1] for f in glob.glob("DCIM/*") ]
	for i in reversed(range(len(images))):			# filter images to those not already on the server
		if images[i].file_name.split("/")[-1] in existing+local:
			del images[i]
	print(len(existing),"/",len(existing)+len(images),"photos already backed up")
	for i in range(1000000):
		connect_wifi(ssid_camera)					# connect to camera
		downloading(i*batch_size)					# download batch
		connect_wifi(ssid_home)						# connect to home
		command(sshpass+" "+rsync,printing=True)	# backup batch
		existing = ls_remote()						# sanity check: make sure they made it
		purge_local()								# delete local

# Execute a command in the command line. caller is responsible for escaping everything (e.g. spaces and shit)
def command(c,printing=False):
	print(c)
	result = ""
	with os.popen(c) as stream:
		#result = stream.read()		# appears hung during rsync's long-running
		for line in stream:			# prints stream line-by-line, but rsync's progress updates now show as multiple lines
			if printing:
				print(line, end="")
			result+=line
		#while True:				# allegedly handles rsync progress updates, but doesn't actually
		#	char = stream.read(1)
		#	if not char:
		#		break
		#	if printing:
		#		sys.stdout.write(char)
		#	result+=char
		#	if char == '\r' or char == '\n':
		#		sys.stdout.flush()
	return result

# given a network name, try to connect until connection is confirmed
def connect_wifi(ssid,max_attempts=100):
	ct=0
	while which_wifi() != ssid:
		command("nmcli device wifi connect "+ssid)
		time.sleep(.5)
		ct+=1
		if ct>max_attempts:
			sys.exit()

# nmcli query, parsed, to determine which wifi network we're connected to
def which_wifi():
	result = command("nmcli")
	result = result.split("\n")
	for l in result:
		if "connected to" in l:
			print(l)
			return l.split("connected to")[1].split()[0].strip()
	print(result)
	return None

# list files in remote directory, returns file list of PNGs and ORFs. connects to home network if not connected
def ls_remote():
	connect_wifi(ssid_home)
	files = command(sshpass+" ssh "+user_ip+" 'ls "+remote_path.replace(" ","\\ ")+"'").split("\n")
	files = [ f for f in files if ".JPG" in f or ".ORF" in f ]
	return files

# list files on camera, creates camera object, returns image list. connects to camera network if not connected
camera = None
def connect_camera():
	connect_wifi(ssid_camera)
	global camera
	# https://github.com/joergmlpts/olympus-wifi ; https://github.com/tpchuckles/olyviewer/blob/main/olyviewer.py
	from olympuswifi.camera import OlympusCamera
	camera = OlympusCamera()
	return camera.list_images()

# loops through images, downloads to local, records downloads vs skipped (already on server)
def downloading(i=0):
	print("downloading",images[i].file_name,"-",images[i+batch_size].file_name)
	success = [] ; skipped = []
	for i,image in enumerate(tqdm(images[i:i+batch_size])):
		fi = image.file_name
		f = fi.split("/")[-1]
		fo = "DCIM/"+f
		if f in existing:
			skipped.append(f)
			continue
		im = camera.download_image(fi)
		with open(fo, 'wb') as fo:
			fo.write(im)
		success.append(f)
		existing.append(f)
	print("completed",len(success),"skipped",len(skipped),"of",batch_size)

# delete all local files already on the server
def purge_local():
	files = glob.glob("DCIM/*")
	for f in files:
		if f.split("/")[-1] in existing:
			os.remove(f)

main()
