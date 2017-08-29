import socketserver, connections, time, options, log, sqlite3, socks, hashlib, random, re, keys, base64, sys, os, math
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA
from Crypto import Random
import threading

config = options.Get()
config.read()
debug_level = config.debug_level_conf
port = config.port
genesis_conf = config.genesis_conf
verify_conf = config.verify_conf
thread_limit_conf = config.thread_limit_conf
rebuild_db_conf = config.rebuild_db_conf
debug_conf = config.debug_conf
node_ip_conf = config.node_ip_conf
purge_conf = config.purge_conf
pause_conf = config.pause_conf
ledger_path_conf = config.ledger_path_conf
hyperblocks_conf = config.hyperblocks_conf
warning_list_limit_conf = config.warning_list_limit_conf
tor_conf = config.tor_conf
debug_level_conf = config.debug_level_conf
allowed = config.allowed_conf
pool_ip_conf = config.pool_ip_conf
sync_conf = config.sync_conf
pool_percentage_conf = config.pool_percentage_conf
mining_threads_conf = config.mining_threads_conf
diff_recalc_conf = config.diff_recalc_conf
pool_conf = config.pool_conf
ram_conf = config.ram_conf
pool_address = config.pool_address_conf
version = config.version_conf

# load config


#(port, genesis_conf, verify_conf, version_conf, thread_limit_conf, rebuild_db_conf, debug_conf, purge_conf, pause_conf, ledger_path_conf, hyperblocks_conf, warning_list_limit_conf, tor_conf, debug_level_conf, allowed, mining_ip_conf, sync_conf, mining_threads_conf, diff_recalc_conf, pool_conf, pool_address, ram_conf, pool_percentage_conf, node_ip_conf) = options.read()
(key, private_key_readable, public_key_readable, public_key_hashed, address) = keys.read() #import keys
app_log = log.log("pool.log",debug_level_conf)

# load config
try:
	
	lines = [line.rstrip('\n') for line in open('pool.txt')]
	for line in lines:
		try:
			if "mine_diff=" in line:
				mdiff = int(line.split('=')[1])
		except Exception as e:
			mdiff = 65
		try:
			if "min_payout=" in line:
				min_payout = float(line.split('=')[1])
		except Exception as e:
			min_payout = 1
		try:
			if "pool_fee=" in line:
				pool_fee = float(line.split('=')[1])
		except Exception as e:
			pool_fee = 0

except Exception as e:
	min_payout = 1
	mdiff = 65
	pool_fee = 0
# load config

bin_format_dict = dict((x, format(ord(x), '8b').replace(' ', '0')) for x in '0123456789abcdef')

def percentage(percent, whole):
	return int((percent * whole) / 100)
	
def checkdb():
	shares = sqlite3.connect('shares.db')
	shares.text_factory = str
	s = shares.cursor()
	s.execute("SELECT * FROM shares")
	present = s.fetchall()
	
	if not present:
		return False
	else:
		return True

