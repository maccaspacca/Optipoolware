# optihash.py v 0.10 to be used with Python3.5
# Optimized CPU-miner for Optipoolware based pool mining only
# Copyright Hclivess, Primedigger, Maccaspacca 2017
# .

import hashlib, time, socks, connections, sys, os, binascii
from multiprocessing import Process, freeze_support
from random import getrandbits
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
	if "max_diff=" in line:
		max_diff = int(line.split('=')[1])

# load config

bin_format_dict = dict((x, format(ord(x), '8b').replace(' ', '0')) for x in '0123456789abcdef')

def bin_convert(string):
	return ''.join(bin_format_dict[x] for x in string)

def bin_convert_orig(string):
	return ''.join(format(ord(x), '8b').replace(' ', '0') for x in string)

def getcondition(db_block_hash, mine_diff):

	mining_condition_bin = bin_convert_orig(db_block_hash)[0:mine_diff]

	mining_condition_test_bin = ''
	diff_hex = 0
	while (len(mining_condition_test_bin) < mine_diff):
		diff_hex += 1
		mining_condition_test_bin = bin_convert(db_block_hash[0:diff_hex])
	diff_hex -= 1

	mining_condition = db_block_hash[0:diff_hex]
	
	return mining_condition, mining_condition_bin
	
def diffme(pool_address,nonce,db_block_hash):

	diff_broke = 0
	diff = 0

	while diff_broke == 0:

		mining_hash = bin_convert(hashlib.sha224((pool_address + nonce + db_block_hash).encode("utf-8")).hexdigest())
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

def getbits(t):

	ret_bits = [('%0x' % getrandbits(32 * 4)) for i in range(t*10000)]

	return ret_bits

@cache(maxsize=None)
def miner(q, pool_address, db_block_hash, diff, mining_condition, mining_condition_bin):

	tries = 0
	my_hash_rate = 0
	# Compute the static part of the hash (this doesn't change if we change the nonce)
	start_hash = hashlib.sha224()
	start_hash.update(pool_address.encode("utf-8"))
	address = pool_address
	count = 0
	start_time = time.time()
	timeout = time.time() + nonce_time
	while time.time() < timeout:
		try:
			tries = tries + 1
			if diff > max_diff:
				print("Difficulty too high for efficiency....waiting")
				time.sleep(nonce_time)
			
			else:
			
				#try_arr = []
				try_arr = getbits(nonce_time)
				
				for i in range(nonce_time*10000):
				
					mining_hash_lib = start_hash.copy()
					mining_hash_lib.update((try_arr[i] + db_block_hash).encode("utf-8"))
					mining_hash = mining_hash_lib.hexdigest()

					# we first check hex diff, then binary diff
					if mining_condition in mining_hash:
						block_timestamp = '%.2f' % time.time()
						if mining_condition_bin in bin_convert(mining_hash):
							# recheck
							mining_hash_check = hashlib.sha224((address + try_arr[i] + db_block_hash).encode("utf-8")).hexdigest()
							if mining_hash_check != mining_hash or mining_condition_bin not in bin_convert_orig(
									mining_hash_check):
								print("FOUND solution, but hash doesn't match:", mining_hash_check, 'vs.', mining_hash)
								break
							else:
								print("Thread {} solved work in {} cycles - YAY!".format(q, tries))

							block_send = []
							del block_send[:]  # empty
							
							xdiffx = diffme(str(address[:56]),str(try_arr[i]),db_block_hash)

							block_send.append((block_timestamp, try_arr[i], xdiffx, diff, db_block_hash))
							print("Sending solution: {}".format(block_send))

							tries = 0

							# submit mined nonce to pool

							try:
								s1 = socks.socksocket()
								s1.settimeout(0.3)
								if tor_conf == 1:
									s1.setproxy(socks.PROXY_TYPE_SOCKS5, "127.0.0.1", 9050)
								s1.connect((mining_ip_conf, int(port)))  # connect to pool
								print("Miner: connected to pool, proceeding to submit solution")
								connections.send(s1, "block", 10)
								connections.send(s1, self_address, 10)
								connections.send(s1, block_send, 10)
								print("Miner: solution submitted to pool")
								print("Miner: solution difficulty = {}".format(str(xdiffx)))
								time.sleep(0.2)

							except Exception as e:
								print("Miner: Could not submit solution to pool")
								pass	
				count += 1

		except Exception as e:
			print(e)
			time.sleep(0.1)
			raise
	stop_time = time.time()
	time_diff = stop_time - start_time
	my_hash_rate = '%.2f' % ((float(count) / float(time_diff))*(nonce_time*10))
	print('Thread {} is finding solutions at difficulty {} for {} seconds. Running @ {} KHs'.format(str(q), diff, nonce_time, my_hash_rate))

def runit():
#if __name__ == '__main__':
	#freeze_support()  # must be this line, dont move ahead

	# verify connection
	connected = 0
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
			s.close()
			connected = 1
			
			mcond = getcondition(db_block_hash, diff)
			mining_condition = mcond[0]
			mining_condition_bin = mcond[1]
		
			instances = range(int(mining_threads_conf))
			#print(instances)
			for q in instances:
				p = Process(target=miner, args=(str(q + 1), paddress, db_block_hash, diff, mining_condition, mining_condition_bin))
				p.daemon = True
				p.start()
			print("{} miners started......".format(mining_threads_conf))
		
			time.sleep(nonce_time)
			
			for q in instances:
				p.join()
				p.terminate()
			
		except Exception as e:
			print(e)
			print("Miner: Unable to connect to pool check your connection or IP settings.")
			time.sleep(1)
	# verify connection
	
if __name__ == '__main__':
	freeze_support()  # must be this line, dont move ahead
	
	runit()
