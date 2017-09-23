import sqlite3, time, keys
from bottle import route, run, static_file

(key, private_key_readable, public_key_readable, public_key_hashed, address) = keys.read() #import keys

# load config

try:
	
	lines = [line.rstrip('\n') for line in open('pool.txt')]
	for line in lines:
		try:
			if "m_timeout=" in line:
				m_timeout = int(line.split('=')[1])
		except Exception as e:
			m_timeout = 5

except Exception as e:
	m_timeout = 5

# load config

@route('/static/<filename>')
def server_static(filename):
    return static_file(filename, root='static/')

@route('/')
def hello():

	conn = sqlite3.connect('static/ledger.db')
	conn.text_factory = str
	c = conn.cursor()

	shares = sqlite3.connect('shares.db')
	shares.text_factory = str
	s = shares.cursor()
	
	oldies = sqlite3.connect('archive.db')
	oldies.text_factory = str
	o = oldies.cursor()

	addresses = []
	for row in s.execute("SELECT * FROM shares"):
		shares_address = row[0]
		shares_value = row[1]
		shares_timestamp = row[2]

		if shares_address not in addresses:
			addresses.append(shares_address)

	total_hash = 0
	worker_count = 0
	output_shares = []	
	output_timestamps = []
	view = []

	view.append('<head class="navbar navbar-inverse navbar-fixed-top" role="banner">\n')
	view.append(' <meta charset="utf-8">')
	view.append('   <meta http-equiv="X-UA-Compatible" content="IE=edge">')
	view.append('   <meta name="viewport" content="width=device-width, initial-scale=1.0">')
	view.append('  <link rel="shortcut icon" href="favicon.ico">')
	view.append('  <title>pool.bismuth.online</title>')
	view.append('<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css" >')
	view.append('  <link rel="stylesheet" href="//netdna.bootstrapcdn.com/font-awesome/4.0.3/css/font-awesome.css" >')
	view.append('<div class="container">')
	view.append('<a class="navbar-brand" href="#">pool.bismuth.online <span id="currency"></span></a>')
	view.append('</div>')
	view.append('<link href="css/style.css" rel="stylesheet">')
	view.append('</head>\n')
	view.append("<body>")

		
	view.append('<div class="container">')
	view.append('<section class="panel panel-default clearfix">')
	view.append('<div class="panel-heading">')
	view.append('<h4>Pool Configuration</h4>')
	view.append('</div>')
	view.append("Welcome to the optipoolware public Bismuth pool")
	view.append("<br>Config details in your miner.txt:")
	view.append("<br>mining_ip=78.28.250.81")
	view.append("<br>miner_address=your mining address")
	view.append("<br>Download miner:https://github.com/maccaspacca/Optipoolware")
	view.append('</div>')
	view.append('</section>')

	view.append('<div class="container">')
	view.append('<div id="node_alerts" class="alert alert-danger hidden"></div>')
	view.append('<div class="alert alert-info hidden">2013-12-13: This is a message to miners on my node telling them something really cool.</div>')
	view.append('<div id="header_content"></div>')
	view.append('<section class="panel panel-default">')
	view.append('<div class="panel-heading">')
	view.append('<h4>Miners Since Last Payout</h4>')
	view.append('</div>')
	view.append('<div class="table table-responsive">')
	view.append('<table id="active_miners" class="table table-hover">')
	view.append('<thead>')
	view.append('<tr>')
	view.append('<th class="text-left">Address</th>')
	view.append('<th class="text-center">Number of shares</th>')
	view.append('<th class="text-center">Current Hashrate</th>')
	view.append('<th class="text-center">Last worker</th>')
	view.append('<th class="text-center">Workers</th>')
	view.append('</tr>')
	view.append('</thead>')

	for x in addresses:
		s.execute("SELECT sum(shares) FROM shares WHERE address = ? AND paid != 1", (x,))
		shares_sum = s.fetchone()[0]
		if shares_sum == None:
			shares_sum = 0
			continue
		output_shares.append(shares_sum)


		s.execute("SELECT timestamp FROM shares WHERE address = ? ORDER BY timestamp ASC LIMIT 1", (x,))
		shares_timestamp = s.fetchone()[0]
		output_timestamps.append(float(shares_timestamp))

		s.execute("SELECT * FROM shares WHERE address = ? ORDER BY timestamp DESC LIMIT 1", (x,))
		shares_last = s.fetchone()
		#mrate = shares_last[4]
		mname = shares_last[7] # last worker
		
		
		s.execute("SELECT DISTINCT name FROM shares WHERE address = ?", (x,))
		shares_names = s.fetchall()
		
		nrate = []
		ncount = []
		for n in shares_names:
			s.execute("SELECT * FROM shares WHERE address = ? AND name = ? ORDER BY timestamp DESC LIMIT 1", (x,n[0]))
			names_last = s.fetchone()
			t1 = time.time()
			t2 = float(names_last[2])
			t3 = (t1 - t2)/60
			if t3 < m_timeout:
				nrate.append(int(names_last[4]))
				ncount.append(int(names_last[6]))
			else:
				nrate.append(0)
				ncount.append(0)
	
		mrate = sum(nrate) # hashrate of address
		wcount = sum(ncount) # worker count
		total_hash = total_hash + mrate
		worker_count = worker_count + wcount
		
		color_cell = "white"

		view.append("<tr bgcolor ={}>".format(color_cell))
		view.append("<td>{}</td>".format(x))
		view.append("<td class='text-center'>{}</td>".format(shares_sum))
		view.append("<td class='text-center'>{} kh/s</td>".format(str(mrate)))
		view.append("<td class='text-center'>{}</td>".format(mname))
		view.append("<td class='text-center'>{}</td>".format(str(wcount)))
		view.append("<tr>")

	try:
		shares_total = sum(output_shares)
	except:
		shares_total = 0

	view.append("</table>")
	view.append('</div>')
	view.append('</div>')
	view.append('</section>')

	view.append('<div class="container">')
	view.append('<section class="panel panel-default clearfix">')
	view.append('<div class="panel-heading">')
	view.append('<h4>Block and Pool Stats for this round</h4>')
	view.append('</div>')

	try:
		block_threshold = min(output_timestamps)
	except:
		block_threshold = time.time()

	view.append("<table class='table table-responsive'>")
	reward_list = []
	for row in c.execute("SELECT * FROM transactions WHERE address = ? AND CAST(timestamp AS INTEGER) >= ? AND reward != 0", (address,)+(block_threshold,)):
		view.append("<td>{}</td>".format(row[0]))
		view.append("<td>{}</td>".format(row[9]))
		view.append("<tr>")
		reward_list.append(float(row[9]))
	
	view.append('</div>')
	

	view.append("<th width='50%'>Shares total</th>")
	view.append("<td class='text-left'>{}</td>".format(shares_total))
	view.append("<tr>")

	reward_total = sum(reward_list)

	view.append("<th width='50%'>Reward per share</th>")
	try:
		reward_per_share = reward_total/shares_total
	except:
		reward_per_share = 0

	view.append("<td class='text-left'>{}</td>".format(reward_per_share))
	view.append("<tr>")

	view.append("<th width='50%'>Mined rewards for this round</th>")
	view.append("<td class='text-left'>{}</td>".format(reward_total))
	view.append("<tr>")
	
	view.append("<th width='50%'>Est pool hashrate (mh/s)</th>")
	view.append("<td class='text-left'>{}</td>".format('%.2f' % (total_hash/1000)))
	view.append("<tr>")
	
	view.append("<th width='50%'>Worker Count</th>")
	view.append("<td class='text-left'>{}</td>".format(str(worker_count)))
	view.append("<tr>")

	view.append("</table>")
	view.append('</div>')
	view.append('</section>')

	
	
	# payout view
	view.append('<div class="container">')
	view.append('<section class="panel panel-default clearfix">')
	view.append('<div class="panel-heading">')
	view.append('<h4>Pending payouts</h4>')
	view.append('</div>')
	view.append('<div class="table table-responsive">')
	view.append('<table id="pending_payouts" class="table table-hover">')
	view.append('<thead>')
	view.append('<tr>')
	view.append("<th>Address</th>")
	view.append("<th>Bismuth reward</th>")
	view.append('</tr>')
	view.append('</thead>')
	view.append("<tr>")

	for x, y in zip(addresses, output_shares):

		try:
			claim = y*reward_per_share
		except:
			claim = 0

		view.append("<td>{}</td>".format(x))
		view.append("<td>{}</td>".format('%.8f' %(claim)))
		view.append("<tr>")
	# payout view
	view.append("</table>")
	view.append('</div>')
	view.append('</div>')
	view.append('</section>')
	
	
	view.append('<div class="container">')
	view.append('<div id="node_alerts" class="alert alert-danger hidden"></div>')
	view.append('<div class="alert alert-info hidden">2013-12-13: This is a message to miners on my node telling them something really cool.</div>')
	view.append('<div id="header_content"></div>')
	view.append('<section class="panel panel-default">')
	view.append('<div class="panel-heading">')
	view.append('<h4>Previous payouts</h4>')
	view.append('</div>')
	view.append('<div class="table table-responsive">')
	view.append('<table id="previous_payouts" class="table table-hover">')
	view.append('<thead>')
	view.append('<tr>')
	view.append('<th class="text-left">Address</th>')
	view.append('<th class="text-right">Bismuth reward</th>')
	view.append('<th class="text-right">Block height</th>')
	view.append('<th class="text-right">Time</th>')
	view.append('</tr>')
	view.append('</thead>')

	o.execute("SELECT DISTINCT address FROM shares")
	add_num = o.fetchall()
	acount = str(len(add_num))
	
	for row in c.execute("SELECT * FROM transactions WHERE address = ? and openfield = ? ORDER BY timestamp DESC LIMIT ?",(address,)+("pool",)+(acount,)):
		view.append("<td>{}</td>".format(row[3]))
		view.append("<td class='text-right'>{}</td>".format(row[4]))
		view.append("<td class='text-right'>{}</td>".format(row[0]))
		view.append("<td class='text-right'>{}</td>".format(time.strftime("%Y/%m/%d,%H:%M:%S", time.gmtime(float(row[1])))))
		view.append("<tr>")

	view.append("</table>")
	view.append('</div>')
	view.append('</div>')
	view.append('</section>')

	view.append("</body>")

	conn.close()
	shares.close()
	oldies.close()

	return ''.join(view)

run(host='0.0.0.0', port=9080, debug=True)