# payout processing
def payout(payout_threshold,myfee):
	
	print("Minimum payout is {} Bismuth".format(str(payout_threshold)))
	print("Current pool fee is {} Percent".format(str(myfee)))
	
	shares = sqlite3.connect('shares.db')
	shares.text_factory = str
	s = shares.cursor()

	conn = sqlite3.connect(ledger_path_conf)
	conn.text_factory = str
	c = conn.cursor()

	#get unique addresses
	addresses = []
	for row in s.execute("SELECT * FROM shares"):
		shares_address = row[0]
		shares_value = row[1]
		shares_timestamp = row[2]

		if shares_address not in addresses:
			addresses.append(shares_address)
	print (addresses)
	#get unique addresses

	# get shares for address
	output_shares = []
	output_timestamps = []
	

	for x in addresses:
		# get mined block threshold
		s.execute("SELECT timestamp FROM shares WHERE address = ? ORDER BY timestamp ASC LIMIT 1", (x,))
		shares_timestamp = s.fetchone()[0]
		output_timestamps.append(float(shares_timestamp))
		# get mined block threshold

		s.execute("SELECT sum(shares) FROM shares WHERE address = ? AND paid != 1", (x,))
		shares_sum = s.fetchone()[0]

		if shares_sum == None:
			shares_sum = 0

		output_shares.append(shares_sum)
	

	print(output_shares)
	# get shares for address

	try:
		block_threshold = min(output_timestamps)
	except:
		raise
		block_threshold = time.time()
	print(block_threshold)

	#get eligible blocks
	reward_list = []
	for row in c.execute("SELECT * FROM transactions WHERE address = ? AND CAST(timestamp AS INTEGER) >= ? AND reward != 0", (address,) + (block_threshold,)):
		reward_list.append(float(row[9]))

	reward_total = sum(reward_list)
	#get eligible blocks

	shares_total = sum(output_shares) * ((100 - myfee)/100)

	try:
		reward_per_share = reward_total / shares_total
	except:
		reward_per_share = 0

	# calculate payouts
	#payout_threshold = 1
	payout_passed = 0
	for recipient, y in zip(addresses, output_shares):
		print(recipient)
		try:
			claim = float('%.8f' % (y * reward_per_share))
		except:
			claim = 0
		print(claim)


		if claim >= payout_threshold:
			payout_passed = 1
			openfield = "pool"
			keep = 0
			fee = float('%.8f' % float(0.01 + (float(claim) * 0.001) + (float(len(openfield)) / 100000) + (float(keep) / 10)))  # 0.1% + 0.01 dust
			#make payout

			timestamp = '%.2f' % time.time()
			transaction = (str(timestamp), str(address), str(recipient), '%.8f' % float(claim - fee), str(keep), str(openfield))  # this is signed
			# print transaction

			h = SHA.new(str(transaction).encode("utf-8"))
			signer = PKCS1_v1_5.new(key)
			signature = signer.sign(h)
			signature_enc = base64.b64encode(signature)
			print("Encoded Signature: {}".format(signature_enc.decode("utf-8")))

			verifier = PKCS1_v1_5.new(key)
			if verifier.verify(h, signature) == True:
				print("The signature is valid, proceeding to save transaction to mempool")

				mempool = sqlite3.connect('mempool.db')
				mempool.text_factory = str
				m = mempool.cursor()

				m.execute("INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?)", (str(timestamp), str(address), str(recipient), '%.8f' % float(claim - fee), str(signature_enc.decode("utf-8")), str(public_key_hashed), str(keep), str(openfield)))
				mempool.commit()  # Save (commit) the changes
				mempool.close()
				print("Mempool updated with a received transaction")

			s.execute("UPDATE shares SET paid = 1 WHERE address = ?",(recipient,))
			shares.commit()

	if payout_passed == 1:
		s.execute("UPDATE shares SET timestamp = ?", (time.time(),))
		shares.commit()

	# calculate payouts
	#payout
	s.close()

	
def commit(cursor):
	# secure commit for slow nodes
	passed = 0
	while passed == 0:
		try:
			cursor.commit()
			passed = 1
		except Exception as e:
			app_log.warning("Retrying database execute due to " + str(e))
			time.sleep(random.random())
			pass
			# secure commit for slow nodes


def execute(cursor, what):
	# secure execute for slow nodes
	passed = 0
	while passed == 0:
		try:
			# print cursor
			# print what

			cursor.execute(what)
			passed = 1
		except Exception as e:
			app_log.warning("Retrying database execute due to {}".format(e))
			time.sleep(random.random())
			pass
			# secure execute for slow nodes
	return cursor


def execute_param(cursor, what, param):
	# secure execute for slow nodes
	passed = 0
	while passed == 0:
		try:
			# print cursor
			# print what
			cursor.execute(what, param)
			passed = 1
		except Exception as e:
			app_log.warning("Retrying database execute due to " + str(e))
			time.sleep(0.1)
			pass
			# secure execute for slow nodes
	return cursor

	
def bin_convert(string):
	return ''.join(bin_format_dict[x] for x in string)

def bin_convert_orig(string):
	return ''.join(format(ord(x), '8b').replace(' ', '0') for x in string)

def s_test(testString):

	if testString.isalnum():
		if (re.search('[abcdef]',testString)):
			if len(testString) == 56:
				return True
	else:
		return False
	
def paydb():

	while True:
		time.sleep(3601)
		payout(min_payout,pool_fee)
		app_log.warning("Payout running...")
		
