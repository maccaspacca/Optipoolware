Please note: Version 0.1 and 0.2 are NOT compatible with each other

Known issue: Optipoolware will not stop execution with normal ctr-c in windows - use alt-f4 instead

# Changes from version 0.1

TCP server from pool now multithreaded

Background worker task gets network difficulty and blockhash from ledger

autopayout (untested due to lack of block finds)

Miner address check (56 hex characters, alphanumeric)

Static pool difficulty configured by pool.txt

Network diff rounded up using math.ceil

Mining worker name support

Miner hashrate recorded for later web presentation

Returned nonce submitted against actual blockhash mined

Optihash is updated to match new poolware

Pool fee support

Minimum payout can be adjusted

Pool port can be changed by passing arguement at startup

# optipoolware.py version 0.2

This needs to be placed in the Bismuth folder.

It uses a new custom database that has the same name as the poolware_dappie.py database but has additional table information so don't confuse the two.

node.py needs to be running.

Port 8525 needs to open in the default setting or you can change the port by typing the port number as an arguement on startup
If you change the port please make sure you let your miners know so they can change their settings !!

The pool share difficulty is set in pool.txt and is static - no percentage etc.

Optipoolware.py records hash rate and worker name information
Although poolware_explorer.py script can be used with this application you may wish to customise this to present hash and worker information.

A custom version of poolware_explorer is planned but I cannot tell you when I will be able to complete this.

Autopayout runs every hour - this has not been fully tested. The minimum payout can be set in pool.txt

Pool fee can be set as a percentage in pool.txt e.g. for 5% fee just enter 5 in the appropriate line

Also a fee for an alternate address (dev, charity, your friend) can be set in pool.txt (alt_fee)

Alt_add is the alternate address suggested above.

pool.txt

mine_diff= pool share difficulty

min_payout= minimum payout for autopayout function

pool_fee= pool fee percentage

alt_fee= alternative address fee

alt_add= alternative address to send the alt_fee to

worker_time= how often the pool checks diff and blockhash to be mined in seconds

m_timeout= if a miner does not send a share within this many minutes the hashrate will be reduced / set to zero 

# optihash.py

This is the stand alone to be used against optipoolware.py only.
It has no dependency on node.py and relies only on connections.py and picklemagic.py which have been copied as is from the Bismuth repo
miner.txt contains the information needed to mine against the pool

port=8525 or port presented by the pool

mining_ip= ip address of the pool

mining_threads= number of mining threads to be used by the miner

miner_address= miners bismuth address

nonce_time= time in seconds you wish optihash to mine between getting new work from the pool

max_diff= the maximum difficulty you wish you miner to work at

miner_name= Base name of each worker, this name will be appended with the thread number to give a name for each worker

# How it Works

The miner starts and connects to pool ip
It requests the block hash, diff and pool address to find from the pool
It then hashes as normal using the pool address for the mining hash
Once a nonce is found at the required difficulty it is timestamped and sent to the pool togther with the miners address for processing
The pool receives the nonce and if it meets the network difficulty, validates it and then processes the mempool, creates and signs the transaction block
The block is then transmitted to all nodes from the pool.

# Filelist

Place in and run from bismuth folder

optipoolware.py, pool.txt

Place and run from any suitable folder on miner - node is not needed (but a bismuth address is!)

optihash.py, miner.txt, connections.py, picklemagic.py
