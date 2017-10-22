# optihash.py v 0.30 to be used with Python3.5 or better
# Optimized CPU-miner for Optipoolware based pool mining only
# Copyright Hclivess, Primedigger, Maccaspacca, SylvainDeaure 2017
# .

import time, socks, connections, sys, os, math
from multiprocessing import Process, freeze_support, Queue
from random import getrandbits
from hashlib import sha224
from functools import lru_cache as cache

# load config
lines = [line.rstrip('\n') for line in open('miner.txt')]
for line in lines:
	if "port=" in line:
		port = line.split('=')[1]
	if "mining_ip=" in line:
		mining_ip_conf = line.split('=')[1]
	if "mining_threads=" in line:
		mining_threads_conf = line.strip('mining_threads=')
	if "tor=" in line:
		tor_conf = int(line.strip('tor='))
	if "miner_address=" in line:
		self_address = line.split('=')[1]
	if "nonce_time=" in line:
		nonce_time = int(line.split('=')[1])
	if "miner_name=" in line:
		mname = line.split('=')[1]
	if "hashcount=" in line:
		hashcount = int(line.split('=')[1])

# load config

bin_format_dict = dict((x, format(ord(x), '8b').replace(' ', '0')) for x in '0123456789abcdef')

@cache(maxsize=None)
def getarr():
	# This is how we will *always* sample a backyard.
	do_arr = [('%0x' % getrandbits(32)) for i in range(nonce_time*hashcount)]
	return do_arr

try_arr = getarr()

def bin_convert(string):
	return ''.join(bin_format_dict[x] for x in string)

def bin_convert_orig(string):
	return ''.join(format(ord(x), '8b').replace(' ', '0') for x in string)

def diffme(pool_address,nonce,db_block_hash):

	diff_broke = 0
	diff = 0

	while diff_broke == 0:

		mining_hash = bin_convert(sha224((pool_address + nonce + db_block_hash).encode("utf-8")).hexdigest())
		mining_condition = bin_convert(db_block_hash)[0:diff]
		if mining_condition in mining_hash:
			diff_result = diff
			diff = diff + 1
		else:
			diff_broke = 1
	try:

		return diff_result

	except:
		pass

def miner(q, pool_address, db_block_hash, diff, mining_condition, mining_condition_bin, netdiff, hq, thr, dh):

	tries = 0
	my_hash_rate = 0
	address = pool_address
	count = 0
	timeout = time.time() + nonce_time
	#print(pool_address)
	
	while time.time() < timeout:
		try:
			t1 = time.time()
			tries = tries + 1	
			# generate the "address" of a random backyard that we will sample in this try
			seed = ('%0x' % getrandbits(128-32))
			# this part won't change, so concat once only
			prefix = pool_address+seed
			# This is where the actual hashing takes place
			possibles = [nonce for nonce in try_arr if mining_condition in (sha224((prefix + nonce + db_block_hash).encode("utf-8")).hexdigest())]
			#hashrate calculation
			try:
				t2 = time.time()
				h1 = int(((nonce_time*hashcount) / (t2 - t1))/1000)
			except Exception as e:
				h1 = 1
			#hashit bit
			
			if possibles:
				#print(possibles)
				for nonce in possibles:
					# add the seed back to get a full 128 bits nonce
					nonce = seed + nonce
					xdiffx = diffme(str(address[:56]),str(nonce),db_block_hash)
					
					if xdiffx < diff:
						pass
					else:
						print("Thread {} solved work in {} cycles - YAY!".format(q, tries))
						
						wname = "{}{}".format(mname, str(q))
						print("{} running at {} kh/s".format(wname,str(h1)))
						block_send = []
						del block_send[:]  # empty
												
						block_timestamp = '%.2f' % time.time()
						block_send.append((block_timestamp, nonce, db_block_hash, netdiff, xdiffx, dh, mname, thr, str(q)))
						print("Sending solution: {}".format(block_send))

						tries = 0

						# submit mined nonce to pool

						try:
							s1 = socks.socksocket()
							if tor_conf == 1:
								s1.setproxy(socks.PROXY_TYPE_SOCKS5, "127.0.0.1", 9050)
							s1.connect((mining_ip_conf, int(port)))  # connect to pool
							print("Miner: connected to pool, proceeding to submit solution")
							connections.send(s1, "block", 10)
							connections.send(s1, self_address, 10)
							connections.send(s1, block_send, 10)
							print("Miner: solution submitted to pool")
							time.sleep(0.2)
							s1.close()

						except Exception as e:
							print("Miner: Could not submit solution to pool")
							pass	

		except Exception as e:
			print(e)
			time.sleep(0.1)
			raise

	my_hash_rate = str(h1)
	hq.put(str(h1))

def runit():

	connected = 0
	dh = 0
	hq = Queue()

	while True:
		try:
			
			s = socks.socksocket()
			if tor_conf == 1:
				s.setproxy(socks.PROXY_TYPE_SOCKS5, "127.0.0.1", 9050)
			s.connect((mining_ip_conf, int(port)))  # connect to pool
			connections.send(s, "getwork", 10)
			work_pack = connections.receive(s, 10)
			db_block_hash = (work_pack[-1][0])
			diff = int((work_pack[-1][1]))
			paddress = (work_pack[-1][2])
			netdiff = int((work_pack[-1][3]))
			s.close()
			connected = 1
	
			mining_condition_bin = bin_convert_orig(db_block_hash)[0:diff]
			diff_hex = math.ceil((diff / 8) - 1)
			mining_condition = db_block_hash[0:diff_hex]
	
			instances = range(int(mining_threads_conf))
			thr = int(mining_threads_conf)
	
			for q in instances:
				p = Process(target=miner, args=(str(q + 1), paddress, db_block_hash, diff, mining_condition, mining_condition_bin, netdiff, hq, thr, dh))
				p.daemon = True
				p.start()
			print("{} miners searching for solutions at difficulty {} and condition {}".format(mining_threads_conf,str(diff),str(mining_condition)))
	
			time.sleep(nonce_time)
			
			for q in instances:
				p.join()
				p.terminate()
				
			results = [int(hq.get()) for q in instances]
			dh = sum(results)
			print("Current total hashrate is {} kh/s".format(str(dh)))
			
		except Exception as e:
			print(e)
			print("Miner: Unable to connect to pool check your connection or IP settings.")
			time.sleep(1)
	# verify connection
	
if __name__ == '__main__':
	freeze_support()  # must be this line, dont move ahead
	
	runit()
