package params

var (
	// consensus layer
	consensus 			= "eth" 			// blockchain consensus, PoS Gasper in this case
	// network layer
    block_size 			= 30000000 			// gas upperbound in one block, in gas
    block_interval 		= 12 				// time interval that generates a block, in second
    mempool 			= "public_pool"		// where tx wait to get packaged
	// application layer
    vm 					= "eth" 			// virtual machine that executes codes
    dapp 				= "top10" 			// dapps that run in the vm
    tx 					= "historical" 		// tx that interact with the dapps
    tx_injection_speed 	= 1000 				// in tx/s  
	// data layer
	tx_path 			= "./tx/10000000-10010000.csv" 	// inject tx from this path
    log_path 			= "./log/" 			// save log to this path
)



