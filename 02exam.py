import configparser
import logging
from web3 import Web3  # 导入Web3库，用于与以太坊兼容区块链交互
from eth_account import Account  # 导入Account库，用于创建和管理以太坊账户

# 配置日志
logging.basicConfig(filename='arb_log.txt',level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 读取配置文件
config = configparser.ConfigParser()
config.read('config.ini')

class AccountManager:
    """
    账户管理类，负责创建新账户。
    """
    @staticmethod
    def create_address():
        account = Account.create()  # 创建一个新的以太坊账户
        private_key = account.key.hex()  # 获取账户的私钥，转换为十六进制字符串
        address = account.address  # 获取账户的地址
        print(f"新地址: {address}")
        print(f"私钥: {private_key}")
        logging.info(f"新地址: {address}")
        logging.info(f"私钥: {private_key}")
        return address, private_key

class ArbitrumClient:
    """
    Arbitrum 网络客户端，封装 ETH 及 ERC-20 相关操作。
    """
    def __init__(self):
        rpc_url = config['DEFAULT']['RPC_URL']
        chain_id = int(config['DEFAULT']['CHAIN_ID'])
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))  # 创建Web3实例
        self.chain_id = chain_id
        if self.w3.is_connected():
            print("已成功连接到 Arbitrum One 网络。")
            logging.info("已成功连接到 Arbitrum One 网络。")
        else:
            print("无法连接到 Arbitrum One 网络，请检查网络配置。")
            logging.error("无法连接到 Arbitrum One 网络，请检查网络配置。")
        # ERC-20 代币合约的ABI
        self.erc20_abi = [
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function"
            },
            {
                "constant": False,
                "inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}],
                "name": "transfer",
                "outputs": [{"name": "", "type": "bool"}],
                "payable": False,
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]

    def get_eth_balance(self, address):
        balance = self.w3.eth.get_balance(address)  # 获取指定地址的ETH余额，单位为wei
        balance_eth = self.w3.from_wei(balance, 'ether')  # 将wei转换为ether
        print(f"地址 {address} 的 ARB ETH 余额: {balance_eth} ETH")
        logging.info(f"地址 {address} 的 ARB ETH 余额: {balance_eth} ETH")
        return balance_eth

    def send_eth(self, sender_private_key, receiver_address, amount_eth):
        sender_account = Account.from_key(sender_private_key)  # 从私钥创建账户对象
        sender_address = sender_account.address  # 获取发送方地址
        gas_price = self.w3.eth.gas_price  # 获取当前的gas价格
        nonce = self.w3.eth.get_transaction_count(sender_address)  # 获取发送方的交易计数
        amount_wei = self.w3.to_wei(amount_eth, 'ether')  # 将ETH金额转换为wei
        checksum_receiver = Web3.to_checksum_address(receiver_address)  # 校验和格式
        tx = {
            'chainId': self.chain_id,
            'nonce': nonce,
            'to': checksum_receiver,
            'value': amount_wei,
            'gas': 30000,
            'gasPrice': gas_price
        }
        signed_tx = sender_account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"ARB ETH 转账交易哈希: {tx_hash.hex()}")
        logging.info(f"ARB ETH 转账交易哈希: {tx_hash.hex()}")
        return tx_receipt

    def get_erc20_balance(self, contract_address, address):
        checksum_address = Web3.to_checksum_address(address)
        checksum_contract = Web3.to_checksum_address(contract_address)
        contract = self.w3.eth.contract(address=checksum_contract, abi=self.erc20_abi)
        decimals = contract.functions.decimals().call()
        raw_balance = contract.functions.balanceOf(checksum_address).call()
        balance = raw_balance / (10 ** decimals)
        print(f"地址 {address} 的 ERC-20 代币余额: {raw_balance} (原始值)")
        print(f"地址 {address} 的 ERC-20 代币余额: {balance} (转换后)")
        logging.info(f"地址 {address} 的 ERC-20 代币余额: {raw_balance} (原始值)")
        logging.info(f"地址 {address} 的 ERC-20 代币余额: {balance} (转换后)")
        return balance

    def send_erc20_token(self, sender_private_key, receiver_address, contract_address, amount_decimal):
        sender_account = Account.from_key(sender_private_key)
        sender_address = sender_account.address
        checksum_receiver = Web3.to_checksum_address(receiver_address)
        checksum_contract = Web3.to_checksum_address(contract_address)
        contract = self.w3.eth.contract(address=checksum_contract, abi=self.erc20_abi)
        decimals = contract.functions.decimals().call()
        amount_raw = int(amount_decimal * (10 ** decimals))
        print(f"转账金额: {amount_decimal} (人类可读值)")
        print(f"转账金额: {amount_raw} (合约原始值)")
        logging.info(f"转账金额: {amount_decimal} (人类可读值)")
        logging.info(f"转账金额: {amount_raw} (合约原始值)")
        nonce = self.w3.eth.get_transaction_count(sender_address)
        gas_price = self.w3.eth.gas_price
        tx = contract.functions.transfer(checksum_receiver, amount_raw).build_transaction({
            'chainId': self.chain_id,
            'gas': 200000,
            'gasPrice': gas_price,
            'nonce': nonce,
        })
        signed_tx = sender_account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"ERC-20 代币转账交易哈希: {tx_hash.hex()}")
        logging.info(f"ERC-20 代币转账交易哈希: {tx_hash.hex()}")
        return tx_receipt

if __name__ == "__main__":
    # 创建新地址
    # new_address, new_private_key = AccountManager.create_address()

    # 示例地址，用于测试查询余额和发送代币
    test_address = config['ACCOUNT']['TEST_ADDRESS']
    test_private_key = config['ACCOUNT']['TEST_PRIVATE_KEY']
    receiver_address = config['ACCOUNT']['RECEIVER_ADDRESS']
    erc20_contract_address = config['ACCOUNT']['ERC20_CONTRACT_ADDRESS']

    client = ArbitrumClient()

    # client.get_eth_balance(test_address)  # 查询 ARB ETH 余额
    # client.send_eth(test_private_key, receiver_address, 0.00001)  # 发送 ARB ETH
    # client.get_erc20_balance(erc20_contract_address, test_address)  # 查询 ERC-20 代币余额
    # client.send_erc20_token(test_private_key, receiver_address, erc20_contract_address, 0.01)  # 发送 ERC-20 代币
    