def worker():

	while True:
		time.sleep(10)
		global new_diff
		global new_hash

		conn = sqlite3.connect(ledger_path_conf,timeout=1)
		conn.text_factory = str
		c = conn.cursor()
		c.execute("SELECT * FROM transactions WHERE reward != 0 ORDER BY block_height DESC LIMIT 1;")
		block_last = c.fetchall()[0]
		blockhash = block_last[7]

		c.execute("SELECT * FROM transactions ORDER BY block_height DESC LIMIT 1")
		result = c.fetchall()[0]
		timestamp_last = float(result[1])
		block_height = int(result[0])

		c.execute("SELECT block_height FROM transactions WHERE CAST(timestamp AS INTEGER) > ? AND reward != 0",(timestamp_last - 86400,))  # 86400=24h
		blocks_per_1440 = len(c.fetchall())

		c.execute("SELECT difficulty FROM misc ORDER BY block_height DESC LIMIT 1")
		try:
			diff_block_previous = float(c.fetchone()[0])
		except:
			diff_block_previous = 45

		try:
			log = math.log2(blocks_per_1440 / 1440)
		except:
			log = math.log2(0.5 / 1440)

		difficulty = diff_block_previous + log  # increase/decrease diff by a little

		time_now = time.time()
		if time_now > timestamp_last + 300: #if 5 minutes have passed
			difficulty2 = percentage(90,difficulty)

		else:
			difficulty2 = difficulty

		if difficulty < 45 or difficulty2 < 45:
			difficulty = 45
			difficulty2 = 45

		new_diff = float(difficulty)
		new_diff = math.ceil(new_diff)
		#(float(difficulty), float(difficulty2))		
		new_hash = blockhash

		c.close()
		
		app_log.warning("Worker task...")
		
if not os.path.exists('shares.db'):
	# create empty mempool
	shares = sqlite3.connect('shares.db')
	shares.text_factory = str
	s = shares.cursor()
	execute(s, "CREATE TABLE IF NOT EXISTS shares (address, shares, timestamp, paid, rate, name)")
	execute(s, "CREATE TABLE IF NOT EXISTS nonces (nonce)") #for used hash storage
	app_log.warning("Created shares file")
	s.close()
	# create empty mempool
	
if checkdb():
	payout(min_payout,pool_fee)

diff_percentage = pool_percentage_conf

