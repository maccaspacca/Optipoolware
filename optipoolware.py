import socketserver, connections, time, options, log, sqlite3, socks, hashlib, random, re, keys, base64, sys, os
import multiprocessing
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA
from Crypto import Random
from multiprocessing import Process
(port, genesis_conf, verify_conf, version_conf, thread_limit_conf, rebuild_db_conf, debug_conf, purge_conf, pause_conf, ledger_path_conf, hyperblocks_conf, warning_list_limit_conf, tor_conf, debug_level_conf, allowed, mining_ip_conf, sync_conf, mining_threads_conf, diff_recalc_conf, pool_conf, pool_address, ram_conf, pool_percentage_conf, node_ip_conf) = options.read()
(key, private_key_readable, public_key_readable, public_key_hashed, address) = keys.read() #import keys
app_log = log.log("pool.log",debug_level_conf)

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

def payout():
	shares = sqlite3.connect('shares.db')
	shares.text_factory = str
	s = shares.cursor()

	conn = sqlite3.connect('static/ledger.db')
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

	shares_total = sum(output_shares)

	try:
		reward_per_share = reward_total / shares_total
	except:
		reward_per_share = 0

	# calculate payouts
	payout_threshold = 1
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


def diffget(s):
	connections.send(s, "diffget", 10)
	diff = (connections.receive(s, 10))
	print(diff)
	diff = int(diff[1])
	return diff

def bin_convert(string):
	return ''.join(bin_format_dict[x] for x in string)

def bin_convert_orig(string):
	return ''.join(format(ord(x), '8b').replace(' ', '0') for x in string)

def getablock():

	# sock
	s2 = socks.socksocket()
	if tor_conf == 1:
		s2.setproxy(socks.PROXY_TYPE_SOCKS5, "127.0.0.1", 9050)
	s2.connect(("127.0.0.1", int(port)))  # connect to local node,
	# sock
	
	# get last block
	connections.send(s2, "blocklast", 10)
	blocklast = connections.receive(s2, 10)[7]
	s2.close()
	
	return blocklast
	
if not os.path.exists('shares.db'):
	# create empty mempool
	shares = sqlite3.connect('shares.db')
	shares.text_factory = str
	s = shares.cursor()
	execute(s, "CREATE TABLE IF NOT EXISTS shares (address, shares, timestamp, paid)")
	execute(s, "CREATE TABLE IF NOT EXISTS nonces (nonce)") #for used hash storage
	app_log.warning("Created shares file")
	s.close()
	# create empty mempool

def paydb():

	if checkdb():
		payout()
	
	while True:
		time.sleep(3600)
		print("Payout check....")
		if checkdb():
			payout()

diff_percentage = pool_percentage_conf

class MyTCPHandler(socketserver.BaseRequestHandler):

	def handle(self):
		from Crypto.PublicKey import RSA
		key = RSA.importKey(private_key_readable)

		peer_ip = self.request.getpeername()[0]

		data = connections.receive(self.request, 10)
		
		app_log.warning("Received: {} from {}".format(data, peer_ip))  # will add custom ports later

		if data == "getwork":  # sends the miner the blockhash and mining diff for shares
		
			new_hash = getablock()
			# get last block
		
			try:
				mdiff = int(sys.argv[1])
			except Exception as e:
				# sock
				s3 = socks.socksocket()
				s3.connect(("127.0.0.1", int(port)))  # connect to local node,
				# sock
				diff = int(diffget(s3))
				s3.close()
				xdiff = percentage(diff_percentage, diff)
				if xdiff < 60:
					mdiff = 60
				else:
					mdiff = xdiff
		
			#print(mdiff)

			work_send = []
			work_send.append((new_hash, mdiff, address))
			#print(work_send)
			print("Work package sent.... {}".format(str(new_hash)))

			connections.send(self.request, work_send, 10)

		elif data == "block":  # from miner to node

			# sock
			s1 = socks.socksocket()
			if tor_conf == 1:
				s1.setproxy(socks.PROXY_TYPE_SOCKS5, "127.0.0.1", 9050)
			s1.connect(("127.0.0.1", int(port)))  # connect to local node,
			# sock


			# receive nonce from miner
			miner_address = connections.receive(self.request, 10)
			app_log.warning("Received a solution from miner {} ({})".format(peer_ip,miner_address))

			block_nonce = connections.receive(self.request, 10)
			nonce = (block_nonce[-1][1])
			block_timestamp = (block_nonce[-1][0])
			sdiffs = (block_nonce[-1][2]) # claimed difficulty
			mine_diff = int((block_nonce[-1][3])) # required difficulty#
			mine_hash = ((block_nonce[-1][4])) # block hash claimed

			app_log.warning("Mined nonce details: {}".format(block_nonce))
			app_log.warning("Claimed difficulty: {}".format(int(sdiffs)))
			app_log.warning("Claimed hash: {}".format(mine_hash))

			# check difficulty
			app_log.warning("Asking node for difficulty")
			diff = int(diffget(s1))
			# diff = 60 # for testing
			app_log.warning("Network difficulty: {}".format(diff))
			# check difficulty

			app_log.warning("Asking node for last block")

			# get last block
			connections.send(s1, "blocklast", 10)
			blocklast = connections.receive(s1, 10)
			db_block_hash = blocklast[7]
			# get last block

			app_log.warning("Last Hash: {}".format(db_block_hash))

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

			if diff < mine_diff:
				diff_shares = diff
			else:
				diff_shares = mine_diff
	
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

					s.execute("INSERT INTO shares VALUES (?,?,?,?)", (str(miner_address), str(1), timestamp, "0"))
					shares.commit()

				else:
					app_log.warning("Difficulty requirement not satisfied for anything \n")

			#s.close()
			s1.close()

		#elif data == "startup":  # sends the miner the pool address
		
			#connections.send(self.request, address, 10)
			#print("Start package sent to {}".format(peer_ip))

app_log.warning("Starting up...")

if __name__ == "__main__":
	multiprocessing.freeze_support()
	background_thread = Process(target=paydb)
	background_thread.daemon = True
	background_thread.start()
	
	HOST, PORT = "0.0.0.0", 8525

	# Create the server, binding to localhost on port 9999
	server = socketserver.TCPServer((HOST, PORT), MyTCPHandler)

	# Activate the server; this will keep running until you
	# interrupt the program with Ctrl-C
	server.serve_forever()