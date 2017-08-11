# optipoolware.py

This needs to be placed in the Bismuth folder and is a drop in replacement for poolware_dappie.py
It uses the same database as poolware_dappie.py so previous shares can be preserved
node.py needs to be running.
Port 8525 needs to open in the default setting or you can change the port in the node config.txt.
If you change the port please make sure you let your miners know so they can change their settings !!

The pool share difficulty will pick the percentage up from config.txt but this can be overridden by passing a pool share diff as an argument on start up.
e.g. python optipoolware.py 70

The poolware_explorer.py script can be used with this application in order to display statistics

# optihash.py

This is the stand alone to be used against optipoolware.py only.
It has no dependency on node.py and relies only on connections.py and picklemagic.py which have been copied as is from the Bismuth repo
miner.txt contains the information needed to mine against the pool

port=8525 or port presented by the pool
mining_ip=ip address of the pool
mining_threads=number of mining threads to be used by the miner
tor=0
miner_address=miners bismuth address
nonce_time=time in seconds you wish optihash to mine between getting new work from the pool
max_diff=<the maximum difficulty you wish you miner to work at>

# How it Works

The miner starts and connects to pool ip
It requests the block hash, diff and pool address to find from the pool
It then hashes as normal using the pool address for the mining hash
Once a nonce is found at the required difficulty it is timestamped and sent to the pool togther with the miners address for processing
The pool receives the nonce, validates it and then processes the mempool, creates and signs the transaction block
The block is then transmitted to all nodes from the pool.

# Filelist

Place in and run from bismuth folder

optipoolware.py

Place and run from any suitable folder on miner - node is not needed (but a bismuth address is!)

optihash.py
miner.txt
connections.py
picklemagic.py