class MyTCPHandler(socketserver.BaseRequestHandler):

	def handle(self):
		from Crypto.PublicKey import RSA
		key = RSA.importKey(private_key_readable)
		
		self.allow_reuse_address = True

		peer_ip = self.request.getpeername()[0]

		try:
			data = connections.receive(self.request, 10)
	
			app_log.warning("Received: {} from {}".format(data, peer_ip))  # will add custom ports later

			if data == "getwork":  # sends the miner the blockhash and mining diff for shares
			
				work_send = []
				work_send.append((new_hash, mdiff, address, new_diff))

				connections.send(self.request, work_send, 10)
				
				print("Work package sent.... {}".format(str(new_hash)))

			elif data == "block":  # from miner to node

				# sock
				s1 = socks.socksocket()
				if tor_conf == 1:
					s1.setproxy(socks.PROXY_TYPE_SOCKS5, "127.0.0.1", 9050)
				s1.connect(("127.0.0.1", int(port)))  # connect to local node,
				# sock


				# receive nonce from miner
				miner_address = connections.receive(self.request, 10)
				
				if not s_test(miner_address):
					
					app_log.warning("Bad Miner Address Detected - Changing to default")
					miner_address = "92563981cc1e70d160c176edf368ea4bbc1d8d5ba63aceee99ef6ebd"
					#s1.close()
				
				else:
					
					app_log.warning("Received a solution from miner {} ({})".format(peer_ip,miner_address))

					block_nonce = connections.receive(self.request, 10)
					block_timestamp = (block_nonce[-1][0])
					nonce = (block_nonce[-1][1])
					mine_hash = ((block_nonce[-1][2])) # block hash claimed
					ndiff = ((block_nonce[-1][3])) # network diff when mined
					sdiffs = ((block_nonce[-1][4])) # actual diff mined
					mrate = ((block_nonce[-1][5])) # hash rate in khs
					wname = ((block_nonce[-1][6])) # worker name

					app_log.warning("Mined nonce details: {}".format(block_nonce))
					app_log.warning("Claimed hash: {}".format(mine_hash))
					app_log.warning("Claimed diff: {}".format(sdiffs))

					diff = int(ndiff)
					db_block_hash = mine_hash
					
					mining_hash = bin_convert_orig(hashlib.sha224((address + nonce + db_block_hash).encode("utf-8")).hexdigest())
					mining_condition = bin_convert_orig(db_block_hash)[0:diff]			

					if mining_condition in mining_hash:

						app_log.warning("Difficulty requirement satisfied for mining")
						app_log.warning("Sending block to node {}".format(peer_ip))

						mempool = sqlite3.connect("mempool.db")
						mempool.text_factory = str
						m = mempool.cursor()
						execute(m, ("SELECT * FROM transactions ORDER BY timestamp;"))
						result = m.fetchall()  # select all txs from mempool
						mempool.close()

						# include data
						block_send = []
						del block_send[:]  # empty
						removal_signature = []
						del removal_signature[:]  # empty

						for dbdata in result:
							transaction = (
								str(dbdata[0]), str(dbdata[1][:56]), str(dbdata[2][:56]), '%.8f' % float(dbdata[3]),
								str(dbdata[4]), str(dbdata[5]), str(dbdata[6]),
								str(dbdata[7]))  # create tuple
							# print transaction
							block_send.append(transaction)  # append tuple to list for each run
							removal_signature.append(str(dbdata[4]))  # for removal after successful mining

						# claim reward
						transaction_reward = tuple
						transaction_reward = (str(block_timestamp), str(address[:56]), str(address[:56]), '%.8f' % float(0), "0", str(nonce))  # only this part is signed!
						print(transaction_reward)

						h = SHA.new(str(transaction_reward).encode("utf-8"))
						signer = PKCS1_v1_5.new(key)
						signature = signer.sign(h)
						signature_enc = base64.b64encode(signature)

						if signer.verify(h, signature) == True:
							app_log.warning("Signature valid")

							block_send.append((str(block_timestamp), str(address[:56]), str(address[:56]), '%.8f' % float(0), str(signature_enc.decode("utf-8")), str(public_key_hashed), "0", str(nonce)))  # mining reward tx
							app_log.warning("Block to send: {}".format(block_send))

						global peer_dict
						peer_dict = {}
						with open("peers.txt") as f:
							for line in f:
								line = re.sub("[\)\(\:\\n\'\s]", "", line)
								peer_dict[line.split(",")[0]] = line.split(",")[1]

							for k, v in peer_dict.items():
								peer_ip = k
								# app_log.info(HOST)
								peer_port = int(v)
								# app_log.info(PORT)
								# connect to all nodes

								try:
									s = socks.socksocket()
									s.settimeout(0.3)
									if tor_conf == 1:
										s.setproxy(socks.PROXY_TYPE_SOCKS5, "127.0.0.1", 9050)
									s.connect((peer_ip, int(peer_port)))  # connect to node in peerlist
									app_log.warning("Connected")

									app_log.warning("Miner: Proceeding to submit mined block")

									connections.send(s, "block", 10)
									connections.send(s, block_send, 10)

									app_log.warning("Miner: Block submitted to {}".format(peer_ip))
								except Exception as e:
									app_log.warning("Miner: Could not submit block to {} because {}".format(peer_ip, e))
									pass

					if diff < mdiff:
						diff_shares = diff
					else:
						diff_shares = mdiff
						
					shares = sqlite3.connect('shares.db')
					shares.text_factory = str
					s = shares.cursor()

					# protect against used share resubmission
					execute_param(s, ("SELECT nonce FROM nonces WHERE nonce = ?"), (nonce,))

					try:
						result = s.fetchone()[0]
						app_log.warning("Miner trying to reuse a share, ignored")
					except:
						# protect against used share resubmission
						mining_condition = bin_convert_orig(db_block_hash)[0:diff_shares] #floor set by pool
						if mining_condition in mining_hash:
							app_log.warning("Difficulty requirement satisfied for saving shares \n")

							execute_param(s, ("INSERT INTO nonces VALUES (?)"), (nonce,))
							commit(shares)

							timestamp = '%.2f' % time.time()

							s.execute("INSERT INTO shares VALUES (?,?,?,?,?,?)", (str(miner_address), str(1), timestamp, "0", str(mrate), wname))
							shares.commit()

						else:
							app_log.warning("Difficulty requirement not satisfied for anything \n")

					s.close()
	
				#elif data == "startup":  # sends the miner the pool address
				
					#connections.send(self.request, address, 10)
					#print("Start package sent to {}".format(peer_ip))
			self.request.close()
		except Exception as e:
			pass
	app_log.warning("Starting up...")

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
	pass

if __name__ == "__main__":

	background_thread = threading.Thread(target=paydb)
	background_thread.daemon = True
	background_thread.start()
	
	worker_thread = threading.Thread(target=worker)
	worker_thread.daemon = True
	worker_thread.start()
	app_log.warning("Starting up background tasks....")
	time.sleep(10)

	try:
		pool_port = int(sys.argv[1])
	except Exception as e:
		pool_port = 8525

	HOST, PORT = "0.0.0.0", pool_port
	
	# Create the server thread handler, binding to localhost on port above
	server = ThreadedTCPServer((HOST, PORT), MyTCPHandler)
	ip, port = server.server_address
	
	server_thread = threading.Thread(target=server.serve_forever)
	
	server_thread.daemon = True
	server_thread.start()
	server_thread.join()
	server.shutdown()
	server.server_close()
	
sys.exit()
